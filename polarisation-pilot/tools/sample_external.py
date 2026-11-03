"""
Draw a hand-labelling sample from two external Reddit corpora, in label_pilot.py sample format.

Sources (both CC BY 4.0; Reddit content, so quote paraphrased in papers)
  MFRC  Moral Foundations Reddit Corpus, huggingface.co/datasets/USC-MOLA-Lab/MFRC (Trager et al.).
        One row per (comment, annotator); no comment ids or parent text. Deduplicated on text here.
  CAD   Contextual Abuse Dataset (Vidgen et al., NAACL 2021), ConvoKit corpus "contextual-abuse".
        Comments only, from the train/dev/test splits (the exclude_* splits are empty, bot, non-English
        or image entries). parent_text is the post or comment it replies to; empty when that parent is an
        image/link post with no text.

Outputs (in --out, default ./data; gitignored)
  ext_sample.csv        post_id, stratum, text, parent_text. Rows shuffled so MFRC and CAD are interleaved.
  ext_sample_key.csv    post_id + the source corpus's own labels. Do NOT open before hand-labelling.

Usage
  python tools/sample_external.py --mfrc data/raw_ext/mfrc.parquet --n-mfrc 100 --n-cad 50 --seed 11
  python label_pilot.py gold-template --sample data/ext_sample.csv --coder jesse

Needs: pip install pandas pyarrow convokit
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

COLS = ["post_id", "stratum", "text", "parent_text"]


def sample_mfrc(path: str | Path, n: int, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_parquet(path)
    raw = raw[raw["text"].fillna("").str.strip() != ""]
    labels = (raw.groupby("text")
              .agg(subreddit=("subreddit", "first"), bucket=("bucket", "first"),
                   mfrc_annotations=("annotation", lambda s: "; ".join(sorted(s))),
                   mfrc_n_annotators=("annotator", "nunique"))
              .reset_index())
    pick = labels.sample(n=n, random_state=seed)
    pick["post_id"] = "mfrc_" + pick["text"].map(lambda t: hashlib.sha1(t.encode()).hexdigest()[:10])
    sample = pd.DataFrame({"post_id": pick["post_id"], "stratum": "mfrc:" + pick["subreddit"],
                           "text": pick["text"], "parent_text": ""})
    key = pick[["post_id", "subreddit", "bucket", "mfrc_annotations", "mfrc_n_annotators"]]
    return sample, key


def parent_text(reply_to: str | None, text: dict[str, str]) -> str:
    """CAD in ConvoKit stores posts as "<reddit id>-post", but top-level comments reply_to the bare id."""
    if not reply_to:
        return ""
    return text.get(reply_to, text.get(f"{reply_to}-post", ""))


def sample_cad(n: int, seed: int, corpus_name: str = "contextual-abuse") -> tuple[pd.DataFrame, pd.DataFrame]:
    from convokit import Corpus, download
    corpus = Corpus(filename=download(corpus_name))
    text = {u.id: u.text or "" for u in corpus.iter_utterances()}
    rows = []
    for u in corpus.iter_utterances():
        m = u.meta
        if m.get("entry_type") != "comment" or m.get("split") not in ("train", "dev", "test"):
            continue
        if not (u.text or "").strip():
            continue
        rows.append({"utt_id": u.id, "text": u.text, "parent_text": parent_text(u.reply_to, text),
                     "subreddit": m.get("info_subreddit"), "cad_primary": m.get("annotation_Primary"),
                     "cad_split": m.get("split")})
    pick = pd.DataFrame(rows).sample(n=n, random_state=seed)
    pick["post_id"] = "cad_" + pick["utt_id"].astype(str)
    sample = pd.DataFrame({"post_id": pick["post_id"], "stratum": "cad:" + pick["subreddit"].astype(str),
                           "text": pick["text"], "parent_text": pick["parent_text"]})
    key = pick[["post_id", "subreddit", "cad_primary", "cad_split"]]
    return sample, key


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mfrc", required=True, help="MFRC parquet (data/train_dedup-*.parquet from Hugging Face)")
    ap.add_argument("--n-mfrc", type=int, default=100)
    ap.add_argument("--n-cad", type=int, default=50)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default="data")
    a = ap.parse_args(argv)

    ms, mk = sample_mfrc(a.mfrc, a.n_mfrc, a.seed)
    cs, ck = sample_cad(a.n_cad, a.seed)
    sample = pd.concat([ms, cs]).sample(frac=1, random_state=a.seed)[COLS]
    assert sample["post_id"].is_unique
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out / "ext_sample.csv", index=False, encoding="utf-8")
    pd.concat([mk, ck]).to_csv(out / "ext_sample_key.csv", index=False, encoding="utf-8")
    print(f"{len(ms)} MFRC + {len(cs)} CAD -> {out / 'ext_sample.csv'} (labels in ext_sample_key.csv; open after "
          f"hand-labelling)")


if __name__ == "__main__":
    main()
