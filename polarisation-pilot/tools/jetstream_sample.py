"""
Random sampler: an unselected sample of English Bluesky posts from Jetstream, for prevalence estimates (D1).

Why this exists
  sample_bluesky.py selects on topic keywords, so it is fine for testing the codebook (V1) but biased for
  prevalence. Jetstream relays every public post on the network, so keeping each English post with a fixed
  probability p gives an equal-probability (Bernoulli) sample of English posts IN THE TIME WINDOW YOU RAN.
  One window is a cluster sample in time: for D1, run many short windows spread across days and hours.

What it does
  1. Connects to a public Jetstream instance, subscribed to app.bsky.feed.post only.
  2. Keeps commit "create" events whose record declares an English language tag (en, en-GB, en-US, ...).
  3. Thins: keeps each eligible post with probability --p (seeded, so runs are reproducible).
  4. Pseudonymises the author DID and the DIDs inside every at:// URI with salted sha256 (same function and
     salt as sample_bluesky.py, so pseudonyms match across datasets). Parent/root/quote links still join.
  5. Reconnects after drops with cursor = last time_us minus --rewind seconds, de-duplicating on URI.
  6. Stops after --max-posts kept posts or --minutes of wall-clock time, or on Ctrl+C (output is flushed).

Outputs (in --out, default ./data)
  jetstream_<start>.jsonl or .parquet   one row per kept post (columns below). KEEP PRIVATE (ethics).
  jetstream_<start>.meta.json           run settings, counts (seen / English / kept), time_us range,
                                        reconnects, and URIs of kept posts deleted during the run (purge these).

Columns
  uri, did, created_at, time_us, text, langs, is_reply, parent_uri, root_uri, quote_uri
  did is the pseudonym. created_at is client-claimed (can be wrong or backdated); time_us is when Jetstream
  saw the event, so use time_us for windows. quote_uri is set only when the embedded record is a post.

Usage (Windows PowerShell)
  $env:PSEUDONYM_SALT="the-same-secret-salt-as-the-pilot"
  python jetstream_sample.py --minutes 2 --max-posts 50                    # smoke test first
  python jetstream_sample.py --minutes 60 --p 0.1 --format parquet --seed 11
  python jetstream_sample.py --minutes 15 --p 0.05 --endpoint wss://jetstream1.us-west.bsky.network/subscribe

Needs: pip install websockets pandas pyarrow
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

POST_NSID = "app.bsky.feed.post"
DEFAULT_ENDPOINT = "wss://jetstream2.us-east.bsky.network/subscribe"
COLUMNS = ["uri", "did", "created_at", "time_us", "text", "langs", "is_reply",
           "parent_uri", "root_uri", "quote_uri"]
AT_URI = re.compile(r"^at://([^/]+)(/.*)?$")


# ---------------------------------------------------------------------------- pseudonymisation
def pseudonym(did: str, salt: str, length: int = 12) -> str:
    """Same construction as sample_bluesky.py: sha256(salt + did), truncated hex."""
    return hashlib.sha256((salt + did).encode()).hexdigest()[:length]


def pseudo_uri(uri: str | None, salt: str, length: int = 12) -> str | None:
    """at://did:plc:abc/app.bsky.feed.post/rkey -> at://<pseudonym>/app.bsky.feed.post/rkey."""
    if not uri:
        return None
    m = AT_URI.match(uri)
    if not m:
        return uri
    return f"at://{pseudonym(m.group(1), salt, length)}{m.group(2) or ''}"


# ---------------------------------------------------------------------------- message parsing
def normalise(msg: dict) -> dict | None:
    """Return a v1-shaped event {did, time_us, kind, commit:{operation, collection, rkey, record, cid}}.

    v1 (jetstream1/2.*.bsky.network, documented in github.com/bluesky-social/jetstream) is used as is.
    v2 (jetstream.*.bsky.network, bsky.network/docs/jetstream) wraps events in {"$type": "message",
    "payload": {...}} with ISO "time" and a "seq"; it is converted here. v2 support follows the one
    documented example only and is untested live.
    """
    if "kind" in msg:
        return msg
    payload = msg.get("payload")
    if not isinstance(payload, dict):
        return None
    ptype = payload.get("$type", "")
    kind = ptype.rsplit("#", 1)[-1] if "#" in ptype else None
    t = payload.get("time")
    time_us = None
    if t:
        try:
            dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
            time_us = int(dt.timestamp() * 1_000_000)
        except ValueError:
            pass
    out = {"did": payload.get("did"), "time_us": time_us, "kind": kind, "seq": payload.get("seq")}
    if kind == "commit":
        out["commit"] = {k: payload.get(k) for k in ("rev", "operation", "collection", "rkey", "record", "cid")}
    return out


def is_english(langs: list | None, lang: str = "en") -> bool:
    if not langs:
        return False
    lang = lang.lower()
    return any(isinstance(x, str) and (x.lower() == lang or x.lower().startswith(lang + "-")) for x in langs)


def quote_target(embed: dict | None) -> str | None:
    """URI of a quoted post, from app.bsky.embed.record or app.bsky.embed.recordWithMedia."""
    if not isinstance(embed, dict):
        return None
    etype = embed.get("$type", "")
    ref = None
    if etype == "app.bsky.embed.record":
        ref = embed.get("record")
    elif etype == "app.bsky.embed.recordWithMedia":
        inner = embed.get("record") or {}
        ref = inner.get("record") if isinstance(inner, dict) else None
    uri = ref.get("uri") if isinstance(ref, dict) else None
    # embed.record can also point at a list, feed generator or starter pack; only posts count as quotes
    if uri and f"/{POST_NSID}/" in uri:
        return uri
    return None


def post_from_event(ev: dict) -> dict | None:
    """Raw (un-pseudonymised) post row for a post-create commit, else None."""
    if not ev or ev.get("kind") != "commit":
        return None
    c = ev.get("commit") or {}
    if c.get("collection") != POST_NSID or c.get("operation") != "create":
        return None
    rec = c.get("record")
    if not isinstance(rec, dict):
        return None
    did, rkey = ev.get("did"), c.get("rkey")
    if not did or not rkey:
        return None
    reply = rec.get("reply") or {}
    parent = (reply.get("parent") or {}).get("uri") if isinstance(reply, dict) else None
    root = (reply.get("root") or {}).get("uri") if isinstance(reply, dict) else None
    return {
        "uri": f"at://{did}/{POST_NSID}/{rkey}",
        "did": did,
        "created_at": rec.get("createdAt"),
        "time_us": ev.get("time_us"),
        "text": rec.get("text") or "",
        "langs": list(rec.get("langs") or []),
        "is_reply": bool(parent),
        "parent_uri": parent,
        "root_uri": root,
        "quote_uri": quote_target(rec.get("embed")),
    }


def deleted_post_uri(ev: dict) -> str | None:
    if not ev or ev.get("kind") != "commit":
        return None
    c = ev.get("commit") or {}
    if c.get("collection") == POST_NSID and c.get("operation") == "delete" and ev.get("did") and c.get("rkey"):
        return f"at://{ev['did']}/{POST_NSID}/{c['rkey']}"
    return None


def pseudonymise_row(row: dict, salt: str, length: int = 12) -> dict:
    out = dict(row)
    out["did"] = pseudonym(row["did"], salt, length)
    for k in ("uri", "parent_uri", "root_uri", "quote_uri"):
        out[k] = pseudo_uri(row.get(k), salt, length)
    return out


# ---------------------------------------------------------------------------- output
class JsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        self.f = open(path, "w", encoding="utf-8")

    def write(self, row: dict) -> None:
        self.f.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.f.flush()

    def close(self) -> None:
        self.f.close()


class ParquetWriter:
    """Buffers rows and writes a row group every `flush_every` rows. A hard kill (not Ctrl+C) loses
    the unclosed file; use JSONL for long unattended runs."""

    def __init__(self, path: Path, flush_every: int = 1000):
        import pyarrow as pa
        import pyarrow.parquet as pq
        self.pa, self.path, self.flush_every, self.buf = pa, path, flush_every, []
        self.schema = pa.schema([
            ("uri", pa.string()), ("did", pa.string()), ("created_at", pa.string()), ("time_us", pa.int64()),
            ("text", pa.string()), ("langs", pa.list_(pa.string())), ("is_reply", pa.bool_()),
            ("parent_uri", pa.string()), ("root_uri", pa.string()), ("quote_uri", pa.string()),
        ])
        self.w = pq.ParquetWriter(str(path), self.schema)

    def write(self, row: dict) -> None:
        self.buf.append(row)
        if len(self.buf) >= self.flush_every:
            self._flush()

    def _flush(self) -> None:
        if self.buf:
            self.w.write_table(self.pa.Table.from_pylist(self.buf, schema=self.schema))
            self.buf = []

    def close(self) -> None:
        self._flush()
        self.w.close()


# ---------------------------------------------------------------------------- sampler
class Sampler:
    """Holds state across reconnects. `offer(event)` decides whether to keep a post."""

    def __init__(self, salt: str, p: float = 1.0, seed: int = 7, lang: str = "en", hash_len: int = 12,
                 dedup_window: int = 200_000):
        if not 0 < p <= 1:
            raise ValueError("p must be in (0, 1]")
        self.salt, self.p, self.lang, self.hash_len = salt, p, lang, hash_len
        self.rng = random.Random(seed)
        # raw URIs of recent posts, for de-duplication across reconnects (in memory only, bounded)
        self.seen_uris: set[str] = set()
        self._seen_order: deque[str] = deque()
        self.dedup_window = dedup_window
        self.kept_uris: set[str] = set()
        self.deleted_kept: list[str] = []
        self.n_events = self.n_posts = self.n_english = self.n_kept = self.n_dupes = 0
        self.first_time_us = self.last_time_us = None
        self.last_seq = None

    def offer(self, raw_msg: dict) -> dict | None:
        ev = normalise(raw_msg)
        if ev is None:
            return None
        self.n_events += 1
        if ev.get("time_us"):
            self.last_time_us = ev["time_us"]
            self.first_time_us = self.first_time_us or ev["time_us"]
        if ev.get("seq") is not None:
            self.last_seq = ev["seq"]
        d = deleted_post_uri(ev)
        if d and d in self.kept_uris:
            self.deleted_kept.append(pseudo_uri(d, self.salt, self.hash_len))
            return None
        row = post_from_event(ev)
        if row is None:
            return None
        if row["uri"] in self.seen_uris:  # replay after reconnect: same decision already made
            self.n_dupes += 1
            return None
        self.seen_uris.add(row["uri"])
        self._seen_order.append(row["uri"])
        if len(self._seen_order) > self.dedup_window:  # replays only reach back --rewind seconds
            self.seen_uris.discard(self._seen_order.popleft())
        self.n_posts += 1
        if not is_english(row["langs"], self.lang):
            return None
        self.n_english += 1
        if self.p < 1 and self.rng.random() >= self.p:
            return None
        self.n_kept += 1
        self.kept_uris.add(row["uri"])
        return pseudonymise_row(row, self.salt, self.hash_len)

    def cursor(self, rewind_s: float, protocol: str = "v1") -> int | None:
        if protocol == "v2" and self.last_seq is not None:
            return int(self.last_seq)  # inclusive; duplicates removed by URI
        if self.last_time_us is None:
            return None
        return int(self.last_time_us - rewind_s * 1_000_000)


def build_url(endpoint: str, protocol: str = "v1", cursor: int | None = None) -> str:
    key = "wantedCollections" if protocol == "v1" else "collections"
    params = [(key, POST_NSID)]
    if cursor is not None:
        params.append(("cursor", str(cursor)))
    return f"{endpoint}?{urlencode(params)}"


def default_connect(url: str):
    from websockets.asyncio.client import connect
    # short close_timeout: on a busy stream the close handshake can stall behind queued frames
    return connect(url, max_size=2 ** 22, open_timeout=20, ping_interval=20, ping_timeout=30, close_timeout=2)


async def collect(sampler: Sampler, writer, *, endpoint: str, protocol: str = "v1", max_posts: int | None = None,
                  minutes: float | None = None, rewind_s: float = 3.0, max_backoff: float = 60.0,
                  connect=default_connect, clock=time.monotonic, sleep=asyncio.sleep, log=print) -> dict:
    """Main loop. Returns run stats. `connect`, `clock` and `sleep` are injectable for tests."""
    start = clock()
    deadline = start + minutes * 60 if minutes else None
    reconnects, backoff, stop_reason = 0, 1.0, None

    def done() -> str | None:
        if max_posts and sampler.n_kept >= max_posts:
            return "max_posts"
        if deadline and clock() >= deadline:
            return "minutes"
        return None

    try:
        while not stop_reason:
            url = build_url(endpoint, protocol, sampler.cursor(rewind_s, protocol))
            try:
                async with connect(url) as ws:
                    log(f"connected: {url}")
                    backoff = 1.0
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except (json.JSONDecodeError, TypeError):
                            continue
                        row = sampler.offer(msg)
                        if row is not None:
                            writer.write(row)
                            if sampler.n_kept % 500 == 0:
                                log(f"  kept {sampler.n_kept} (seen {sampler.n_posts} posts)")
                        stop_reason = done()
                        if stop_reason:
                            break
                    else:
                        raise ConnectionError("server closed the stream")
            except (asyncio.CancelledError, KeyboardInterrupt):
                raise
            except Exception as e:  # drops, timeouts, 5xx on upgrade
                stop_reason = done()
                if stop_reason:
                    break
                reconnects += 1
                log(f"  ! connection lost ({type(e).__name__}: {e}); reconnecting in {backoff:.0f}s "
                    f"with cursor {sampler.cursor(rewind_s, protocol)}")
                await sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                stop_reason = done()
    except (asyncio.CancelledError, KeyboardInterrupt):
        stop_reason = "interrupted"
        log("\nInterrupted: flushing output.")
    finally:
        writer.close()
    return {"stop_reason": stop_reason, "reconnects": reconnects, "elapsed_s": round(clock() - start, 1)}


def write_meta(path: Path, sampler: Sampler, stats: dict, args: argparse.Namespace, data_path: Path) -> None:
    meta = {
        "data_file": data_path.name, "endpoint": args.endpoint, "protocol": args.protocol,
        "p": args.p, "seed": args.seed, "lang": args.lang, "hash_len": args.hash_len,
        "started_utc": args.started_utc, **stats,
        "events_seen": sampler.n_events, "posts_seen": sampler.n_posts, "english_posts_seen": sampler.n_english,
        "kept": sampler.n_kept, "duplicates_skipped": sampler.n_dupes,
        "first_time_us": sampler.first_time_us, "last_time_us": sampler.last_time_us,
        "deleted_during_run": sampler.deleted_kept,
        "note": "Kept/english_posts_seen should be close to p. Purge deleted_during_run before analysis.",
    }
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Jetstream subscribe URL without query string")
    ap.add_argument("--protocol", choices=["v1", "v2"], default="v1",
                    help="v1 = jetstream1/2.* instances (tested shape); v2 = jetstream.* (untested)")
    ap.add_argument("--max-posts", type=int, default=None, help="stop after this many kept posts")
    ap.add_argument("--minutes", type=float, default=None, help="stop after this many minutes")
    ap.add_argument("--p", type=float, default=1.0, help="keep each English post with this probability")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--lang", default="en", help="language tag prefix to keep (default en)")
    ap.add_argument("--rewind", type=float, default=3.0, help="seconds to rewind the cursor on reconnect")
    ap.add_argument("--hash-len", type=int, default=12, help="hex chars of the pseudonym (12 matches the pilot)")
    ap.add_argument("--format", choices=["jsonl", "parquet"], default="jsonl")
    ap.add_argument("--out", default="data")
    args = ap.parse_args(argv)

    if not args.max_posts and not args.minutes:
        sys.exit("Set --max-posts and/or --minutes, so the run has an end.")
    salt = os.environ.get("PSEUDONYM_SALT")
    if not salt:
        sys.exit("Set PSEUDONYM_SALT (use the same secret as the pilot so pseudonyms match).")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    args.started_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stem = "jetstream_" + args.started_utc.replace(":", "").replace("-", "")
    data_path = out / f"{stem}.{args.format}"
    writer = JsonlWriter(data_path) if args.format == "jsonl" else ParquetWriter(data_path)
    sampler = Sampler(salt, p=args.p, seed=args.seed, lang=args.lang, hash_len=args.hash_len)

    try:
        stats = asyncio.run(collect(sampler, writer, endpoint=args.endpoint, protocol=args.protocol,
                                    max_posts=args.max_posts, minutes=args.minutes, rewind_s=args.rewind))
    except KeyboardInterrupt:  # Ctrl+C landing outside the coroutine (common on Windows)
        stats = {"stop_reason": "interrupted", "reconnects": None, "elapsed_s": None}
        try:
            writer.close()
        except Exception:
            pass
    write_meta(out / f"{stem}.meta.json", sampler, stats, args, data_path)
    rate = sampler.n_kept / sampler.n_english if sampler.n_english else 0
    print(f"\nStopped ({stats['stop_reason']}). Kept {sampler.n_kept} of {sampler.n_english} English posts "
          f"({rate:.3f}; p={args.p}) from {sampler.n_posts} posts seen. Wrote {data_path} + .meta.json")


if __name__ == "__main__":
    main()
