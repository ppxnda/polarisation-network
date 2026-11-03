# Independent methods review: Punitive Codebook v0

Reviewer: independent (did not draft the codebook). Reviewed: `polarisation-pilot/codebook_v0.md` (v0.1, 3 Nov 2026) against `polarisation-research.txt` sections 2 to 4 and 7. Companion stress set: `hard_cases.csv` (60 constructed posts, including 12 left/right mirrored pairs and 1 status-group pair).

## Verdict

The construct is sound and worth testing. The codebook as written does not yet operationalise it. Three structural problems will each, on their own, depress alpha on the 1 vs 3 boundary or make a pass uninterpretable:

1. Category 2 is defined lexically (a sanction is named) while category 1 is defined by deservingness. The two categories measure different things, so "punitive yes/no" mixes a word-detector with a construct-detector.
2. Steps 2 and 3 key on **conduct**, not **moral wrongdoing**. Any contempt about any behaviour (parking, refereeing, incompetence, a bad argument) reaches category 1 before step 5 can catch it. Category 5 is nearly empty by construction, and category 1 will absorb ordinary insult, which is the route by which the punitive score collapses into toxicity (your own falsification test).
3. The identity rule (step 1) decides which hostile posts leave the punitive class, and it does so along lines that track left/right targets. This contaminates H1 and H8 before any data arrive.

On the stress set, I expect 33 of 60 items to be high-disagreement. That is by design (they are boundary cases), but the causes cluster in a small number of fixable rules, listed below.

## Top problems, ranked by damage to V1

| # | Problem | Where | Consequence | Fix (see rewrites) |
|---|---|---|---|---|
| 1 | Calibration table contradicts the decision procedure | "lol he got sacked" = 1, but step 2 says celebrating a sanction = 2; "never work in media again" = +2, but the +3 anchor names permanent exclusion; "gloat" anchored at +1 but example scored +2 | Coders trained on examples and coders following the procedure diverge systematically. The LLM never sees the examples at all (they sit below `PROMPT END`), so human and LLM are not coding to the same codebook, contrary to the file's stated purpose | R1, R14 |
| 2 | "Conduct" where the construct means "moral wrongdoing" | Construct; steps 2 and 3 | Incompetence (HC34), error (HC35), inconsiderate parking (HC33) and refereeing ("ref is blind" calibration example) all satisfy step 3. Cat 1 inflates with low-stakes insult; cat 5 empties; toxicity correlation rises | R2 |
| 3 | Cat 2 is "sanction named", not "deserves harm" | Step 2, 1 vs 2 rule, score +2 anchor | "She should resign" (HC44) is 2/+2, "Absolute clown" (HC10) is 1/+1, doxxing a private person (HC17) is 1. The ordering inverts severity and conflates accountability with punishment, the very distinction Braithwaite and your section 2 rely on | R3, R4 |
| 4 | 1 vs 3 test is two unobservable criteria with no default | 1 vs 3 boundary rule | "Owed basic decency" and "capable of change" are rarely signalled either way. Silence is the modal case (HC05, HC15) and the rule gives no default, so coders fill the gap with priors | R5 |
| 5 | Identity precedence and the protected list create political asymmetry | Step 1, OPEN 2 | Status and ideology groups (landlords, Tories, Zionists, trans activists, "illegals", Christians who voted X) are sorted into 4 or 1/2 by coder judgement of proxy and group power, not text. Cat 4 counts as non-punitive in `label_pilot.py`, so the sort moves posts in or out of the outcome variable | R6, R7 |

## 1. Internal contradictions (fix before the pilot, not after)

| Item | Says | Conflicts with |
|---|---|---|
| "lol he got sacked. Couldn't happen to a nicer guy" = cat 1, +2 | implicit | Step 2: "celebrate ... a sanction ... 'good, they deserved it'" = cat 2. Being sacked is the paradigm sanction |
| Same item scored +2 | gloat = +2 | Score table: +1 = "sneer, gloat" |
| "Get him off every platform. He should never work in media again." = +2 | permanent exclusion = +2 | Score table: +3 = "permanent exclusion" |
| "Disgraceful. Remember this when you vote" = 1 | electoral sanction is implicit and punitive | Accountability rule: proportionate institutional process = 3. Voting is the most proportionate accountability a democracy has. Meanwhile "shouldn't be anywhere near power" (HC16) is explicit exclusion = 2 |
| "Typical [party] voters, every one of them a liar" = 1 | group generalisation + absolutism is punitive | Construct: deservingness, not disapproval. Nothing here says anyone deserves harm; by the construct it is 3 with `group_for_individual` and `absolutism` true |
| "Imagine being this stupid and still having a job" = 1 | contempt about stupidity is punitive | Construct is about wrongdoing; stupidity is not a wrong. Either this is 5, or "still having a job" is an implied sanction, which the codebook does not define |
| Punitive score "independent of category" | | +2 anchor is "explicit sanction demand", i.e. the definition of cat 2. Score and category are partly the same measurement, which inflates any category/score agreement you report |
| Codebook falsification threshold alpha < 0.6 | | Design doc pass threshold alpha >= 0.67. Pick one and pre-register it |
| "One file is both human codebook and LLM prompt" | | Calibration examples are outside the prompt markers. The LLM gets none; humans get eight, three of which are internally inconsistent |

## 2. Rules that are ambiguous

| Rule | Ambiguity | Cases |
|---|---|---|
| Step 1 "attack ... a group because of a protected identity" | Does an identity label plus a conduct qualifier ("Muslims who celebrated") count? Does a slur at an individual count (step 1 says "group")? Are ideology terms that function as proxies (Zionist, trans activist, globalist) identity? Is immigration status nationality? Are majority groups covered symmetrically? | HC24, HC25, HC28, HC29, HC30 |
| Step 2 sanction list | "Boycott of a person" vs of a business or institution; "exclusion" includes electoral defeat?; "prison" vs "face the courts"; "hope they suffer" vs "hope he gets what's coming"; "name and shame" absent | HC16, HC21, HC22, HC23, HC45, HC60 |
| Step 3 "performative condemnation to an audience" | Nearly all public moral criticism is addressed to an audience. As a signal it pushes every third-person post about a public figure towards 1 | HC03, HC08, HC10 |
| "Contempt usually does" | "Usually" is not a decision rule. Is a stock insult ("clown", "muppet") contempt? | HC10, HC11, HC33, HC36 |
| Parent rule "use it only to understand" | Can the parent change the category? It must (HC36 is 5 alone and 1 with the parent; HC41 is uncodable without it), but the wording invites coders to ignore it | HC36, HC41, HC42, HC56 |
| Multiple targets | No rule for posts that defend one target and condemn another | HC53 |
| Implied sanctions | Rhetorical questions and naming-to-mobilise sit between 1 and 2 with no rule. These are the iceberg cases D1 exists to find | HC17, HC20, HC56 |
| Repair rejection | Section 3 of the design doc lists repair rejection as punitive action; the codebook has no rule or feature | HC06, HC07, HC56 |
| Self-directed rule | "unless directed at a group the speaker belongs to" does not say what to code instead | none in set; flag for pilot |
| No-target rule | "usually 3 or 6" gives no criterion | HC40 |
| Score -1 vs -2 | -1 requires criticism; good faith without criticism has no anchor except -2 by elimination | HC51 |
| Score for cat 4 | A cat 4 post wishing death on a group scores +3 on the "punitive" axis, although by definition it is not conduct-licensed. The continuous score therefore carries identity hate into any analysis that uses it | HC24, HC25 |

## 3. Features not observable from text

| Feature | Problem | Observable replacement |
|---|---|---|
| `contested_claim_as_fact` | Requires knowing whether the claim is disputed in the world. Coders will mark claims they personally doubt, so the feature encodes coder politics (HC03 vs HC04, HC28 vs HC29). An LLM also has a knowledge cut-off | `unhedged_allegation`: an allegation of wrongdoing stated without hedge ("allegedly", "if", "reports say"), source or evidence in the post. Codes epistemic marking, not truth |
| `spoken_about_not_to` | Weak proxy for reputational gain: true for every group target and almost every top-level post, so near-constant. An @-mention is not the same as addressing | `addressivity`: `addressed` (second person to the target) / `tagged_about` (target mentioned or tagged, spoken about) / `about` (not tagged). Reputational gain is better measured downstream from likes and quotes |
| `target_in_out_group` | Single posts rarely reveal the speaker's side; "unclear" will dominate, and where coders do guess they guess from stereotypes, the bias the instruction forbids. This is also the variable H8 depends on | Drop from text coding. Derive from network community membership of speaker and target |
| "Performative condemnation" (step 3 signal) | Intent | `audience_call`: explicit address to onlookers ("look at this", "remember the name", "RT", "everyone needs to see"), or naming/locating a private person |
| "Capable of change" (1 vs 3 test) | Rarely signalled | Code only explicit foreclosure ("will never change", "beyond help", "nothing he says now matters") as a cat 1 cue |
| `defensiveness`, `stonewalling` | Relational; need the parent (OPEN 5 already says so) | Code only when a parent is present; otherwise NA, not false. Same for a new `repair_rejected` |
| `deservingness` ("claims or implies") | "Implies" without cues is unbounded | Keep, but tie to cues: desert words with the target as the one deserving a bad outcome, celebration of a bad outcome, "no sympathy" |
| `punitive_lexicon` | Surface word presence. Fires on victims ("girls paid for it", HC04), on the target's reported view ("thinks the poor deserve", HC26), on negation ("doesn't deserve any of it", HC53), and on sarcasm opposing punishment (HC43) | Restrict to uses where the speaker applies the term to the target, or rename to `lexicon_present` and stop treating it as a trace of punitiveness |
| Sarcasm "intended meaning" | Intent; but readable from cues | Add `sarcasm` flag; see R10 |

## 4. Decision order: counterintuitive results

Stop-at-first-fit with step 2 before the boundary rules means the boundary rules can never rescue a post that step 2 has already captured.

| Post | Procedure gives | Most readers would say | Why |
|---|---|---|---|
| "Suspend the whip until the inquiry reports. That's how it should work for every party." (HC48) | 2, +2 | 3, 0 or -1 | Step 2 (exclusion) fires before the accountability rule is consulted |
| "She should resign." (HC44) | 2, +2 | 3 or 2, +1 | Ranked more punitive than "Absolute clown" (+1) |
| "His name is Gary Felton... Just putting that out there." (HC17) | 1 | the most dangerous post in the set | No named sanction |
| "You absolute muppet, you've parked across my drive again." (HC33) | 1 | 5 | Step 3 asks for conduct, not moral wrongdoing, and comes before step 5 |
| "Muslims who celebrated the attack should be deported." (HC24) | 4, leaves punitive class | punitive and identity-based | Step 1 precedence; `label_pilot.py` counts 4 as not punitive |
| "Great idea, let's just lock up everyone who disagrees with us." (HC43), if uncertain | 2 (literal) | 3 | Sarcasm fallback to literal |

## 5. Political asymmetry and speaker-identity bias

**The structural asymmetry.** Left-coded hostility tends to target roles, classes and parties (landlords, billionaires, Tories, police); right-coded hostility more often targets groups adjacent to protected identities (migrants, Muslims, trans people). Under step 1 precedence, the second set is routed to cat 4 and out of the punitive class; the first set stays in. Any left/right difference in punitive rates (H8) or reward (H1) is then partly produced by the codebook. Pairs HC28/HC29 and HC30/HC31 test this directly. The asymmetry runs the other way for majority-religion and majority-ethnicity targets (HC25), where coders are less likely to apply cat 4 at all. Both directions are coder-power judgements, not text judgements.

**Truth-status features.** `contested_claim_as_fact` will be marked when the coder disbelieves the claim. Pairs HC03/HC04 and HC28/HC29 should be coded identically on this feature; measure whether they are.

**Idiom familiarity.** "Do the work" (HC13) reads as invitation to change for in-group readers and as penance to others; its mirror (HC14) is more transparent. Score sign then depends on coder subculture. This is the mechanism Sap et al. (2019) document for dialect: annotators and classifiers rated African American English tweets as more offensive, and priming annotators with dialect information reduced this. The UK analogues to test are Multicultural London English, regional banter registers and Very Online irony.

**Speaker position (OPEN 1).** The plan to let "a marginalised speaker calling out a powerful target read differently" must not enter labelling. If identical text receives different labels by speaker, that is the Sap et al. bias, introduced on purpose. Keep labels identity-blind and test power as a moderator in the models.

**LLM-specific risk.** The model will infer side and identity from cues regardless of the "do not guess" instruction. `target_in_out_group` gives it a slot to record those guesses, which then feed H8.

**Audit protocol (add to the pilot).**
- Counterfactual minimal pairs (in the spirit of Dixon et al. 2018 and Garg et al. 2019): swap target party/group, swap dialect/register, swap addressivity. Require label invariance; report the flip rate per swap type for each coder (human and LLM).
- The 13 pairs (26 items) in `hard_cases.csv` are a seed set. Expand to ~40 pairs, hold them out of any prompt examples, and treat a flip rate above ~10% on party swaps as a failure condition alongside alpha.
- Report alpha separately for left-coded, right-coded and non-political strata. A pooled alpha of 0.7 can hide 0.8 on one side and 0.5 on the other.

## 6. Pilot design implications

- **Category sparsity.** Six categories on 100 posts, keyword-sampled, will leave cats 4 and 5 with a handful of items. The 1 vs 3 subset alpha will rest on perhaps 25 to 40 posts; its confidence interval will be wide. Bootstrap it and report the interval, not the point.
- **The 1 vs 3 subset in `label_pilot.py`** includes posts where either coder chose 1 or 3, so a 1-vs-2 disagreement enters the "1 vs 3" statistic. Report it, but also report the strict binary (both coders in {1, 3}) and the confusion matrix.
- **Punitive yes/no** treats cat 4 as non-punitive, including mixed posts. Either count `identity_and_conduct_mixed = true` as punitive, or adopt multi-label (R6).
- **Hard cases are not pilot items.** Keep `hard_cases.csv` as a separate stress test; including it in the 100 would bias alpha downwards and prevalence upwards.
- **Toxicity falsification test.** With "contempt usually does" and stock insults coded 1, the punitive/toxicity correlation is inflated by the codebook, not the world. After R2 and R5 it becomes a fair test. Also note the pilot is keyword-sampled, so the correlation is not a population estimate.

## 7. Proposed rule rewrites

### R1. Calibration examples

| Old | New |
|---|---|
| Examples sit after `<!-- PROMPT END -->` | Move a corrected example table inside the prompt so human and LLM coders share it. Keep `hard_cases.csv` out of the prompt as a held-out test |
| "lol he got sacked. Couldn't happen to a nicer guy" = 1, +2 | = 2, +2 (celebrates a sanction) |
| "Get him off every platform. He should never work in media again." = 2, +2 | = 2, +3 (permanent exclusion), or change the +3 anchor; do not keep both |
| "Typical [party] voters, every one of them a liar." = 1, +1 | = 3, +1, `group_for_individual` and `absolutism` true. Use "Typical [party] voters. Every one of them deserves what's coming." as the cat 1/2 contrast |
| "Imagine being this stupid and still having a job..." = 1 | Replace with a moral example: "Imagine lying to grieving families and still having a job. Some people are beyond help." = 1, +1 |
| "Disgraceful. Remember this when you vote" = 1 | = 3, 0. Electoral accountability is proportionate process |

### R2. Moral wrongdoing, not conduct

| Old | New |
|---|---|
| Construct: "because of something they did (or are said to have done)" | "because of an alleged **moral wrong**: harm, dishonesty, unfairness, betrayal, cruelty. Errors, incompetence, bad arguments and matters of taste are not moral wrongs" |
| Step 3: "treat the target as deserving harm or as outside moral concern because of conduct" | "...because of an alleged moral wrong. Contempt about incompetence, error or taste goes to step 5" |
| Step 5: "without any moral-wrongdoing frame" | Keep, and add examples: "Incompetent clowns" (government), "your argument is idiotic", "ref is blind" |

### R3. Category 2 by deservingness, with sanction type recorded separately

| Old | New |
|---|---|
| Step 2: explicitly calls for, endorses, celebrates or wishes a sanction ... firing, banning ... boycott of a person ... | "Explicitly calls for, wishes or celebrates **harm, ruin or exclusion beyond proportionate process**: violence, death, suffering, permanent exclusion ('never work again', 'should be shunned'), ruin, deplatforming, celebrating a target's loss or downfall." |
| (none) | New field `sanction_named`: `none` / `proportionate` (resign, suspend pending inquiry, investigate, prosecute if, vote out, personal boycott) / `exclusionary` (never again, ban for life, shun, deplatform) / `harm` (violence, death, suffering, ruin) |
| 1 vs 2: "She should resign" = 2 | "A proportionate sanction demand without contempt, deservingness or exclusion cues is cat 3 with `sanction_named = proportionate`. With such cues it is cat 1. Exclusionary or harm sanctions are cat 2." This resolves OPEN 3 by recording it rather than deciding it, and lets you test whether proportionate demands behave like punitive ones in H1 |

### R4. Score anchors independent of category

| Old | New |
|---|---|
| +3 Wishes or celebrates severe harm, ruin, death or permanent exclusion | +3 Target treated as deserving severe harm, ruin, death or permanent exclusion (stated, wished, celebrated or clearly implied) |
| +2 Explicit sanction demand, or strong contempt / dehumanisation | +2 Target treated as deserving a significant bad outcome or as beneath decency: strong contempt, dehumanisation, gloating at a loss, exclusionary demand |
| +1 Mild implicit punitiveness: sneer, gloat, moral exclusion hint | +1 Mild: sneer, "no sympathy", "people like this", demand with a contemptuous edge |
| 0 No punitive or solidaric content | 0 Includes proportionate sanction demands without contempt ("she should resign", "investigate this") |
| -1 Criticism paired with recognition of the target's standing | -1 Recognition of an opponent's or target's standing, good faith or capacity to change, with or without criticism |
| -2 Active repair or solidarity across a divide | -2 Active repair: apology, concession, defending an opponent from abuse, or explicit de-escalation |
| (none) | "Score only conduct-licensed punitiveness. For a cat 4 post, score the conduct-licensed component; if none, 0." |

### R5. The 1 vs 3 boundary as observable cues with a default

| Old | New |
|---|---|
| "Is the target still treated as someone owed basic decency and capable of change? ... Anger alone does not make a post punitive. Contempt usually does." | "Code 1 only if at least one cue is present in the text (with the parent): (a) mockery of, or pleasure in, the target's harm or loss; (b) denial of sympathy or decency ('no sympathy', 'don't care what happens to'); (c) dehumanising reference; (d) explicit foreclosure of change ('beyond help', 'will never change'); (e) the wrong generalised to the target's kind with a desert or exclusion claim ('people like this deserve...'); (f) `audience_call` aimed at mobilising sanction. Insults, anger, disgust and character criticism without these cues are 3, with `criticism_of_person` or `contempt` marked as features. **If no cue is present, code 3.**" |
| Signal: "performative condemnation to an audience" | Replace with cue (f) and the `audience_call` feature |

### R6. Identity hate as a separate axis

| Old | New |
|---|---|
| Step 1: identity hate overrides; mixed posts = 4 | Remove cat 4 from the single-choice list. Add `identity_attack` (true/false) coded first and independently. Then code the punitive category (1, 2, 3, 5, 6) as if the identity element were absent. A post can be `identity_attack = true` and cat 2 |
| (consequence) | H1 and D1 keep mixed posts in the punitive class; the 1 vs 4 separability test (novelty 1) becomes a test of whether `identity_attack` and punitive category dissociate. Costs one extra binary decision, not half the alpha budget |

If you keep single-choice, at minimum adopt R7 and count `identity_and_conduct_mixed = true` as punitive in `label_pilot.py`.

### R7. Protected identity, proxies and status groups

| Old | New |
|---|---|
| "protected identity (race, ethnicity, religion, nationality, gender, gender identity, sexuality, disability)" | Add: "Applies equally to majority and minority groups. Immigration status is [decide: protected / conduct]; record the decision. Political parties, ideologies, occupations, classes, regions and movements are not protected identities." |
| (none) | "Proxy terms: code `identity_attack` only if the text itself links the term to the identity (e.g. uses a slur, a stereotype of the identity, or treats all members of the identity as holders of the ideology). Do not infer proxy status from your own knowledge of how a term is used." Then audit the proxy pairs (HC28/HC29) for symmetry |

### R8. Parent post

| Old | New |
|---|---|
| "use it only to understand what the post is responding to. Label the target post, not the parent." | "Label the target post's stance. The parent may supply the target, the alleged wrong and the meaning of irony, and so may change the category. Do not label the parent's own content." |

### R9. Multiple targets, implied sanctions, repair rejection

| Old | New |
|---|---|
| (none) | "If a post takes stances towards more than one target, code the most punitive stance towards any target, and record the target in `blame_target`." |
| (none) | "An implied sanction (rhetorical 'why is she still employed?', naming or locating a private person, 'I won't say what should happen') is cat 1 with `implied_sanction = true`, scored by the severity of what is implied." |
| (none) | New feature `repair_rejected` (needs a parent containing an apology, concession or olive branch): true when the post refuses, mocks or sets aside it. NA without a parent |

### R10. Sarcasm

| Old | New |
|---|---|
| "Code the intended meaning. If uncertain, code the literal meaning and set confidence low." | "Code the most plausible intended meaning and set `sarcasm = true`. Cues: exaggerated praise of an act the post frames as bad, 'oh yes', 'what could go wrong', mocking emoji (😂, 🙄, 🤡) after sympathy. If genuinely undecidable, code the intended reading you think more likely and set confidence low. Never code ironic praise as praise." |

### R11. Features

| Old | New |
|---|---|
| `contested_claim_as_fact` | `unhedged_allegation` (see section 3) |
| `spoken_about_not_to` | `addressivity` = `addressed` / `tagged_about` / `about` |
| `target_in_out_group` | Remove from text coding; derive from the network |
| `punitive_lexicon`: words of sanction or desert | "Desert or sanction words that the **speaker** applies to the **target**. Negated, reported or victim-directed uses are false." |
| `defensiveness`, `stonewalling` | NA when no parent is supplied |

### R12. Small rules

| Old | New |
|---|---|
| "Self-directed ('I deserve this') → 6, unless directed at a group the speaker belongs to." | "...If directed at a group the speaker belongs to, code as for any other target and set `target_in_out_group = in_group` from the text only if the speaker states membership." |
| "No identifiable target → usually 3 or 6." | "No identifiable target: 3 if a moral judgement is made, otherwise 6." |
| Accountability: "proportionate institutional process ... → 3, unless paired with deservingness or contempt" | Keep, and move it above the category list as a definition used by step 2 (see R3) so the stop-at-first-fit order cannot bypass it |

## 8. Questions you should be able to answer before the pilot

1. What would make you conclude that "she should resign" is punitive? If nothing would, it is not cat 2; record it (R3) and stop debating it.
2. If, after R2 and R5, cat 1 is rare in the pilot, is that a failure of the construct or evidence that most hostility is ordinary insult? Decide now which reading you will take, or the result is unfalsifiable.
3. If party-swap flip rates differ by side, will you revise the codebook or report it as a finding about coders? Pre-register.
4. Is immigration status protected? This one decision moves a large share of immigration-topic posts in or out of the punitive class and should be logged as a design decision, not left to coders.

## References cited in this review

- Braithwaite, J. (1989). *Crime, Shame and Reintegration*. Cambridge University Press.
- Dixon, L., Li, J., Sorensen, J., Thain, N., & Vasserman, L. (2018). Measuring and mitigating unintended bias in text classification. *AIES 2018*.
- Fehr, E., & Gächter, S. (2002). Altruistic punishment in humans. *Nature*, 415, 137 to 140.
- Garg, S., Perot, V., Limtiaco, N., Taly, A., Chi, E. H., & Beutel, A. (2019). Counterfactual fairness in text classification through robustness. *AIES 2019*.
- Sap, M., Card, D., Gabriel, S., Choi, Y., & Smith, N. A. (2019). The risk of racial bias in hate speech detection. *ACL 2019*.
