"""Offline tests: synthetic Jetstream messages (shapes from the Jetstream README) and fake scorers.

Run:  python -m pytest tests -q
"""
from __future__ import annotations

import asyncio
import io
import json
import sys
import types
import urllib.error
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import jetstream_sample as js  # noqa: E402
import score_toxicity as st  # noqa: E402

SALT = "test-salt"
A, B = "did:plc:aaaaaaaaaaaaaaaaaaaaaaaa", "did:plc:bbbbbbbbbbbbbbbbbbbbbbbb"


# ---------------------------------------------------------------------------- message factories (v1 shape)
def post_event(did=A, rkey="3l3qo2vuowo2b", time_us=1725911162329308, text="hello", langs=("en",),
               reply=None, embed=None, operation="create"):
    rec = {"$type": "app.bsky.feed.post", "text": text, "createdAt": "2026-11-03T10:00:00.000Z"}
    if langs is not None:
        rec["langs"] = list(langs)
    if reply:
        rec["reply"] = reply
    if embed:
        rec["embed"] = embed
    return {"did": did, "time_us": time_us, "kind": "commit",
            "commit": {"rev": "3l3qo2vutsw2b", "operation": operation, "collection": "app.bsky.feed.post",
                       "rkey": rkey, "record": rec, "cid": "bafyreidwaivazkwu67xztlmuobx35hs2lnfh3kolmgfmucldvhd3sgzcqi"}}


def delete_event(did=A, rkey="3l3qo2vuowo2b", time_us=1725911162330000):
    return {"did": did, "time_us": time_us, "kind": "commit",
            "commit": {"rev": "x", "operation": "delete", "collection": "app.bsky.feed.post", "rkey": rkey}}


IDENTITY = {"did": A, "time_us": 1725516665234703, "kind": "identity",
            "identity": {"did": A, "handle": "x.bsky.social", "seq": 1409752997, "time": "2024-09-05T06:11:04.870Z"}}
ACCOUNT = {"did": A, "time_us": 1725516665333808, "kind": "account",
           "account": {"active": True, "did": A, "seq": 1409753013, "time": "2024-09-05T06:11:04.870Z"}}
LIKE = {"did": A, "time_us": 1725911162329308, "kind": "commit",
        "commit": {"rev": "r", "operation": "create", "collection": "app.bsky.feed.like", "rkey": "k",
                   "record": {"$type": "app.bsky.feed.like", "createdAt": "2024-09-09T19:46:02.102Z",
                              "subject": {"cid": "c", "uri": f"at://{B}/app.bsky.feed.post/p"}}}}


# ---------------------------------------------------------------------------- parsing
def test_top_level_post():
    row = js.post_from_event(post_event(text="Top level"))
    assert row["uri"] == f"at://{A}/app.bsky.feed.post/3l3qo2vuowo2b"
    assert row["is_reply"] is False and row["parent_uri"] is None and row["quote_uri"] is None
    assert row["created_at"] == "2026-11-03T10:00:00.000Z" and row["time_us"] == 1725911162329308


def test_reply_and_quote_fields():
    parent, root = f"at://{B}/app.bsky.feed.post/par", f"at://{B}/app.bsky.feed.post/root"
    quoted = f"at://{B}/app.bsky.feed.post/q"
    ev = post_event(reply={"root": {"uri": root, "cid": "c1"}, "parent": {"uri": parent, "cid": "c2"}},
                    embed={"$type": "app.bsky.embed.record", "record": {"uri": quoted, "cid": "c3"}})
    row = js.post_from_event(ev)
    assert row["is_reply"] and row["parent_uri"] == parent and row["root_uri"] == root
    assert row["quote_uri"] == quoted


def test_quote_with_media_and_non_post_embeds():
    quoted = f"at://{B}/app.bsky.feed.post/q"
    rwm = {"$type": "app.bsky.embed.recordWithMedia",
           "record": {"$type": "app.bsky.embed.record", "record": {"uri": quoted, "cid": "c"}},
           "media": {"$type": "app.bsky.embed.images", "images": []}}
    assert js.post_from_event(post_event(embed=rwm))["quote_uri"] == quoted
    feed_embed = {"$type": "app.bsky.embed.record",
                  "record": {"uri": f"at://{B}/app.bsky.feed.generator/f", "cid": "c"}}
    assert js.post_from_event(post_event(embed=feed_embed))["quote_uri"] is None
    ext = {"$type": "app.bsky.embed.external", "external": {"uri": "https://x.org", "title": "", "description": ""}}
    assert js.post_from_event(post_event(embed=ext))["quote_uri"] is None


def test_non_post_events_ignored():
    for ev in (IDENTITY, ACCOUNT, LIKE, delete_event(), post_event(operation="update")):
        assert js.post_from_event(ev) is None
    assert js.deleted_post_uri(delete_event()) == f"at://{A}/app.bsky.feed.post/3l3qo2vuowo2b"


@pytest.mark.parametrize("langs,expected", [(["en"], True), (["en-GB"], True), (["EN-us", "fr"], True),
                                            (["fr"], False), ([], False), (None, False), (["eng"], False)])
def test_is_english(langs, expected):
    assert js.is_english(langs) is expected


def test_v2_envelope_normalised():
    v2 = {"$type": "message", "payload": {
        "$type": "network.bsky.jetstream.subscribeEvents#commit", "did": A, "seq": 24664288881,
        "time": "2026-08-13T06:47:43.959305Z", "operation": "create", "collection": "app.bsky.feed.post",
        "rkey": "r1", "rev": "v", "cid": "c", "record": {"text": "hi", "langs": ["en"], "createdAt": "x"}}}
    ev = js.normalise(v2)
    assert ev["kind"] == "commit" and ev["seq"] == 24664288881
    assert ev["time_us"] == 1786603663959305
    assert js.post_from_event(ev)["uri"] == f"at://{A}/app.bsky.feed.post/r1"


# ---------------------------------------------------------------------------- pseudonymisation
def test_pseudonyms_match_pilot_and_links_join():
    # same construction as sample_bluesky.pseudonym
    import hashlib
    assert js.pseudonym(A, SALT) == hashlib.sha256((SALT + A).encode()).hexdigest()[:12]
    assert js.pseudonym(A, SALT) != js.pseudonym(A, "other")
    s = js.Sampler(SALT)
    parent = s.offer(post_event(did=B, rkey="par", time_us=1))
    child = s.offer(post_event(did=A, rkey="ch", time_us=2,
                               reply={"root": {"uri": f"at://{B}/app.bsky.feed.post/par", "cid": "c"},
                                      "parent": {"uri": f"at://{B}/app.bsky.feed.post/par", "cid": "c"}}))
    assert child["parent_uri"] == parent["uri"]
    for row in (parent, child):
        assert "did:plc" not in json.dumps(row)


# ---------------------------------------------------------------------------- sampler
def test_thinning_rate_and_reproducibility():
    def run(seed):
        s = js.Sampler(SALT, p=0.2, seed=seed)
        kept = [s.offer(post_event(rkey=f"r{i}", time_us=i + 1)) for i in range(20000)]
        return s, [k["uri"] for k in kept if k]
    s1, k1 = run(3)
    _, k2 = run(3)
    _, k3 = run(4)
    assert k1 == k2 and k1 != k3
    rate = s1.n_kept / s1.n_english
    assert abs(rate - 0.2) < 4 * np.sqrt(0.2 * 0.8 / 20000)


def test_language_filter_counts():
    s = js.Sampler(SALT)
    s.offer(post_event(rkey="a", langs=("en",)))
    s.offer(post_event(rkey="b", langs=("ja",)))
    s.offer(post_event(rkey="c", langs=None))
    s.offer(LIKE)
    assert (s.n_events, s.n_posts, s.n_english, s.n_kept) == (4, 3, 1, 1)


def test_duplicates_and_deletes():
    s = js.Sampler(SALT)
    assert s.offer(post_event(rkey="a", time_us=10)) is not None
    assert s.offer(post_event(rkey="a", time_us=10)) is None
    assert s.n_dupes == 1
    s.offer(delete_event(rkey="a", time_us=11))
    s.offer(delete_event(rkey="never-kept", time_us=12))
    assert s.deleted_kept == [js.pseudo_uri(f"at://{A}/app.bsky.feed.post/a", SALT)]


def test_cursor_and_url():
    s = js.Sampler(SALT)
    assert s.cursor(3) is None
    s.offer(post_event(time_us=1_725_911_162_329_308))
    assert s.cursor(3) == 1_725_911_159_329_308
    url = js.build_url(js.DEFAULT_ENDPOINT, cursor=s.cursor(3))
    assert url == ("wss://jetstream2.us-east.bsky.network/subscribe?wantedCollections=app.bsky.feed.post"
                   "&cursor=1725911159329308")
    assert "collections=app.bsky.feed.post" in js.build_url("wss://x/subscribe", protocol="v2")


# ---------------------------------------------------------------------------- full loop with a fake websocket
class FakeWS:
    def __init__(self, messages, drop_after=None):
        self.messages, self.drop_after = messages, drop_after

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for i, m in enumerate(self.messages):
            if self.drop_after is not None and i == self.drop_after:
                raise ConnectionResetError("simulated drop")
            yield json.dumps(m)
        # stay open (live tail) until the caller stops
        while True:
            await asyncio.sleep(3600)


class FakeConnect:
    """First connection drops mid-stream; second replays from the cursor (with overlap)."""

    def __init__(self, stream, drop_at):
        self.stream, self.drop_at, self.urls = stream, drop_at, []

    def __call__(self, url):
        self.urls.append(url)
        if len(self.urls) == 1:
            return FakeWS(self.stream, drop_after=self.drop_at)
        cursor = int(url.split("cursor=")[1])
        return FakeWS([m for m in self.stream if m["time_us"] >= cursor])


def make_stream(n=60):
    msgs = []
    for i in range(n):
        t = 1_700_000_000_000_000 + i * 500_000  # one event every 0.5 s
        msgs.append(post_event(did=A if i % 2 else B, rkey=f"r{i:03d}", time_us=t, text=f"post {i}",
                               langs=("en",) if i % 5 else ("de",)))
    msgs.insert(10, IDENTITY | {"time_us": msgs[9]["time_us"] + 1})
    return msgs


async def _noop_sleep(_):
    return None


@pytest.mark.parametrize("fmt", ["jsonl", "parquet"])
def test_collect_reconnects_dedups_and_stops(tmp_path, fmt):
    stream = make_stream(60)
    english = [m for m in stream if m["kind"] == "commit" and "en" in m["commit"]["record"]["langs"]]
    conn = FakeConnect(stream, drop_at=30)
    path = tmp_path / f"out.{fmt}"
    writer = js.JsonlWriter(path) if fmt == "jsonl" else js.ParquetWriter(path, flush_every=7)
    s = js.Sampler(SALT, p=1.0)
    stats = asyncio.run(js.collect(s, writer, endpoint="wss://x/subscribe", max_posts=len(english),
                                   rewind_s=3.0, connect=conn, sleep=_noop_sleep, log=lambda *_: None))
    assert stats["stop_reason"] == "max_posts" and stats["reconnects"] == 1
    last_before_drop = stream[29]["time_us"]
    assert conn.urls[1].endswith(f"cursor={last_before_drop - 3_000_000}")
    assert s.n_dupes > 0  # the rewind replayed events we had already seen
    df = pd.read_json(path, lines=True) if fmt == "jsonl" else pd.read_parquet(path)
    assert list(df.columns) == js.COLUMNS
    assert len(df) == len(english) and df["uri"].is_unique
    assert not df["did"].str.contains("did:").any()


def test_collect_stops_on_minutes(tmp_path):
    t = {"now": 0.0}

    def clock():
        t["now"] += 1.0  # each check advances one second
        return t["now"]
    writer = js.JsonlWriter(tmp_path / "o.jsonl")
    s = js.Sampler(SALT)
    stats = asyncio.run(js.collect(s, writer, endpoint="wss://x/subscribe", minutes=0.5,
                                   connect=lambda url: FakeWS(make_stream(200)), clock=clock,
                                   sleep=_noop_sleep, log=lambda *_: None))
    assert stats["stop_reason"] == "minutes" and 0 < s.n_kept < 200


def test_collect_flushes_on_cancel(tmp_path):
    path = tmp_path / "o.parquet"
    writer = js.ParquetWriter(path, flush_every=1000)
    s = js.Sampler(SALT)

    async def main():
        task = asyncio.create_task(js.collect(s, writer, endpoint="wss://x/subscribe", max_posts=10_000,
                                              connect=lambda url: FakeWS(make_stream(40)), log=lambda *_: None))
        await asyncio.sleep(0.05)
        task.cancel()  # what Ctrl+C does to the main task under asyncio.run
        return await task
    stats = asyncio.run(main())
    assert stats["stop_reason"] == "interrupted"
    assert len(pd.read_parquet(path)) == s.n_kept > 0


def test_cli_requires_salt_and_stop(monkeypatch):
    monkeypatch.delenv("PSEUDONYM_SALT", raising=False)
    with pytest.raises(SystemExit):
        js.main(["--minutes", "1"])
    monkeypatch.setenv("PSEUDONYM_SALT", "x")
    with pytest.raises(SystemExit):
        js.main([])


# ---------------------------------------------------------------------------- toxicity: Detoxify (mocked)
class FakeDetoxify:
    def __init__(self, model, device="cpu"):
        self.model = model

    def predict(self, texts):
        tox = [0.9 if "idiot" in t else 0.1 for t in texts]
        return {"toxicity": tox, "insult": [x / 2 for x in tox], "identity_attack": [0.0] * len(texts)}


@pytest.fixture
def fake_detoxify(monkeypatch):
    mod = types.ModuleType("detoxify")
    mod.Detoxify = FakeDetoxify
    monkeypatch.setitem(sys.modules, "detoxify", mod)


def test_detoxify_columns(fake_detoxify):
    df = pd.DataFrame({"post_id": ["p1", "p2", "p3"], "text": ["you idiot", "fine point", ""]})
    out = st.add_scores(df, "text", [st.DetoxifyScorer("unbiased", batch_size=2)])
    assert out["tox_detoxify_toxicity"].tolist() == [0.9, 0.1, 0.1]
    assert {"tox_detoxify_insult", "tox_detoxify_identity_attack"} <= set(out.columns)
    with pytest.raises(ValueError):
        st.DetoxifyScorer("multilingual")


def test_score_cli_roundtrip(fake_detoxify, tmp_path):
    inp = tmp_path / "in.jsonl"
    pd.DataFrame({"post_id": ["p1", "p2"], "text": ["idiot", "ok"]}).to_json(inp, orient="records", lines=True)
    st.main(["score", "--input", str(inp), "--output", str(tmp_path / "out.csv")])
    out = pd.read_csv(tmp_path / "out.csv")
    assert out["tox_detoxify_toxicity"].tolist() == [0.9, 0.1]


# ---------------------------------------------------------------------------- toxicity: Perspective (mocked)
class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def perspective_response(v):
    return {"attributeScores": {a: {"summaryScore": {"value": v, "type": "PROBABILITY"}, "spanScores": []}
                                for a in st.PERSPECTIVE_ATTRS}, "languages": ["en"]}


def test_perspective_request_parse_rate_limit_and_cache(tmp_path):
    clock = FakeClock()
    calls = []

    def post(url, body):
        calls.append((clock.t, url, body))
        return perspective_response(0.42)
    cache = tmp_path / "cache.jsonl"
    p = st.PerspectiveScorer("KEY", post=post, limiter=st.RateLimiter(1.0, clock=clock, sleep=clock.sleep),
                             cache_path=cache)
    res = p.score(["a", "b", "c", "a"], log=lambda *_: None)
    assert len(calls) == 3  # fourth is a cache hit
    assert [c[0] for c in calls] == [0.0, 1.0, 2.0]  # 1 qps
    _, url, body = calls[0]
    assert url.endswith("comments:analyze?key=KEY")
    assert body["doNotStore"] is True and set(body["requestedAttributes"]) == set(st.PERSPECTIVE_ATTRS)
    assert res[0] == {"tox_perspective_toxicity": 0.42, "tox_perspective_severe_toxicity": 0.42,
                      "tox_perspective_insult": 0.42, "tox_perspective_identity_attack": 0.42,
                      "tox_perspective_error": ""}
    p2 = st.PerspectiveScorer("KEY", post=lambda *a: pytest.fail("should use cache"), cache_path=cache)
    assert p2.score_one("b")["tox_perspective_toxicity"] == 0.42


def test_perspective_retries_429_then_records_400():
    clock = FakeClock()
    state = {"n": 0}

    def post(url, body):
        state["n"] += 1
        if body["comment"]["text"] == "bad-lang":
            raise urllib.error.HTTPError(url, 400, "bad", {}, io.BytesIO(
                json.dumps({"error": {"message": "Attribute TOXICITY does not support request languages: xx"}}).encode()))
        if state["n"] == 1:
            raise urllib.error.HTTPError(url, 429, "quota", {}, io.BytesIO(b"{}"))
        return perspective_response(0.8)
    p = st.PerspectiveScorer("K", post=post, limiter=st.RateLimiter(1.0, clock=clock, sleep=clock.sleep),
                             sleep=clock.sleep)
    assert p.score_one("text")["tox_perspective_toxicity"] == 0.8 and state["n"] == 2
    bad = p.score_one("bad-lang")
    assert bad["tox_perspective_toxicity"] is None and bad["tox_perspective_error"].startswith("HTTP 400")
    assert p.score_one("   ")["tox_perspective_error"] == "empty"


# ---------------------------------------------------------------------------- iceberg
def test_iceberg_point_estimates():
    df = pd.DataFrame({
        "category": [1, 1, 2, 2, 1, 3, 4, 5, 6, 2],
        "tox": [0.1, 0.4, 0.6, 0.8, 0.65, 0.0, 0.9, 0.95, 0.0, 0.2],
    })
    res = st.iceberg(df, "tox", n_boot=500).set_index("threshold")
    # punitive scores: .1 .4 .6 .8 .65 .2 -> below .5: 3/6; below .7: 5/6
    assert res.loc[0.5, "n_punitive"] == 6 and res.loc[0.5, "n_below"] == 3
    assert res.loc[0.5, "share_below"] == pytest.approx(0.5)
    assert res.loc[0.7, "share_below"] == pytest.approx(5 / 6)
    for th in (0.5, 0.7):
        assert res.loc[th, "ci_low"] <= res.loc[th, "share_below"] <= res.loc[th, "ci_high"]


def test_iceberg_ci_coverage_roughly_right():
    rng = np.random.default_rng(0)
    n = 400
    df = pd.DataFrame({"category": rng.choice([1, 2], n), "tox": rng.uniform(0, 1, n)})
    r = st.iceberg(df, "tox", thresholds=[0.5], n_boot=3000).iloc[0]
    se = np.sqrt(r.share_below * (1 - r.share_below) / n)
    assert (r.ci_high - r.ci_low) == pytest.approx(2 * 1.96 * se, rel=0.15)


def test_iceberg_cluster_bootstrap_wider_when_clustered():
    # 20 authors, 20 posts each; whole authors are either all-low or all-high
    rows = [{"category": 1, "did": f"u{a}", "tox": 0.1 if a % 2 else 0.9} for a in range(20) for _ in range(20)]
    df = pd.DataFrame(rows)
    naive = st.iceberg(df, "tox", thresholds=[0.5], n_boot=2000).iloc[0]
    clus = st.iceberg(df, "tox", thresholds=[0.5], n_boot=2000, cluster_col="did").iloc[0]
    assert naive.share_below == clus.share_below == 0.5
    assert (clus.ci_high - clus.ci_low) > 3 * (naive.ci_high - naive.ci_low)


def test_iceberg_missing_and_empty():
    df = pd.DataFrame({"category": [1, 2, 3], "tox": [None, 0.2, 0.9]})
    r = st.iceberg(df, "tox", thresholds=[0.5]).iloc[0]
    assert r.n_punitive == 1 and r.n_missing_score == 1 and r.share_below == 1.0
    empty = st.iceberg(pd.DataFrame({"category": [3], "tox": [0.1]}), "tox").iloc[0]
    assert empty.n_punitive == 0 and np.isnan(empty.share_below)


def test_iceberg_cli_join(tmp_path, capsys):
    pd.DataFrame({"post_id": ["p1", "p2", "p3"], "category": [1, 2, 4]}).to_csv(tmp_path / "lab.csv", index=False)
    pd.DataFrame({"post_id": ["p1", "p2", "p3"], "text": ["a", "b", "c"],
                  "tox_detoxify_toxicity": [0.1, 0.9, 0.95]}).to_csv(tmp_path / "sc.csv", index=False)
    st.main(["iceberg", "--labels", str(tmp_path / "lab.csv"), "--scores", str(tmp_path / "sc.csv"),
             "--by-category", "--output", str(tmp_path / "ice.csv"), "--n-boot", "200"])
    out = capsys.readouterr().out
    assert "1/2 = 0.500" in out
    assert len(pd.read_csv(tmp_path / "ice.csv")) == 2
    tab = st.share_below_by_category(pd.read_csv(tmp_path / "lab.csv").merge(pd.read_csv(tmp_path / "sc.csv")),
                                     "tox_detoxify_toxicity")
    assert tab.set_index("category").loc[4, "share_below_0.5"] == 0.0


def test_iceberg_all_posts_needs_no_labels(tmp_path, capsys):
    df = pd.DataFrame({"did": ["a", "a", "b", "c"], "tox_detoxify_toxicity": [0.1, 0.6, 0.8, 0.2]})
    r = st.iceberg(df, "tox_detoxify_toxicity", thresholds=[0.5], punitive=None, cluster_col="did").iloc[0]
    assert r.n_punitive == 4 and r.share_below == 0.5
    df.to_csv(tmp_path / "sc.csv", index=False)
    st.main(["iceberg", "--input", str(tmp_path / "sc.csv"), "--all-posts", "--cluster-col", "did", "--n-boot", "50"])
    out = capsys.readouterr().out
    assert "all posts" in out and "3 distinct did" in out and "2/4 = 0.500" in out
    with pytest.raises(SystemExit):
        st.main(["iceberg", "--input", str(tmp_path / "sc.csv"), "--all-posts", "--cluster-col", "author"])


def test_score_drop_text(fake_detoxify, tmp_path):
    inp = tmp_path / "in.csv"
    pd.DataFrame({"post_id": ["p1"], "text": ["idiot"]}).to_csv(inp, index=False)
    st.main(["score", "--input", str(inp), "--output", str(tmp_path / "out.csv"), "--drop-text"])
    out = pd.read_csv(tmp_path / "out.csv")
    assert "text" not in out.columns and out["tox_detoxify_toxicity"].tolist() == [0.9]


def test_real_websockets_against_local_server(tmp_path):
    """Exercises default_connect and the real websockets client against a local server (no internet)."""
    from websockets.asyncio.server import serve
    stream = make_stream(20)
    seen_paths = []

    async def handler(ws):
        seen_paths.append(ws.request.path)
        for m in stream:
            await ws.send(json.dumps(m))
        await ws.wait_closed()

    async def main():
        async with serve(handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            s = js.Sampler(SALT)
            w = js.JsonlWriter(tmp_path / "o.jsonl")
            stats = await js.collect(s, w, endpoint=f"ws://127.0.0.1:{port}/subscribe", max_posts=5,
                                     log=lambda *_: None)
            return s, stats
    s, stats = asyncio.run(main())
    assert stats["stop_reason"] == "max_posts" and s.n_kept == 5
    assert seen_paths[0] == "/subscribe?wantedCollections=app.bsky.feed.post"
