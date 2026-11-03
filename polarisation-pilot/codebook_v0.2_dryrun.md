---
title: Codebook v0.2 dry run on the 60 hard cases
status: draft
created: 2026-11-03
links: "[[Polarisation Network]]"
---
# Codebook v0.2 dry run on the 60 hard cases

**Method.** Claude (in a cloud session, not through the Batch API) read the v0.2 prompt exactly as `label_pilot.py` extracts it. It then labelled the 60 posts in `hard_cases.csv` from `case_id, parent_text, text` only, without seeing the expected or note columns. Labels are in `hard_cases_claude_v02_dryrun.csv` (category, score, identity_attack). Features and flags were not coded.

**Caveats.** This is one coder, and it's the same model family that wrote the hard cases and the review, so read it as a smoke test, not a reliability estimate. It isn't the frozen pipeline either: there was no tool schema and temperature wasn't controlled.

## 1. The headline: the answer key is stale

`expected_category` in `hard_cases.csv` was written for **v0.1**. It still uses category 4, which is retired, and its notes describe v0.1 failures that v0.2 then fixed. Agreement with it was 34/60, but **most of the 26 misses are v0.2 working as designed**:

| Case | v0.1 key | v0.2 dry run | Why v0.2 differs (changelog) |
|---|---|---|---|
| HC44 "She should resign..." | 2 | 3 | Proportionate demand without a cue = 3 (#5) |
| HC48 "Suspend the whip until the inquiry reports" | 2 | 3 | Proportionate process (#5) |
| HC33 parking, HC34 incompetence | 1 | 5 | Construct keyed on moral wrong (#4) |
| HC56 "why is she still being paid...?" | 3 | 1 | Implied-sanction rule (#12) |
| HC24, HC25 | 4 | 2 | Category 4 retired; identity is a separate axis (#9) |
| HC21 boycott | 2 | 3 | Personal boycott is proportionate (#5) |
| HC01, 02, 08, 10, 11, 26, 27, 38, 39 | 1 | 3 | Default 3 when no cue (a)–(f) is present (#8) |

**Action (you, about 1 hour).** Re-key `hard_cases.csv` under v0.2 **yourself**, in a new column `expected_v02`, without opening the dry-run CSV. Then compare the two files. That gives you a genuine two-coder check on the hardest boundary cases before any API money is spent. If you open my labels first, your key will be anchored on them.

## 2. Real problems with v0.2 (where I hesitated or mirror pairs split)

Mirror pairs are the same structure with the political lean swapped. The coder should give both posts in a pair the same label.

| # | Problem | Cases | My call | Proposed v0.3 rule |
|---|---|---|---|---|
| P1 | **A mirror pair split on category.** The barges post got 3 (housing asylum seekers on barges read as cruelty). The lecturing post got 5, because "lecturing farmers" is none of harm, dishonesty, unfairness, betrayal or cruelty. The wording is the same, but the parent decided whether a moral wrong exists, and that reading depends on the coder's politics | HC08 / HC09 | 3 / 5 | **Moral-emotion words** (sickening, disgusting, shameful, vile, disgraceful) applied to the target's act count as attributing a moral wrong. Both become 3. This also settles HC57 (dog fouling, "disgusting human being") as 3 |
| P2 | **identity_attack split across the mirror pair.** "Deportation presupposes the identity" makes the Muslim post true and the Christian post ("rot in hell") false. That is arguably right, since the sanction differs, but it **will** show up in the flip-audit as asymmetry | HC24 / HC25 | ia 1 / 0 | Decide whether the identity call follows the sanction (current rule) or the group definition. Then build a mirror pair that holds the sanction constant (e.g. two religions, both "deported") |
| P3 | Mockery with **no moral wrong supplied** comes out as 5 under v0.2, though it reads as gloating | HC41, HC42 (and HC19) | 5, 5, 2 | Keep 5 (the construct needs a wrong) and add a calibration example so coders don't drift. For HC19, "couldn't happen to a nicer guy" implies bad character but no wrong, so v0.3 should say whether ironic character judgement supplies the wrong |
| P4 | **"lol" / 😂 as stated pleasure vs irony**, i.e. 2 vs 1 | HC19 | 2 | Laughter tokens about the loss count as *stated* pleasure (2) unless the whole post is framed as irony (1) |
| P5 | "Unfit for power" **with no wrong named**: 3 or 5? | HC16 | 5 | If no moral wrong is stated or supplied, 5; "unfit" alone is a competence judgement |
| P6 | **Deprivation** ("not a penny, not a bed") isn't clearly harm or exclusion | HC30 | 2, +2 | Add "deny basic needs or support" to the harm list |
| P7 | **Club or employer sanctions** ("never plays for us again"): exclusionary or proportionate? | HC54 | 2 | Permanent exclusion from one organisation = proportionate (like dismissal); from a whole field or every platform = exclusionary. If adopted, HC54 becomes 3 with a cue check |
| P8 | **Score −1 vs 0** for "needs to understand / do the work" (implies capacity to change) | HC13, HC14 | 0, 0 | Add an anchor: an explicit path back ("needs to understand", "can make it right by...") is −1 |
| P9 | **Cue (d) foreclosure** is a judgement call for rhetorical distrust ("why would anyone believe a word she says?") | HC05 | 1 | Keep, but add this case's twin as a calibration example, because silence vs foreclosure is the modal 1/3 problem |
| P10 | **Cue (f) at low stakes** ("someone check his bank account", "name and shame" for a parkrun cheat) | HC32, HC60 | 3, 1 | Cue (f) needs mobilisation *against a person*. "Check X" without naming or locating anyone is 3 |

## 3. What this says about the pilot

- The **1 vs 3 default rule works mechanically**: with no cue present I defaulted to 3 quickly. The cost is that cat 1 will be rarer than v0.1 implied (the dry run gave 7 of 60 cat 1, while v0.1 keyed 21). Check the pilot's "≥ 10 of 100 cat 1" pass mark against that.
- The **3 vs 5 boundary is now the riskier one** (P1, P3, P5). It decides whether a post is moral at all, and it's where politics can slip in through the parent post.
- **Run `flip-audit`** on the 13 mirror pairs once you have API labels. P1 and P2 are the predicted failures.

## 4. Next steps
1. Re-key under v0.2 yourself (section 1), without opening the dry-run CSV.
2. Decide P1, P2 and P7. They change the construct, so they're your call.
3. Fold the decisions into a v0.3 with new calibration examples. Never copy hard cases into the prompt.
