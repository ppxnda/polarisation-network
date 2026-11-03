---
title: Polarisation Gap Matrix
status: draft
created: 2026-11-03
links: "[[Polarisation Network]]"
---
# Lit review gap matrix (first pass, 3 Nov 2026)

> First pass from your Readwise library, the Polarisation Network reading list and targeted web searches. **This is not exhaustive.** About 20 searches, so "no prior work found" means "not found yet", not "doesn't exist". Every row was checked against the paper's own page unless the Verify column says otherwise.

## Novelty claims being tested

| | Claim (design doc §5) |
|---|---|
| **N1** | Iceberg: a substantial share of punitive content scores below standard toxicity thresholds |
| **N2** | Beyond toxicity: punitive-signed edges explain network structure better than toxicity-signed edges, out of sample |
| **N3** | Reservoir: two-layer fast–slow model (policy acts on expression, culture drains attitude) with a fold |
| **N4** | Synthesis: micro → meso → macro, anchored in the four Fehr–Gächter conditions |

## Matrix

● = covers it, ◐ = partly covers it, ○ = doesn't touch it

| Work | What it does | N1 | N2 | N3 | N4 | Delta you claim | Verify |
|---|---|---|---|---|---|---|---|
| **Guo, Zhang, Bonnet, Pierrehumbert & Dong 2026**, arXiv 2605.12814 | Reddit r/Brexit (DEBAGREEMENT), 24 monthly windows. Edges signed by LLM-classified **stance** (agree/disagree). Scalar-intensity language prevalence correlates with frustration index (r = +0.56 count index, +0.36 weighted); **toxicity (toxic-bert) shows no comparable association**. Lagged language does **not** forecast next-month polarisation. | ○ | ● | ○ | ○ | Construct (theory-derived punitive vs a GPT-made intensity lexicon); signing edges by punitiveness rather than stance; multi-topic Bluesky; dynamical model | Title differs between versions ("Linking Extreme Discourse…" vs "Linking Scalar-Intensity Language…"); cite the version you read |
| **Fraxanet, Pellert, Schweighofer, Gómez & Garcia 2024**, PNAS Nexus | FAULTANA: antagonism × alignment in signed networks (Birdwatch, DerStandard). Signs from votes and ratings, not text. | ○ | ◐ | ○ | ○ | Text-derived signs; punitive/repair framing rather than antagonism/alignment (your framing rule) | Volume not checked |
| **Candellone, Babul, Togay, Bovet & Garcia-Bernardo 2025**, Network Science | Menéame: negative ties reveal extreme users who are invisible in unsigned networks | ○ | ◐ | ○ | ○ | Supports keeping negative edges; you add *what kind* of negativity | How signs are derived not confirmed from the abstract |
| **Macy, Ma, Tabin, Gao & Szymanski 2021**, PNAS 118(50) | ABM of legislative polarisation; tipping points and **asymmetric hysteresis**, so polarisation can be irreversible | ○ | ○ | ◐ | ○ | No latent/expressed split, no repair, no policy-vs-culture asymmetry, legislature not online | Checked |
| **Ye, Qin, Govaert, Anderson & Cao**, arXiv 1806.11236 (EPO model) | Private vs expressed opinions on influence networks (Asch conformity); generic private/expressed gap | ○ | ○ | ◐ | ○ | Their model is linear and converges (no fold or hysteresis), with no reward for punitive expression | Final venue (*Automatica*?) not checked |
| **Coscia & Rossi 2022**, PLoS ONE | ABM: users minimising conflict (unfollowing, flagging) can *increase* polarisation | ○ | ○ | ◐ | ○ | Relevant to M2: suppressing expression can backfire. Cite as mechanism support | Checked |
| **Brady et al. 2021**, Science Advances | Likes and shares reinforce moral-outrage expression (social learning) | ○ | ○ | ○ | ◐ | Outrage ≠ punitive; their Digital Outrage Classifier is your baseline. H1 must beat "it's just outrage" | Checked |
| **Rathje, Van Bavel & van der Linden 2021**, PNAS | Out-group words predict engagement more than in-group words | ○ | ○ | ○ | ○ | Lexical out-group reference, not punitiveness; no counter-mobilisation outcome (your H9) | Checked |
| **ElSherief et al. 2021**, Latent Hatred (EMNLP) | Implicit hate benchmark; implicit hate evades toxicity classifiers | ◐ | ○ | ○ | ○ | Identity-based, yours is conduct-based. This is the template for N1, so you must show the two come apart | In vault |
| **Dehumanising-language NLP** (arXiv 2402.13818 and a 2025 bilingual dataset, arXiv 2510.18582) | Detecting dehumanisation beyond hate speech | ◐ | ○ | ○ | ○ | One of your features, not the construct | Authors not checked |
| **Muir et al. 2023**, PLoS ONE | Survey: moral, emotional and personality predictors of online shaming | ○ | ○ | ○ | ◐ | Self-report, individual level; you measure text and network | Checked |
| **Bono, Liu, Russo & Pierri 2026**, ICWSM (arXiv 2505.01174) | Blocking on Bluesky; 86 behavioural features predict being blocked | ○ | ○ | ○ | ○ | Possible **outcome variable** for H3 (exit/silencing) on your platform | Checked; findings not read |
| **Mamakos & Finkel 2023**, PNAS Nexus | Engaged partisans are toxic even in non-political subreddits | ○ | ○ | ○ | ○ | Supports topic-agnostic network + spillover tags | Checked |
| **Guess et al. 2023**, Science 381 | Changing Facebook/Instagram feed algorithms shifted exposure but not attitudes or polarisation | ○ | ○ | ◐ | ○ | Consistent with the reservoir (expression/exposure moves, attitudes don't), but also consistent with "platforms don't matter". Engage in M2 | Checked |
| Holme & Newman 2006; Sobieraj & Berry 2011 | Coevolution phase transition; outrage typology | ○ | ○ | ◐ | ○ | Already in your design | Known |

## What this means for each claim

| Claim | Status | Why |
|---|---|---|
| **N1** | **Open, medium confidence** | Nothing found measuring *conduct-based* punitive content below toxicity thresholds. Implicit hate (ElSherief) is the closest and is identity-based. Risk: reviewers will say "this is implicit hate plus outrage". The pilot's 1-vs-3 and 1-vs-4 separability is the answer. |
| **N2** | **Narrowed** | Guo et al. 2026 already show that toxicity doesn't track frustration but another language feature does. "Beyond toxicity" as such is no longer yours. What's left: (a) a theory-derived construct, (b) **signing edges by punitiveness** compared with stance and toxicity signing, (c) out of sample. Cite them as the precedent and claim the delta. |
| **N3** | **Narrowed to a combination** | Hysteresis exists (Macy et al. 2021). A private/expressed split exists (Ye et al.; Kuran). The open part is the **combination**: two layers, a fold in Π, and the asymmetry that policy moves x but only repair drains a. State it as a combination claim. |
| **N4** | **Not a novelty claim** | Synthesis is the capstone's integration chapter, but a reviewer won't credit it as a contribution. Keep it out of the paper's novelty list. |

## Counter-evidence you have to engage

1. **Guo et al.: lagged language doesn't forecast polarisation.** This is a direct problem for **H7** (pre-event implicit markers predict post-event surges). Possible answers: event-locked windows instead of calendar months; a different construct; or H7 may simply be false. Pre-register it either way.
2. **Guess et al. 2023: feed changes didn't move attitudes.** You read this as the reservoir. The rival reading is that platforms barely matter. M2 needs a prediction that tells the two apart. One candidate: the reservoir predicts **reactivation after the intervention ends**; "doesn't matter" predicts no effect either way.
3. **Brady/Rathje: outrage and out-group animosity already explain engagement.** H1 has to show that punitive expression adds something **over** the Digital Outrage Classifier and out-group terms, not just over toxicity.

## Next searches (not done)

- Conduct-based vs identity-based hostility, "moralised hostility", "condemnation" corpora (Kteily; Crockett 2017 is theory only)
- Call-out culture / pile-on detection on Twitter/X (quote-dunk literature, e.g. "dunking" studies)
- Fast–slow (slow manifold) opinion models: search "multiscale opinion dynamics latent attitude"
- CMV persuasion and repair: Tan et al. 2016 is in the vault; check follow-ups on conciliatory openings
- Read the Guo et al. paper in full (methods §4, limitations §6) before the Giles pitch
