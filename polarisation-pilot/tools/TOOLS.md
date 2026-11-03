# D1 tools: random Jetstream sampler + toxicity scorer

Built 3 Nov 2026 to sit beside `polarisation-pilot/`. Same conventions: argparse CLI, usage in the docstring, `PSEUDONYM_SALT` from the environment, outputs in `data/`.

| File | What |
|---|---|
| `jetstream_sample.py` | Equal-probability sample of English posts from Jetstream over a time window, for prevalence (D1). |
| `score_toxicity.py` | `score`: adds `tox_*` columns (Detoxify, optional Perspective). `iceberg`: share of punitive posts (category 1 or 2) below a toxicity threshold, bootstrap 95% CI. |
| `tests/test_tools.py` | 34 offline pytest tests (synthetic Jetstream messages, fake scorers, a local websocket server). |
| `requirements.txt` | Dependencies. |

## Run order (Windows PowerShell)

```powershell
pip install -r requirements.txt
$env:PSEUDONYM_SALT="the-same-secret-salt-as-the-pilot"

# 1. Smoke test, then a real window
python jetstream_sample.py --minutes 2 --max-posts 50
python jetstream_sample.py --minutes 60 --p 0.1 --format parquet --seed 11

# 2. Label (label_pilot.py, or the distilled encoder later), then score
python score_toxicity.py score --input data\jetstream_X.parquet --output data\jetstream_tox.parquet --model unbiased

# Optional Perspective baseline (1 request per second: 10,000 posts is about 2.8 hours)
$env:PERSPECTIVE_API_KEY="..."
python score_toxicity.py score --input data\pilot_sample.csv --output data\pilot_tox.csv --perspective

# 3. Iceberg
python score_toxicity.py iceberg --labels data\llm_labels.csv --scores data\pilot_tox.csv `
    --score-col tox_detoxify_toxicity --thresholds 0.5 0.7 --by-category
# For a Jetstream sample, cluster by author:  --cluster-col did
```

Check `.meta.json` after every run: `kept / english_posts_seen` should be close to `--p`, and `deleted_during_run` lists posts to purge.

## Design choices worth knowing

- **English** means the post's self-declared `langs` includes `en` or `en-*`. Posts with no `langs` are excluded and counted. Self-tags are set by clients and are imperfect; check a sample by hand.
- **Pseudonymisation** covers the author and the DID inside every `at://` URI (`uri`, `parent_uri`, `root_uri`, `quote_uri`), using the pilot's `sha256(salt + did)[:12]`. Links within the dataset still join. The cost: you cannot rehydrate a parent's text from the API later. If you need parent text for D1, that is a design decision (store raw URIs privately), not a flag to flip casually.
- **`time_us` vs `created_at`.** `created_at` is client-claimed and can be backdated. Define windows on `time_us`.
- **Reconnects** use `cursor = last time_us - 3 s` and de-duplicate on URI, so a replay never re-rolls the thinning coin.
- **Empty text.** Image-only posts have empty `text`; Detoxify scores them near 0, so they inflate any "share below threshold". Drop or report them separately.
- **Unlabelled baseline.** `iceberg --all-posts` gives the share of *all* posts below each threshold (no labels needed). `score --drop-text` writes scores without the post text.
- **Iceberg CI** is a percentile bootstrap. `--cluster-col did` resamples authors instead of posts. Use it for Jetstream data, where heavy posters make posts non-independent; the test shows the naive CI can be several times too narrow.

## Methodological caveats (D1)

1. **A window is a cluster in time.** One 60-minute run is a random sample of that hour, not of the month. For D1, schedule many short windows spread over days of the week and hours (e.g. 24 x 15 minutes across a fortnight via Task Scheduler) and report the design.
2. **Post-weighted vs author-weighted prevalence** differ when heavy posters are more punitive. Report both.
3. **The iceberg inherits label error.** If category 1/2 comes from the LLM or encoder, the share below threshold is conditional on that classifier. Report it on the human gold set too, and propagate classifier uncertainty as the doc's DATA section already plans.
4. **Thresholds are conventions.** 0.5 and 0.7 are common, but report the full curve (share below t for t in 0 to 1) in the paper, so the result doesn't hang on one cut-off.
5. **The comparison that matters is 1 vs 4.** `--by-category` shows whether implicit punitive (1) sits below threshold more than identity hate (4) does. If 4 also sits mostly below, the claim collapses into "classifiers miss implicit content", which ElSherief et al. 2021 already showed.

## Ethics

- Raw outputs contain post text and pseudonyms. Keep them out of Git and the vault, as with `pilot_raw.jsonl`.
- Post text can be searched to re-identify authors, so pseudonyms are not anonymity. Quote paraphrased text in the paper.
- Purge `deleted_during_run` URIs, and plan a later deletion sweep for posts deleted after collection.
- Check the LIS ethics process before collecting beyond a smoke test; this is a larger, untargeted collection than the pilot.

## What is untested live

The sandbox could not reach Bluesky or Google. Tested offline only:

| Component | Tested with | Not yet verified |
|---|---|---|
| Jetstream v1 parsing | Synthetic messages from the Jetstream README field names, **and a live run on 3 Nov 2026** (6 x 5-minute windows on `jetstream2.us-east`, p = 0.1): kept/English matched p, zero reconnects | Eyeball 20 rows yourself before D1. |
| Reconnect + cursor | Fake socket that drops mid-stream | Real drops, and whether the public instance honours old cursors |
| `--protocol v2` | One documented v2 example | Everything. Use v1 (`jetstream1/2.*`) unless v1 is retired. |
| Detoxify | Mocked module, **and a live run** (detoxify 0.5.4, torch CPU): weights download, output keys match `tox_detoxify_*` above | GPU, and the `unbiased` head |
| Perspective | Fake HTTP (request body, 1 qps, 429 retry, 400 handling, cache) | A real key and response |

**Perspective deadline.** perspectiveapi.com says the service runs until 31 December 2026 and that it stopped taking new usage requests after February 2026. Your D1 is scheduled for January 2027. If you want Perspective at all, you need an existing key and must score everything before 31 December; otherwise Detoxify is the only baseline and the paper should say so.
