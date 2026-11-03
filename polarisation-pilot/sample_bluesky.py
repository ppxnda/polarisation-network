"""
Pilot sampler: a topic-stratified sample of English Bluesky posts for the codebook v0 pilot.

What it does
  1. For each topic stratum, runs several search queries over a fixed date window and builds a candidate pool.
  2. Filters (length, language, no bare links), de-duplicates, and pseudonymises authors.
  3. Draws a fixed number per stratum, half replies and half top-level posts where possible.
  4. Fetches parent text for replies, so coders see what a reply is answering.

Outputs (in --out, default ./data)
  pilot_raw.jsonl     full records incl. DIDs and engagement counts. KEEP PRIVATE (ethics).
  pilot_sample.csv    what coders and the LLM see: post_id, stratum, is_reply, text, parent_text.

IMPORTANT LIMITATION
  Keyword search selects on topic words, so this sample is fine for testing the codebook (V1)
  but must NOT be used to estimate prevalence (D1). D1 needs a random sample from Jetstream/firehose.

Usage
  set BSKY_HANDLE=yourname.bsky.social
  set BSKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx     (Settings > Privacy and security > App passwords)
  python sample_bluesky.py --since 2026-10-01 --until 2026-11-01 --n 100 --seed 7
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import time
from pathlib import Path

from atproto import Client

# ---------------------------------------------------------------------------
# Strata. Edit freely: keys are stratum names, values are search queries.
# Balanced across political and non-political topics (design doc, section 4).
# Queries are deliberately broad nouns, not outrage words, to avoid selecting on the outcome.
# ---------------------------------------------------------------------------
STRATA: dict[str, list[str]] = {
    "politics_uk": ["Starmer", "Reform UK", "Farage", "Labour government", "Badenoch"],
    "politics_us": ["Trump", "Democrats", "Republicans", "Congress"],
    "immigration": ["immigration", "asylum seekers", "migrants", "small boats"],
    "religion": ["Muslims", "Islam", "mosque", "Christians"],
    "gender_sexuality": ["trans people", "feminism", "gender critical", "LGBT"],
    "crime_justice": ["sentenced", "police officer", "prison", "court ruling"],
    "celebrity_media": ["apology statement", "cancelled", "influencer", "BBC presenter"],
    "sport": ["referee", "VAR", "Premier League", "manager sacked"],
    "everyday_life": ["my landlord", "customer service", "my neighbour", "my boss"],
}

MIN_CHARS = 25
URL_ONLY = re.compile(r"^\s*(https?://\S+\s*)+$")


def pseudonym(did: str, salt: str) -> str:
    return hashlib.sha256((salt + did).encode()).hexdigest()[:12]


def search_pool(client: Client, query: str, since: str, until: str, per_query: int) -> list:
    """Page through searchPosts until per_query posts or results run out."""
    posts, cursor = [], None
    while len(posts) < per_query:
        params = {"q": query, "lang": "en", "limit": 100, "sort": "latest",
                  "since": f"{since}T00:00:00Z", "until": f"{until}T00:00:00Z"}
        if cursor:
            params["cursor"] = cursor
        try:
            resp = client.app.bsky.feed.search_posts(params=params)
        except Exception as e:  # rate limits or transient errors
            print(f"  ! search failed for {query!r}: {e}; backing off")
            time.sleep(10)
            break
        posts.extend(resp.posts)
        cursor = resp.cursor
        if not cursor or not resp.posts:
            break
        time.sleep(0.5)
    return posts[:per_query]


def keep(post) -> bool:
    text = (post.record.text or "").strip()
    if len(text) < MIN_CHARS or URL_ONLY.match(text):
        return False
    langs = getattr(post.record, "langs", None) or []
    return (not langs) or ("en" in langs)


def fetch_parents(client: Client, uris: list[str]) -> dict[str, str]:
    out = {}
    for i in range(0, len(uris), 25):
        chunk = uris[i:i + 25]
        try:
            resp = client.get_posts(uris=chunk)
            for p in resp.posts:
                out[p.uri] = (p.record.text or "").strip()
        except Exception as e:
            print(f"  ! parent fetch failed: {e}")
        time.sleep(0.3)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD (inclusive)")
    ap.add_argument("--until", required=True, help="YYYY-MM-DD (exclusive)")
    ap.add_argument("--n", type=int, default=100, help="total sample size")
    ap.add_argument("--per-query", type=int, default=150, help="candidates pulled per query")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    handle, pw = os.environ.get("BSKY_HANDLE"), os.environ.get("BSKY_APP_PASSWORD")
    if not handle or not pw:
        raise SystemExit("Set BSKY_HANDLE and BSKY_APP_PASSWORD (an app password, not your main password).")
    salt = os.environ.get("PSEUDONYM_SALT", "change-me-and-keep-secret")

    client = Client()
    client.login(handle, pw)
    rng = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    per_stratum = args.n // len(STRATA)
    remainder = args.n - per_stratum * len(STRATA)
    seen: set[str] = set()
    chosen: list[dict] = []

    for s_i, (stratum, queries) in enumerate(STRATA.items()):
        target = per_stratum + (1 if s_i < remainder else 0)
        pool = []
        for q in queries:
            print(f"[{stratum}] searching {q!r}")
            for p in search_pool(client, q, args.since, args.until, args.per_query):
                if p.uri in seen or not keep(p):
                    continue
                seen.add(p.uri)
                pool.append((q, p))
        replies = [x for x in pool if x[1].record.reply]
        tops = [x for x in pool if not x[1].record.reply]
        rng.shuffle(replies)
        rng.shuffle(tops)
        half = target // 2
        pick = replies[:half] + tops[:target - half]
        if len(pick) < target:  # top up from whichever side has spares
            spare = replies[half:] + tops[target - half:]
            pick += spare[: target - len(pick)]
        print(f"[{stratum}] pool={len(pool)} replies={len(replies)} top={len(tops)} -> picked {len(pick)}")
        for q, p in pick:
            chosen.append({
                "stratum": stratum,
                "query": q,
                "uri": p.uri,
                "cid": p.cid,
                "author_did": p.author.did,
                "author_pseudonym": pseudonym(p.author.did, salt),
                "created_at": p.record.created_at,
                "is_reply": bool(p.record.reply),
                "parent_uri": p.record.reply.parent.uri if p.record.reply else None,
                "text": p.record.text.strip(),
                "like_count": p.like_count, "repost_count": p.repost_count,
                "reply_count": p.reply_count, "quote_count": p.quote_count,
            })

    parents = fetch_parents(client, [r["parent_uri"] for r in chosen if r["parent_uri"]])
    for r in chosen:
        r["parent_text"] = parents.get(r["parent_uri"], "") if r["parent_uri"] else ""

    rng.shuffle(chosen)  # so coders don't see strata in blocks; IDs assigned after shuffling
    for i, r in enumerate(chosen, 1):
        r["post_id"] = f"p{i:04d}"
    with open(out / "pilot_raw.jsonl", "w", encoding="utf-8") as f:
        for r in chosen:
            f.write(json.dumps({"post_id": r["post_id"], **r}, ensure_ascii=False) + "\n")
    with open(out / "pilot_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["post_id", "stratum", "is_reply", "text", "parent_text"])
        w.writeheader()
        for r in chosen:
            w.writerow({k: r[k] for k in w.fieldnames})
    print(f"\nWrote {len(chosen)} posts to {out}/pilot_sample.csv (+ private pilot_raw.jsonl)")


if __name__ == "__main__":
    main()
