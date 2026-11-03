---
title: Punitive Codebook v0
status: draft
version: 0.1
created: 2026-11-03
links: "[[Polarisation Network]], [[Punitive by Default]]"
---
# Punitive Codebook v0

> Draft for the 100-item pilot. Built from the essay's text-trace features and section 4 of the design doc. Everything here is a proposal to be broken by the pilot. Sections marked **OPEN** are decisions you have not made yet.
>
> This file is also the LLM prompt: `label_pilot.py` reads everything below the line `<!-- PROMPT START -->` verbatim. Edit here, not in the script, so the human and LLM coders always share one codebook.

## Why this codebook exists (not for the prompt)

Toxicity classifiers score *how* something is said (profanity, insult, threat). The construct here is *what licenses* the harshness: a perceived wrong that makes the target deserve harm or exclusion. The two come apart in both directions:

| | Low toxicity | High toxicity |
|---|---|---|
| **Punitive** | "Some people should never be allowed near a classroom again. Remember the name." (the iceberg, D1) | "This vile ****er should be fired and never work again" |
| **Not punitive** | "I think this policy is wrong and here's why" | "lmao this ref is f***ing blind" |

The pilot's job is to show the top-left cell exists, is codable with acceptable alpha, and is separable from category 3 (non-punitive moral criticism). If the boundary between 1 and 3 can't be coded reliably, V1 fails, and that's the result that matters most.

**What would falsify the construct at pilot stage:**
- Alpha on category 1 vs 3 below ~0.6 after one codebook revision.
- Implicit-punitive posts almost all scoring high on Perspective anyway (no iceberg).
- The punitive score collapsing into toxicity (correlation above ~0.8 on the pilot).

<!-- PROMPT START -->

# Codebook: punitive expression in social media posts

## Construct

**Punitive expression**: text that treats a target as deserving harm, suffering, exclusion or loss of standing *because of something they did* (or are said to have done). The core logic is: *"you did wrong, so you deserve to be hurt or cast out."*

Key properties:
- **Conduct-based.** The harshness is licensed by an alleged act, statement or choice. If the harshness is licensed by who the target *is* (race, religion, ethnicity, gender, sexuality, disability, nationality), that is identity-based hate (category 4), not punitive expression.
- **Deservingness, not just disapproval.** Saying an act was wrong is moral criticism. Saying or implying the person *deserves* something bad, or is no longer owed decency, is punitive.
- **Mostly implicit.** Most punitive expression contains no explicit call for punishment. It shows up as contempt, mockery of suffering, moral exclusion ("people like this"), or performed condemnation for an audience.

Unit of analysis: **one post**. If a parent post is supplied, use it only to understand what the post is responding to. Label the target post, not the parent.

## Categories (choose exactly one)

Apply the decision procedure below in order. Stop at the first category that fits.

### Decision procedure

1. Does the post attack, demean or wish harm on a group **because of a protected identity** (race, ethnicity, religion, nationality, gender, gender identity, sexuality, disability)? → **4 Identity-based hate**.
   - If the post punishes a person for conduct *and* uses identity slurs or identity-based generalisation, still choose **4**, and set `identity_and_conduct_mixed = true`.
2. Does the post **explicitly** call for, endorse, celebrate or wish a sanction on a target for alleged wrongdoing? Sanctions include: firing, banning, deplatforming, prison, violence, death, ruin, exclusion, boycott of a person, "should never work again", "hope they suffer", "good, they deserved it". → **2 Explicit punitive**.
3. Does the post, without an explicit sanction, treat the target as **deserving harm or as outside moral concern** because of conduct? Signals: contempt, mockery of their suffering or downfall, dehumanising reference, "people like this", moral exclusion, gloating, "remember the name", performative condemnation to an audience. → **1 Implicit punitive**.
4. Does the post make a **moral judgement** (wrong, unfair, harmful, dishonest, hypocritical) about conduct *without* implying the person deserves harm or exclusion? It may be blunt or angry. → **3 Non-punitive moral criticism**.
5. Is the post hostile, insulting or profane **without any moral-wrongdoing frame** (e.g. sports banter, personal insult unrelated to conduct, generic swearing)? → **5 Non-moral toxicity**.
6. Otherwise → **6 Neutral / other** (information, questions, jokes, support, praise, personal news).

### Boundary rules

- **1 vs 3 (the key boundary).** Ask: *after reading this, is the target still treated as someone owed basic decency and capable of change?* If yes → 3. If the post forecloses that (contempt, "they're beyond help", relish at their downfall) → 1. Anger alone does not make a post punitive. Contempt usually does.
- **1 vs 2.** Explicit = a sanction is named or wished. "She should resign" about an official's conduct is a sanction demand → 2. "Disgraceful. Remember this when you vote" → 1 (implicit; no specific sanction on a person, but performed condemnation).
- **Accountability demands.** Calls for *proportionate institutional process* ("this should be investigated", "the regulator should look at this") → 3, unless paired with deservingness or contempt. Calls for *ruin or exclusion* ("hope this ends his career") → 2.
- **Sarcasm and irony.** Code the intended meaning. If uncertain, code the literal meaning and set `confidence` low.
- **Quoting or reporting** punitive speech in order to criticise it → code the post's own stance, not the quoted text.
- **Self-directed** ("I deserve this") → 6, unless directed at a group the speaker belongs to.
- **No identifiable target** (vague moralising about "society") → usually 3 or 6.

## Punitive score (continuous)

`punitive_score` from **-2 to +3**, independent of category. It records degree on the punitive-to-solidaric axis:

| Score | Meaning |
|---|---|
| +3 | Wishes or celebrates severe harm, ruin, death or permanent exclusion |
| +2 | Explicit sanction demand, or strong contempt / dehumanisation |
| +1 | Mild implicit punitiveness: sneer, gloat, moral exclusion hint |
| 0 | No punitive or solidaric content |
| -1 | Criticism paired with recognition of the target's standing ("I disagree, but…", "they can fix this") |
| -2 | Active repair or solidarity across a divide: apology, concession, de-escalation, extending good faith to an opponent |

## Features (true / false)

These are the text traces of the four broken Fehr–Gächter conditions, plus psychology. Mark each independently of category.

| Feature | True when |
|---|---|
| `contested_claim_as_fact` | An allegation of wrongdoing that is disputed or unverified in the post is stated as settled fact (condition 1: violation alleged, not displayed). |
| `group_for_individual` | A group is blamed or condemned for what an individual (or a few) did: "typical leftists", "this is what Tories are like" (condition 2: attribution). |
| `spoken_about_not_to` | The target is discussed in the third person for an audience rather than addressed directly (condition 4: audience performance). If the target is directly addressed (@-reply, "you"), false. |
| `absolutism` | Totalising language: always, never, every single one, completely, beyond redemption. |
| `dehumanising` | Target likened to animals, vermin, disease, filth, objects, or described as less than human. |
| `punitive_lexicon` | Words of sanction or desert: deserve, punish, pay for, consequences, karma, burn, cancel, ruin, jail, fired, banned. |
| `deservingness` | Claims or implies the target *deserves* a bad outcome. |
| `contempt` | Sneering superiority, mockery, eye-rolling disgust, treating the target as beneath engagement. |
| `moral_exclusion` | Target placed outside the scope of fairness or concern: "people like this don't deserve…", "no sympathy", "not one of us". |
| `criticism_of_person` | Gottman's *criticism*: attacks character ("you are selfish") rather than behaviour ("that was selfish"). |
| `defensiveness` | Counter-attack or victimhood in response to a criticism ("well what about you…"). |
| `stonewalling` | Refusal to engage: "not reading that", "blocked", "I'm done with you people". |
| `repair_attempt` | Any move to de-escalate or restore: apology, concession, humour to defuse, acknowledgement, "fair point", "I hear you". |

## Flags

| Flag | Values |
|---|---|
| `target_type` | `individual`, `group`, `institution`, `none` |
| `target_in_out_group` | `in_group` (speaker appears to share the target's side), `out_group`, `unclear`. Code `unclear` unless the text makes it evident. Do not guess from stereotypes. |
| `blame_target` | Free text, 1–4 words: who is blamed for the wrong (e.g. "the government", "trans activists", "a teacher"). `none` if no blame. |
| `topic` | One of: `politics_domestic`, `politics_international`, `race_ethnicity`, `religion`, `gender_sexuality`, `immigration`, `crime_justice`, `celebrity_media`, `sport`, `tech`, `everyday_life`, `other` |
| `identity_and_conduct_mixed` | true / false (see rule 1) |
| `confidence` | `high`, `medium`, `low` |

## Output

Return one label per post using the `record_label` tool. Give a one-sentence `rationale` that names the decisive cue.

<!-- PROMPT END -->

## OPEN decisions (not in the prompt; resolve after the pilot)

1. **Speaker position (condition 3: cost).** Cannot be coded from text. Plan: attach as metadata later (follower count, verified/institutional account, power relative to target). This also handles the power-asymmetry critique: a marginalised speaker calling out a powerful target may read differently. Do not ask coders to infer it.
2. **Category 4 precedence.** Currently identity hate overrides conduct-based punishment. Alternative: make punitive and identity-hate two independent axes (multi-label). Multi-label is more faithful but halves your alpha budget. Decide after seeing how many pilot posts are mixed.
3. **"Should resign."** Is a resignation demand about an official's conduct punitive (2) or accountability (3)? Currently 2. This is the single most likely disagreement; watch it.
4. **Score scale.** -2 to +3 is asymmetric on purpose (repair is rarer and less graded than punitiveness online). Check whether coders use -2 at all; if not, collapse to -1.
5. **Gottman tags at post level.** Defensiveness and stonewalling are relational; they may only be codable with the parent post. Consider moving them to the conversation layer if pilot alpha is poor.
6. **Islamophobia focus case.** Topic list has `religion` and `race_ethnicity`; decide whether Islamophobia gets its own topic tag for the H7 reservoir test.

## Constructed examples (for calibration; not real posts)

| Post | Cat | Score | Decisive cue |
|---|---|---|---|
| "The minister misled Parliament. That's a serious breach and it needs a proper inquiry." | 3 | 0 | Moral judgement + proportionate process, no deservingness |
| "Imagine being this stupid and still having a job. Some people are just beyond help." | 1 | +1 | Contempt + foreclosing change, no named sanction |
| "Get him off every platform. He should never work in media again." | 2 | +2 | Explicit exclusion/ruin |
| "lol he got sacked. Couldn't happen to a nicer guy 😂" | 1 | +2 | Gloating at downfall |
| "Typical [party] voters, every one of them a liar." | 1 | +1 | Group-for-individual, absolutism |
| "Honestly fair point, I was too harsh earlier. Sorry." | 6 | -2 | Repair attempt |
| "Ref is absolutely blind tonight, what a joke" | 5 | 0 | Hostile, no moral wrongdoing frame |
| "I think she's wrong on this, but she's clearly acting in good faith and could still change it." | 3 | -1 | Criticism + recognition of standing |
