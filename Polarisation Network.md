---
fileClass: build
aliases:
status: seed
created: 2026-08-25
links:
tags:
  - domain/sociology/polarisation
project-status: not-started
tier: 4-primary
target-completion: 2027-06-30
next-action: Check the LIS ethics approval process for Bluesky collection and interviews
org: 
last-reviewed:
area:
repo-url:
maintenance-status:
build-type: model
---
## Log

- **2026-11-03** Codebook v0 drafted (one file = human codebook + LLM prompt), then v0.2 after an independent red-team review (`polarisation-pilot/codebook_review.md`, 60 hard cases held out in `hard_cases.csv`). Category 4 retired in favour of a separate `identity_attack` axis.
- **2026-11-03** Pilot scripts built (keyword sampler, labeller, agreement), plus `tools/` (random Jetstream sampler for D1, toxicity scorer). None run against live Bluesky or the API yet.
- **2026-11-03** Lit rounds 1–2 ([[Polarisation Gap Matrix]], [[Polarisation Lit Round 2]]). N1 open but crowded (state the triple: deservingness licence, separation from identity hate/outrage/UCC, sub-threshold prevalence on a non-keyword sample). N2 narrowed by Guo et al. 2026 (sign edges by punitiveness vs stance vs toxicity on the same edge set; score on an independent outcome). N3 narrowed to a mechanism-plus-data claim (Klingborg et al. 2026, Sznajd-Weron group). N4 is the integration chapter, not a paper novelty claim.
- **2026-11-03** H7 at risk from Guo et al.'s lagged-forecast null. Redesign as a pre-registered, event-locked pooled study with persistence baselines.
- **2026-11-03** Perspective API retires 31 Dec 2026. Use Detoxify as the primary toxicity baseline; score anything that needs Perspective before then.
- **2026-11-03** Toy reservoir model (`polarisation-pilot/model/`): fold for 2.03 < Π < 4.83; policy alone has a minimum duration of about one repair time. **Decision pending:** "policy and culture are complements" holds only in a narrow band; the sharper claim is "policy buys time and cuts inflow; only repair raises the drain ceiling". Pick one for the one-line argument.
- **2026-11-03** Normal-form note: near a fold the recovery *rate* scales as √distance (slope +½ on log-log); the recovery *time* has slope −½. Fix wherever the design doc states this.
- **2026-11-03** Conversation layer prototype (`polarisation-pilot/conversation/`): gain g, cut/repaired endings as an absorbing Markov chain, H2 plan. Key caveat: CMV Rule 2 removes rude comments, so CMV is a truncated, conservative test.

## Notes

Ask part of your capstone for part of the analysis your should contact:
- [[Christian Dinvyne]] (@xiandivyne, [[TikTok]])
- [[Ell (cultivatingboldspaces)]] (@cultivatingboldspaces, [[TikTok]])
- [[Jamelle Bouie]] (@jamellebouie, [[TikTok]])
- [[Ben Gail]] (@oldirtydog, [[TikTok]])
- [[John (diaryofapeasant)]] (@diaryofapeasant, [[TikTok]])
- [[Mark L.Y.]] (@mly 2365, [[TikTok]])
Build this list into 15+ interviewees...

### To mention (not analyse): misquote quote-tweets on X

- **Pattern:** a quote-tweet attaches a false or distorted claim to a video. The claim travels; the video goes unwatched. Replies sanction the claim, not the event.
- **Fit with the conditions (Table 1):** the extreme failure of condition 1. The evidence is literally attached, yet the violation is still only *alleged*, and alleged falsely. Also condition 3 (denunciation is costless) and the core claim that reward is decoupled from harm: the QT is rewarded whether or not it is true.
- **Why mention only:** the scorer reads text. An accurate and a fabricated QT can score identically; the falsity lives in the gap between post and source, which needs per-video ground truth. Out of scope; belongs in discussion/limitations.
- **Evidence to cite:** Gabielkov et al. 2016, "Social Clicks" (most shared links are never clicked); Vosoughi, Roy & Aral 2018, *Science* (false news spreads further and faster on Twitter); Brady et al. 2017, *PNAS* (moral-emotional language increases diffusion).
- **Intervention hook:** Community Notes; friction prompts (Twitter's 2020 "read before you retweet" test).

## Structure

| Layer | Block | Content |
|---|---|---|
| L0 Social theory | I Meaning | Durkheim, Collins (interaction ritual), Braithwaite, Opotow, Kuran, Garland, Nietzsche (ressentiment), Foucault; defines punitive thinking |
| L1 Moral psychology | I Meaning | Contempt vs anger, deservingness, dehumanisation, signalling |
| L2 Political and cultural context | I Meaning | Affective polarisation, elite cues, camps, events, left/right asymmetry (H8) |
| L3 Platforms and data | II Measurement | Bluesky (core network), X elite-reply sample, ChangeMyView (comparison case) |
| L4 NLP | II Measurement | Codebook: implicit / explicit punitive, non-punitive moral criticism, identity hate, non-moral toxicity, neutral; flags: amplification, repair, target, topic |
| L4b Conversation | II Measurement | Reply = signed edge; thread = chain; gain g; repair; derailment; CMV deltas |
| L5 Network | III Mechanism | Signed reply/quote network, likes as reward and silent endorsement; frustration index, signed Laplacian, Watts cascades |
| L6 Inference | IV Synthesis | Pre-registered event studies, early warning, hierarchical models, SBI for Π |
| L7 Model | III Mechanism | ABM: attitude a (slow), expression x (fast), threshold c, elite cue E, repair |
| L8 Maths | III Mechanism | Π = κ_cut / κ_repair, fold/cusp, two-layer fast–slow model, cascade condition |
| L9 Interventions | IV Synthesis | Individual, community, platform, policy; durability via policy feedback |

**Main question:** Why doesn't online polarisation reverse, and what would it take to reverse it?
**Focus case:** Islamophobia (H7 reservoir test).

## Venues

| Venue | Format | Deadline | Status |
|---|---|---|---|
| IC2S2 2027 | Extended abstract | TBC (historically Feb–Mar) | Main target |
| NetSci 2027 (Dresden, 17–21 May) | 1-page abstract + figure | TBC | Target |
| ACM Collective Intelligence 2027 | TBC | TBC | Check Jan |
| ICWSM 2027 Round 3 | Full paper | 15 Jan 2027 | Not targeting |
| Interdisciplinary Science Reviews | Journal article | Rolling | After 11 Jul 2027 |

Gate for both abstracts: one real preliminary figure from Bluesky data by late Jan 2027.

## Reading

### Core

Read these (whole or the named parts); everything else in the layer lists below is cite-only. Work one layer at a time.

- **L0:** [[Interaction Ritual Chains]] · [[The Elementary Forms of Religious Life]] (selected chapters) · [[Crime, Shame and Reintegration]] · [[Private Truths, Public Lies]]
- **L1:** [[Beat them or ban them - The characteristics and social functions of anger and contempt]] · [[The ascent of man - Theoretical and empirical evidence for blatant dehumanization]]
- **L2:** [[Uncivil Agreement]]
- **L3:** [[Bit by Bit]] (ch. 2 and 6)
- **L4:** [[Latent Hatred - A Benchmark for Understanding Implicit Hate Speech]] · [[Text as Data]] (parts)
- **L4b:** [[Conversations Gone Awry - Detecting Early Signs of Conversational Failure]]
- **L5:** [[Networks - An Introduction]] (chapters) · [[Negative ties highlight hidden extremes in social media polarization]] · [[How Behavior Spreads]]
- **L6:** [[Early-warning signals for critical transitions]]
- **L7:** [[Dynamics of social balance on networks]]
- **L8:** [[Nonlinear Dynamics and Chaos]]
- **L9:** [[Reducing Exclusionary Attitudes through Interpersonal Conversation - Evidence from Three Field Experiments]]

### L0 Social theory
- [[The Elementary Forms of Religious Life]]
- [[The Division of Labor in Society]]
- [[Interaction Ritual Chains]]
- [[Crime, Shame and Reintegration]]
- [[Moral Exclusion and Injustice - An Introduction]]
- [[Private Truths, Public Lies]]
- [[Punishment and Modern Society]]
- [[On the Genealogy of Morality]]
- [[Discipline and Punish]]
- [[Stigma]]

### L1 Moral psychology
- [[Anger and Forgiveness]]
- [[The Righteous Mind]]
- [[Beat them or ban them - The characteristics and social functions of anger and contempt]]
- [[The ascent of man - Theoretical and empirical evidence for blatant dehumanization]]
- [[Third-party punishment as a costly signal of trustworthiness]]
- [[Cooperation and Punishment in Public Goods Experiments]]
- [[Antisocial Punishment Across Societies]]
- [[How social learning amplifies moral outrage expression in online social networks]]
- [[Examining the role of moral, emotional, behavioural, and personality factors in predicting online shaming]]
- [[So You've Been Publicly Shamed]]

### L2 Political and cultural context
- [[Uncivil Agreement]]
- [[Why We're Polarized]]
- [[Network Propaganda]]
- [[Breaking the Social Media Prism]]
- [[How social media shapes polarization]]
- [[How digital media drive affective polarization through partisan sorting]]
- [[Polarization on Social Media - Micro-Level Evidence and Macro-Level Implications]]
- [[From Extreme to Mainstream - The Erosion of Social Norms]]
- [[From Hashtag to Hate Crime - Twitter and Antiminority Sentiment]]
- [[Nazi indoctrination and anti-Semitic beliefs in Germany]]
- [[Patterns of Implicit and Explicit Attitudes - I. Long-Term Change and Stability From 2007 to 2016]]
- [[Hate Crime in the Wake of Terror Attacks - Evidence From 7-7 and 9-11]]
- [[The Dynamics of Informational Cascades - The Monday Demonstrations in Leipzig, East Germany, 1989-91]]
- [[Islamophobia - Still a Challenge for Us All]]

### L3 Platforms and data
- [[Bit by Bit]]
- [[Auditing Elon Musk's Impact on Hate Speech and Bots]]
- [[You Can't Stay Here - The Efficacy of Reddit's 2015 Ban Examined Through Hate Speech]]

### L4 NLP
- [[Text as Data]]
- [[Natural Language Processing with Transformers]]
- [[Content Analysis - An Introduction to Its Methodology]]
- [[Latent Hatred - A Benchmark for Understanding Implicit Hate Speech]]

### L4b Conversation
- [[Winning Arguments - Interaction Dynamics and Persuasion Strategies in Good-faith Online Discussions]]
- [[Conversations Gone Awry - Detecting Early Signs of Conversational Failure]]

### L5 Network
- [[Networks - An Introduction]]
- [[How Behavior Spreads]]
- [[Linking Scalar-Intensity Language to Structural Polarization with Validated Signed-Network Measures]]
- [[Negative ties highlight hidden extremes in social media polarization]]
- [[Unpacking polarization - Antagonism and alignment in signed networks of online interaction]]
- [[Emotion shapes the diffusion of moralized content in social networks]]
- [[A simple model of global cascades on random networks]]
- [[Threshold Models of Collective Behavior]]

### L6 Inference
- [[Statistical Rethinking]]
- [[Causal Inference - The Mixtape]]
- [[Early-warning signals for critical transitions]]
- [[The frontier of simulation-based inference]]

### L7 Model
- [[Modeling Social Behavior - Mathematical and Agent-Based Models of Social Dynamics and Cultural Evolution]]
- [[Dynamics of social balance on networks]]
- [[Nonequilibrium phase transition in the coevolution of networks and opinions]]

### L8 Maths
- [[Critical Transitions in Nature and Society]]
- [[Nonlinear Dynamics and Chaos]]
- [[Introduction to Probability Models]]
- [[Contagion in financial networks]]

### L9 Interventions
- [[Reducing Exclusionary Attitudes through Interpersonal Conversation - Evidence from Three Field Experiments]]
- [[When Effect Becomes Cause - Policy Feedback and Political Change]]

### Integration
- [[Interdisciplinary Research - Process and Theory]]

![[references.base#Project Reading]]

## Toolkit

| Stage | Tools |
|---|---|
| Data | Jetstream, atproto SDK, ConvoKit, X pay-per-use (elite timelines), GDELT, Hansard API |
| Storage | Parquet + DuckDB |
| Labelling | Claude Batch API, Label Studio, krippendorff |
| NLP | transformers, datasets, Detoxify (Perspective retires 31 Dec 2026), Mformer |
| Network | networkx, igraph + leidenalg |
| Stats | statsmodels, bambi, lifelines, ewstools |
| Modelling | NumPy + Numba, SciPy, sbi, SALib |
| Qualitative | faster-whisper, Taguette |
| Writing | Zotero + Better BibTeX, Overleaf, Git, OSF |

## Context

```dataviewjs
await dv.view("00 System/scripts/project-context");
```
