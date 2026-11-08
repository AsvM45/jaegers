# Grok historical-feature compliance witness — issue #55

**Evidence rating: `NOT_CERTIFIED`**

This is an independent, code-grounded witness for the champion historical stacker. It does not certify organizer acceptance, does not change the champion, and does not submit anything. Passing tests below mean the measured channels are present in the current champion. They are not a compliance pass.

Three information sets stay separate:

- A historical training row at tick `t` is a feature vector for the spin at `t`. Its label is the observed payout at `t`.
- A parameter learned from the training split can use that split's histories. Applying it at a test cutoff is different from writing it into an earlier training row of the same machines.
- At a test or validation query cutoff `c`, the query signal, the count of ticks before `c`, and a prior fit on the training split are known. Ticks at or after `c` are not.

## Scope

| Item | Value |
| --- | --- |
| Issue | #55 |
| Claim | https://github.com/AsvM45/jaegers/issues/55#issuecomment-6717414592 |
| Agent | Cursor Grok agent for issue #55 (`cursor-grok-he55`) |
| Branch | `agent/grok-he55-asof-witness` |
| Worktree | `C:\Users\asvat\OneDrive\Documents\GitHub\Datathon2026\jaegers-he55-asof-witness` |
| Base | `origin/main` at `d3b286cdcd91d984480ca5bcd2203f73dc67556b` |
| Champion source | `Jaeger_Main/House_Edge/jaegers_entry/jaeger_model.py` |
| Champion params | `Jaeger_Main/House_Edge/jaegers_entry/params.json` |

The worktree was opened at `cf45205` and fast-forwarded to `d3b286c` before any issue #55 edit. That update contains the already-merged HE-46 portability witness, the HE-15 temporal challengers, and Claude's HE-03 causal-stacker challenger. None of those files were edited. `jaegers_entry/jaeger_model.py` and `params.json` are unchanged between those two commits.

SHA-256 of the audited champion files:

- model `10da55e636962ae6032344415390ca6efb38ace734977dc2a94e7065152fa0c3`
- params `af6fd59838f18987bedf9d4bf220634892411ff3be848516c82a1f4bd47b4e3b`

Those match the prefixes recorded in `research/audits/historical_signal.md`. Champion params used here: `gamma=1.0`, `lam=0.95`, `lam_short=0.99`, `prior=0.35`, `prior_short=0.85`.

## What was run

Command, from the worktree root:

```text
python -m pytest Jaeger_Main/House_Edge/tests/test_grok_asof_evidence.py -v --tb=short
```

Result: **9 passed, 0 failed, 0 errors in 2.77s**.

Environment: Windows 11 (`10.0.26300`), CPython 3.13.2, pytest 9.2.0, numpy 2.2.6. The #3 audit reported numpy 2.5.4. Controls that should be identical used `numpy.array_equal`, so this witness does not depend on a hidden-score rerun. No stacker was fit. No public split was read. No cloud call was made.

The same measurements print from:

```text
python Jaeger_Main/House_Edge/tools/grok_asof_evidence.py
```

## Rules used

Organizer `RULES.md`:

> Use observations strictly before the prediction tick, including when making training examples from earlier history.

Organizer `DATA.md`:

> When building training examples from history, a future observation can be a label for its earlier prediction, but never a feature for that prediction.

`DATA.md` also calls `signal` "the observable `signal`" on the query and gives values -1, 0, or 1. It does not define `signal(t)`. Team `AGENTS.md` says not to copy the final query signal onto historical rows. That sentence is team guidance, not an organizer ruling.

## How the champion builds a historical row

`predict(..., collect=True)` walks ticks in order. At tick `t` it calls `stack_features` before updating counts, expert log-likelihood, base rate, or `seen` (`jaeger_model.py` around the collect block and the updates that follow it). The label appended for that row is whether the payout at `t` is positive. `fit_stacker` then trains on `X[:, 1:]`, dropping the constant column. This witness did not call `fit_stacker`.

`learn_expert_prior` runs `predict(..., return_ll=True)` through each training machine's whole history and returns the log-frequency of which expert has the highest final log-likelihood. `predict.py` learns that one vector on the train split and passes it into both `fit_stacker` and test `predict`. Inside `stack_features`, champion `gamma` adds `expert_logprior` to every machine's expert scores before the softmax. The prior is not its own output column. It changes the blend features.

`nobs` is the count of observed ticks before the query cutoff, computed once before the tick loop. If `nobs < 100`, every tick uses `lam_short` and `prior_short`. Otherwise every tick uses `lam` and `prior`.

Column 13 is `float(query["signal"])`, copied on every row.

## Provenance matrix

Synthetic rows are one machine unless noted. The fixed row is the stacker row at tick 20 (`seen=20`, `log1p(seen)=3.044522437723423`) or tick 30 (`3.4339872044851463`). Deltas are absolute. A later-payout comparison keeps the same ticks and changes only payout values after the switch, so coverage does not change.

| col | feature | allowed at tick t | what the code uses | synthetic result |
| --- | --- | --- | --- | --- |
| 0 | `ones` | none; constant | dropped by `fit_stacker` | **PASS**. Delta 0 in every mutation. |
| 1 | `logit_blend` | payouts at ticks `< t`, same episode | blend of experts whose weights include the prior and the final-coverage regime | **FAIL**. Own-future prior delta `0.000255056`. Coverage delta `0.0950365`. |
| 2 | `logit_top_expert` | payouts at ticks `< t`, same episode | probability of the expert with the highest weight | **FAIL** via final coverage, delta `0.089676`. Prior-only delta `0`. |
| 3 | `logit_second_expert` | payouts at ticks `< t`, same episode | probability of the second-weight expert | **FAIL** via final coverage, delta `0.089676`. Prior-only delta `0`. |
| 4 | `logit_base_rate` | this machine's payouts at ticks `< t` | `base_w` / `base_n` with `base_lam` and fixed `prior` | **PASS**. Delta 0 under the prior, coverage, and signal mutations. |
| 5 | `top_weight` | payouts at ticks `< t`, same episode | softmax weight after adding `gamma * expert_logprior` | **FAIL**. Own-future delta `0.171152`. Other-episode delta `0.0972088`. Coverage delta `0.00576467`. |
| 6 | `disagreement` | payouts at ticks `< t`, same episode | weight spread of expert probabilities | **FAIL**. Own-future delta `2.75266e-05`. Coverage delta `0.000607284`. The prior move is small because the expert probabilities are close. |
| 7 | `log1p_top_count` | count state uses ticks `< t`; the selected expert need not | forgotten count of the selected expert | **FAIL**. All-loss prefix, later payouts changed: delta `0.0576346`. Coverage delta `0.449041`. |
| 8 | `blend_times_top_weight` | inherited | product of columns 1 and 5 | **FAIL**. Own-future delta `0.59493`. Other-episode delta `0.337907`. |
| 9 | `blend_times_disagreement` | inherited | product of columns 1 and 6 | **FAIL**. Own-future delta `9.56203e-05`. Coverage delta `0.00205327`. |
| 10 | `blend_times_log1p_top_count` | inherited | product of columns 1 and 7 | **FAIL**. Zeros-prefix prior delta `0.200344`. Coverage delta `1.31568`. |
| 11 | `type_balanced` | static `machine_type` | query field | **PASS**. Future mutations delta 0. Switching steady to jackpot does not change this column. |
| 12 | `type_jackpot` | static `machine_type` | query field | **PASS** against future mutations. Switching steady to jackpot changes only this column. |
| 13 | `query_signal` | not defined as a per-tick series in `RULES.md` | cutoff query signal on every row | **AMBIGUOUS**. Signal `0` versus `-1` changes only this column, from `0.0` to `-1.0`. |
| 14 | `log1p_seen` | observed ticks `< t` on this machine | running count before the snapshot | **PASS**. Stays `log1p(t)` when later ticks are deleted or later payouts change. |

`test_temporal.py` already shows the signal copy and the coverage effect on a different fixture. This witness measures those two channels again, column by column, and adds the expert-prior channel the original #3 audit said had no fixture. It does not import or modify `research/challengers/qa_causal_stacker.py`.

## Concerns

### Same-machine expert prior — behavior `SUPPORTED`, rule `NEEDS_ORGANIZER_RULING`

Fixture: cutoff 120, ticks 0–39 identical, ticks 40–119 differ. Fixed row is tick 20.

- Alternating versus persistence: `learn_expert_prior` argmax moves from expert 1 to expert 36. Log-prior max absolute change `0.693147` (`log 2`). With champion `gamma=1`, column 5 of the tick-20 row moves by `0.171152`.
- Setting `gamma=0` makes the two tick-20 rows identical.
- Passing the first prior into both histories makes the two tick-20 rows identical. Later payout values do not enter the row except through the prior.
- All-loss ticks 0–39, then zeros versus alternating: argmax moves from expert 0 to expert 9. Column 7 moves by `0.0576346` while column 2 stays exactly 0. The count tensor and context do not depend on the prior, and the frozen-prior control keeps column 7 identical, so the count changed because a different expert became top. That expert's win-probability logit matched the previous top, which is why columns 2 and 3 did not move in the prior-only fixtures.

Plain reading of the two quotes above: ticks after `t` are inside a feature of the training row at `t`. Competing reading: the vector is one empirical-Bayes parameter fit on the training split, and any such parameter may use the whole split. This witness does not choose the organizer's reading. It does show the value is inside the feature matrix, not only inside an inference-time offset applied to other episodes.

The historical label stays 0 on both sides. This is not a swapped label and not a hidden-test label.

### Other-episode expert prior — behavior `SUPPORTED`, rule `NEEDS_ORGANIZER_RULING`

Episode A is alternating for all 160 ticks. Episode B matches A through tick 39 and then either continues alternating or switches to persistence. Episode A's tick-30 row is the fixed row. Its own history never changes.

The shared prior still moves by max absolute `0.693147`. Its argmax stays expert 1, so a change of mode is not required. Episode A's column 5 moves by `0.0972088` and column 8 by `0.337907`. `gamma=0` and a frozen prior each remove the difference.

This is the closer case to a parameter learned from other training machines. It is still written into A's historical features. Whether that is allowed is an organizer question. It is not test-target leakage: episode B is part of the same synthetic training folder, and no test labels exist.

### Final history coverage — behavior `SUPPORTED`, rule `PLAIN_READING`

Cutoff 128, alternating payouts. Deleting ticks 70–127 drops `nobs` from 128 to 70, across the hardcoded threshold of 100. The tick-30 row changes in columns 1, 2, 3, 5, 6, 7, 8, 9, and 10. Columns 4, 13, and 14 do not. Setting `lam_short=lam` and `prior_short=prior` makes the two tick-30 rows identical.

So the early row is using how many observations exist before the final cutoff. At cutoff `c` that count is known. At tick `t < c` it is not part of the observations strictly before `t`. This is train/serve skew for historical rows, not a demonstration that test labels were read.

### Query signal on historical rows — behavior `SUPPORTED`, rule `NEEDS_ORGANIZER_RULING`

Changing only the query signal from `0` to `-1` changes column 13 from `0.0` to `-1.0` and leaves the other 14 columns identical. The implementation copies the cutoff signal onto the historical row. `RULES.md` does not say whether that signal was already determined at tick `t`. No compliance claim follows from the copy alone.

### Channels that do not use later information — suspicion `UNSUPPORTED`

With the prior held fixed:

- later payout values on the same machine do not change the fixed row
- a sibling's payout at the same tick `t` does not change the row
- a sibling's payouts after `t` do not change the row
- ticks equal to the cutoff and after the cutoff do not change `predict()` output

Column 4, columns 11 and 12, and column 14 stay on the as-of or static side of the matrix. The label at the fixed row is the outcome at that tick.

No fixture in this witness reads a hidden test label. The concern "this path leaks hidden test labels" is `UNSUPPORTED` here. Absence of a leak in these synthetic tests is not a proof about every other research module.

## What this does not say

Claude's `research/audits/historical_signal.md` and `research/audits/qa_causal_stacker.md` were read only. Their reported validation points, including the cross-fit prior near `+0.01` and the fully as-of no-head loss near `0.29`, were not rerun and are not adopted as measurements of this witness. Their challenger is a separate implementation. This report does not promote it and does not edit it.

`SIZE_REGIMES` are constants in the size model. They are not columns of `stack_features`. This witness does not re-audit them.

Nothing here authorizes an organizer upload, a merge to `main`, or a claim about the hidden test score. The frozen `REVIEW_MAIN_9PM` pair was not opened or modified.

## Question for the release lead on issue #5

1. Is `queries.csv` `signal` a constant machine attribute for the whole history, or a cutoff-time value that historical training rows must not use?
2. May one expert-frequency prior fit on other training episodes be inserted into historical-row features, given that the same-machine future and the final tick count are already shown to enter those features?
3. The frozen champion is unchanged by this PR. Keeping it, or later adopting any as-of challenger, remains a release decision. This witness is `NOT_CERTIFIED` until that ruling or a historical-training path that is independently shown to use only as-of inputs.
