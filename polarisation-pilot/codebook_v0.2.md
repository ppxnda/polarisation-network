---
title: Punitive Codebook v0.2
status: draft
version: 0.2
created: 2026-11-03
supersedes: codebook_v0.md (v0.1, kept unchanged for the record)
links: "[[Polarisation Network]], [[Punitive by Default]]"
---
# Punitive Codebook v0.2

> Revision of v0.1 after an independent methods review (`codebook_review.md`, rewrites R1 to R12), made before the 100-item pilot. Everything here is still a proposal to be broken by the pilot.
>
> This file is also the LLM prompt: `label_pilot.py` reads everything between `<!-- PROMPT START -->` and `<!-- PROMPT END -->` verbatim, except HTML comments, which are stripped. Edit here, not in the script, so the human and LLM coders always share one codebook. The calibration examples are now inside the prompt. `hard_cases.csv` is a held-out stress test and must never be copied into the prompt.

## Changelog v0 to v0.2 (not for the prompt)

| # | Change | Review ref | Why |
|---|---|---|---|
| 1 | Calibration examples moved inside the prompt markers and corrected: sacked-gloat now 2/+2, "never work in media again" now 2/+3, "typical [party] voters ... liar" now 3/+1, "this stupid" replaced by a moral-wrong example, "remember this when you vote" now 3/0. Added examples for every boundary type in `hard_cases.csv` | R1 | Human and LLM coders now see the same examples, and the examples agree with the procedure |
| 2 | The v0 example "lol he got sacked. Couldn't happen to a nicer guy" replaced by a different text with the same structure | R1, section 5 audit | It is verbatim hard case HC19; held-out items cannot appear in the prompt |
| 3 | R2's suggested step-5 examples ("incompetent clowns", "your argument is idiotic") paraphrased, not copied | R2 | They are near-verbatim HC34 and HC35 |
| 4 | Construct keyed on **alleged moral wrong** (harm, dishonesty, unfairness, betrayal, cruelty), not conduct. Errors, incompetence, bad arguments and taste go to 5 or 6 | R2 | Stops category 1 absorbing ordinary insult |
| 5 | Category 2 redefined as explicit harm, ruin or exclusion **beyond proportionate process**, or explicit celebration of a loss the target suffered. "Proportionate process" defined once, above the procedure | R3, R12 | Accountability is no longer captured by step 2 before the boundary rule can apply |
| 6 | New field `sanction_named` (`none`, `proportionate`, `exclusionary`, `harm`) | R3 | Records "she should resign" (OPEN 3) instead of deciding it |
| 7 | Score anchors rewritten so they do not restate category definitions; proportionate demands anchored at 0; -1 no longer requires criticism; identity-licensed hostility not scored | R4 | Score and category become separate measurements |
| 8 | 1 vs 3 boundary is now a list of six observable cues (a) to (f), **default 3** when none is present | R5 | Replaces two unobservable criteria with no default |
| 9 | Category 4 retired. `identity_attack` (true/false) coded first as a separate axis; category is coded as if the identity element were absent. Categories are now 1, 2, 3, 5, 6 (numbering kept) | R6 | Mixed posts stay in the punitive class; removes the left/right routing asymmetry |
| 10 | Protected list applies to majority and minority groups alike; parties, ideologies, occupations, classes, regions and movements are not protected; proxy terms count only when the text links them to the identity | R7 | Identity coding follows the text, not coder judgements of group power |
| 11 | Parent rule: the parent may supply the target, the wrong and the meaning of irony, and so may change the category | R8 | v0 wording invited coders to ignore the parent |
| 12 | Rules for multiple targets (most punitive stance governs), implied sanctions (category 1 with `implied_sanction`), and new relational feature `repair_rejected` | R9 | Covers the "polite sanction" iceberg cases D1 must catch |
| 13 | New `sarcasm` flag; code the most plausible intended meaning, never ironic praise as praise | R10 | v0 fallback to the literal reading gave the furthest possible label |
| 14 | `contested_claim_as_fact` replaced by `unhedged_allegation`; `spoken_about_not_to` replaced by `addressivity`; `target_in_out_group` removed (derive from the network); `punitive_lexicon` restricted to speaker-to-target uses; new `audience_call` feature | R11, section 3 | Each feature now codes something visible in the text, not coder beliefs about truth or sides |
| 15 | `defensiveness`, `stonewalling`, `repair_rejected` are relational: coded `na` when no parent is supplied, and treated as missing (not false) in alpha | R11, OPEN 5 | Absence of a parent is not evidence of absence |
| 16 | Self-directed and no-target rules made decisive | R12 | v0 said "usually 3 or 6" with no criterion |
| 17 | One pass threshold, stated once below | Section 1 | v0 codebook said 0.6, design doc said 0.67 |
| 18 | `identity_and_conduct_mixed` removed; it is now derivable as `identity_attack = true` and category in {1, 2} | R6 | Redundant under the separate axis |

## Why this codebook exists (not for the prompt)

Toxicity classifiers score *how* something is said (profanity, insult, threat). The construct here is *what licenses* the harshness: an alleged moral wrong that makes the target deserve harm or exclusion. The two come apart in both directions:

| | Low toxicity | High toxicity |
|---|---|---|
| **Punitive (cat 1 or 2)** | "Some people should never be allowed near a classroom again. Remember the name." (cat 2; the iceberg, D1) | "This vile ****er should be fired and never work again" (cat 2) |
| **Not punitive (cat 3, 5, 6)** | "I think this policy is wrong and here's why" (cat 3) | "lmao this ref is f***ing blind" (cat 5) |

The pilot's job is to show the top-left cell exists, is codable with acceptable alpha, and is separable from category 3 (non-punitive moral criticism). If the boundary between 1 and 3 cannot be coded reliably, V1 fails, and that is the result that matters most. Under v0.2 the second separability test (novelty 1) is whether `identity_attack` and the punitive category dissociate, rather than a 1 vs 4 contrast.

**Pass threshold (pre-registered): Krippendorff's alpha >= 0.667.** Every alpha-based test in this file and in `label_pilot.py` uses this one value. Report the bootstrap 95% interval alongside every point estimate; with 25 to 40 posts in the 1 vs 3 subset the interval will be wide.

**What would falsify the construct at pilot stage:**
- Strict 1 vs 3 alpha (both coders chose 1 or 3) below the pass threshold after one post-pilot revision of this codebook.
- Implicit-punitive posts (cat 1) almost all scoring high on Perspective anyway (no iceberg).
- The punitive score collapsing into toxicity (correlation above about 0.8 on the pilot). After R2 and R5 this is a fair test; note the pilot is keyword-sampled, so the correlation is not a population estimate.
- Label flips on counterfactual minimal pairs: a flip rate above about 10% on party swaps, for either coder (review's proposed line; see D6). Run with `label_pilot.py flip-audit`.
- Alpha by stratum: the pooled alpha can hide a pass on one side and a fail on the other. Report left-coded, right-coded and non-political strata separately.

## Decisions needed (not for the prompt)

These belong to the researcher. Each has a default so the prompt is usable now; the default is marked in the prompt with an HTML comment (stripped before the model sees it). Log each decision in the vault and update `polarisation-research.txt` when made.

| ID | Placeholder | Default used in the prompt | Why this default |
|---|---|---|---|
| D1 | **[DECISION NEEDED: is immigration status a protected identity, or conduct?]** | Not protected by itself. `identity_attack` is true only if the text links the immigration-status term to nationality, ethnicity or religion, uses a slur, or the sanction presupposes the identity | Matches the v0 protected list, which named nationality but not status, and the Equality Act 2010, whose protected characteristics do not include immigration status. Under R6 this decision now changes only `identity_attack`, not whether a post is punitive, so the conservative default costs little. Audit with immigration-term minimal pairs |
| D2 | **[DECISION NEEDED: does Islamophobia get its own topic tag for the H7 reservoir test?]** | No new tag. Use `topic = religion` (or `race_ethnicity` if the text frames it that way) with `identity_attack` and `blame_target` | Keeps the v0 topic list stable for the pilot; Islamophobia posts can be recovered from `topic`, `identity_attack` and the free-text target. Also unresolved in the project brief |
| D3 | **[DECISION NEEDED: do low-stakes everyday breaches (inconsiderate parking, not buying a round, queue-jumping) count as moral wrongs?]** | Not a moral wrong (route to 5 or 6) unless the post itself frames the act as harm, dishonesty, unfairness, betrayal or cruelty ("cheat", "stealing", "takers", "exploiting") | Follows R2's list and the review's reading of the parking case (most readers say 5). The line is fuzzy and will move category 1 counts in non-political strata, so it is your call |
| D4 | **[DECISION NEEDED: how to record a post aimed at a group the speaker says they belong to, now that `target_in_out_group` is removed?]** | Code as for any other target; mention the stated membership in `rationale`. No new field | R12 relied on `target_in_out_group`, which R11 removes. Adding a field is a schema change you should choose deliberately |
| D5 | **[DECISION NEEDED: if category 1 is rare in the pilot after v0.2, is that a failure of the construct or evidence that most hostility is ordinary insult?]** | Not applicable to the prompt (analysis decision) | Review question 2. Must be pre-registered before the pilot or the result is unfalsifiable |
| D6 | **[DECISION NEEDED: if party-swap flip rates differ by side, will you revise the codebook or report it as a finding about coders? And do you adopt the 10% flip-rate failure line?]** | Not applicable to the prompt (analysis decision). `flip-audit` reports flip rates and marks those above 10% | Review question 3 and section 5 audit protocol |

## Drafting calls made in v0.2 (check these; not flagged as researcher decisions)

Where the review's rewrites overlapped or left a gap, I made these calls to keep the procedure decidable. Each is easy to reverse.

| Call | Reason |
|---|---|
| R3 lists "celebrating a target's loss or downfall" under cat 2 while R5 cue (a) lists "pleasure in the target's harm or loss" under cat 1. Resolved by explicitness: stated pleasure ("good", "brilliant", "lol he got sacked", "enjoy the job centre") is 2; pleasure conveyed only through mock sympathy or irony ("thoughts and prayers 😂", "oh no, anyway") is 1 | R3 says "explicitly"; keeps the cat 1/2 line observable |
| Calm approval that a proportionate outcome happened ("right outcome, the inquiry did its job") is 3, not "celebrating a loss" | Otherwise every approving reaction to a resignation becomes cat 2 |
| Dismissal through a process and "unfit for office / shouldn't be in power" are listed as proportionate | R3 lists resign and vote out as proportionate; dismissal and electoral unfitness are the same kind of sanction |
| R1 scored "Imagine lying to grieving families and still having a job..." at +1; v0.2 gives +2 | R9 says score implied sanctions by the severity implied, and R4 puts a significant bad outcome (job loss) at +2 |
| Multiple targets: category and score follow the most punitive stance; if no stance scores above 0, the score follows the most solidaric stance | R9 covers category only; without this, R4's "defending an opponent from abuse = -2" anchor could almost never be used, because such posts also condemn the abusers |
| Categories 5 and 6 score 0 or below | R2 plus R4's "score only wrong-licensed punitiveness"; a cat 5 post has no alleged moral wrong to license desert |
| `addressivity` gets a fourth value, `none`, for posts with no identifiable target | The three values in R11 assume a target exists |
| `sanction_named` records only sanctions the text states (or that the post celebrates and the parent reports); implied sanctions are `none` with `implied_sanction = true` | Keeps the two fields from double-counting |

## Still open after v0.2 (resolve after the pilot)

1. **Speaker position (condition 3: cost).** Not coded from text. Attach as metadata later (follower count, institutional account, power relative to target) and test as a moderator. Labels stay identity-blind: identical text must get identical labels whoever posts it (review section 5).
2. **Score scale.** -2 to +3 is asymmetric on purpose. If coders never use -2, collapse to -1.
3. **Relational features.** If alpha on `defensiveness`, `stonewalling` or `repair_rejected` is poor even with parents, move them to the conversation layer.
4. **Minimal-pair set.** The 13 pairs in `hard_cases.csv` are a seed. Expand to about 40 pairs (party, dialect/register and addressivity swaps), keep them out of the prompt, and run `flip-audit` for each coder.

<!-- PROMPT START -->

# Codebook: punitive expression in social media posts

## 1. Construct

**Punitive expression**: text that treats a target as deserving harm, suffering, exclusion or loss of standing *because of an alleged moral wrong*. The core logic is: *"you did wrong, so you deserve to be hurt or cast out."*

**Moral wrong** means harm, dishonesty, unfairness, betrayal or cruelty that the post attributes to the target (directly, or by responding to a parent post that reports it). Errors, incompetence, bad arguments, poor performance, matters of taste and etiquette are **not** moral wrongs. Minor inconsiderateness (parking, queue manners) is not a moral wrong unless the post itself frames it as harm, dishonesty, unfairness, betrayal or cruelty ("cheat", "stealing", "takers"). <!-- [DECISION NEEDED D3] low-stakes everyday breaches; default above -->

Key properties:
- **Wrong-licensed.** The harshness is licensed by an alleged moral wrong. Hostility licensed by who the target *is* (a protected identity) is recorded separately as `identity_attack` (section 3). Hostility about incompetence or error is category 5.
- **Deservingness, not disapproval.** Saying an act was wrong is moral criticism. Saying or signalling that the person *deserves* something bad, or is no longer owed decency, is punitive.
- **Mostly implicit.** Most punitive expression contains no explicit call for punishment. It shows up through the cues listed in section 5.

**Unit of analysis: one post.** Label the target post's stance. If a parent post is supplied, it may supply the target, the alleged wrong and the meaning of irony, and so may change the category. Do not label the parent's own content.

**Symmetry.** Apply identical criteria whichever side the speaker or target is on. Do not infer the speaker's politics, identity or group from stereotypes. Identical text must receive identical labels.

## 2. Definitions used by the procedure

**Proportionate process** (not punitive in itself): investigate, hold an inquiry, regulator review, prosecute or "face the courts" if the allegations stand, resign, be dismissed or suspended through a process, suspend pending an inquiry, lose an election, vote out, "shouldn't be in power" or "unfit for office", personal boycott ("not one more penny from me", "cancelled my subscription", "never watching him again") of a person, business or institution.

**Beyond proportionate process:**
- **Exclusionary**: permanent or total exclusion: "never work again", "never sit on a board again", ban for life, shun, deplatform ("off every platform"), run out of the town or country, deport as punishment.
- **Harm**: violence, death, suffering ("let him rot", "hope they suffer"), ruin (lose everything, seize their property, financial or personal ruin).

**`sanction_named`** records the most severe sanction the post names, demands, wishes or celebrates: `none`, `proportionate`, `exclusionary`, `harm`. Include a sanction reported in the parent that the post celebrates or approves. An implied sanction that the text does not state is `none`, with `implied_sanction = true`.

## 3. Identity attack (code first, independently)

`identity_attack = true` when the post attacks, demeans, stereotypes or wishes harm on people **because of a protected identity**: race, ethnicity, nationality, religion, gender, gender identity, sexuality, disability. It applies to an individual (an identity slur at one person) as well as to a group.

- **Symmetric.** Applies equally to majority and minority groups (for example a majority religion or majority ethnicity).
- **Not protected:** political parties, ideologies, occupations, classes, regions, movements, fan groups.
- **Immigration status** is not protected by itself. Code `identity_attack` for an immigration-status term only under the proxy rule below. <!-- [DECISION NEEDED D1] immigration status protected or conduct; default: not protected by itself -->
- **Proxy terms.** For a term that is not itself a protected identity (an ideology, movement or status term), code `identity_attack` only if the text itself links it to the identity: it uses a slur or a stereotype of the identity, or treats all members of the identity as holders of the ideology. Do not infer proxy status from your own knowledge of how a term is used.
- **Identity term narrowed by conduct** ("[religion] voters who backed the bill"): `identity_attack = true` only if the post attributes the conduct or the harshness to the identity itself ("typical of them", "what do you expect from [group]"), uses a slur, extends the claim to all members of the identity, or demands a sanction that presupposes the identity (for example deporting people defined by religion). Otherwise false, and the post is coded on its conduct.
- Mentioning a protected identity, or defending someone who has one, is not an identity attack. Quoting identity hate in order to criticise it is not an identity attack.

**Then code the category and score as if the identity element were absent.** `identity_attack` never changes the category. A post can be `identity_attack = true` and category 2.

## 4. Category (choose exactly one of 1, 2, 3, 5, 6)

Category 4 is retired (identity hate is now `identity_attack`). Apply the steps in order and stop at the first that fits.

1. **2 Explicit punitive.** In response to an alleged moral wrong, the post explicitly calls for, wishes or celebrates harm, ruin or exclusion **beyond proportionate process** (`sanction_named` is `exclusionary` or `harm`); **or** it explicitly states pleasure at a loss, sanction or harm the target has suffered, including a proportionate one ("good, he got sacked", "brilliant", "karma, enjoy the job centre").
2. **1 Implicit punitive.** No explicit punitive content, but at least one cue (a) to (f) from section 5 is present, or the post makes an implied sanction (section 5, 1 vs 2), in response to an alleged moral wrong.
3. **3 Non-punitive moral criticism.** A moral judgement about an alleged wrong with none of the above. It may be blunt, angry, insulting or disgusted. Includes proportionate sanction demands without cues ("she should resign"), calm approval of a proportionate outcome, and moralising with no identifiable target.
4. **5 Non-moral toxicity.** Hostile, insulting or profane **without** an alleged moral wrong: incompetence ("useless, the lot of them"), error, a bad argument ("brainless take"), sports performance ("ref is blind"), etiquette. Hostile wishes about a non-moral matter are also 5.
5. **6 Neutral / other.** Information, questions, jokes, support, praise, personal news, repair without criticism, mock-moral vocabulary about taste ("putting milk in first is a crime").

## 5. Boundary rules

**1 vs 3 (the key boundary).** Code 1 only if at least one of these cues is present in the text (read with the parent):
- (a) mockery of, or pleasure in, the target's harm or loss, conveyed indirectly (mock sympathy, ironic condolences, laughing emoji after "sympathy");
- (b) denial of sympathy or decency ("no sympathy", "not crying", "don't care what happens to him");
- (c) a dehumanising reference (vermin, parasites, disease, filth, animals as a category);
- (d) explicit foreclosure of change ("beyond help", "will never change", "nothing he says now matters");
- (e) the wrong generalised to the target's kind together with a desert or exclusion claim ("people like this deserve...");
- (f) an `audience_call` that mobilises onlookers against the target outside proportionate process (pile-on, "name and shame", naming or locating a private person, "you know what to do").

Insults, anger, disgust, sneering and character criticism without these cues are **3**, with `contempt` or `criticism_of_person` marked as features. **If no cue is present, code 3.**

**1 vs 2.**
- Explicit means the harm, ruin or exclusion beyond proportionate process is stated, or pleasure at the target's loss is stated. A vague wish for an unnamed bad outcome ("hope he gets what's coming", "karma has a long memory") is **1** with `implied_sanction = true`.
- **Implied sanction**: a rhetorical question implying removal ("why is she still employed?"), naming or locating a private person, "I won't say what should happen to people like that". Code **1** with `implied_sanction = true`, and score by the severity of what is implied.
- Pleasure conveyed only by irony or mock sympathy is cue (a), so **1**. Stated pleasure is **2**.

**Accountability (3 vs 1 and 2).** A proportionate sanction demand without any cue (a) to (f) is **3** with `sanction_named = proportionate`. With a cue it is **1**. Exclusionary or harm sanctions are **2**. Calmly approving that a proportionate outcome happened ("right outcome") is 3; relishing it as the target's suffering is 2.

**3 vs 5.** Ask only: does the post (with the parent) attribute a moral wrong to the target? If yes, 3 or higher; if no, 5 (hostile) or 6. The parent can supply the wrong: "What a muppet" is 5 alone, but 3 as a reply to a report of a landlord leaving tenants without heating.

**Multiple targets.** If a post takes stances towards more than one target, code the category and score of the most punitive stance towards any target, and record that target in `blame_target`. If no stance scores above 0, score the most solidaric stance (for example a post defending an opponent from abuse while condemning the abusers without cues is category 3, score -2).

**Sarcasm and irony.** Code the most plausible intended meaning and set `sarcasm = true`. Cues: exaggerated praise of an act the post frames as bad, "oh yes", "what could go wrong", mocking emoji (😂, 🙄, 🤡) after sympathy. Never code ironic praise as praise. Sarcasm that opposes a punitive proposal is criticism of punitiveness, not punitiveness. If genuinely undecidable, code the intended reading you think more likely and set `confidence = low`.

**Quoting or reporting** punitive speech in order to criticise it: code the post's own stance, not the quoted text.

**Self-directed** ("I deserve this") is 6. If directed at a group the speaker belongs to, code as for any other target, and mention the stated membership in `rationale`. <!-- [DECISION NEEDED D4] self-group targets; default: no field, note in rationale -->

**No identifiable target** (vague moralising about "society" or "politicians"): 3 if a moral judgement is made, otherwise 6.

## 6. Punitive score (continuous, -2 to +3)

`punitive_score` records degree on the punitive-to-solidaric axis. Score only punitiveness licensed by an alleged moral wrong: identity-licensed hostility is not scored (for an `identity_attack` post, score the wrong-licensed component; if none, 0). Categories 5 and 6 therefore score 0 or below.

| Score | Meaning |
|---|---|
| +3 | Target treated as deserving severe harm, ruin, death or permanent exclusion (stated, wished, celebrated or clearly implied) |
| +2 | Target treated as deserving a significant bad outcome (for example losing a job) or as beneath decency: strong contempt, dehumanisation, gloating at a loss, an exclusionary demand |
| +1 | Mild: a sneer, "no sympathy", "people like this", a demand with a contemptuous edge |
| 0 | No punitive or solidaric content. Includes proportionate sanction demands without contempt ("she should resign", "investigate this") |
| -1 | Recognition of an opponent's or target's standing, good faith or capacity to change, with or without criticism |
| -2 | Active repair: apology, concession, defending an opponent from abuse, or explicit de-escalation |

## 7. Features (true / false)

Mark each independently of category.

| Feature | True when |
|---|---|
| `unhedged_allegation` | The post alleges wrongdoing by the target without a hedge ("allegedly", "reportedly", "if true"), a source, or evidence in the post. A parent report counts as a source only if the post's claim does not go beyond it. Code the epistemic marking only; never judge whether the claim is true |
| `group_for_individual` | A group is blamed or condemned for what an individual (or a few) did: "typical [party] voters", "this is what [group] are like" |
| `absolutism` | Totalising language: always, never, every single one, the lot of them, completely, beyond redemption |
| `dehumanising` | Target likened to animals, vermin, parasites, disease, filth or objects, or described as less than human. Stock insults (clown, muppet, idiot) are not dehumanising by themselves |
| `punitive_lexicon` | Desert or sanction words (deserve, punish, pay for, consequences, karma, burn, cancel, ruin, jail, fired, banned) that the **speaker** applies to the **target**. Negated ("doesn't deserve this"), reported (the target's own view), victim-directed ("the victims paid for it") and sarcastic anti-punitive uses are false |
| `deservingness` | The target is presented as deserving a bad outcome: desert words with the target as the one deserving it, stated or ironic celebration of a bad outcome, "no sympathy", "had it coming" |
| `contempt` | Sneering superiority, mockery, disgust, treating the target as beneath engagement. A feature only: contempt alone does not make a post category 1 |
| `moral_exclusion` | Target placed outside the scope of fairness or concern: "people like this don't deserve...", "no sympathy", "not one of us" |
| `criticism_of_person` | Attacks character ("you are selfish") rather than behaviour ("that was selfish") |
| `audience_call` | Explicit address to onlookers ("look at this", "remember the name", "RT", "everyone needs to see this", "you know what to do"), or naming or locating a private person |
| `repair_attempt` | Any move to de-escalate or restore: apology, concession, humour to defuse, acknowledgement, "fair point", "I hear you", defending an opponent |

## 8. Relational features (true / false / na)

These need a parent post. **If no parent post is supplied, code each as `na`.** With a parent:

| Feature | True when |
|---|---|
| `defensiveness` | Counter-attack or claimed victimhood in response to a criticism in the parent ("well what about you...") |
| `stonewalling` | Refusal to engage with the parent: "not reading that", "blocked", "save it", "I'm done with you people" |
| `repair_rejected` | The parent contains an apology, concession or olive branch, and the post refuses, mocks or sets it aside. If the parent contains no repair, `false` |

## 9. Flags

| Flag | Values |
|---|---|
| `identity_attack` | true / false (section 3) |
| `sanction_named` | `none`, `proportionate`, `exclusionary`, `harm` (section 2) |
| `implied_sanction` | true / false (section 5, 1 vs 2) |
| `sarcasm` | true / false (section 5) |
| `addressivity` | `addressed` (second person to the target, "you"), `tagged_about` (target @-mentioned or tagged but spoken about in the third person), `about` (target discussed, not tagged), `none` (no identifiable target) |
| `target_type` | `individual`, `group`, `institution`, `none` |
| `blame_target` | Free text, 1 to 4 words: who is blamed for the wrong (for example "the government", "a teacher"). `none` if no blame |
| `topic` | One of: `politics_domestic`, `politics_international`, `race_ethnicity`, `religion`, `gender_sexuality`, `immigration`, `crime_justice`, `celebrity_media`, `sport`, `tech`, `everyday_life`, `other` <!-- [DECISION NEEDED D2] Islamophobia topic tag; default: use religion --> |
| `confidence` | `high`, `medium`, `low` |

## 10. Calibration examples (constructed; not real posts)

"Codes" lists only values that are not the default (features false, `sanction_named = none`, flags false, `addressivity = about`, `target_type` as evident from the post). Relational features are `na` wherever no parent is shown; "relational all false" means a parent is present and none applies. Square brackets are placeholders: treat them as the kind of term named.

| Boundary | Parent (context) | Post | Cat | Score | Codes | Decisive cue |
|---|---|---|---|---|---|---|
| 1v3 | | "The minister misled Parliament. That's a serious breach and it needs a proper inquiry." | 3 | 0 | sanction_named=proportionate; unhedged_allegation | Moral judgement plus proportionate process, no cue |
| 1v3 | | "Imagine lying to grieving families and still having a job. Some people are beyond help." | 1 | +2 | implied_sanction; contempt; unhedged_allegation | Cue (d) foreclosure; implied job loss |
| 1v3 | | "Typical [party] voters, every one of them a liar." | 3 | +1 | group_for_individual; absolutism; criticism_of_person | Generalised insult, no desert or exclusion claim |
| 1v3 | | "Typical [party] voters. Every one of them deserves what's coming." | 1 | +2 | implied_sanction; group_for_individual; absolutism; deservingness; punitive_lexicon | Cue (e): kind plus desert claim; unnamed outcome, so not 2 |
| 1v3 | | "What a spineless coward. He knew about the abuse for years and said nothing." | 3 | +1 | contempt; criticism_of_person; unhedged_allegation | Insult and anger without any cue, so default 3 |
| 1v3 | Ex-chief executive who cut staff pensions says he can't find work. | "No sympathy. He made his bed." | 1 | +1 | deservingness; moral_exclusion; relational all false | Cue (b) denial of sympathy; parent supplies the wrong |
| 1v3 | | "I think she's wrong on this, but she's clearly acting in good faith and could still change it." | 3 | -1 | | Criticism plus recognition of standing |
| 1v2 | Director found to have faked safety tests is dismissed. | "Brilliant. Hope he enjoys explaining that gap on his CV 😂" | 2 | +2 | sanction_named=proportionate; contempt; deservingness; relational all false | Stated pleasure at a sanction suffered |
| 1v2 | | "Get him off every platform. He should never work in media again." | 2 | +3 | sanction_named=exclusionary | Permanent exclusion demanded |
| 1v2 | | "After what he did to those tenants, I'll just say karma has a long memory." | 1 | +2 | implied_sanction; punitive_lexicon; deservingness | Vague wish for an unnamed bad outcome |
| 1v2 | Clip of a delivery driver being racially abused at a petrol station. | "That's Kev Marsh from Hadley, works at the garage on Mill Road. You know what to do." | 1 | +2 | implied_sanction; audience_call; relational all false | Cue (f): naming and locating a private person to mobilise a pile-on. The target is the abuser, so identity_attack=false |
| 1v2 | Care home owner convicted of neglecting residents. | "Let him rot in there." | 2 | +3 | sanction_named=harm; deservingness; relational all false | Wished suffering beyond the sentence |
| accountability | Councillor resigns after an expenses inquiry. | "Right outcome. The inquiry did its job." | 3 | 0 | sanction_named=proportionate; relational all false | Calm approval of a proportionate outcome, not relish |
| accountability | | "He should resign. Sitting on that safety report for a year was indefensible." | 3 | 0 | sanction_named=proportionate; unhedged_allegation | Proportionate demand without any cue |
| accountability | | "If the report confirms she leaked it, she should be prosecuted like anyone else." | 3 | 0 | sanction_named=proportionate | Conditional, proportionate process |
| accountability | | "Disgraceful. Remember this when you vote." | 3 | 0 | sanction_named=proportionate; audience_call | Electoral accountability is proportionate; the audience call does not mobilise outside process |
| accountability | | "He should resign, and the vermin who covered for him should be run out of the country." | 2 | +3 | sanction_named=exclusionary; dehumanising; group_for_individual | Multiple targets: the most punitive stance governs |
| identity | | "Every [nationality] in this town is a thief. Send them all back." | 2 | +3 | identity_attack; sanction_named=exclusionary; group_for_individual; absolutism; unhedged_allegation | Identity axis true; category coded on the alleged wrong plus exclusion |
| identity | | "[Ethnic group] are disgusting. Can't stand being near them." | 5 | 0 | identity_attack; contempt; group_for_individual | Identity hostility with no alleged moral wrong: identity_attack true, category 5, score 0 |
| identity | | "[Majority religion] voters who backed this bill are hypocrites, plain and simple." | 3 | 0 | group_for_individual; criticism_of_person | Identity term narrowed by conduct, no link to the identity itself, so identity_attack=false (applies equally to majority groups) |
| identity | | "[Ideology] supporters have wrecked this country and should be shunned." | 2 | +2 | sanction_named=exclusionary; group_for_individual; unhedged_allegation | Ideology is not protected and the text does not link it to an identity, so identity_attack=false |
| 3v5 | | "Ref is absolutely blind tonight, what a joke" | 5 | 0 | contempt | Hostile, no moral wrong |
| 3v5 | | "Useless, the lot of them. This lot couldn't run a bath." | 5 | 0 | contempt; absolutism | Incompetence is not a moral wrong |
| 3v5 | Four-day weeks would boost productivity. | "That's the most brainless take I've read all week." | 5 | 0 | contempt; relational all false | A bad argument is not a moral wrong |
| 3v5 | Landlord fined for leaving tenants without heating all winter. | "What a muppet." | 3 | +1 | contempt; relational all false | Parent supplies the moral wrong; without it this would be 5 |
| 3v5 | | "Putting milk in before the water is a crime against tea. Unfollowing." | 6 | 0 | | Mock-moral vocabulary about taste |
| sarcasm | | "Oh brilliant, another minister 'learning lessons' after the fact. So reassuring." | 3 | 0 | sarcasm; contempt | Intended meaning is weary criticism; no cue |
| sarcasm | Pundit who mocked flood victims has his own basement flooded. | "Oh no. Anyway 🙂" | 1 | +2 | sarcasm; contempt; deservingness; relational all false | Cue (a): pleasure in misfortune conveyed by mock sympathy |
| sarcasm | | "Sure, ban every newspaper that annoys you. That always ends well." | 3 | 0 | sarcasm | Sarcasm opposing a punitive proposal; punitive_lexicon false |
| repair | | "Honestly fair point, I was too harsh earlier. Sorry." | 6 | -2 | repair_attempt | Apology and concession |
| repair | | "We'll never agree on tax, but she's been decent to me every time we've debated." | 6 | -1 | | Good faith towards an opponent, no criticism |
| repair | I'm sorry, I misread your post and went off on one. | "Too little, too late. Save it." | 3 | +1 | addressivity=addressed; contempt; stonewalling=true; repair_rejected=true; defensiveness=false | Repair rejected; the earlier abuse is the wrong; no cue (a) to (f) |
| repair | | "Can't stand his politics, but the threats he's getting are disgusting. Leave his family alone." | 3 | -2 | repair_attempt | Multiple targets: condemnation of the abusers has no cue (score 0), so the score follows the defence of the opponent |
| non-political (sport) | | "Cheated his way to that penalty. Hope he gets a lifetime ban." | 2 | +3 | sanction_named=exclusionary; unhedged_allegation | Cheating is a moral wrong; a lifetime ban is exclusionary |
| non-political (everyday) | | "Whoever keeps nicking milk from the office fridge: grow up." | 3 | 0 | addressivity=addressed | Theft is a moral wrong; a reprimand without a cue |
| non-political (workplace) | | "A colleague blamed me in front of the client for her own mistake. Fuming." | 3 | 0 | unhedged_allegation | Anger alone is not punitive |
| non-political (celebrity) | Actor caught on tape berating a junior crew member. | "Never watching anything he's in again." | 3 | 0 | sanction_named=proportionate; relational all false | Personal boycott is proportionate |
| neutral | | "Council meeting on the bypass is Thursday at 7, all welcome." | 6 | 0 | target_type=none; addressivity=none | Information |
| no target | | "Honesty seems to be optional in public life now." | 3 | 0 | target_type=none; addressivity=none | Moral judgement with no identifiable target |

## 11. Output

Return one label per post using the `record_label` tool. Give a one-sentence `rationale` that names the decisive cue (for category 1, name the cue letter (a) to (f) or "implied sanction").

<!-- PROMPT END -->
