# Tool validation run, 3 Nov 2026

A tool-validation run, not a dataset. It checks that the Jetstream sampler, Detoxify scoring and the CMV conversation pipeline run on live data. **None of these numbers is a finding.** The Jetstream shares cover all English posts, unlabelled; the CMV tables use the keyword stub, not codebook labels. The fixes are in `ppxnda/polarisation-network#3`.

## 1. Jetstream + Detoxify

**Design.** Six 5-minute windows on `wss://jetstream2.us-east.bsky.network` (protocol v1), starting every 10 minutes from 19:38 to 20:28 UTC on 3 Nov 2026 (a Tuesday evening in Europe). The keep probability was p = 0.1, with seeds 101 to 106. One throwaway pseudonym salt was used across the windows (so authors join across them), and it does not match the pilot's. Posts deleted during the run were purged. The scoring model was Detoxify `original` 0.5.4 on CPU, using `tox_detoxify_toxicity`. Raw text was deleted after scoring.

**Sampler checks.**

| Window | Start (UTC) | English seen | Kept | Kept / English | Reconnects | Duplicates | Purged (deleted) |
|---|---|---|---|---|---|---|---|
| 1 | 19:38:19 | 10,287 | 1,020 | 0.099 | 0 | 0 | 9 |
| 2 | 19:48:19 | 10,500 | 1,048 | 0.100 | 0 | 0 | 13 |
| 3 | 19:58:20 | 10,899 | 1,088 | 0.100 | 0 | 0 | 12 |
| 4 | 20:08:20 | 10,216 | 1,036 | 0.101 | 0 | 0 | 14 |
| 5 | 20:18:20 | 10,370 | 1,048 | 0.101 | 0 | 0 | 11 |
| 6 | 20:28:21 | 10,417 | 998 | 0.096 | 0 | 1 | 12 |
| **Total** | | 62,689 | 6,238 | 0.0995 | 0 | 1 | 71 |

After purging, 6,167 posts remained, from 5,547 distinct authors (at most 12 posts per author). 4.7% (288 posts) had empty text, which means image-only posts.

**Share of posts below each Detoxify threshold.** The 95% CIs are percentile bootstraps with 4,000 resamples of authors (`--cluster-col did`).

| Posts | n | < 0.5 | 95% CI | < 0.7 | 95% CI |
|---|---|---|---|---|---|
| All posts | 6,167 | 0.917 | 0.910 to 0.924 | 0.936 | 0.930 to 0.942 |
| Non-empty text | 5,879 | 0.913 | 0.906 to 0.921 | 0.933 | 0.926 to 0.939 |
| Non-empty, naive (post) bootstrap | 5,879 | 0.913 | 0.906 to 0.920 | 0.933 | 0.927 to 0.939 |

The author-weighted share below 0.5 (non-empty text, each author counted once) is 0.913.

**By window (non-empty text).**

| Window | n | < 0.5 | < 0.7 |
|---|---|---|---|
| 1 | 964 | 0.906 | 0.925 |
| 2 | 977 | 0.902 | 0.928 |
| 3 | 1,026 | 0.923 | 0.943 |
| 4 | 978 | 0.925 | 0.938 |
| 5 | 984 | 0.910 | 0.931 |
| 6 | 950 | 0.913 | 0.933 |

**Reading it.**
- These are shares of **all** posts, not of punitive posts, so this is the baseline the iceberg statistic will be compared against.
- **Author clustering barely changes the CI here**, because at p = 0.1 over 30 minutes almost every author appears once. It will matter for longer windows or a higher p.
- **The window-to-window range (0.902 to 0.925) is about what sampling noise gives** at about 970 posts per window (SE about 0.009). Six windows in one evening say nothing about day-of-week or time-of-day variation (TOOLS.md, caveat 1).
- **Image-only posts score near 0** and add about 0.4 percentage points to the share below 0.5. Exclude them, or report them separately.

## 2. ConvoKit CMV (Winning Args), `chains.py --stub-labels`

**Design.** 50 conversations drawn at random (`--seed 7`) from `winning-args-corpus`, using `load --max-conversations 50`, then `analyse --stub-labels --n-boot 100`. The stub is a keyword heuristic, used here only to check the pipeline.

**Load.**

| | |
|---|---|
| Utterances after cleaning | 3,942 (50 conversations) |
| Bot turns removed (DeltaBot, AutoModerator) | 116 |
| OP delta awards | 96 |
| DeltaBot-confirmed OP awards | 83 |
| Delta-token recall against DeltaBot | 100% (was 60% before the fix) |

**Deletion.**

| | |
|---|---|
| Replies that are `[deleted]` tombstones | 86 / 3,892 (2.2%) |
| Openings that are tombstones | 29 / 741 (3.9%) |
| Tombstones with replies | 70 |
| Orphans (parent missing) | 0 |
| Author account deleted, text kept | 105 |
| Moderator removal notices | 16 (Rule 1: 7, Rule 5: 5, Rule 2: 3, unparsed: 1) |

Reddit shows both user deletions and moderator removals as `[deleted]`. Only 3 tombstones carry a Rule 2 (rude/hostile) notice, so most deletion here cannot be attributed to Rule 2 moderation.

**Tree shapes (per conversation).**

| | Mean | Min | Median | Max |
|---|---|---|---|---|
| Utterances | 78.8 | 17 | 47.5 | 445 |
| Openings (top-level replies) | 14.8 | 5 | 12 | 56 |
| Max depth | 7.9 | 3 | 9 | 10 |
| Leaves | 31.4 | 8 | 20 | 174 |
| Mean replies per internal reply node | 1.31 | 1.00 | 1.29 | 1.67 |
| Largest sub-thread share | 0.34 | 0.16 | 0.32 | 0.72 |

**Root-to-leaf chains.** There are 1,572 chains, with mean length 3.9 turns from the opening, median 3, 90th percentile 8 and maximum 10.

| Chain length | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Chains | 308 | 254 | 307 | 163 | 155 | 109 | 94 | 46 | 46 | 90 |

| Max depth | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|
| Conversations | 2 | 4 | 5 | 1 | 7 | 5 | 6 | 20 |

**Depth cap.** 20 of 50 trees stop at exactly depth 10, and chains of length 10 jump from 46 to 90. The Winning Args trees look truncated at 10 levels, so a chain ending at depth 10 may be a collection artefact rather than a real ending. Check this against a full Reddit dump before using chain endings for H2b.

## 3. Environment

The run used Python 3.13, pandas 3.0.5, numpy 2.5.3, pyarrow, websockets 17.4, detoxify 0.5.4, torch 2.15 (CPU) and convokit 5.0.0. Under pandas 3, `str.contains` uses pyarrow/RE2, which is the cause of the `DELTA_RE` bug fixed in `ppxnda/polarisation-network#3`.
