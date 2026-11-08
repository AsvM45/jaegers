# Champion audit evidence and independent review

This note separates source observations from executed checks. Live numeric results
and release status belong only in [CURRENT_STATE.md](CURRENT_STATE.md). Independent
statistical review is [issue #3](https://github.com/AsvM45/jaegers/issues/3); CHAT has
not claimed or closed that independent review.

## Observed source behavior

The frozen b78abe75 implementation uses 73 lag experts, recency-discounted likelihoods,
sibling evidence, short-history smoothing, payout-size regimes/experts, a train-fitted
expert prior and a HistGradientBoostingClassifier win stacker.

- `stack_features` includes final query signal in historical collect=True rows.
  Historical signal(t) is not separately supplied.
- Final observed-history count selects smoothing used while replaying earlier ticks.
- SIZE_REGIMES source comments explicitly attribute constants to public validation
  targets. Selection exposure is separate from whether published rules permit it.

## Executed evidence

`tests/test_temporal.py` exercises future/sibling mutations, row order, episode
isolation, deterministic probability outputs, copied signal and future coverage.
The coverage fixture removes later observations across the 100-observation threshold
and demonstrates a change in earlier stack features. These are dependency findings,
not an assertion of contest-rule violations.

The integration adapter's `causal=True` preset removes signal from stack fitting and
inference and fixes smoothing independent of final history count. It changes both
policies and must not be described as a pure signal-only ablation. Specialist review
should compare the factors separately and establish metadata availability.

Windows and Linux reproduced different predictions with matching package versions.
The Linux-generated package subsequently passed exact cold Linux parity. The cause
of the cross-platform difference has not been established; no unsupported causal
explanation is recorded. Preserve both the failed and successful release evidence.

## Remaining statistical work

Independent reviewers should trace every feature/learned transform, test unsupported
historical context and validate episode-held-out comparisons. Keep the original
champion frozen. Public true-vector scores are development-exposed; sampled-label
Brier and test-format checks do not establish hidden-test performance or acceptance.
