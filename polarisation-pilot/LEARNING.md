---
title: Learning the pilot code (rebuild path)
status: draft
created: 2026-11-03
links: "[[Polarisation Network]]"
---
# Learning the pilot: rebuild it yourself, with AI as tutor

**Goal:** you can explain every line and change it without AI. The code in this repo is a reference answer to check against, not something to memorise.

## Rules for AI-assisted rebuilding

1. **You type the code.** Ask AI to *explain*, *quiz you*, *review your attempt* or *give a hint*, never to write the whole thing. A useful prompt: "Here is my attempt at X. Don't fix it. Tell me what's wrong, and ask me a question that leads me to the bug."
2. **Do it by hand on paper first.** Every core quantity below has a hand exercise with the answer at the end. If you can't do it by hand, code won't help.
3. **Check against the reference.** After your version works, diff it against the repo's function and explain every difference.
4. **The checkpoint:** close everything and explain the idea aloud in 2 minutes, then change one thing (a threshold, a state, a rule) and predict the effect *before* running it.

## Suggested order (matches your plan)

| # | Piece | Why it matters | Hand exercise | Then code | Reference |
|---|---|---|---|---|---|
| 1 | The codebook | It *is* your construct; examiners probe it first | Re-key `hard_cases.csv` under v0.2 (see `codebook_v0.2_dryrun.md`) | none | `codebook_v0.2.md` |
| 2 | Krippendorff's α | Your V1 pass/fail rests on it | §A below | ~30 lines, nominal only | `label_pilot.py: alpha, alpha_ci` |
| 3 | Gain g + endings | H2's core numbers | §B below | ~60 lines | `conversation/chains.py: gain_table, chain_endings` |
| 4 | The fold | M1, and the 30 Nov maths test | §C below (Strogatz ch. 3 first) | ~25 lines + one plot | `model/build_notebook.py` Part 3 |
| 5 | Plumbing | Needed, but not examined | Read, run, change one thing each | none | `sample_bluesky.py`, `tools/`, batch code |

---

## A. Krippendorff's α from one concrete example

**Why it exists.** Raw agreement flatters you when one category dominates. If 90% of posts are "neutral", two coders who always say neutral agree 90% of the time while learning nothing. α asks: *how much less do we disagree than we would by chance, given how often each category is used?*

    alpha = 1 − (observed disagreement / disagreement expected by chance)

**Example.** Two coders, six posts, nominal categories:

| post | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| You | 1 | 1 | 3 | 3 | 5 | 6 |
| Claude | 1 | 3 | 3 | 3 | 5 | 6 |

Raw agreement is 5/6 = 0.833. Now by hand:

1. **Pair the values.** Each post gives two ordered pairs, (you, Claude) and (Claude, you), so 12 values in all. List the pairs. How many are disagreements?
2. **Observed disagreement** D_o = disagreeing pairs / 12.
3. **Category totals:** count how often each category appears among the 12 values (n₁, n₃, n₅, n₆).
4. **Chance disagreement** D_e = (12² − Σ n_c²) / (12 × 11). This is the probability that two values drawn at random without replacement differ.
5. α = 1 − D_o / D_e.

**Then:** change post 2 so both say 1. Predict whether α rises above or below raw agreement. Then change everything to category 3 except one post, and see why α falls when categories are lopsided.

**Code it:** `alpha_nominal(a: list, b: list) -> float`, then check it against `krippendorff.alpha(..., level_of_measurement="nominal")`.

---

## B. Gain g and chain endings on an 8-post tree

**Why it exists.** A reply thread is a tree. If each punitive post provokes on average more than one punitive reply, punitiveness spreads like a chain reaction (g > 1). That's the same arithmetic as R₀ in epidemics and the cascade condition in L5. The decisive comparison is with non-punitive moral criticism (M): if g_P ≈ g_M, it's moral disagreement that provokes punitive replies, not punitiveness itself.

**The tree** (R is the original post, which isn't counted as a reply):

    R
    ├── a (P)
    │   ├── b (P)
    │   └── c (N)
    │       └── d (R)
    └── e (M)
        ├── f (P)
        └── g (N)

States: P punitive, M moral criticism, R repair, N neutral.

1. **g_s = mean number of P children per post in state s** (leaves count, with zero children). Compute g_P (posts a, b, f) and g_M (post e).
2. Split g into **mean replies × share of replies that are P**, for P and for M. Which part drives the difference here?
3. **Endings.** List the four root-to-leaf chains (a→b, a→c→d, e→f, e→g). The ending is the last non-neutral state: P = CUT, R = REPAIRED, otherwise OTHER. What fraction of chains starting with P end CUT?
4. **The Markov chain.** At each post you either step to a reply (chosen uniformly) or stop if it is a leaf. From a P post, what is the probability of ending CUT? Hint: a, b and f are pooled together. Why does this differ from step 3's answer, and what does that tell you about the Markov assumption?

**Code it:** a `children` dictionary, then `g(state)`, then a recursive `endings(node)`. Compare with `chains.py`.

---

## C. The fold, from a ball in a landscape

**Why it exists.** Your central claim is that polarisation doesn't reverse when you undo its cause. A fold (saddle-node) is the simplest mathematics that has that property, called **hysteresis**.

1. Read Strogatz §3.1 (saddle-node) and §3.6 (imperfect bifurcations). Draw **ẋ = h + x − x³** as curves for h = −0.6, 0, +0.6: plot ẋ against x and mark where it crosses zero (the equilibria). Use arrows on the x-axis for the direction of flow.
2. Now plot the **equilibria against h**, which gives the S-shaped curve. Mark the two fold points where the middle branch meets the outer ones. (They are at x = ±1/√3. Derive this by setting ẋ = 0 and d(ẋ)/dx = 0.)
3. **Hysteresis by hand.** Start at h = −1 on the lower branch and raise h slowly. Where do you jump? Now lower h. Where do you jump back? Shade the bistable band.
4. **Recovery near the fold** (the normal form): near the fold, ẋ ≈ r + x². Show that the eigenvalue at the stable point scales as √r. So the recovery *rate* goes as √(distance), slope +½ on log-log axes, and the recovery *time* has slope −½.

**Code it:** a root finder over a grid of h, a plot, then a forward-and-backward sweep with simple Euler steps. Compare with `build_notebook.py` Part 1 (the same potential, `V(u, h)`), then read Part 3, where the variable is Π instead of h.

---

## D. Plumbing: read, run, change one thing

For each one, run it, read it top to bottom with AI explaining anything unclear, then make the change listed and predict the result first.

| File | Change to make |
|---|---|
| `sample_bluesky.py` | Add a 10th topic stratum; check the sample is still balanced |
| `label_pilot.py` (estimate, sync) | Print the token count per post; find where the codebook text enters the request |
| `tools/jetstream_sample.py` | Halve the window length; what happens to the CI width and why? |
| `tools/score_toxicity.py` | Report the share below 0.3 too; compare with 0.5 and 0.7 |
| `conversation/chains.py` (bootstrap, CLI) | Resample posts instead of conversations; watch the CI shrink, and explain why that's wrong |

---

## Answers (cover before attempting)

**A.** Pairs: (1,1) ×2, (1,3), (3,1), (3,3) ×4, (5,5) ×2, (6,6) ×2. Disagreements: 2, so D_o = 2/12 = 0.167. Totals: n₁ = 3, n₃ = 5, n₅ = 2, n₆ = 2, so Σn² = 42. D_e = (144 − 42)/132 = 0.773. **α = 1 − 0.167/0.773 = 0.784**, below raw agreement (0.833) because chance agreement is high.

**B.**
1. g_P = (1 + 0 + 0)/3 = **0.33** (a has one P child, b; b and f are leaves). g_M = 1/1 = **1.0** (e has one P child, f).
2. P: 0.67 replies × 0.5 P-share. M: 2 replies × 0.5 P-share. **Reply volume** drives the difference here, not contagion.
3. Chains starting with P (a): a→b ends CUT, a→c→d ends REPAIRED, so **1/2 end CUT**.
4. The Markov chain gives P(CUT | P) = **0.8**. It pools a, b and f: b and f are leaves (CUT), and a goes to b (CUT) or onwards to repair. The chain forgets *which* P post it is in, so a P late in a thread (b, f) is treated the same as one early (a). If the empirical and model endings differ a lot on real data, escalation has memory, which is a finding.

**C.** Fold points at x = ±1/√3, h = ∓2/(3√3) ≈ ∓0.385. Rising h, you jump up at h ≈ +0.385; falling, you jump down at h ≈ −0.385. The bistable band is |h| < 0.385.
