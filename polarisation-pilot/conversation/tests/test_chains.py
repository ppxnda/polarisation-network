"""Offline tests: hand-built trees with known answers, plus a simulated branching process with known gains."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chains as C  # noqa: E402


def tree(edges, states, conv="c1", texts=None, speakers=None):
    """edges: list of (id, parent or None)."""
    rows = []
    for i, p in edges:
        rows.append({"id": i, "conversation_id": conv, "reply_to": p, "state": states.get(i, "N"),
                     "speaker": (speakers or {}).get(i, "u_" + i), "text": (texts or {}).get(i, ""),
                     "timestamp": 0})
    return pd.DataFrame(rows)


# root -> a(P) -> b(N) -> c(R)        ending REPAIRED
#      -> d(M) -> e(P) -> f(N)        ending CUT (neutral after P remembers P)
#      -> g(N)                        ending OTHER
EDGES = [("root", None), ("a", "root"), ("b", "a"), ("c", "b"), ("d", "root"), ("e", "d"), ("f", "e"),
         ("g", "root")]
STATES = {"a": "P", "b": "N", "c": "R", "d": "M", "e": "P", "f": "N", "g": "N"}


def test_state_priority():
    assert C.state_from_label(2, 1) == "P"          # punitive beats repair
    assert C.state_from_label(3, "true") == "R"     # repair beats moral criticism
    assert C.state_from_label("3", 0) == "M"
    assert C.state_from_label(6, 0) == "N"
    assert C.state_from_label(None, None) == "N"


def test_chain_endings_hand_tree():
    df = tree(EDGES, STATES)
    e = C.chain_endings(df).set_index("leaf")
    assert e.loc["c", "ending"] == "REPAIRED"
    assert e.loc["f", "ending"] == "CUT"
    assert e.loc["g", "ending"] == "OTHER"
    assert e.loc["f", "opening_state"] == "M"
    assert e.loc["c", "length"] == 3


def test_gain_hand_tree():
    df = tree(EDGES, STATES)
    g = C.gain_table(df)
    # M-nodes: d has one P child -> g_M = 1. P-nodes: a (child N), e (child N) -> g_P = 0.
    assert g.loc["M", "g"] == 1.0
    assert g.loc["P", "g"] == 0.0
    assert g.loc["P", "mean_replies"] == 1.0


def test_absorbing_rows_sum_to_one_and_match_paths():
    df = tree(EDGES, STATES)
    res = C.absorbing_analysis(C.transition_counts(df))
    B = res["ending_probs"].dropna()
    assert np.allclose(B.sum(axis=1), 1.0)
    # The chain pools the two P turns (a ends REPAIRED, e ends CUT), so from P it is 50/50, and M (whose only
    # move is to P) inherits that. This is the Markov assumption at work: history before the last state is lost
    # except for the "last informative" memory carried by NP/NR.
    assert B.loc["P", "CUT"] == pytest.approx(0.5)
    assert B.loc["M", "CUT"] == pytest.approx(0.5)
    assert B.loc["NP", "CUT"] == pytest.approx(0.5)


def test_deltas_only_from_op():
    df = tree([("r", None), ("x", "r"), ("y", "x"), ("z", "x")], {},
              texts={"y": "Fair, Δ for you", "z": "!delta lol"},
              speakers={"r": "op", "y": "op", "z": "someone"})
    df = C.mark_deltas(df)
    assert df.set_index("id").loc["y", "delta_award"]
    assert not df.set_index("id").loc["z", "delta_award"]
    oo = C.opening_outcomes(df.assign(state="N"))
    assert oo.set_index("opening_id").loc["x", "delta"]


def test_clean_drops_orphans_recursively():
    df = pd.DataFrame({"id": ["r", "a", "b"], "conversation_id": "c", "reply_to": [None, "gone", "a"],
                       "speaker": "s", "text": "", "timestamp": 0})
    out = C.clean(df)
    assert list(out["id"]) == ["r"]


def simulate(n_conv, kids_mean, p_child, seed=0, max_depth=8):
    """Branching process: each reply has Poisson(kids_mean[s]) children with state ~ p_child[s]."""
    rng = np.random.default_rng(seed)
    rows = []
    states = list(p_child)
    for c in range(n_conv):
        root = f"c{c}_r"
        rows.append({"id": root, "conversation_id": f"c{c}", "reply_to": None, "state": "N"})
        frontier = []
        for k in range(rng.poisson(3) + 1):
            s = rng.choice(states, p=[0.25, 0.25, 0.1, 0.4])
            i = f"{root}_{k}"
            rows.append({"id": i, "conversation_id": f"c{c}", "reply_to": root, "state": s})
            frontier.append((i, s, 1))
        while frontier:
            i, s, d = frontier.pop()
            if d >= max_depth:
                continue
            for k in range(rng.poisson(kids_mean[s])):
                s2 = rng.choice(states, p=p_child[s])
                j = f"{i}_{k}"
                rows.append({"id": j, "conversation_id": f"c{c}", "reply_to": i, "state": s2})
                frontier.append((j, s2, d + 1))
    df = pd.DataFrame(rows)
    df["speaker"], df["text"], df["timestamp"] = "s", "", 0
    return df


def test_gain_recovered_from_simulation():
    kids = {"P": 0.9, "M": 0.6, "R": 0.4, "N": 0.5}
    pc = {"P": [0.5, 0.2, 0.1, 0.2], "M": [0.2, 0.3, 0.1, 0.4], "R": [0.05, 0.15, 0.3, 0.5],
          "N": [0.1, 0.2, 0.1, 0.6]}
    df = simulate(400, kids, pc, seed=1, max_depth=50)
    g = C.gain_table(df)
    # true g_s = kids_mean[s] * P(child = P | s)
    assert g.loc["P", "g"] == pytest.approx(0.9 * 0.5, abs=0.05)
    assert g.loc["M", "g"] == pytest.approx(0.6 * 0.2, abs=0.03)
    assert g.loc["P", "share_P"] == pytest.approx(0.5, abs=0.05)


def test_cluster_bootstrap_ci_covers_truth():
    kids = {"P": 0.9, "M": 0.6, "R": 0.4, "N": 0.5}
    pc = {"P": [0.5, 0.2, 0.1, 0.2], "M": [0.2, 0.3, 0.1, 0.4], "R": [0.05, 0.15, 0.3, 0.5],
          "N": [0.1, 0.2, 0.1, 0.6]}
    df = simulate(150, kids, pc, seed=3, max_depth=50)
    t = C.gain_with_ci(df, n_boot=150, seed=0)
    assert t.loc["P", "g_lo"] <= 0.45 <= t.loc["P", "g_hi"]
    r, lo, hi = t.attrs["gP_over_gM"]
    assert lo <= 0.45 / 0.12 * 1.6 and hi >= 0.45 / 0.12 * 0.6


def test_markov_matches_empirical_endings():
    kids = {"P": 0.7, "M": 0.6, "R": 0.4, "N": 0.6}
    pc = {"P": [0.4, 0.2, 0.1, 0.3], "M": [0.2, 0.3, 0.1, 0.4], "R": [0.05, 0.15, 0.3, 0.5],
          "N": [0.1, 0.2, 0.1, 0.6]}
    df = simulate(600, kids, pc, seed=2, max_depth=60)
    model = C.absorbing_analysis(C.transition_counts(df))["ending_probs"]
    emp = C.chain_endings(df)
    # Chains weighted by random-walk probability = 1/prod(branching) is what the model predicts; compare on
    # single-child-or-leaf conversations is too strict, so check ordering, which is what H2 uses.
    assert model.loc["P", "CUT"] > model.loc["M", "CUT"] > model.loc["R", "CUT"]
    assert model.loc["R", "REPAIRED"] > model.loc["P", "REPAIRED"]
    shares = pd.crosstab(emp["opening_state"], emp["ending"], normalize="index")
    assert shares.loc["P", "CUT"] > shares.loc["R", "CUT"]


def test_export_roundtrip(tmp_path):
    df = tree(EDGES, STATES, texts={"a": "hello", "root": "my view"})
    n = C.export_for_labelling(df, tmp_path / "x.csv")
    out = pd.read_csv(tmp_path / "x.csv", keep_default_na=False)
    assert n == 7 and "root" not in set(out["post_id"])
    assert out.set_index("post_id").loc["a", "parent_text"] == "my view"


def test_attach_states_from_label_csv():
    df = tree(EDGES, {})
    labels = pd.DataFrame({"post_id": ["a", "c", "d"], "category": [2, 6, 3], "repair_attempt": [0, 1, 0]})
    out = C.attach_states(df, labels).set_index("id")
    assert out.loc["a", "state"] == "P" and out.loc["c", "state"] == "R" and out.loc["d", "state"] == "M"
    assert out.loc["g", "state"] == "N" and not out.loc["g", "labelled"]
