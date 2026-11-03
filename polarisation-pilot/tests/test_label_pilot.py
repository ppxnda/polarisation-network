"""Tests for label_pilot.py against codebook v0.2. Synthetic data and a mocked Anthropic client; no network."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import label_pilot as lp  # noqa: E402

HARD_CASES = Path("/home/claude/bg/codebook/hard_cases.csv")


# ---------------------------------------------------------------------------- fixtures and fakes
@pytest.fixture
def tmp_data(tmp_path, monkeypatch):
    """Redirect every write the script makes into a temporary data dir (never the real data/)."""
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setattr(lp, "DATA", d)
    monkeypatch.setattr(lp, "BATCH_STATE", d / "batch_state.json")
    return d


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> Path:
    fields = fields or list(rows[0])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return path


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_label(category=3, score=0, identity=False, sanction="none", rel="na", **feat):
    return {
        "identity_attack": identity, "category": category, "punitive_score": score, "sanction_named": sanction,
        "implied_sanction": False, "sarcasm": False,
        "features": {f: bool(feat.get(f, False)) for f in lp.FEATURES},
        "relational_features": {f: rel for f in lp.RELATIONAL},
        "addressivity": "about", "target_type": "individual", "blame_target": "a minister",
        "topic": "politics_domestic", "confidence": "high", "rationale": "Synthetic.",
    }


class FakeMessages:
    def __init__(self, labeller):
        self.labeller = labeller
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        content = kw["messages"][0]["content"]
        text = re.search(r"<target_post>\n(.*?)\n</target_post>", content, re.S).group(1)
        block = SimpleNamespace(type="tool_use", input=self.labeller(text, content))
        return SimpleNamespace(content=[block], usage=SimpleNamespace(input_tokens=12, cache_read_input_tokens=0))


class FakeBatches:
    def __init__(self):
        self.requests = None

    def create(self, requests):
        self.requests = requests
        return SimpleNamespace(id="msgbatch_test")


class FakeClient:
    def __init__(self, labeller):
        self.messages = FakeMessages(labeller)
        self.messages.batches = FakeBatches()


# ---------------------------------------------------------------------------- prompt extraction
def test_prompt_extraction_from_v02_markers(capsys):
    system = lp.load_codebook()  # default is codebook_v0.2.md
    assert lp.CODEBOOK.name == "codebook_v0.2.md"
    assert system.startswith("You are a careful content-analysis coder.")
    body = system.split("\n\n", 1)[1]
    assert body.startswith("# Codebook: punitive expression in social media posts")
    assert "## 10. Calibration examples" in body  # examples are inside the prompt now
    for leak in ["<!--", "DECISION NEEDED", "Changelog", "Why this codebook exists", "Drafting calls",
                 "hard_cases", "PROMPT END"]:
        assert leak not in body, leak
    assert capsys.readouterr().err == ""  # every schema field is mentioned in the prompt


def test_prompt_markers_required_and_comments_stripped():
    with pytest.raises(ValueError):
        lp.extract_prompt("no markers here")
    txt = ("pre mentions `<!-- PROMPT START -->` inline\n<!-- PROMPT START -->\nA <!-- hidden\nnote --> B\n"
           "<!-- PROMPT END -->\npost")
    assert lp.extract_prompt(txt) == "A B"


def test_old_codebook_warns_about_schema(capsys):
    lp.load_codebook(ROOT / "codebook_v0.md")
    assert "does not mention schema fields" in capsys.readouterr().err


def test_v0_codebook_unchanged_markers_still_present():
    assert "<!-- PROMPT START -->" in (ROOT / "codebook_v0.md").read_text(encoding="utf-8")


def test_codebook_style_no_dashes():
    txt = (ROOT / "codebook_v0.2.md").read_text(encoding="utf-8")
    assert "\u2014" not in txt and "\u2013" not in txt


# ---------------------------------------------------------------------------- schema
def test_schema_is_json_serialisable_and_complete():
    js = json.loads(json.dumps(lp.LABEL_TOOL))
    schema = js["input_schema"]
    props, req = schema["properties"], schema["required"]
    assert set(req) <= set(props)
    assert set(req) == set(props)  # every field is required
    assert props["category"]["enum"] == [1, 2, 3, 5, 6]
    assert props["sanction_named"]["enum"] == ["none", "proportionate", "exclusionary", "harm"]
    assert props["addressivity"]["enum"] == ["addressed", "tagged_about", "about", "none"]
    assert set(props["features"]["required"]) == set(lp.FEATURES)
    rel = props["relational_features"]
    assert set(rel["required"]) == set(lp.RELATIONAL)
    assert all(rel["properties"][f]["enum"] == ["true", "false", "na"] for f in lp.RELATIONAL)
    for gone in ["contested_claim_as_fact", "spoken_about_not_to", "target_in_out_group",
                 "identity_and_conduct_mixed"]:
        assert gone not in json.dumps(js)


def test_schema_validates_example_label():
    jsonschema = pytest.importorskip("jsonschema")
    schema = lp.LABEL_TOOL["input_schema"]
    jsonschema.validate(make_label(category=2, score=3, identity=True, sanction="harm"), schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(make_label(category=4), schema)  # category 4 retired
    bad = make_label()
    bad["relational_features"]["stonewalling"] = None
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_request_params_shape():
    row = {"post_id": "p1", "text": "hello", "parent_text": ""}
    params = lp.request_params(row, "m", "SYS")
    json.dumps(params)
    assert params["tool_choice"] == {"type": "tool", "name": "record_label"}
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert "relational feature as na" in params["messages"][0]["content"]
    with_parent = lp.user_message({"text": "t", "parent_text": "p"})
    assert "<parent_post" in with_parent and "as na" not in with_parent


# ---------------------------------------------------------------------------- flatten
def test_flatten_with_na_and_forced_na():
    lab = make_label(category=1, score=2, identity=True, sanction="proportionate", rel="true", contempt=True)
    lab["relational_features"]["stonewalling"] = "false"
    lab["relational_features"]["repair_rejected"] = "na"
    row = lp.flatten("p1", lab, parent=True)
    assert set(row) == set(lp.LABEL_COLUMNS)
    assert row["identity_attack"] == 1 and row["category"] == 1 and row["sanction_named"] == "proportionate"
    assert row["contempt"] == 1 and row["dehumanising"] == 0
    assert (row["defensiveness"], row["stonewalling"], row["repair_rejected"]) == (1, 0, lp.NA)
    forced = lp.flatten("p2", lab, parent=False)  # no parent: model output is overridden
    assert all(forced[f] == lp.NA for f in lp.RELATIONAL)
    # nullable booleans are accepted too
    lab["relational_features"] = {"defensiveness": True, "stonewalling": None, "repair_rejected": False}
    row = lp.flatten("p3", lab)
    assert (row["defensiveness"], row["stonewalling"], row["repair_rejected"]) == (1, lp.NA, 0)


def test_na_is_missing_in_alpha():
    assert lp._num("NA") != lp._num("NA") and lp._num("") != lp._num("")
    assert lp._num("true") == 1.0 and lp._num("0") == 0.0
    a = [1, 0, "NA", 1, 0, "NA"]
    b = [1, 0, 1, 1, 0, "NA"]
    _al, n = lp.alpha(a, b, "nominal")
    assert n == 4


# ---------------------------------------------------------------------------- agree
LABEL_FIELDS = lp.LABEL_COLUMNS


def synthetic_pair(n=40):
    """Two coders, mostly agreeing; some 1 vs 3 and 1 vs 2 disagreements; two strata."""
    A, B = [], []
    cats = [1, 2, 3, 5, 6]
    for i in range(n):
        ca = cats[i % 5]
        cb = ca
        if i % 9 == 0 and ca == 1:
            cb = 3
        if i % 11 == 0 and ca == 2:
            cb = 1
        sa = {1: 1, 2: 3, 3: 0, 5: 0, 6: -1}[ca]
        sb = sa if i % 7 else sa + 1
        ida = int(i % 4 == 0)
        idb = ida if i % 13 else 1 - ida
        rel = lp.NA if i % 2 else (i % 3 == 0)
        san = lp.SANCTIONS[i % 4]
        for out, c, s, idt in ((A, ca, sa, ida), (B, cb, sb, idb)):
            row = {k: "" for k in LABEL_FIELDS}
            row.update({"post_id": f"p{i:04d}", "category": c, "punitive_score": s, "identity_attack": idt,
                        "sanction_named": san, "addressivity": "about", "implied_sanction": 0, "sarcasm": 0})
            for f in lp.FEATURES:
                row[f] = int((i + len(f)) % 3 == 0)
            for f in lp.RELATIONAL:
                row[f] = rel if rel == lp.NA else int(rel)
            out.append(row)
    return A, B


def test_agreement_report_ci_and_strata():
    A, B = synthetic_pair()
    Ad = {r["post_id"]: {k: str(v) for k, v in r.items()} for r in A}
    Bd = {r["post_id"]: {k: str(v) for k, v in r.items()} for r in B}
    strata = {pid: ("left" if int(pid[1:]) % 2 else "right") for pid in Ad}
    rep = lp.agreement_report(Ad, Bd, strata, n_boot=200, seed=1)
    names = [m["measure"] for m in rep["main"]]
    for want in ["category (5-way, nominal)", "punitive yes/no (cat 1-2 vs rest)", "punitive_score (interval)",
                 "1 vs 3 strict (both coders in {1,3})", "1 vs 3 either (either coder in {1,3})",
                 "identity_attack", "sanction_named (nominal)"]:
        assert want in names
    for m in rep["main"]:
        if m["alpha"] == m["alpha"] and m["ci_low"] == m["ci_low"]:
            assert m["ci_low"] <= m["alpha"] + 1e-9 and m["alpha"] <= m["ci_high"] + 1e-9
    strict = next(m for m in rep["main"] if m["measure"].startswith("1 vs 3 strict"))
    either = next(m for m in rep["main"] if m["measure"].startswith("1 vs 3 either"))
    n_strict = sum(1 for a, b in zip(A, B) if a["category"] in (1, 3) and b["category"] in (1, 3))
    n_either = sum(1 for a, b in zip(A, B) if a["category"] in (1, 3) or b["category"] in (1, 3))
    assert strict["n"] == n_strict and either["n"] == n_either and n_either > n_strict
    assert set(rep["strata"]) == {"left", "right"}
    assert sum(s["n"] for s in rep["strata"].values()) == 40
    rel = next(f for f in rep["features"] if f["measure"] == "feature: stonewalling")
    assert rel["n"] == 20  # NA rows are missing, not false
    assert "4" not in rep["confusion"]["cats"]


def test_bootstrap_is_seeded():
    A, B = synthetic_pair()
    a = [r["category"] for r in A]
    b = [r["category"] for r in B]
    assert lp.alpha_ci(a, b, "nominal", n_boot=300, seed=5) == lp.alpha_ci(a, b, "nominal", n_boot=300, seed=5)


def test_punitive_ignores_identity_attack():
    A = {"p1": {"category": "2", "identity_attack": "1"}, "p2": {"category": "5", "identity_attack": "1"},
         "p3": {"category": "1", "identity_attack": "0"}}
    assert [lp._punitive(A[k]["category"]) for k in ("p1", "p2", "p3")] == [1.0, 0.0, 1.0]


def test_cmd_agree_end_to_end_with_sample_strata(tmp_data, capsys):
    A, B = synthetic_pair()
    pa = write_csv(tmp_data / "gold_a.csv", A, LABEL_FIELDS)
    pb = write_csv(tmp_data / "llm.csv", B, LABEL_FIELDS)
    sample = write_csv(tmp_data / "pilot_sample.csv",
                       [{"post_id": r["post_id"], "stratum": "immigration" if i < 20 else "sport",
                         "is_reply": "0", "text": f"t{i}", "parent_text": ""} for i, r in enumerate(A)])
    lp.main(["agree", "--a", str(pa), "--b", str(pb), "--sample", str(sample), "--n-boot", "100", "--seed", "3"])
    out = capsys.readouterr().out
    assert "95% CI" in out and "1 vs 3 strict" in out and "1 vs 3 either" in out
    assert "identity_attack" in out and "sanction_named" in out
    assert "[immigration] n=20" in out and "[sport] n=20" in out
    assert "alpha >= 0.667" in out
    dis = read_csv(tmp_data / "disagreements.csv")
    assert dis and {"stratum", "identity_A", "identity_B"} <= set(dis[0])
    assert {d["stratum"] for d in dis} <= {"immigration", "sport"}


def test_cmd_agree_without_strata(tmp_data, capsys):
    A, B = synthetic_pair(20)
    pa = write_csv(tmp_data / "a.csv", A, LABEL_FIELDS)
    pb = write_csv(tmp_data / "b.csv", B, LABEL_FIELDS)
    lp.main(["agree", "--a", str(pa), "--b", str(pb), "--sample", str(tmp_data / "missing.csv"), "--n-boot", "50"])
    assert "skipping alpha by stratum" in capsys.readouterr().out


# ---------------------------------------------------------------------------- flip audit
def minimal_pairs():
    return [
        {"pair_id": "party-01", "variant": "L", "text": "Typical Red voters, liars.", "parent_text": ""},
        {"pair_id": "party-01", "variant": "R", "text": "Typical Blue voters, liars.", "parent_text": ""},
        {"pair_id": "party-02", "variant": "L", "text": "Red MP should be shunned forever.", "parent_text": ""},
        {"pair_id": "party-02", "variant": "R", "text": "Blue MP should resign.", "parent_text": ""},
        {"pair_id": "dialect-01", "variant": "std", "text": "He is lying.", "parent_text": "Claim posted."},
        {"pair_id": "dialect-01", "variant": "mle", "text": "Man's chatting breeze.", "parent_text": "Claim posted."},
    ]


def test_flip_audit_with_existing_labels(tmp_data, capsys):
    pairs = write_csv(tmp_data / "pairs.csv", minimal_pairs())
    labs = []
    for r in minimal_pairs():
        cat, score, san = 3, 1, "none"
        if r["pair_id"] == "party-02":
            cat, score, san = (2, 3, "exclusionary") if r["variant"] == "L" else (3, 0, "proportionate")
        row = {k: "" for k in LABEL_FIELDS}
        row.update({"pair_id": r["pair_id"], "variant": r["variant"], "category": cat, "punitive_score": score,
                    "identity_attack": 0, "sanction_named": san})
        labs.append(row)
    lab_path = write_csv(tmp_data / "labels.csv", labs, ["pair_id", "variant"] + LABEL_FIELDS)
    out = tmp_data / "flip.csv"
    lp.main(["flip-audit", "--pairs", str(pairs), "--labels", str(lab_path), "--out", str(out)])
    printed = capsys.readouterr().out
    detail = {r["pair_id"]: r for r in read_csv(out)}
    assert detail["party-01"]["category_flip"] == "0"
    assert detail["party-02"]["category_flip"] == "1" and detail["party-02"]["punitive_flip"] == "1"
    assert detail["party-02"]["sanction_flip"] == "1" and float(detail["party-02"]["score_range"]) == 3.0
    assert detail["dialect-01"]["category_flip"] == "0"
    assert re.search(r"party\s+2\s+0\.50\s+0\.50", printed) and "above 10%" in printed
    assert re.search(r"dialect\s+1\s+0\.00", printed)


def test_flip_audit_pure_function_types_and_missing():
    pairs = [dict(r, pair_type="swap") for r in minimal_pairs()[:2]] + [
        {"pair_id": "solo", "variant": "a", "text": "x", "parent_text": ""}]
    labels = {lp.pair_key("party-01", "L"): {"category": "1", "identity_attack": "", "punitive_score": "1"},
              lp.pair_key("party-01", "R"): {"category": "1", "identity_attack": "", "punitive_score": "2"}}
    per_pair, summary = lp.flip_audit(pairs, labels)
    assert len(per_pair) == 1  # 'solo' has one variant and no label
    assert per_pair[0]["pair_type"] == "swap" and per_pair[0]["identity_flip"] == 0  # missing == missing
    assert summary[0]["category_flip_rate"] == 0.0 and summary[0]["mean_score_range"] == 1.0
    assert lp.pair_type_of({"pair_id": "nosep"}) == "all"


def test_flip_audit_with_mocked_model(tmp_data, monkeypatch, capsys):
    def labeller(text, content):
        # Party-biased fake coder: punishes 'Red' harder.
        if "Red" in text:
            return make_label(category=2, score=3, sanction="exclusionary", rel="true")
        return make_label(category=3, score=0, rel="true")
    fake = FakeClient(labeller)
    monkeypatch.setattr(lp, "client", lambda: fake)
    pairs = write_csv(tmp_data / "pairs.csv", minimal_pairs())
    out = tmp_data / "flip.csv"
    lp.main(["flip-audit", "--pairs", str(pairs), "--out", str(out), "--limit", "10"])
    assert len(fake.messages.calls) == 6
    labels = {r["post_id"]: r for r in read_csv(tmp_data / "flip_labels.csv")}
    assert labels["party-01:L"]["stonewalling"] == lp.NA  # no parent: forced NA despite model saying true
    assert labels["dialect-01:std"]["stonewalling"] == "1"  # parent present: kept
    detail = {r["pair_id"]: r for r in read_csv(out)}
    assert detail["party-01"]["category_flip"] == "1" and detail["dialect-01"]["category_flip"] == "0"
    assert re.search(r"party\s+2\s+1\.00\s+1\.00", capsys.readouterr().out)


def test_flip_audit_limit_guard(tmp_data, monkeypatch):
    monkeypatch.setattr(lp, "client", lambda: pytest.fail("should not call the API"))
    pairs = write_csv(tmp_data / "pairs.csv", minimal_pairs())
    with pytest.raises(SystemExit):
        lp.main(["flip-audit", "--pairs", str(pairs), "--limit", "2", "--out", str(tmp_data / "f.csv")])


# ---------------------------------------------------------------------------- sync, submit, gold template
def sample_rows():
    return [{"post_id": "p0001", "stratum": "sport", "is_reply": "1", "text": "Ref is blind", "parent_text": "Match"},
            {"post_id": "p0002", "stratum": "immigration", "is_reply": "0", "text": "Send them back", "parent_text": ""}]


def test_sync_with_mocked_client(tmp_data, monkeypatch, capsys):
    fake = FakeClient(lambda text, content: make_label(category=5, rel="false"))
    monkeypatch.setattr(lp, "client", lambda: fake)
    sample = write_csv(tmp_data / "pilot_sample.csv", sample_rows())
    lp.main(["sync", "--sample", str(sample), "--limit", "2"])
    rows = read_csv(tmp_data / "llm_labels_sync.csv")
    assert list(rows[0]) == lp.LABEL_COLUMNS
    assert rows[0]["stonewalling"] == "0" and rows[1]["stonewalling"] == lp.NA
    sys_text = fake.messages.calls[0]["system"][0]["text"]
    assert "## 10. Calibration examples" in sys_text


def test_submit_records_codebook_sha(tmp_data, monkeypatch):
    fake = FakeClient(lambda *a: make_label())
    monkeypatch.setattr(lp, "client", lambda: fake)
    sample = write_csv(tmp_data / "pilot_sample.csv", sample_rows())
    lp.main(["submit", "--sample", str(sample)])
    state = json.loads((tmp_data / "batch_state.json").read_text())
    cb = ROOT / "codebook_v0.2.md"
    assert state["codebook"] == "codebook_v0.2.md"
    assert state["codebook_sha256"] == hashlib.sha256(cb.read_bytes()).hexdigest()
    assert "codebook_mtime" not in state and state["no_parent_ids"] == ["p0002"]
    assert len(fake.messages.batches.requests) == 2


def test_codebook_argument(tmp_data, monkeypatch, tmp_path):
    custom = tmp_path / "cb.md"
    custom.write_text((ROOT / "codebook_v0.2.md").read_text(encoding="utf-8").replace(
        "# Codebook: punitive", "# Codebook CUSTOM: punitive"), encoding="utf-8")
    fake = FakeClient(lambda *a: make_label())
    monkeypatch.setattr(lp, "client", lambda: fake)
    sample = write_csv(tmp_data / "pilot_sample.csv", sample_rows())
    lp.main(["sync", "--sample", str(sample), "--limit", "1", "--codebook", str(custom)])
    assert "CUSTOM" in fake.messages.calls[0]["system"][0]["text"]
    lp.main(["submit", "--sample", str(sample), "--codebook", str(custom)])
    assert json.loads((tmp_data / "batch_state.json").read_text())["codebook"] == "cb.md"


def test_gold_template_columns(tmp_data):
    sample = write_csv(tmp_data / "pilot_sample.csv", sample_rows())
    lp.main(["gold-template", "--coder", "test", "--sample", str(sample)])
    rows = read_csv(tmp_data / "gold_test.csv")
    header = list(rows[0])
    assert header == ["post_id", "text", "parent_text"] + lp.LABEL_COLUMNS[1:]
    for col in ["identity_attack", "sanction_named", "implied_sanction", "sarcasm", "unhedged_allegation",
                "audience_call", "repair_rejected", "addressivity"]:
        assert col in header
    for col in ["stratum", "target_in_out_group", "contested_claim_as_fact", "spoken_about_not_to",
                "identity_and_conduct_mixed"]:
        assert col not in header
    assert rows[0]["stonewalling"] == "" and rows[1]["stonewalling"] == lp.NA  # pre-filled NA without parent
    with pytest.raises(SystemExit):
        lp.main(["gold-template", "--coder", "test", "--sample", str(sample)])  # refuses to overwrite


# ---------------------------------------------------------------------------- hard-case coverage
def calibration_rows(prompt: str) -> list[list[str]]:
    sec = prompt.split("## 10. Calibration examples", 1)[1].split("## 11.", 1)[0]
    rows = [ln for ln in sec.splitlines() if ln.startswith("| ") and not ln.startswith("| Boundary")]
    return [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in rows]


# hard_cases.csv boundary type -> calibration-table boundary tag in v0.2 (cat 4 is now the identity axis)
BOUNDARY_MAP = {"1v3": "1v3", "1v2": "1v2", "1/2v4": "identity", "3v5": "3v5", "sarcasm": "sarcasm",
                "accountability": "accountability", "repair": "repair"}


@pytest.mark.skipif(not HARD_CASES.exists(), reason="hard_cases.csv not available")
def test_every_hard_case_boundary_is_covered_in_prompt():
    prompt = lp.load_codebook()
    rows = calibration_rows(prompt)
    assert len(rows) >= 20
    assert all(len(r) == 7 for r in rows), "calibration table rows must have 7 cells"
    tags = {r[0] for r in rows}
    cats = {r[3] for r in rows}
    assert cats <= {"1", "2", "3", "5", "6"}
    types = {r["boundary_tested"] for r in read_csv(HARD_CASES)}
    missing = [t for t in types if BOUNDARY_MAP.get(t, t) not in tags]
    assert not missing, f"no calibration example for boundary types {missing}"
    # Each boundary also has a rule in the prompt body.
    rules = {"1v3": "**1 vs 3", "1v2": "**1 vs 2.**", "identity": "## 3. Identity attack", "3v5": "**3 vs 5.**",
             "sarcasm": "**Sarcasm and irony.**", "accountability": "**Accountability", "repair": "Active repair"}
    for tag, marker in rules.items():
        assert marker in prompt, tag


@pytest.mark.skipif(not HARD_CASES.exists(), reason="hard_cases.csv not available")
def test_no_hard_case_text_in_prompt():
    norm = lambda s: re.sub(r"\s+", " ", s.lower()).strip()
    prompt = norm(lp.load_codebook())
    leaked = [r["case_id"] for r in read_csv(HARD_CASES) if norm(r["text"]) in prompt]
    assert not leaked, f"held-out hard cases copied into the prompt: {leaked}"
