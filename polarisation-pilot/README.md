# Polarisation pilot: codebook v0 + 100-item labelling pilot

Built 3 Nov 2026. Purpose: test whether punitive expression (codebook v0) can be coded reliably and separated from non-punitive moral criticism, before the gold set (Dec) and V1 (Jan).

## Files

| File | What |
|---|---|
| `codebook_v0.2.md` | The current codebook (v0.2, after the methods review). Text between `PROMPT START` and `PROMPT END` (HTML comments stripped) is the LLM system prompt, so one file serves human and machine coders. `codebook_v0.md` is kept unchanged for the record. |
| `sample_bluesky.py` | Topic-stratified sample of 100 English Bluesky posts (9 strata, about half replies), with parent text. |
| `label_pilot.py` | Gold template, cost estimate, sync test, Batch API submit/fetch, Krippendorff's alpha with bootstrap CIs, alpha by stratum, confusion matrix, minimal-pair `flip-audit`. `--codebook` picks the codebook file. |
| `codebook_v0.2_dryrun.md`, `hard_cases_claude_v02_dryrun.csv` | Dry run of v0.2 on the 60 hard cases. The `expected_*` columns in `hard_cases.csv` are keyed to v0.1: re-key under v0.2 yourself **before** opening the dry-run CSV. |
| `LEARNING.md` | Rebuild path with hand exercises (α, gain g, the fold) and answers |
| `pilot_samples/` | 150 external Reddit comments (MFRC + CAD, CC BY 4.0) for hand-labelling, plus Claude's practice labels under v0.2. Read its README before opening the labels. |
| `tests/` | `python -m pytest tests` (mocked API, no network). |
| `requirements.txt` | Python dependencies. |

## Run order (Windows PowerShell)

```powershell
pip install -r requirements.txt

# 1. Sample (needs a Bluesky app password: Settings > Privacy and security > App passwords)
$env:BSKY_HANDLE="you.bsky.social"; $env:BSKY_APP_PASSWORD="xxxx-xxxx-xxxx-xxxx"
$env:PSEUDONYM_SALT="pick-a-random-string-and-keep-it"
python sample_bluesky.py --since 2026-10-01 --until 2026-11-01 --n 100 --seed 7

# 2. Hand-label FIRST, blind to the model
python label_pilot.py gold-template --coder jesse     # fill data/gold_jesse.csv

# 3. Model labels (needs a funded API key)
python label_pilot.py estimate
python label_pilot.py sync --limit 5                  # read the rationales before spending more
python label_pilot.py submit
python label_pilot.py status
python label_pilot.py fetch

# 4. Agreement
python label_pilot.py agree --a data/gold_jesse.csv --b data/llm_labels.csv
```

## Rules that protect validity

1. **Hand-label before you see model labels.** Otherwise the gold set anchors on Claude and the alpha is inflated.
2. **Freeze the codebook version per run.** `batch_state.json` records the codebook filename and sha256; `fetch` warns if the file has changed since submit. If you edit the codebook, rerun the batch.
3. **Don't estimate prevalence (D1) from this sample.** Keyword search selects on topic words. D1 needs a random Jetstream sample.
4. **One coder vs the LLM isn't intercoder reliability.** For V1 you need a second human on a subset (say 50 posts). Ask a coursemate early.
5. **`data/pilot_raw.jsonl` holds DIDs.** Keep it out of Git and the vault. Check the LIS ethics process before collecting beyond the pilot.

## What counts as a pass

| Measure | Pass | Fail → action |
|---|---|---|
| 1 vs 3 boundary alpha (strict: both coders in {1,3}) | ≥ 0.667, read with the bootstrap CI | Rewrite the 1/3 boundary rule; check `disagreements.csv` |
| Punitive yes/no alpha | ≥ 0.667 | Construct too vague; narrow it |
| Score (interval) alpha | ≥ 0.667 | Collapse the scale |
| Category 1 count | ≥ 10 of 100 | Too rare in this sample: oversample replies to contentious threads |

## Known gaps

- The sampler was tested against a mocked Bluesky client, not the live API (this workspace can't reach Bluesky). Run it once with `--n 18` first.
- The labeller was tested end to end with synthetic labels, not live API calls. `sync --limit 5` is the first real test.
- `DEFAULT_MODEL` in `label_pilot.py` may need changing to a model shown in your Console.
- Toxicity scoring and the random (non-keyword) sampler for D1 are in `tools/` (see `tools/TOOLS.md`). **Perspective API shuts down on 31 Dec 2026**: score anything you need before then, or use Detoxify.
- Conversation layer (CMV, gain g, cut/repaired chains as an absorbing Markov chain) is in `conversation/`: `chains.py`, 17 offline tests, and `H2_analysis_plan.md`. Plumbing checked on 50 live CMV conversations with stub labels; no real labels yet. The toy reservoir model is in `model/`.
