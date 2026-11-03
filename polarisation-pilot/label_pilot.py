"""
Pilot labeller: Claude labels posts against the codebook (default codebook_v0.2.md); agreement with human gold
labels via Krippendorff's alpha with bootstrap intervals.

Commands
  gold-template  Make a blank CSV for a human coder (you), from the sample.
  estimate       Rough token / cost estimate before spending anything.
  sync           Label the first --limit posts immediately (debugging the prompt; full price).
  submit         Send all posts as one Message Batch (about half price; results within 24h, usually much sooner).
  status         Check the batch.
  fetch          Download batch results to data/llm_labels.csv.
  agree          Alpha (with bootstrap 95% CI), alpha by stratum and confusion matrix between two label files.
  flip-audit     Label flip rate on counterfactual minimal pairs, per pair type (model labels or an existing file).

Typical pilot run
  python label_pilot.py gold-template --coder jesse        -> fill data/gold_jesse.csv BEFORE looking at LLM labels
  python label_pilot.py estimate
  python label_pilot.py sync --limit 5                     -> read the rationales; fix the codebook if they're off
  python label_pilot.py submit
  python label_pilot.py status
  python label_pilot.py fetch
  python label_pilot.py agree --a data/gold_jesse.csv --b data/llm_labels.csv
  python label_pilot.py flip-audit --pairs data/minimal_pairs.csv

Needs ANTHROPIC_API_KEY in the environment. The codebook text between PROMPT START/END markers (HTML comments
stripped) is the system prompt, cached, so editing the codebook changes what the model sees. Re-run everything
after edits. batch_state.json records the codebook filename and sha256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
CODEBOOK = HERE / "codebook_v0.2.md"
BATCH_STATE = DATA / "batch_state.json"

# Check the model list in the Console if this errors; any current Claude model works.
DEFAULT_MODEL = "claude-sonnet-5-5"

PASS_ALPHA = 0.667  # pre-registered pass threshold (Krippendorff), as stated in the codebook
FLIP_REVIEW_LINE = 0.10  # review's proposed failure line for party-swap flip rates (codebook D6)
N_BOOT = 1000
BOOT_SEED = 20261103

# Category 4 (identity-based hate) is retired in v0.2; identity is the separate `identity_attack` axis.
CATEGORIES = {1: "implicit_punitive", 2: "explicit_punitive", 3: "non_punitive_moral_criticism",
              5: "non_moral_toxicity", 6: "neutral_other"}
PUNITIVE_CATS = {1, 2}
FEATURES = ["unhedged_allegation", "group_for_individual", "absolutism", "dehumanising", "punitive_lexicon",
            "deservingness", "contempt", "moral_exclusion", "criticism_of_person", "audience_call",
            "repair_attempt"]
RELATIONAL = ["defensiveness", "stonewalling", "repair_rejected"]  # need a parent; "na" otherwise
FLAGS_BOOL = ["identity_attack", "implied_sanction", "sarcasm"]
SANCTIONS = ["none", "proportionate", "exclusionary", "harm"]
ADDRESSIVITY = ["addressed", "tagged_about", "about", "none"]
TARGET_TYPES = ["individual", "group", "institution", "none"]
TOPICS = ["politics_domestic", "politics_international", "race_ethnicity", "religion", "gender_sexuality",
          "immigration", "crime_justice", "celebrity_media", "sport", "tech", "everyday_life", "other"]
CONFIDENCE = ["high", "medium", "low"]
TRISTATE = ["true", "false", "na"]
NA = "NA"  # written to CSV for relational features with no parent; read back as missing

LABEL_COLUMNS = (["post_id", "identity_attack", "category", "punitive_score", "sanction_named",
                  "implied_sanction", "sarcasm"] + FEATURES + RELATIONAL +
                 ["addressivity", "target_type", "blame_target", "topic", "confidence", "rationale"])

LABEL_TOOL = {
    "name": "record_label",
    "description": "Record the codebook (v0.2) label for one post.",
    "input_schema": {
        "type": "object",
        "properties": {
            "identity_attack": {"type": "boolean",
                                "description": "Coded first and independently (codebook section 3)."},
            "category": {"type": "integer", "enum": list(CATEGORIES),
                         "description": "1 implicit punitive, 2 explicit punitive, 3 non-punitive moral criticism, "
                                        "5 non-moral toxicity, 6 neutral/other. Category 4 is retired. Coded as if "
                                        "any identity element were absent."},
            "punitive_score": {"type": "integer", "minimum": -2, "maximum": 3},
            "sanction_named": {"type": "string", "enum": SANCTIONS},
            "implied_sanction": {"type": "boolean"},
            "sarcasm": {"type": "boolean"},
            "features": {"type": "object",
                         "properties": {f: {"type": "boolean"} for f in FEATURES},
                         "required": FEATURES},
            "relational_features": {
                "type": "object",
                "description": "Need a parent post. Use \"na\" for every one when no parent is supplied.",
                "properties": {f: {"type": "string", "enum": TRISTATE} for f in RELATIONAL},
                "required": RELATIONAL},
            "addressivity": {"type": "string", "enum": ADDRESSIVITY},
            "target_type": {"type": "string", "enum": TARGET_TYPES},
            "blame_target": {"type": "string"},
            "topic": {"type": "string", "enum": TOPICS},
            "confidence": {"type": "string", "enum": CONFIDENCE},
            "rationale": {"type": "string", "description": "One sentence naming the decisive cue."},
        },
        "required": ["identity_attack", "category", "punitive_score", "sanction_named", "implied_sanction",
                     "sarcasm", "features", "relational_features", "addressivity", "target_type",
                     "blame_target", "topic", "confidence", "rationale"],
    },
}

# Schema fields the prompt must mention; a mismatch usually means an old codebook is being used with this schema.
SCHEMA_TERMS = (["identity_attack", "sanction_named", "implied_sanction", "sarcasm", "addressivity",
                 "target_type", "blame_target", "topic", "confidence"] + FEATURES + RELATIONAL)


# ---------------------------------------------------------------------------- helpers
def resolve_codebook(path: str | Path | None) -> Path:
    if path is None:
        return CODEBOOK
    p = Path(path)
    if not p.is_absolute() and not p.exists() and (HERE / p).exists():
        p = HERE / p
    return p


def extract_prompt(text: str) -> str:
    """Body between the PROMPT markers, with HTML comments (e.g. DECISION NEEDED notes) removed.

    Markers count only on a line of their own, so a preamble that mentions them in backticks is not matched
    (v0's extractor split on the first occurrence anywhere, which pulled its preamble into the prompt)."""
    m = re.search(r"^<!-- PROMPT START -->[ \t]*$(.*?)^<!-- PROMPT END -->[ \t]*$", text, flags=re.S | re.M)
    if not m:
        raise ValueError("codebook must contain PROMPT START / PROMPT END markers, each on its own line.")
    body = m.group(1)
    body = re.sub(r"[ \t]*<!--.*?-->", "", body, flags=re.S)
    return body.strip()


def load_codebook(path: str | Path | None = None) -> str:
    p = resolve_codebook(path)
    try:
        body = extract_prompt(p.read_text(encoding="utf-8"))
    except ValueError as e:
        sys.exit(f"{p.name}: {e}")
    missing = [t for t in SCHEMA_TERMS if t not in body]
    if missing:
        print(f"WARNING: {p.name} does not mention schema fields {missing}; is it a v0.2 codebook?",
              file=sys.stderr)
    return ("You are a careful content-analysis coder. Apply the codebook below exactly. "
            "Code what the text does, not what you think of its politics; apply identical criteria "
            "whichever side the speaker or target is on.\n\n" + body)


def codebook_sha256(path: str | Path | None = None) -> str:
    return hashlib.sha256(resolve_codebook(path).read_bytes()).hexdigest()


def load_sample(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def has_parent(row: dict) -> bool:
    return bool((row.get("parent_text") or "").strip())


def user_message(row: dict) -> str:
    parent = (row.get("parent_text") or "").strip()
    parts = []
    if parent:
        parts.append(f"<parent_post context_only=\"true\">\n{parent}\n</parent_post>")
    parts.append(f"<target_post>\n{row['text'].strip()}\n</target_post>")
    parts.append("Label the target post." if parent else
                 "Label the target post. No parent post was supplied, so code every relational feature as na.")
    return "\n\n".join(parts)


def request_params(row: dict, model: str, system: str) -> dict:
    return {
        "model": model,
        "max_tokens": 700,
        "temperature": 0,
        "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        "tools": [LABEL_TOOL],
        "tool_choice": {"type": "tool", "name": "record_label"},
        "messages": [{"role": "user", "content": user_message(row)}],
    }


def _tri(v):
    """true/false/na (or bool/None) -> 1 / 0 / NA."""
    if isinstance(v, bool):
        return int(v)
    if v is None:
        return NA
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return 1
    if s in ("false", "0", "no"):
        return 0
    return NA


def flatten(post_id: str, label: dict, parent: bool | None = None) -> dict:
    """One CSV row from a tool input. parent=False forces relational features to NA whatever the model said."""
    out = {"post_id": post_id, "category": label.get("category"), "punitive_score": label.get("punitive_score"),
           "sanction_named": label.get("sanction_named", "")}
    for k in FLAGS_BOOL:
        out[k] = int(bool(label.get(k))) if k in label else ""
    feats = label.get("features", {}) or {}
    for f in FEATURES:
        out[f] = int(bool(feats.get(f))) if f in feats else ""
    rel = label.get("relational_features", {}) or {}
    for f in RELATIONAL:
        out[f] = NA if parent is False else _tri(rel.get(f))
    for k in ["addressivity", "target_type", "blame_target", "topic", "confidence", "rationale"]:
        out[k] = label.get(k, "")
    return out


def tool_input(message) -> dict:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use":
            return block.input
    raise ValueError("no tool_use block in response")


def write_labels(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def client():
    import anthropic
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set.")
    return anthropic.Anthropic()


def label_rows_sync(c, rows: list[dict], model: str, system: str, id_key=lambda r: r["post_id"],
                    verbose: bool = True) -> list[dict]:
    out = []
    for r in rows:
        msg = c.messages.create(**request_params(r, model, system))
        lab = flatten(id_key(r), tool_input(msg), parent=has_parent(r))
        out.append(lab)
        if verbose:
            u = msg.usage
            print(f"{lab['post_id']}  cat={lab['category']} score={lab['punitive_score']} "
                  f"id={lab['identity_attack']} sanction={lab['sanction_named']} conf={lab['confidence']}  "
                  f"[in {u.input_tokens}, cache_read {getattr(u, 'cache_read_input_tokens', 0)}]\n"
                  f"   text: {r['text'][:140]!r}\n   why:  {lab['rationale']}\n")
    return out


# ---------------------------------------------------------------------------- commands
def cmd_gold_template(a):
    rows = load_sample(Path(a.sample))
    out = DATA / f"gold_{a.coder}.csv"
    if out.exists() and not a.force:
        sys.exit(f"{out} exists; use --force to overwrite (you'd lose labels).")
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["post_id", "text", "parent_text"] + LABEL_COLUMNS[1:]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:  # stratum deliberately omitted so the coder is blind to it
            row = {"post_id": r["post_id"], "text": r["text"], "parent_text": r.get("parent_text", "")}
            if not has_parent(r):
                row.update({f: NA for f in RELATIONAL})
            w.writerow(row)
    print(f"Wrote {out}. Fill identity_attack (0/1), category (1,2,3,5,6), punitive_score (-2..3), "
          f"sanction_named ({'/'.join(SANCTIONS)}), implied_sanction and sarcasm (0/1), features as 0/1, "
          f"relational features as 0/1 (pre-filled NA where there is no parent), addressivity "
          f"({'/'.join(ADDRESSIVITY)}), flags as in the codebook.")


def cmd_estimate(a):
    rows = load_sample(Path(a.sample))
    sys_tokens = len(load_codebook(a.codebook)) / 4 + 700  # + tool schema
    per_post_in = sum(len(user_message(r)) for r in rows) / 4 / max(len(rows), 1)
    out_tokens = 220
    n = len(rows)
    print(f"{n} posts | system+tool ~{sys_tokens:.0f} tokens (cached) | ~{per_post_in:.0f} input + ~{out_tokens} output tokens per post")
    print(f"Total ~{n * (sys_tokens + per_post_in) / 1e6:.3f}M input tokens uncached, ~{n * out_tokens / 1e6:.3f}M output.")
    print("Multiply by your model's per-million prices (Console > Pricing); batch is ~50% off, cache reads ~90% off.")


def cmd_sync(a):
    c, system = client(), load_codebook(a.codebook)
    rows = load_sample(Path(a.sample))[: a.limit]
    out_rows = label_rows_sync(c, rows, a.model, system)
    write_labels(out_rows, DATA / "llm_labels_sync.csv")
    print(f"Saved to {DATA / 'llm_labels_sync.csv'}")


def cmd_submit(a):
    c, system = client(), load_codebook(a.codebook)
    rows = load_sample(Path(a.sample))
    reqs = [{"custom_id": r["post_id"], "params": request_params(r, a.model, system)} for r in rows]
    batch = c.messages.batches.create(requests=reqs)
    DATA.mkdir(parents=True, exist_ok=True)
    cb = resolve_codebook(a.codebook)
    BATCH_STATE.write_text(json.dumps({
        "batch_id": batch.id, "model": a.model, "n": len(reqs),
        "codebook": cb.name, "codebook_sha256": codebook_sha256(cb),
        "no_parent_ids": [r["post_id"] for r in rows if not has_parent(r)],
        "submitted": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2))
    print(f"Submitted batch {batch.id} with {len(reqs)} requests (codebook {cb.name}). Run `status` to check.")


def _batch_state() -> dict:
    return json.loads(BATCH_STATE.read_text()) if BATCH_STATE.exists() else {}


def _batch_id(a):
    if getattr(a, "batch_id", None):
        return a.batch_id
    if not BATCH_STATE.exists():
        sys.exit("No batch_state.json; pass --batch-id.")
    return _batch_state()["batch_id"]


def cmd_status(a):
    b = client().messages.batches.retrieve(_batch_id(a))
    print(f"{b.id}: {b.processing_status} | {b.request_counts}")


def cmd_fetch(a):
    c = client()
    bid = _batch_id(a)
    state = _batch_state()
    if state.get("codebook"):
        cb = resolve_codebook(state["codebook"])
        if cb.exists() and codebook_sha256(cb) != state.get("codebook_sha256"):
            print(f"WARNING: {cb.name} has changed since this batch was submitted; these labels are from the old text.")
    no_parent = set(state.get("no_parent_ids", []))
    rows, failed = [], []
    for entry in c.messages.batches.results(bid):
        if entry.result.type == "succeeded":
            try:
                parent = False if entry.custom_id in no_parent else None
                rows.append(flatten(entry.custom_id, tool_input(entry.result.message), parent=parent))
            except ValueError:
                failed.append(entry.custom_id)
        else:
            failed.append(entry.custom_id)
    rows.sort(key=lambda r: r["post_id"])
    write_labels(rows, DATA / "llm_labels.csv")
    print(f"Saved {len(rows)} labels to {DATA / 'llm_labels.csv'}. Failed: {failed or 'none'}")


# ---------------------------------------------------------------------------- agreement
def _read_labels(path: Path) -> dict[str, dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return {r["post_id"]: r for r in csv.DictReader(f)}


_BOOL_STR = {"true": 1.0, "false": 0.0, "yes": 1.0, "no": 0.0}


def _num(v):
    """Numeric code; booleans as text become 1/0; blank, NA and anything unparseable become NaN (missing)."""
    if isinstance(v, bool):
        return float(v)
    if v is None:
        return float("nan")
    s = str(v).strip().lower()
    if s in _BOOL_STR:
        return _BOOL_STR[s]
    if s in ("", "na", "nan", "n/a", "none"):
        return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _enc(values, vocab):
    """Encode a nominal string field as integer codes; unknown or blank -> NaN."""
    idx = {v: float(i) for i, v in enumerate(vocab)}
    return [idx.get(str(v).strip().lower(), float("nan")) if v is not None else float("nan") for v in values]


def _alpha_arr(data, level):
    import krippendorff
    import numpy as np
    pairable = (~np.isnan(data)).all(axis=0)
    d = data[:, pairable]
    if d.shape[1] < 2 or len(set(d.flatten())) < 2:
        return float("nan"), int(d.shape[1])
    return float(krippendorff.alpha(reliability_data=d, level_of_measurement=level)), int(d.shape[1])


def alpha(a_vals, b_vals, level):
    import numpy as np
    data = np.array([[_num(x) for x in a_vals], [_num(x) for x in b_vals]], dtype=float)
    return _alpha_arr(data, level)


def alpha_ci(a_vals, b_vals, level, n_boot=N_BOOT, seed=BOOT_SEED):
    """Point alpha plus a percentile bootstrap 95% CI, resampling pairable units with replacement."""
    import numpy as np
    data = np.array([[_num(x) for x in a_vals], [_num(x) for x in b_vals]], dtype=float)
    data = data[:, (~np.isnan(data)).all(axis=0)]
    point, n = _alpha_arr(data, level)
    if n < 2 or np.isnan(point):
        return point, float("nan"), float("nan"), n
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        al, _n = _alpha_arr(data[:, rng.integers(0, n, n)], level)
        if not np.isnan(al):
            boots.append(al)
    if not boots:
        return point, float("nan"), float("nan"), n
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return point, float(lo), float(hi), n


def _punitive(v):
    x = _num(v)
    return float("nan") if x != x else float(int(x) in PUNITIVE_CATS)


def _main_measures(A, B, ids):
    """(name, a_values, b_values, level) for the headline measures."""
    col = lambda D, k: [D[i].get(k, "") for i in ids]
    strict = [i for i in ids if A[i].get("category") in ("1", "3") and B[i].get("category") in ("1", "3")]
    either = [i for i in ids if A[i].get("category") in ("1", "3") or B[i].get("category") in ("1", "3")]
    return [
        ("category (5-way, nominal)", col(A, "category"), col(B, "category"), "nominal"),
        ("punitive yes/no (cat 1-2 vs rest)", [_punitive(v) for v in col(A, "category")],
         [_punitive(v) for v in col(B, "category")], "nominal"),
        ("punitive_score (interval)", col(A, "punitive_score"), col(B, "punitive_score"), "interval"),
        ("1 vs 3 strict (both coders in {1,3})", [A[i]["category"] for i in strict],
         [B[i]["category"] for i in strict], "nominal"),
        ("1 vs 3 either (either coder in {1,3})", [A[i]["category"] for i in either],
         [B[i]["category"] for i in either], "nominal"),
        ("identity_attack", col(A, "identity_attack"), col(B, "identity_attack"), "nominal"),
        ("sanction_named (nominal)", _enc(col(A, "sanction_named"), SANCTIONS),
         _enc(col(B, "sanction_named"), SANCTIONS), "nominal"),
    ]


def agreement_report(A: dict, B: dict, strata: dict | None = None, n_boot=N_BOOT, seed=BOOT_SEED) -> dict:
    """All agreement numbers as a dict (used by cmd_agree and the tests)."""
    ids = sorted(set(A) & set(B))
    rep = {"n": len(ids), "main": [], "features": [], "strata": {}}
    for name, av, bv, level in _main_measures(A, B, ids):
        point, lo, hi, n = alpha_ci(av, bv, level, n_boot=n_boot, seed=seed)
        rep["main"].append({"measure": name, "alpha": point, "ci_low": lo, "ci_high": hi, "n": n})
    col = lambda D, k: [D[i].get(k, "") for i in ids]
    for f in ["implied_sanction", "sarcasm"] + FEATURES + RELATIONAL:
        al, n = alpha(col(A, f), col(B, f), "nominal")
        rep["features"].append({"measure": f"feature: {f}", "alpha": al, "n": n})
    al, n = alpha(_enc(col(A, "addressivity"), ADDRESSIVITY), _enc(col(B, "addressivity"), ADDRESSIVITY), "nominal")
    rep["features"].append({"measure": "addressivity (nominal)", "alpha": al, "n": n})
    if strata:
        by = defaultdict(list)
        for i in ids:
            if strata.get(i):
                by[strata[i]].append(i)
        for s, sids in sorted(by.items()):
            rows = []
            for name, av, bv, level in _main_measures(A, B, sids)[:4]:
                al, n = alpha(av, bv, level)
                rows.append({"measure": name, "alpha": al, "n": n})
            rep["strata"][s] = {"n": len(sids), "measures": rows}
    seen = sorted({str(v) for i in ids for v in (A[i].get("category"), B[i].get("category")) if v not in ("", None)},
                  key=lambda x: (_num(x) != _num(x), _num(x)))
    cats = [str(k) for k in CATEGORIES] + [c for c in seen if c not in {str(k) for k in CATEGORIES}]
    conf = Counter((A[i].get("category"), B[i].get("category")) for i in ids)
    rep["confusion"] = {"cats": cats, "counts": {(ra, cb): conf.get((ra, cb), 0) for ra in cats for cb in cats}}
    return rep


def load_strata(A: dict, B: dict, sample_path: Path | None) -> dict:
    """post_id -> stratum, from either label file, else the sample (joined on post_id)."""
    strata = {}
    if sample_path and Path(sample_path).exists():
        for r in load_sample(Path(sample_path)):
            if r.get("stratum"):
                strata[r["post_id"]] = r["stratum"]
    for D in (B, A):  # label files override the sample; A takes precedence over B
        for i, r in D.items():
            if r.get("stratum"):
                strata[i] = r["stratum"]
    return strata


def _fmt(x):
    return "    nan" if x != x else f"{x:7.3f}"


def cmd_agree(a):
    A, B = _read_labels(Path(a.a)), _read_labels(Path(a.b))
    ids = sorted(set(A) & set(B))
    if not ids:
        sys.exit("No overlapping post_ids.")
    strata = load_strata(A, B, Path(a.sample) if a.sample else None)
    rep = agreement_report(A, B, strata, n_boot=a.n_boot, seed=a.seed)
    print(f"{rep['n']} posts in both files\n")

    print(f"{'measure':42s} {'alpha':>7s} {'95% CI':>17s} {'n':>5s}")
    for r in rep["main"]:
        ci = "" if r["ci_low"] != r["ci_low"] else f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
        print(f"{r['measure']:42s} {_fmt(r['alpha'])} {ci:>17s} {r['n']:5d}")
    print(f"\nBootstrap: {a.n_boot} resamples of pairable posts, seed {a.seed}, percentile interval.")
    print(f"Pass threshold (pre-registered): alpha >= {PASS_ALPHA}. Read the interval, not only the point.\n")

    print(f"{'measure':42s} {'alpha':>7s} {'n':>5s}")
    for r in rep["features"]:
        print(f"{r['measure']:42s} {_fmt(r['alpha'])} {r['n']:5d}")
    print("Feature alphas are unstable when a feature is rare; check counts before trusting them. "
          "Relational features count NA as missing, not false.\n")

    if rep["strata"]:
        print("Alpha by stratum (no CI: strata are small)")
        for s, d in rep["strata"].items():
            print(f"  [{s}] n={d['n']}")
            for r in d["measures"]:
                print(f"    {r['measure']:40s} {_fmt(r['alpha'])} {r['n']:5d}")
        print()
    else:
        print("No 'stratum' column found in either file or the sample; skipping alpha by stratum.\n")

    cats = rep["confusion"]["cats"]
    cnt = rep["confusion"]["counts"]
    print("Confusion (rows = A, cols = B)\n     " + " ".join(f"{c:>4s}" for c in cats))
    for ra in cats:
        print(f"{ra:>4s} " + " ".join(f"{cnt[(ra, cb)]:4d}" for cb in cats))

    dis = [i for i in ids if A[i].get("category") != B[i].get("category")
           or A[i].get("identity_attack") != B[i].get("identity_attack")]
    out = DATA / "disagreements.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["post_id", "stratum", "text", "cat_A", "cat_B", "identity_A", "identity_B", "score_A", "score_B",
                    "sanction_A", "sanction_B", "rationale_A", "rationale_B"])
        for i in dis:
            w.writerow([i, strata.get(i, ""), A[i].get("text") or B[i].get("text", ""),
                        A[i].get("category"), B[i].get("category"),
                        A[i].get("identity_attack"), B[i].get("identity_attack"),
                        A[i].get("punitive_score"), B[i].get("punitive_score"),
                        A[i].get("sanction_named"), B[i].get("sanction_named"),
                        A[i].get("rationale", ""), B[i].get("rationale", "")])
    print(f"\n{len(dis)} category or identity disagreements written to {out}. "
          "Read these: they are where the codebook is vague.")


# ---------------------------------------------------------------------------- flip audit
def pair_key(pair_id: str, variant: str) -> str:
    return f"{pair_id}:{variant}"


def pair_type_of(row: dict) -> str:
    """Explicit pair_type column if present; else the pair_id prefix before the first '-' or '_'; else 'all'."""
    if (row.get("pair_type") or "").strip():
        return row["pair_type"].strip()
    m = re.match(r"^([^-_]+)[-_]", row["pair_id"])
    return m.group(1) if m else "all"


def flip_audit(pairs: list[dict], labels: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Per-pair flips and per-type summary. labels is keyed by pair_key(pair_id, variant)."""
    groups = defaultdict(list)
    types = {}
    for r in pairs:
        groups[r["pair_id"]].append(r)
        types.setdefault(r["pair_id"], pair_type_of(r))
    per_pair = []
    for pid, rows in groups.items():
        labs = [labels[pair_key(pid, r["variant"])] for r in rows if pair_key(pid, r["variant"]) in labels]
        if len(labs) < 2:
            continue
        def diff(k, fn=lambda v: v):
            vals = set()
            for lab in labs:
                x = fn(lab.get(k))
                vals.add(None if isinstance(x, float) and x != x else x)  # NaN-safe: missing compares equal
            return int(len(vals) > 1)

        scores = [_num(l.get("punitive_score")) for l in labs]
        scores = [s for s in scores if s == s]
        per_pair.append({
            "pair_id": pid, "pair_type": types[pid], "n_variants": len(labs),
            "categories": "/".join(str(l.get("category")) for l in labs),
            "category_flip": diff("category", lambda v: str(v)),
            "punitive_flip": diff("category", _punitive),
            "identity_flip": diff("identity_attack", lambda v: _num(v)),
            "sanction_flip": diff("sanction_named", lambda v: str(v or "").lower()),
            "score_range": (max(scores) - min(scores)) if scores else float("nan"),
        })
    summary = []
    by = defaultdict(list)
    for p in per_pair:
        by[p["pair_type"]].append(p)
    for t, ps in sorted(by.items()):
        n = len(ps)
        rng = [p["score_range"] for p in ps if p["score_range"] == p["score_range"]]
        summary.append({
            "pair_type": t, "n_pairs": n,
            "category_flip_rate": sum(p["category_flip"] for p in ps) / n,
            "punitive_flip_rate": sum(p["punitive_flip"] for p in ps) / n,
            "identity_flip_rate": sum(p["identity_flip"] for p in ps) / n,
            "sanction_flip_rate": sum(p["sanction_flip"] for p in ps) / n,
            "mean_score_range": sum(rng) / len(rng) if rng else float("nan"),
        })
    return per_pair, summary


def _read_existing_flip_labels(path: Path) -> dict[str, dict]:
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("pair_id") and r.get("variant"):
                out[pair_key(r["pair_id"], r["variant"])] = r
            elif r.get("post_id"):
                out[r["post_id"]] = r
    return out


def cmd_flip_audit(a):
    pairs = load_sample(Path(a.pairs))
    need = {"pair_id", "variant", "text"}
    if not pairs or not need <= set(pairs[0]):
        sys.exit(f"{a.pairs} needs columns pair_id, variant, text (parent_text and pair_type optional).")
    if a.labels:
        labels = _read_existing_flip_labels(Path(a.labels))
    else:
        if len(pairs) > a.limit:
            sys.exit(f"{len(pairs)} rows exceeds --limit {a.limit} for sync labelling; raise --limit or pass --labels.")
        c, system = client(), load_codebook(a.codebook)
        rows = label_rows_sync(c, pairs, a.model, system, id_key=lambda r: pair_key(r["pair_id"], r["variant"]),
                               verbose=False)
        labels = {r["post_id"]: r for r in rows}
        lab_out = Path(a.out).with_name(Path(a.out).stem + "_labels.csv")
        write_labels(rows, lab_out)
        print(f"Model labels saved to {lab_out}")
    per_pair, summary = flip_audit(pairs, labels)
    if not per_pair:
        sys.exit("No pair has two or more labelled variants.")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(per_pair[0]))
        w.writeheader()
        w.writerows(per_pair)
    print(f"{'pair_type':20s} {'pairs':>5s} {'cat':>6s} {'pun':>6s} {'ident':>6s} {'sanct':>6s} {'score_rng':>9s}")
    for s in summary:
        mark = "  <- above 10%" if max(s["category_flip_rate"], s["punitive_flip_rate"]) > FLIP_REVIEW_LINE else ""
        print(f"{s['pair_type']:20s} {s['n_pairs']:5d} {s['category_flip_rate']:6.2f} {s['punitive_flip_rate']:6.2f} "
              f"{s['identity_flip_rate']:6.2f} {s['sanction_flip_rate']:6.2f} {s['mean_score_range']:9.2f}{mark}")
    print(f"\nFlip = labels differ within a pair. Review's proposed failure line: {FLIP_REVIEW_LINE:.0%} on party swaps "
          f"(pre-register; codebook D6). Per-pair detail in {out}.")


# ---------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sample_default = str(DATA / "pilot_sample.csv")
    cb_help = f"codebook markdown file (default {CODEBOOK.name})"

    p = sp.add_parser("gold-template"); p.add_argument("--sample", default=sample_default)
    p.add_argument("--coder", required=True); p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_gold_template)
    p = sp.add_parser("estimate"); p.add_argument("--sample", default=sample_default)
    p.add_argument("--codebook", default=str(CODEBOOK), help=cb_help); p.set_defaults(fn=cmd_estimate)
    for name, fn in [("sync", cmd_sync), ("submit", cmd_submit)]:
        p = sp.add_parser(name); p.add_argument("--sample", default=sample_default)
        p.add_argument("--model", default=DEFAULT_MODEL)
        p.add_argument("--codebook", default=str(CODEBOOK), help=cb_help); p.set_defaults(fn=fn)
        if name == "sync":
            p.add_argument("--limit", type=int, default=5)
    for name, fn in [("status", cmd_status), ("fetch", cmd_fetch)]:
        p = sp.add_parser(name); p.add_argument("--batch-id"); p.set_defaults(fn=fn)
    p = sp.add_parser("agree"); p.add_argument("--a", required=True); p.add_argument("--b", required=True)
    p.add_argument("--sample", default=sample_default, help="sample CSV to take 'stratum' from (joined on post_id)")
    p.add_argument("--n-boot", type=int, default=N_BOOT); p.add_argument("--seed", type=int, default=BOOT_SEED)
    p.set_defaults(fn=cmd_agree)
    p = sp.add_parser("flip-audit", help="label flip rate on minimal pairs")
    p.add_argument("--pairs", required=True, help="CSV: pair_id, variant, text, parent_text (pair_type optional)")
    p.add_argument("--labels", help="existing labels (pair_id+variant columns, or post_id 'pair_id:variant'); "
                                    "omit to label with the model (sync)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--codebook", default=str(CODEBOOK), help=cb_help)
    p.add_argument("--limit", type=int, default=100, help="max rows to label with the model (sync is full price)")
    p.add_argument("--out", default=str(DATA / "flip_audit.csv"))
    p.set_defaults(fn=cmd_flip_audit)

    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
