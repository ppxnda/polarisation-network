"""
Toxicity scorer + iceberg statistic: the comparison baseline for the punitive codebook (novelty claim 1, D1).

Commands
  score    Add tox_* columns to a CSV/JSONL/Parquet of posts, using Detoxify (local) and optionally Perspective.
  iceberg  Share of punitive posts (category 1 or 2) that a toxicity score puts BELOW a threshold,
           with a bootstrap 95% CI. Default thresholds 0.5 and 0.7.

Columns written by score
  tox_detoxify_<attr>      Detoxify 'original' or 'unbiased' heads (toxicity, severe_toxicity, obscene,
                           threat, insult, identity_attack; 'unbiased' adds sexual_explicit)
  tox_perspective_<attr>   toxicity, severe_toxicity, insult, identity_attack (summary scores, 0 to 1)
  tox_perspective_error    blank, or why Perspective failed for that row

Usage (Windows PowerShell)
  python score_toxicity.py score --input data\\pilot_sample.csv --output data\\pilot_tox.csv
  python score_toxicity.py score --input data\\jetstream_x.parquet --output data\\jetstream_tox.parquet --model unbiased

  $env:PERSPECTIVE_API_KEY="..."        # Google Cloud key with the Comment Analyzer API enabled
  python score_toxicity.py score --input data\\pilot_sample.csv --output data\\pilot_tox.csv --perspective --qps 1

  python score_toxicity.py iceberg --labels data\\llm_labels.csv --scores data\\pilot_tox.csv `
      --score-col tox_detoxify_toxicity --thresholds 0.5 0.7 --by-category

IMPORTANT
  Perspective API says it stops serving after 31 December 2026. If you want Perspective as a baseline,
  score everything you need (pilot, gold set, a D1 sample) before then and keep the outputs; Detoxify runs
  locally and stays available. Perspective is called with doNotStore=true.

Needs: pip install pandas pyarrow detoxify   (detoxify pulls in torch and downloads weights on first use)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

PERSPECTIVE_URL = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
PERSPECTIVE_ATTRS = ["TOXICITY", "SEVERE_TOXICITY", "INSULT", "IDENTITY_ATTACK"]
PUNITIVE = (1, 2)


# ---------------------------------------------------------------------------- io
def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".csv":
        return pd.read_csv(path, dtype={"post_id": str}, keep_default_na=False)
    if path.suffix in (".jsonl", ".ndjson"):
        return pd.read_json(path, lines=True, dtype={"post_id": str})
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    raise SystemExit(f"Unsupported input type: {path.suffix} (use .csv, .jsonl or .parquet)")


def write_table(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".csv":
        df.to_csv(path, index=False, encoding="utf-8")
    elif path.suffix in (".jsonl", ".ndjson"):
        df.to_json(path, orient="records", lines=True, force_ascii=False)
    elif path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    else:
        raise SystemExit(f"Unsupported output type: {path.suffix}")


# ---------------------------------------------------------------------------- Detoxify
class DetoxifyScorer:
    """Wraps detoxify.Detoxify. `model` is 'original' (Jigsaw 2018) or 'unbiased' (Jigsaw 2019, bias-aware)."""

    def __init__(self, model: str = "original", device: str = "cpu", batch_size: int = 32):
        if model not in ("original", "unbiased"):
            raise ValueError("model must be 'original' or 'unbiased'")
        from detoxify import Detoxify
        self.model, self.batch_size = model, batch_size
        self.m = Detoxify(model, device=device)

    def score(self, texts: list[str]) -> list[dict]:
        out: list[dict] = []
        for i in range(0, len(texts), self.batch_size):
            chunk = [t if t else " " for t in texts[i:i + self.batch_size]]
            res = self.m.predict(chunk)  # {attr: [floats]}
            for j in range(len(chunk)):
                out.append({f"tox_detoxify_{k}": float(v[j]) for k, v in res.items()})
        return out


# ---------------------------------------------------------------------------- Perspective
class RateLimiter:
    """At most `qps` calls per second (default 1, Perspective's default quota)."""

    def __init__(self, qps: float = 1.0, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.interval, self.clock, self.sleep, self.last = 1.0 / qps, clock, sleep, None

    def wait(self) -> None:
        now = self.clock()
        if self.last is not None and now - self.last < self.interval:
            self.sleep(self.interval - (now - self.last))
        self.last = self.clock()


def http_post_json(url: str, body: dict, timeout: float = 30) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


class PerspectiveScorer:
    """Calls comments:analyze one text at a time. Retries 429/5xx with backoff. Optional on-disk cache
    (JSONL keyed by sha256 of text) so a rerun after a crash doesn't spend quota twice."""

    def __init__(self, api_key: str, attrs: list[str] = PERSPECTIVE_ATTRS, qps: float = 1.0,
                 languages: list[str] | None = ("en",), cache_path: str | Path | None = None,
                 post: Callable[[str, dict], dict] = http_post_json, limiter: RateLimiter | None = None,
                 max_retries: int = 4, sleep: Callable[[float], None] = time.sleep):
        self.key, self.attrs, self.languages = api_key, list(attrs), list(languages) if languages else None
        self.post, self.limiter = post, limiter or RateLimiter(qps)
        self.max_retries, self.sleep = max_retries, sleep
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache: dict[str, dict] = {}
        if self.cache_path and self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.cache[rec["h"]] = rec["scores"]

    @staticmethod
    def _h(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    def body(self, text: str) -> dict:
        b = {"comment": {"text": text}, "requestedAttributes": {a: {} for a in self.attrs}, "doNotStore": True}
        if self.languages:
            b["languages"] = self.languages
        return b

    def parse(self, resp: dict) -> dict:
        scores = resp.get("attributeScores", {})
        return {f"tox_perspective_{a.lower()}": float(scores[a]["summaryScore"]["value"]) if a in scores else None
                for a in self.attrs}

    def score_one(self, text: str) -> dict:
        h = self._h(text)
        if h in self.cache:
            return {**self.cache[h], "tox_perspective_error": ""}
        if not text.strip():
            return {**{f"tox_perspective_{a.lower()}": None for a in self.attrs}, "tox_perspective_error": "empty"}
        url = f"{PERSPECTIVE_URL}?key={self.key}"
        for attempt in range(self.max_retries + 1):
            self.limiter.wait()
            try:
                scores = self.parse(self.post(url, self.body(text)))
                self.cache[h] = scores
                if self.cache_path:
                    with open(self.cache_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"h": h, "scores": scores}) + "\n")
                return {**scores, "tox_perspective_error": ""}
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503) and attempt < self.max_retries:
                    self.sleep(2 ** attempt * 2)
                    continue
                err = f"HTTP {e.code}"
                if e.code == 400:  # usually unsupported language; record and move on
                    try:
                        err += ": " + json.loads(e.read().decode())["error"]["message"][:120]
                    except Exception:
                        pass
                return {**{f"tox_perspective_{a.lower()}": None for a in self.attrs}, "tox_perspective_error": err}
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < self.max_retries:
                    self.sleep(2 ** attempt * 2)
                    continue
                return {**{f"tox_perspective_{a.lower()}": None for a in self.attrs},
                        "tox_perspective_error": f"network: {e}"}
        raise AssertionError("unreachable")

    def score(self, texts: list[str], log=print) -> list[dict]:
        out = []
        for i, t in enumerate(texts, 1):
            out.append(self.score_one(t))
            if i % 100 == 0:
                log(f"  perspective {i}/{len(texts)}")
        return out


def add_scores(df: pd.DataFrame, text_col: str, scorers: Iterable) -> pd.DataFrame:
    texts = df[text_col].fillna("").astype(str).tolist()
    df = df.copy()
    for s in scorers:
        res = pd.DataFrame(s.score(texts), index=df.index)
        for c in res.columns:
            df[c] = res[c]
    return df


# ---------------------------------------------------------------------------- iceberg
def iceberg(df: pd.DataFrame, score_col: str, category_col: str = "category",
            thresholds: Iterable[float] = (0.5, 0.7), punitive: Iterable[int] = PUNITIVE,
            n_boot: int = 2000, seed: int = 7, cluster_col: str | None = None) -> pd.DataFrame:
    """Share of punitive posts (category in `punitive`) with score < threshold, plus percentile bootstrap 95% CI.
    `punitive=None` uses every row (no labels needed): the share of ALL posts below threshold, a baseline.

    If `cluster_col` is given (e.g. the author pseudonym `did`), resamples clusters rather than posts, because
    posts by the same author are not independent. Rows with a missing score are dropped and counted.
    """
    if punitive is None:
        sub = df
    else:
        cat = pd.to_numeric(df[category_col], errors="coerce")
        sub = df[cat.isin(list(punitive))]
    scores = pd.to_numeric(sub[score_col], errors="coerce")
    n_missing = int(scores.isna().sum())
    keep = scores.notna()
    s = scores[keep].to_numpy(dtype=float)
    clusters = sub.loc[keep, cluster_col].to_numpy() if cluster_col else None
    rng = np.random.default_rng(seed)
    rows = []
    for th in thresholds:
        below = (s < th).astype(float)
        n = len(below)
        if n == 0:
            rows.append({"threshold": th, "n_punitive": 0, "n_missing_score": n_missing, "n_below": 0,
                         "share_below": np.nan, "ci_low": np.nan, "ci_high": np.nan})
            continue
        if clusters is None:
            idx = rng.integers(0, n, size=(n_boot, n))
            boots = below[idx].mean(axis=1)
        else:
            uniq, inv = np.unique(clusters, return_inverse=True)
            k = len(uniq)
            sums = np.bincount(inv, weights=below, minlength=k)
            counts = np.bincount(inv, minlength=k).astype(float)
            draw = rng.integers(0, k, size=(n_boot, k))
            boots = sums[draw].sum(axis=1) / counts[draw].sum(axis=1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        rows.append({"threshold": th, "n_punitive": n, "n_missing_score": n_missing, "n_below": int(below.sum()),
                     "share_below": float(below.mean()), "ci_low": float(lo), "ci_high": float(hi)})
    return pd.DataFrame(rows)


def share_below_by_category(df: pd.DataFrame, score_col: str, category_col: str = "category",
                            thresholds: Iterable[float] = (0.5, 0.7)) -> pd.DataFrame:
    """Context table: share below threshold for every category (e.g. 1 and 2 vs 4 identity hate, 5 toxicity)."""
    d = pd.DataFrame({"category": pd.to_numeric(df[category_col], errors="coerce"),
                      "score": pd.to_numeric(df[score_col], errors="coerce")}).dropna()
    out = d.groupby("category")["score"].agg(n="size").reset_index()
    for th in thresholds:
        out[f"share_below_{th}"] = d.groupby("category")["score"].apply(lambda x: float((x < th).mean())).values
    out["category"] = out["category"].astype(int)
    return out


# ---------------------------------------------------------------------------- commands
def cmd_score(a) -> None:
    df = read_table(a.input)
    if a.text_col not in df.columns:
        sys.exit(f"No column {a.text_col!r} in {a.input}; columns are {list(df.columns)}")
    scorers = []
    if not a.no_detoxify:
        try:
            scorers.append(DetoxifyScorer(a.model, device=a.device, batch_size=a.batch_size))
        except ImportError:
            sys.exit("pip install detoxify (or pass --no-detoxify to use Perspective only)")
    if a.perspective:
        key = os.environ.get("PERSPECTIVE_API_KEY")
        if not key:
            sys.exit("Set PERSPECTIVE_API_KEY.")
        cache = a.cache or str(Path(a.output).with_suffix(".perspective_cache.jsonl"))
        scorers.append(PerspectiveScorer(key, qps=a.qps, cache_path=cache))
        print(f"Perspective at {a.qps} qps: about {len(df) / a.qps / 60:.0f} minutes for {len(df)} rows.")
    if not scorers:
        sys.exit("Nothing to do: Detoxify disabled and --perspective not set.")
    out = add_scores(df, a.text_col, scorers)
    if a.drop_text:
        out = out.drop(columns=[a.text_col])
    write_table(out, a.output)
    print(f"Wrote {len(out)} rows with {sum(c.startswith('tox_') for c in out.columns)} tox_ columns to {a.output}")


def cmd_iceberg(a) -> None:
    if a.input:
        df = read_table(a.input)
    else:
        if not (a.labels and a.scores):
            sys.exit("Give --input (labels and scores in one file) or both --labels and --scores.")
        lab, sc = read_table(a.labels), read_table(a.scores)
        lab[a.id_col], sc[a.id_col] = lab[a.id_col].astype(str), sc[a.id_col].astype(str)
        cols = [a.id_col] + [c for c in sc.columns if c.startswith("tox_") or c == a.cluster_col]
        df = lab.merge(sc[[c for c in dict.fromkeys(cols) if c in sc.columns]], on=a.id_col, how="inner")
        print(f"Joined {len(df)} rows on {a.id_col} ({len(lab)} labels, {len(sc)} scored).")
    if a.cluster_col and a.cluster_col not in df.columns:
        sys.exit(f"--cluster-col {a.cluster_col!r} not found; columns are {list(df.columns)}")
    res = iceberg(df, a.score_col, a.category_col, a.thresholds, n_boot=a.n_boot, seed=a.seed,
                  cluster_col=a.cluster_col, punitive=None if a.all_posts else PUNITIVE)
    if a.cluster_col:
        print(f"Clusters: {df[a.cluster_col].nunique()} distinct {a.cluster_col} for {len(df)} rows "
              f"(CI resamples {a.cluster_col}, not rows).")
    what = "all posts" if a.all_posts else "punitive (categories 1-2) posts"
    print(f"\nIceberg: {what} scoring below threshold on {a.score_col}")
    for _, r in res.iterrows():
        print(f"  < {r.threshold:.2f}: {int(r.n_below)}/{int(r.n_punitive)} = {r.share_below:.3f} "
              f"(95% CI {r.ci_low:.3f} to {r.ci_high:.3f})")
    if res.n_missing_score.iloc[0]:
        print(f"  ({int(res.n_missing_score.iloc[0])} rows had no score and were dropped)")
    if a.by_category and not a.all_posts:
        print("\nShare below threshold, all categories:")
        print(share_below_by_category(df, a.score_col, a.category_col, a.thresholds).to_string(index=False))
    if a.output:
        write_table(res, a.output)
        print(f"\nSaved {a.output}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="add tox_* columns")
    s.add_argument("--input", required=True)
    s.add_argument("--output", required=True)
    s.add_argument("--text-col", default="text")
    s.add_argument("--model", choices=["original", "unbiased"], default="original")
    s.add_argument("--device", default="cpu")
    s.add_argument("--batch-size", type=int, default=32)
    s.add_argument("--no-detoxify", action="store_true")
    s.add_argument("--perspective", action="store_true", help="also call Perspective (PERSPECTIVE_API_KEY)")
    s.add_argument("--qps", type=float, default=1.0, help="Perspective requests per second (default quota is 1)")
    s.add_argument("--cache", default=None, help="Perspective cache file (default next to --output)")
    s.add_argument("--drop-text", action="store_true", help="omit the text column from --output (ethics)")
    s.set_defaults(func=cmd_score)

    i = sub.add_parser("iceberg", help="share of punitive posts below a toxicity threshold")
    i.add_argument("--input", help="one file with category + score columns")
    i.add_argument("--labels", help="labels file (e.g. data/llm_labels.csv or a gold file)")
    i.add_argument("--scores", help="output of the score command")
    i.add_argument("--id-col", default="post_id")
    i.add_argument("--category-col", default="category")
    i.add_argument("--score-col", default="tox_detoxify_toxicity")
    i.add_argument("--thresholds", type=float, nargs="+", default=[0.5, 0.7])
    i.add_argument("--n-boot", type=int, default=2000)
    i.add_argument("--seed", type=int, default=7)
    i.add_argument("--cluster-col", default=None, help="e.g. did: bootstrap by author, not by post")
    i.add_argument("--by-category", action="store_true", help="also show share below for categories 1-6")
    i.add_argument("--all-posts", action="store_true",
                   help="no labels: share of ALL rows below threshold (needs only --input with scores)")
    i.add_argument("--output", default=None)
    i.set_defaults(func=cmd_iceberg)

    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
