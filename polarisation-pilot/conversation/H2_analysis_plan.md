---
title: H2 analysis plan (conversation layer)
status: draft
created: 2026-11-03
links: "[[Polarisation Network]], [[Polarisation Lit Round 2]]"
---
# H2 analysis plan: do punitive turns derail conversations?

> Draft for you to cut down and pre-register. The wording of H2 below is my reconstruction from the design doc's L4b row ("gain g; repair; derailment; CMV deltas") and Lit Round 2. Check it against your own statement of H2 before using it.

## 1. The idea in one picture

Picture a single reply chain: A criticises B, B answers, and so on. Each turn is one of four states:

| State | From codebook v0.2 | Example |
|---|---|---|
| **P** punitive | category 1 or 2 | "No sympathy. He made his bed." |
| **M** moral criticism, not punitive | category 3 | "I think this policy is unfair, and here's why." |
| **R** repair | `repair_attempt` (and not P) | "Fair point, I was too harsh earlier." |
| **N** neutral / other | everything else | "Source?" |

A chain stops at some point. How it stops is the outcome:

- **CUT**: the last informative turn is P. The sanction stands and nobody answers it.
- **REPAIRED**: the last informative turn is R.
- **OTHER**: it fizzles out on M or N.

The question H2 asks is: **once a P turn enters a chain, how likely is the chain to end CUT rather than REPAIRED?** The comparison that matters is P against **M**, not P against neutral. Without that comparison the result could just mean "conversations that contain moral disagreement go badly", which is not what you want to claim.

## 2. Quantities (as defined in `chains.py`)

| Symbol | Definition | What it answers |
|---|---|---|
| g_s | mean number of P direct replies per post in state s | Does punitiveness reproduce itself? g_P > 1 means a punitive post begets on average more than one punitive reply (a supercritical cascade, the Watts condition in L5) |
| g_P / g_M | ratio of the gains | **H2a.** Is it punitiveness specifically, or moral criticism in general, that provokes punitive replies? |
| mean replies × share P | the two parts of g | Separates "punitive posts attract more replies" (attention) from "the replies are more punitive" (contagion) |
| T | transition matrix of a random walk down the tree, states P, M, R, N0, NP, NR → CUT, REPAIRED, OTHER | Turn-by-turn dynamics |
| B = (I − Q)⁻¹R | absorption probabilities | **H2b.** P(CUT \| P) vs P(CUT \| M); P(REPAIRED \| P) vs P(REPAIRED \| M) |
| delta by opening | did the OP award a Δ anywhere under this top-level reply | **H2c.** Do punitive openings change fewer minds than equally critical non-punitive ones? |

Neutral turns carry a one-step memory (NP = neutral after P, NR = neutral after R), so the ending stays Markov. The test file shows the price of this choice: two different P turns get pooled, so the chain forgets which one it came from. **Check the model against the empirical endings** (`analyse` prints both). If they disagree badly, the first-order Markov assumption fails, and that becomes a result in its own right (escalation has memory).

## 3. Hypotheses (proposed, to pre-register)

| | Hypothesis | Test | Pass |
|---|---|---|---|
| H2a | Punitive posts draw more punitive replies than non-punitive moral criticism | g_P / g_M, 95% CI from a bootstrap that resamples conversations | CI lower bound > 1 |
| H2b | Chains that reach P end CUT more often, and REPAIRED less often, than chains that reach M | B[P, CUT] − B[M, CUT], with a bootstrap CI | CI excludes 0 |
| H2c | Under the same OP post, punitive openings get fewer deltas than M openings | Conditional logit: delta ~ opening state, with **one fixed effect per OP post** | Coefficient for P vs M < 0, p < .05 |
| H2d (exploratory) | Whole-thread punitiveness predicts deltas better than the opening alone | Compare H2c with a model using the share of P turns in the thread | Reported, not tested |

H2d exists because Vuyyuru & Jahanbakhsh (2026) find that opening misalignment does **not** predict deltas while whole-conversation alignment does. Plan for the opening effect being weak.

## 4. Threats and design choices

1. **Selection into the opening state.** Who writes a punitive opening, and on which topics, isn't random. The within-post fixed effect in H2c compares openings to *the same OP and the same view*, which removes topic and OP stubbornness. Commenter traits remain; add commenter random effects if the data allow.
2. **Post-treatment controls.** Don't control for thread length or number of replies. They are outcomes of the opening.
3. **CMV Rule 2 removes rude comments, which is the biggest caveat.** Moderators delete hostile comments, so the most punitive turns are missing. ConvoKit keeps deleted comments in place as `[deleted]` tombstones, so their replies are *not* orphans and `clean()` will report zero; `deletion_report()` (printed by `load` and `analyse`) counts tombstones, deleted openings and moderator removal notices by rule. Tombstones stay in trees as N and are not exported for labelling. CMV is therefore a **conservative, truncated** test: what remains is punitive content polite enough to survive moderation. That is the iceberg (D1) in a different form, so it's arguably a feature. Still, report the deletion rate by opening state, and don't compare raw CMV prevalence with Bluesky.
4. **The codebook was built for short posts.** CMV comments are long. Before trusting any number, hand-label about 50 CMV replies and run `label_pilot.py agree` against the LLM labels. `export` truncates to 2,000 characters; check how often truncation cuts the punitive part.
5. **Label whole conversations, not a random sample of utterances.** Any unlabelled reply counts as N, which biases g towards zero and endings towards OTHER. `analyse` warns below 95% coverage. Sample *conversations*, then label everything in them.
6. **Baselines.** H2a and H2c must survive adding: the opening's Detoxify toxicity; ConvoKit politeness strategies (the Conversations Gone Awry pragmatic cues, Zhang et al. 2018); and an outrage score (Brady's classifier if you can obtain it). Otherwise the result is "rude openings go badly", which is already known.
7. **Concession is not repair.** Musi et al. (2018) find concessions equally common in winning and losing CMV arguments. Report R both as coded (`repair_attempt`) and with concessions split off, if the pilot shows the codebook conflates them.
8. **Deltas.** `mark_deltas` counts an OP comment with ∆ (U+2206), Δ, `&amp;#8710;` (Reddit HTML-escapes it) or `!delta`, or one that DeltaBot confirmed; `load` prints the token rule's recall against DeltaBot. Bots (DeltaBot, AutoModerator) are then removed from trees, re-attaching any replies to the bot's parent. Deltas measure *OP* persuasion only, not the commenter's.

## 5. Run order

```powershell
pip install convokit pandas numpy pyarrow pytest
python -m pytest conversation/tests             # 17 offline tests

# 1. Data (needs internet; the Winning Args corpus is large, so start small)
python conversation/chains.py load --corpus winning-args-corpus --max-conversations 50 --out data/cmv_utts.parquet

# 2. Plumbing check only: keyword stub, never report these numbers
python conversation/chains.py analyse --utts data/cmv_utts.parquet --stub-labels --n-boot 100

# 3. Real labels
python conversation/chains.py export --utts data/cmv_utts.parquet --out data/cmv_to_label.csv
python label_pilot.py estimate --sample data/cmv_to_label.csv    # check cost before submitting
# hand-label ~50 first (gold-template), then submit / fetch

# 4. Analysis
python conversation/chains.py analyse --utts data/cmv_utts.parquet --labels data/llm_labels.csv --out-dir data/h2
```

The export uses the same columns as `pilot_sample.csv` (`post_id, stratum, text, parent_text`), and `stratum` holds the conversation id.

## 6. What is still missing

- The **H2c conditional logit** isn't implemented yet. `opening_outcomes.csv` holds everything it needs: `statsmodels` `ConditionalLogit(delta, dummies(opening_state), groups=conversation_id)`. It isn't worth building before real labels exist.
- **The Bluesky adapter.** `load --csv` takes any table with `id, conversation_id, reply_to, text`. For Bluesky, `conversation_id` is the thread root URI and `reply_to` is the parent URI. Both must go through the **same** salted hash so that links survive pseudonymisation.
- **Live CMV run (3 Nov 2026)**: 50 Winning Args conversations load and `analyse --stub-labels` runs end to end. The Winning Args trees never go deeper than 10 turns below the root, which looks like a collection cap: chain endings at depth 10 may be truncation, not real endings.
- **Offline tests** use hand-built or simulated trees. On simulated data with a known g_P = 0.45, the estimate was 0.47 (60 conversations).
