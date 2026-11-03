"""Conversation layer (L4b): reply trees, gain g, and cut vs repaired endings as an absorbing Markov chain.

Prototype for H2. Works on any reply-tree corpus once each utterance carries a codebook v0.2 label:
ChangeMyView via ConvoKit now, Bluesky threads later.

Pipeline
--------
1. load      ConvoKit corpus (or a generic CSV) -> flat utterance table
2. export    utterances + parent text -> CSV that label_pilot.py can label (same columns as pilot_sample.csv)
3. analyse   join labels -> states -> gain g, transition matrix, ending probabilities, delta-by-opening table

States (derived from codebook v0.2 labels, in this priority order)
------------------------------------------------------------------
P  punitive                 category in {1, 2}
R  repair                   repair_attempt == 1 (and not P)
M  moral criticism          category == 3 (non-punitive)
N  neutral / other          everything else (5, 6, unlabelled)

Definitions (stated once; the H2 plan cites these)
-------------------------------------------------
gain g_s        mean number of P direct replies per utterance in state s, leaves included.
                g_P is the punitive branching ratio: g_P > 1 means a punitive post, on average, begets more than
                one punitive reply (supercritical cascade). The decisive contrast is g_P vs g_M: does punitive
                criticism provoke more punitive replies than equally moral but non-punitive criticism?
                g_s = (mean replies per s-node) x (share of those replies that are P); both parts are reported,
                because "punitive posts get more replies" and "replies to punitive posts are more punitive" are
                different mechanisms.
ending          the last informative (non-N) state on a root-to-leaf chain:
                  CUT       last informative turn is P (the chain stops while a sanction stands)
                  REPAIRED  last informative turn is R
                  OTHER     last informative turn is M, or the chain is all N
Markov chain    a random walk down the tree: at each utterance, stop (if it is a leaf) or step to one of its
                replies chosen uniformly. To keep the ending Markov, neutral turns remember the last informative
                state: N0 (none or M before), NP (P before), NR (R before). Transient states P, M, R, N0, NP, NR;
                absorbing CUT, REPAIRED, OTHER.

Nothing here is a finding. The --stub-labels option is a keyword heuristic for checking the plumbing only.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

STATES = ["P", "M", "R", "N"]
TRANSIENT = ["P", "M", "R", "N0", "NP", "NR"]
ABSORBING = ["CUT", "REPAIRED", "OTHER"]
END_OF = {"P": "CUT", "NP": "CUT", "R": "REPAIRED", "NR": "REPAIRED", "M": "OTHER", "N0": "OTHER"}
# Literal characters, not \u escapes: pandas 3 hands regexes to pyarrow/RE2, which rejects "\u".
# CMV deltas are usually U+2206 (INCREMENT, also written &#8710;), sometimes U+0394 (Greek capital delta).
# Reddit text is HTML-escaped, so the entity usually arrives as "&amp;#8710;".
DELTA_RE = re.compile("(?:\u2206|\u0394|&(?:amp;)?#(?:8710|916);|!delta\\b)", re.IGNORECASE)
DELTABOT_CONFIRM = re.compile(r"^\s*Confirmed: \d+ delta", re.IGNORECASE)
TOMBSTONES = {"[deleted]", "[removed]"}       # Reddit placeholders: comment deleted by user or removed
BOTS = {"DeltaBot", "AutoModerator"}           # not participants; removed from trees by drop_bots()
REMOVAL_NOTICE = re.compile(r"your comment has been removed", re.IGNORECASE)
UTT_COLS = ["id", "conversation_id", "reply_to", "speaker", "text", "timestamp"]


# ---------------------------------------------------------------- loading

def load_convokit(name: str, max_conversations: int | None = None, seed: int = 0) -> pd.DataFrame:
    """Flatten a ConvoKit corpus (e.g. 'winning-args-corpus', 'conversations-gone-awry-cmv-corpus')."""
    try:
        from convokit import Corpus, download
    except ImportError:
        sys.exit("pip install convokit  (or use --csv with columns " + ", ".join(UTT_COLS) + ")")
    corpus = Corpus(filename=download(name))
    rows = []
    for u in corpus.iter_utterances():
        r = {"id": u.id, "conversation_id": u.conversation_id, "reply_to": u.reply_to,
             "speaker": u.speaker.id, "text": u.text or "", "timestamp": u.timestamp}
        for k, v in (u.meta or {}).items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                r[f"meta_{k}"] = v
        rows.append(r)
    df = pd.DataFrame(rows)
    if max_conversations:
        convs = df["conversation_id"].drop_duplicates().sample(frac=1, random_state=seed)
        df = df[df["conversation_id"].isin(set(convs[:max_conversations]))]
    return _arrow_safe_meta(df.reset_index(drop=True))


def _arrow_safe_meta(df: pd.DataFrame) -> pd.DataFrame:
    """Meta fields can mix types (CMV 'edited' is False or an edit timestamp), which parquet rejects.
    Cast any meta_ column holding more than one non-null Python type to string, keeping nulls."""
    df = df.copy()
    for c in [c for c in df.columns if c.startswith("meta_")]:
        types = {type(v) for v in df[c] if v is not None and not (isinstance(v, float) and np.isnan(v))}
        if len(types) > 1:
            df[c] = df[c].map(lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v))
    return df


def load_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"id": str, "conversation_id": str, "reply_to": str, "speaker": str})
    missing = set(UTT_COLS) - set(df.columns) - {"timestamp", "speaker"}
    if missing:
        sys.exit(f"{path} is missing columns: {sorted(missing)}")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise reply_to (NaN/'' -> None) and drop replies whose parent is absent (out of sample, or deleted
    in corpora that drop deleted comments; ConvoKit CMV keeps them as tombstones, see deletion_report)."""
    df = df.copy()
    df["reply_to"] = df["reply_to"].where(df["reply_to"].notna() & (df["reply_to"].astype(str) != ""), None)
    ids = set(df["id"])
    orphan = df["reply_to"].notna() & ~df["reply_to"].isin(ids)
    if orphan.any():
        # Orphans become roots of their own subtree would distort openings; drop them and report it.
        print(f"[clean] dropping {int(orphan.sum())} utterances whose parent is missing", file=sys.stderr)
        df = df[~orphan]
        # Repeat until stable: dropping a node orphans its children.
        return clean(df) if orphan.any() else df
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- deltas (CMV)

def mark_deltas(df: pd.DataFrame) -> pd.DataFrame:
    """delta_award: utterance by the conversation's OP that contains a delta token OR that DeltaBot confirmed
    ("Confirmed: 1 delta awarded to ..." as a direct reply). delta_received: the utterance that award replies
    to. Run BEFORE drop_bots(), which removes the confirmations. delta_bot_confirmed is kept separately so the
    regex can be checked against the bot (see delta_check)."""
    df = df.copy()
    roots = df[df["reply_to"].isna()].set_index("conversation_id")["speaker"]
    op = df["conversation_id"].map(roots)
    text = df["text"].fillna("").astype(str)
    confirmed = set(df.loc[(df["speaker"] == "DeltaBot") & text.str.contains(DELTABOT_CONFIRM), "reply_to"].dropna())
    df["delta_bot_confirmed"] = df["id"].isin(confirmed)
    df["delta_token"] = text.str.contains(DELTA_RE)
    df["delta_award"] = (df["speaker"] == op) & (df["delta_token"] | df["delta_bot_confirmed"])
    recv = set(df.loc[df["delta_award"], "reply_to"].dropna())
    df["delta_received"] = df["id"].isin(recv)
    return df


def delta_check(df: pd.DataFrame) -> dict:
    """Agreement between the OP-token rule and DeltaBot confirmations of OP awards (needs mark_deltas output)."""
    roots = df[df["reply_to"].isna()].set_index("conversation_id")["speaker"]
    is_op = df["speaker"] == df["conversation_id"].map(roots)
    tok, bot = is_op & df["delta_token"], is_op & df["delta_bot_confirmed"]
    return {"op_token": int(tok.sum()), "op_bot_confirmed": int(bot.sum()), "both": int((tok & bot).sum()),
            "token_recall_vs_bot": float((tok & bot).sum() / bot.sum()) if bot.sum() else float("nan"),
            "awards": int(df["delta_award"].sum())}


def drop_bots(df: pd.DataFrame, bots: set[str] = BOTS) -> tuple[pd.DataFrame, int]:
    """Remove bot utterances and re-attach their replies to the bot's parent, so no human turn is orphaned.
    Bots are not participants: left in, they pad trees with N leaves and inflate mean_replies."""
    is_bot = df["speaker"].isin(bots) & df["reply_to"].notna()
    if not is_bot.any():
        return df, 0
    parent = dict(zip(df.loc[is_bot, "id"], df.loc[is_bot, "reply_to"]))

    def up(p):
        while p in parent:
            p = parent[p]
        return p

    out = df[~is_bot].copy()
    out["reply_to"] = out["reply_to"].map(lambda p: None if p is None else up(p))
    return out.reset_index(drop=True), int(is_bot.sum())


def is_tombstone(df: pd.DataFrame) -> pd.Series:
    return df["text"].fillna("").astype(str).str.strip().isin(TOMBSTONES)


def deletion_report(df: pd.DataFrame, n_orphans_dropped: int = 0) -> dict:
    """How much of each tree is missing. ConvoKit keeps deleted comments in place as "[deleted]" tombstones
    (so their replies are NOT orphans); orphans only arise from out-of-sample parents. Moderator removal
    notices are counted by rule, because Rule 2 (rude/hostile) removals are the H2 truncation that matters."""
    rep = df["reply_to"].notna()
    tomb = is_tombstone(df) & rep
    kids = set(df["reply_to"].dropna())
    notices = df.loc[df["text"].fillna("").astype(str).str.contains(REMOVAL_NOTICE), "text"].astype(str)
    rules = notices.str.extract(r"(?:Comment )?Rule (\d)", expand=False).fillna("?").value_counts().to_dict()
    open_ = rep & df["reply_to"].isin(set(df.loc[df["reply_to"].isna(), "id"]))
    return {"replies": int(rep.sum()), "tombstones": int(tomb.sum()),
            "tombstone_share": float(tomb.sum() / rep.sum()) if rep.sum() else float("nan"),
            "tombstones_with_replies": int((tomb & df["id"].isin(kids)).sum()),
            "openings": int(open_.sum()), "opening_tombstones": int((tomb & open_).sum()),
            "speaker_deleted_text_kept": int((rep & (df["speaker"] == "[deleted]") & ~tomb).sum()),
            "removal_notices_by_rule": {f"rule_{k}": int(v) for k, v in sorted(rules.items())},
            "orphans_dropped": int(n_orphans_dropped)}


# ---------------------------------------------------------------- export for labelling

def export_for_labelling(df: pd.DataFrame, out: Path, skip_roots: bool = True, max_chars: int = 2000) -> int:
    """Write a CSV label_pilot.py can read (post_id, text, parent_text, stratum). OP root posts are skipped by
    default: in CMV they are long view statements, not replies, and the codebook is built for replies.
    Tombstones ("[deleted]") are skipped; they stay in the tree as N."""
    text = df.set_index("id")["text"]
    rows = df[df["reply_to"].notna()] if skip_roots else df
    rows = rows[~is_tombstone(rows)]  # "[deleted]" has nothing to label; don't pay for it
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["post_id", "stratum", "text", "parent_text"])
        w.writeheader()
        for r in rows.itertuples():
            parent = text.get(r.reply_to, "") if r.reply_to else ""
            w.writerow({"post_id": r.id, "stratum": r.conversation_id,
                        "text": str(r.text)[:max_chars], "parent_text": str(parent)[:max_chars]})
    return len(rows)


# ---------------------------------------------------------------- states

def state_from_label(category, repair_attempt) -> str:
    try:
        c = int(float(category))
    except (TypeError, ValueError):
        c = None
    if c in (1, 2):
        return "P"
    if str(repair_attempt).strip().lower() in ("1", "1.0", "true"):
        return "R"
    if c == 3:
        return "M"
    return "N"


def attach_states(df: pd.DataFrame, labels: pd.DataFrame | None) -> pd.DataFrame:
    """labels: label_pilot.py output (post_id, category, repair_attempt, ...). Roots without labels become N."""
    df = df.copy()
    if labels is None:
        df["state"] = "N"
        return df
    lab = labels.set_index(labels["post_id"].astype(str))
    none = pd.Series([None] * len(df), index=df.index)
    cat = df["id"].map(lab["category"]) if "category" in lab else none
    rep = df["id"].map(lab["repair_attempt"]) if "repair_attempt" in lab else none
    df["state"] = [state_from_label(c, r) for c, r in zip(cat, rep)]
    df["labelled"] = df["id"].isin(lab.index)
    return df


_P_STUB = re.compile(r"\b(?:deserve[sd]?|should be (?:fired|sacked|banned|jailed|ashamed)|disgrace|shame on|"
                     r"never forget|good riddance|karma|scum|vile|pathetic)\b", re.I)
_R_STUB = re.compile(r"\b(?:sorry|fair point|you'?re right|i apologi[sz]e|good point|i stand corrected|"
                     r"i hear you|agreed?)\b", re.I)
_M_STUB = re.compile(r"\b(?:wrong|unfair|immoral|unjust|dishonest|lie[sd]?|hypocri\w*|harm(?:ful)?)\b", re.I)


def stub_states(df: pd.DataFrame) -> pd.DataFrame:
    """Keyword heuristic for pipeline checks ONLY. Not a measure; never report numbers from it."""
    df = df.copy()
    t = df["text"].fillna("")
    df["state"] = np.select([t.str.contains(_P_STUB), t.str.contains(_R_STUB), t.str.contains(_M_STUB)],
                            ["P", "R", "M"], "N")
    df.loc[df["reply_to"].isna(), "state"] = "N"
    df["labelled"] = False
    return df


# ---------------------------------------------------------------- trees

def children_map(df: pd.DataFrame) -> dict[str, list[str]]:
    ch: dict[str, list[str]] = defaultdict(list)
    for i, p in zip(df["id"], df["reply_to"]):
        if p is not None:
            ch[p].append(i)
    return ch


def openings(df: pd.DataFrame) -> pd.DataFrame:
    """Top-level replies to the root post: the 'opening' turn of each sub-thread."""
    roots = set(df.loc[df["reply_to"].isna(), "id"])
    return df[df["reply_to"].isin(roots)]


def subtree_ids(root: str, ch: dict[str, list[str]]) -> list[str]:
    out, stack = [], [root]
    while stack:
        n = stack.pop()
        out.append(n)
        stack.extend(ch.get(n, []))
    return out


def tree_shapes(df: pd.DataFrame) -> pd.DataFrame:
    """One row per conversation: size, openings (top-level replies), max depth, leaves, mean branching of
    internal reply nodes, and the share of utterances in the largest opening's sub-thread."""
    ch = children_map(df)
    rows = []
    for conv, g in df.groupby("conversation_id"):
        root = g.loc[g["reply_to"].isna(), "id"]
        if len(root) != 1:
            continue
        stack, max_d = [(root.iloc[0], 0)], 0
        while stack:
            n, d = stack.pop()
            max_d = max(max_d, d)
            stack.extend((k, d + 1) for k in ch.get(n, []))
        ops = ch.get(root.iloc[0], [])
        sizes = [len(subtree_ids(o, ch)) for o in ops]
        reps = g[g["reply_to"].notna()]
        n_kids = np.array([len(ch.get(i, [])) for i in reps["id"]])
        rows.append({"conversation_id": conv, "utterances": len(g), "openings": len(ops), "max_depth": max_d,
                     "leaves": int((n_kids == 0).sum()),
                     "branching_internal": float(n_kids[n_kids > 0].mean()) if (n_kids > 0).any() else np.nan,
                     "largest_subthread_share": max(sizes) / (len(g) - 1) if sizes else np.nan})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- gain g

def gain_table(df: pd.DataFrame, exclude_roots: bool = True) -> pd.DataFrame:
    """Per parent state s: n nodes, mean replies, share of replies that are P, and g_s = mean P replies."""
    st = df.set_index("id")["state"]
    ch = children_map(df)
    nodes = df[df["reply_to"].notna()] if exclude_roots else df
    rows = []
    for s in STATES:
        ids = nodes.loc[nodes["state"] == s, "id"]
        if len(ids) == 0:
            rows.append({"state": s, "n": 0, "mean_replies": np.nan, "share_P": np.nan, "g": np.nan})
            continue
        n_kids = np.array([len(ch.get(i, [])) for i in ids])
        n_p = np.array([sum(st[c] == "P" for c in ch.get(i, [])) for i in ids])
        rows.append({"state": s, "n": len(ids), "mean_replies": n_kids.mean(),
                     "share_P": n_p.sum() / n_kids.sum() if n_kids.sum() else np.nan, "g": n_p.mean()})
    return pd.DataFrame(rows).set_index("state")


def cluster_bootstrap(df: pd.DataFrame, stat, n_boot: int = 500, seed: int = 0) -> np.ndarray:
    """Resample whole conversations (replies are not independent within a thread). stat(df) -> 1-D array."""
    rng = np.random.default_rng(seed)
    groups = {k: g for k, g in df.groupby("conversation_id")}
    keys = np.array(list(groups))
    out = []
    for _ in range(n_boot):
        pick = rng.choice(keys, size=len(keys), replace=True)
        parts = []
        for j, k in enumerate(pick):  # rename ids so duplicated conversations stay separate trees
            g = groups[k].copy()
            suf = f"#{j}"
            g["id"] = g["id"].astype(str) + suf
            g["reply_to"] = g["reply_to"].map(lambda x: None if x is None else str(x) + suf)
            g["conversation_id"] = str(k) + suf
            parts.append(g)
        out.append(stat(pd.concat(parts, ignore_index=True)))
    return np.array(out)


def gain_with_ci(df: pd.DataFrame, n_boot: int = 500, seed: int = 0) -> pd.DataFrame:
    tab = gain_table(df)

    def stat(d):
        t = gain_table(d)["g"]
        return np.array([t["P"], t["M"], t["P"] / t["M"] if t["M"] else np.nan])

    boots = cluster_bootstrap(df, stat, n_boot, seed)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5], axis=0)
    tab["g_lo"] = np.nan
    tab["g_hi"] = np.nan
    tab.loc["P", ["g_lo", "g_hi"]] = lo[0], hi[0]
    tab.loc["M", ["g_lo", "g_hi"]] = lo[1], hi[1]
    gm = tab.loc["M", "g"]
    tab.attrs["gP_over_gM"] = (tab.loc["P", "g"] / gm if gm else np.nan, lo[2], hi[2])
    return tab


# ---------------------------------------------------------------- Markov chain

def _aug(state: str, last_inf: str | None) -> str:
    if state != "N":
        return state
    return {"P": "NP", "R": "NR"}.get(last_inf, "N0")


def transition_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Random-walk-down-the-tree weights. Each reply (non-root) node contributes weight 1 split equally over
    its children, or weight 1 to the ending its augmented state implies if it is a leaf."""
    st = df.set_index("id")["state"]
    ch = children_map(df)
    cols = TRANSIENT + ABSORBING
    C = pd.DataFrame(0.0, index=TRANSIENT, columns=cols)
    for root in openings(df)["id"]:
        stack = [(root, None)]
        while stack:
            n, last_inf = stack.pop()
            s = st[n]
            a = _aug(s, last_inf)
            li = s if s != "N" else last_inf
            kids = ch.get(n, [])
            if not kids:
                C.loc[a, END_OF[a]] += 1.0
                continue
            w = 1.0 / len(kids)
            for k in kids:
                C.loc[a, _aug(st[k], li)] += w
                stack.append((k, li))
    return C


def absorbing_analysis(C: pd.DataFrame, alpha: float = 0.0) -> dict:
    """Row-normalise (optional add-alpha smoothing on observed transitions), then the fundamental matrix
    N = (I - Q)^-1 gives expected turns before absorption; B = N R gives P(ending | starting state)."""
    C = C.copy()
    C[C > 0] += alpha
    rows = C.sum(axis=1)
    T = C.div(rows.replace(0, np.nan), axis=0).fillna(0.0)
    Q = T[TRANSIENT].to_numpy()
    R = T[ABSORBING].to_numpy()
    seen = rows.to_numpy() > 0
    N = np.full((len(TRANSIENT), len(TRANSIENT)), np.nan)
    Qs = Q[np.ix_(seen, seen)]
    N[np.ix_(seen, seen)] = np.linalg.inv(np.eye(seen.sum()) - Qs)
    B = np.full((len(TRANSIENT), len(ABSORBING)), np.nan)
    B[seen] = N[np.ix_(seen, seen)] @ R[seen]
    return {"T": T,
            "expected_turns": pd.Series(np.nansum(N, axis=1), index=TRANSIENT).where(seen),
            "ending_probs": pd.DataFrame(B, index=TRANSIENT, columns=ABSORBING)}


def chain_endings(df: pd.DataFrame) -> pd.DataFrame:
    """Empirical ending of every root-to-leaf chain, with its opening state (for checking the chain model)."""
    st = df.set_index("id")["state"]
    ch = children_map(df)
    rows = []
    for op_id in openings(df)["id"]:
        stack = [(op_id, None, 1)]
        while stack:
            n, li, depth = stack.pop()
            s = st[n]
            li2 = s if s != "N" else li
            kids = ch.get(n, [])
            if not kids:
                end = {"P": "CUT", "R": "REPAIRED"}.get(li2, "OTHER")
                rows.append({"opening_id": op_id, "opening_state": st[op_id], "leaf": n, "length": depth,
                             "ending": end})
            for k in kids:
                stack.append((k, li2, depth + 1))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- H2 table

def opening_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """One row per opening (top-level reply): its state, subtree size, depth, any P later, any R later,
    and whether the OP awarded a delta anywhere in that sub-thread."""
    ch = children_map(df)
    st = df.set_index("id")["state"]
    recv = df.set_index("id")["delta_received"] if "delta_received" in df else None
    rows = []
    for r in openings(df).itertuples():
        sub = subtree_ids(r.id, ch)
        later = sub[1:]
        rows.append({"opening_id": r.id, "conversation_id": r.conversation_id, "opening_state": r.state,
                     "subtree_size": len(sub),
                     "any_P_later": any(st[i] == "P" for i in later),
                     "any_R_later": any(st[i] == "R" for i in later),
                     "delta": bool(recv is not None and recv.reindex(sub).fillna(False).any())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- CLI

def _fmt_tab(t: pd.DataFrame) -> str:
    return t.to_string(float_format=lambda v: f"{v:.3f}")


def cmd_load(a):
    df = load_convokit(a.corpus, a.max_conversations, a.seed) if a.corpus else load_csv(a.csv)
    n0 = len(df)
    df = mark_deltas(clean(df))
    n_orphans = n0 - len(df)
    dc = delta_check(df)
    df, n_bots = drop_bots(df) if not a.keep_bots else (df, 0)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out) if out.suffix == ".parquet" else df.to_csv(out, index=False)
    print(f"{len(df)} utterances, {df['conversation_id'].nunique()} conversations, "
          f"{dc['awards']} delta awards -> {out}")
    print(f"bots removed: {n_bots}  |  OP delta tokens {dc['op_token']}, DeltaBot-confirmed OP awards "
          f"{dc['op_bot_confirmed']}, token recall vs bot {dc['token_recall_vs_bot']:.0%}")
    print("deletion:", deletion_report(df, n_orphans))


def _read_utts(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path, dtype=str)
    df["reply_to"] = df["reply_to"].where(df["reply_to"].notna() & (df["reply_to"] != ""), None)
    for c in ("delta_award", "delta_received"):
        if c in df:
            df[c] = df[c].astype(str).str.lower().isin(["true", "1"])
    return df


def cmd_export(a):
    df = _read_utts(a.utts)
    n = export_for_labelling(df, Path(a.out))
    print(f"{n} replies -> {a.out}. Label with: python label_pilot.py estimate/submit --sample {a.out}")


def cmd_analyse(a):
    df = _read_utts(a.utts)
    if a.stub_labels:
        print("!! STUB LABELS: keyword heuristic, plumbing check only, not a measure !!\n")
        df = stub_states(df)
    else:
        if not a.labels:
            sys.exit("--labels (label_pilot.py output) or --stub-labels is required")
        df = attach_states(df, pd.read_csv(a.labels, dtype={"post_id": str}))
        cover = df.loc[df["reply_to"].notna() & ~is_tombstone(df), "labelled"].mean()  # tombstones aren't exported
        print(f"label coverage of replies: {cover:.1%}  (unlabelled replies count as N; keep this near 100%)\n")
        if cover < 0.95:
            print("!! coverage < 95%: g and endings are biased towards N. Label whole conversations, not samples.\n")

    print("State counts (replies):\n", df.loc[df["reply_to"].notna(), "state"].value_counts().to_string(), "\n")
    dr = deletion_report(df)
    print(f"Deletion: {dr['tombstones']}/{dr['replies']} replies are tombstones ({dr['tombstone_share']:.1%}); "
          f"{dr['opening_tombstones']}/{dr['openings']} openings; {dr['tombstones_with_replies']} tombstones have "
          f"replies; mod removal notices {dr['removal_notices_by_rule']}; orphans {dr['orphans_dropped']}")
    st = df.set_index("id")["state"]
    rp = df[df["reply_to"].notna()].assign(parent_state=lambda d: d["reply_to"].map(st), tomb=lambda d: is_tombstone(d))
    print("Tombstone share of replies by parent state (H2 plan, threat 3; tombstones are N, so read with care):")
    print(_fmt_tab(rp.groupby("parent_state")["tomb"].agg(["mean", "size"]).rename(columns={"mean": "share", "size": "n"})))
    ts = tree_shapes(df)
    print("\nTree shapes (per conversation):")
    print(_fmt_tab(ts.drop(columns="conversation_id").describe(percentiles=[0.5]).T[["mean", "min", "50%", "max"]]))
    emp0 = chain_endings(df)
    print("Root-to-leaf chain length (turns from opening):",
          emp0["length"].describe(percentiles=[0.5, 0.9]).round(1)[["count", "mean", "50%", "90%", "max"]].to_dict(), "\n")
    gt = gain_with_ci(df, a.n_boot, a.seed)
    print("Gain by parent state (g = mean punitive replies per post; 95% CI resamples conversations):")
    print(_fmt_tab(gt))
    r, lo, hi = gt.attrs["gP_over_gM"]
    note = "   (undefined: g_M = 0)" if not gt.loc["M", "g"] else ""
    print(f"\ng_P / g_M = {r:.2f} [{lo:.2f}, {hi:.2f}]   (H2a: > 1){note}\n")

    res = absorbing_analysis(transition_counts(df), alpha=a.smooth)
    print("Transition matrix (random walk down the tree):\n" + _fmt_tab(res["T"]))
    print("\nP(ending | current state):\n" + _fmt_tab(res["ending_probs"]))
    print("\nExpected further turns:\n" + res["expected_turns"].to_string(float_format=lambda v: f"{v:.2f}"))

    emp = chain_endings(df)
    print("\nEmpirical chain endings by opening state (row shares; check against the model above):")
    print(_fmt_tab(pd.crosstab(emp["opening_state"], emp["ending"], normalize="index")))

    oo = opening_outcomes(df)
    print("\nOpenings: delta rate and later punitive/repair by opening state:")
    print(_fmt_tab(oo.groupby("opening_state")[["delta", "any_P_later", "any_R_later", "subtree_size"]]
                   .agg(["mean"]).droplevel(1, axis=1).assign(n=oo.groupby("opening_state").size())))
    if a.out_dir:
        od = Path(a.out_dir)
        od.mkdir(parents=True, exist_ok=True)
        gt.to_csv(od / "gain.csv")
        res["T"].to_csv(od / "transitions.csv")
        res["ending_probs"].to_csv(od / "ending_probs.csv")
        emp.to_csv(od / "chain_endings.csv", index=False)
        oo.to_csv(od / "opening_outcomes.csv", index=False)
        ts.to_csv(od / "tree_shapes.csv", index=False)
        print(f"\ntables -> {od}/")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("load", help="ConvoKit corpus or CSV -> utterance table")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--corpus", help="ConvoKit corpus name, e.g. winning-args-corpus")
    g.add_argument("--csv", help="CSV with columns " + ", ".join(UTT_COLS))
    p.add_argument("--max-conversations", type=int, default=None)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", default="data/cmv_utts.parquet")
    p.add_argument("--keep-bots", action="store_true", help="keep DeltaBot/AutoModerator turns in the trees")
    p.set_defaults(fn=cmd_load)
    p = sub.add_parser("export", help="utterance table -> CSV for label_pilot.py")
    p.add_argument("--utts", default="data/cmv_utts.parquet")
    p.add_argument("--out", default="data/cmv_to_label.csv")
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("analyse", help="gain, Markov chain, endings, H2 opening table")
    p.add_argument("--utts", default="data/cmv_utts.parquet")
    p.add_argument("--labels", help="label_pilot.py output CSV")
    p.add_argument("--stub-labels", action="store_true", help="keyword heuristic, plumbing check only")
    p.add_argument("--n-boot", type=int, default=500)
    p.add_argument("--smooth", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out-dir", default=None)
    p.set_defaults(fn=cmd_analyse)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
