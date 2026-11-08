# HE-17: paired component ablations of the JAEGERS champion

Issue: AsvM45/jaegers#17. **Verdict: no promotion.** Every ablation is worse than or tied with the
champion; this study only explains what each component contributes. Promotion of anything needs lane A.

## Provenance

- Hypotheses pre-registered in `research/configs/stats/ablations/he17_ablations.json`, committed and pushed
  in `b697dd8` (2026-11-07 18:57 CT) **before** any HE-17 result was computed.
- Harness `research/analysis/stat_ablation_he17.py`; each variant loads a fresh copy of the champion from
  disk and changes only what the config lists. Harness tests: `tests/test_stat_ablation_he17.py` (6 passed).
- Results `research/reports/stat_ablation_he17_results.json` (summary + per-episode losses).
  sha256 prefixes: config `b95b0ddd`, params `1d496f5d`, harness `7155b4c4`, champion `ddd432fb` as checked
  out with CRLF on Windows (= `10da55e6` with LF, the same bytes as on `main`).
- Run: `python -m research.analysis.stat_ablation_he17 --out research/reports/stat_ablation_he17_results.json --workers 3`
  from `Jaeger_Main/House_Edge`; 231 s wall, Windows 11, CPython 3.13.5, numpy 2.5.4, scikit-learn 1.9.1.
- Trial IDs are content hashes (variant + champion + params + config + harness); not yet in the #8 registry,
  which lane A has not published.

**Evaluations (same episodes for every variant):**
- **A** - fit expert prior + stacker on TRAIN, official `score_round` on VALIDATION. *Development-exposed*:
  params and `SIZE_REGIMES` were chosen on these targets, so A favours the champion's settings.
- **B** - fit on VALIDATION, five-class observed-outcome Brier on TRAIN queries (lower is better). Noisy
  (one sampled outcome per query) but independent of validation target vectors except `SIZE_REGIMES`.
- 95% intervals: paired bootstrap of episodes within condition, 4000 resamples.
- Pre-registered rule: *supported* = A interval excludes 0 **and** B points the same way. Below, **B confirms**
  means B's own interval also excludes 0.

## Results

| variant | experts | A points | A diff vs champion [95% CI] | B Brier | B diff [95% CI] | supported | B confirms |
|---|---|---|---|---|---|---|---|
| champion | 73 | **55.122** | - | 0.36514 | - | - | - |
| nostack | 73 | 52.836 | -2.29 [-2.93, -1.72] | 0.37276 | +0.0076 [+0.0033, +0.0119] | yes | yes |
| nosig | 73 | 55.000 | -0.12 [-0.25, -0.00] | 0.36473 | -0.0004 [-0.0019, +0.0011] | no | - |
| no_size_experts | 73 | 53.683 | -1.44 [-1.80, -1.11] | 0.37376 | +0.0086 [+0.0029, +0.0146] | yes | yes |
| no_peer_evidence | 73 | 54.461 | -0.66 [-1.20, -0.17] | 0.36350 | -0.0016 [-0.0048, +0.0010] | no | - |
| no_expert_prior | 73 | 54.697 | -0.43 [-0.71, -0.18] | 0.36538 | +0.0002 [-0.0016, +0.0022] | yes | no |
| single_lag_only | 17 | 32.115 | -23.01 [-23.99, -21.99] | 0.53543 | +0.1703 [+0.1505, +0.1895] | yes | yes |
| binary_categories_only | 37 | 54.026 | -1.10 [-1.41, -0.79] | 0.36679 | +0.0017 [-0.0023, +0.0057] | yes | no |
| no_short_history_prior | 73 | 54.638 | -0.48 [-0.73, -0.23] | 0.36583 | +0.0007 [-0.0009, +0.0024] | yes | no |
| slower_forgetting (lam .99) | 73 | 39.327 | -15.80 [-16.62, -14.95] | 0.47907 | +0.1139 [+0.0981, +0.1298] | yes | yes |
| faster_forgetting (lam .90) | 73 | 53.471 | -1.65 [-2.47, -0.94] | 0.37186 | +0.0067 [+0.0025, +0.0111] | yes | yes |
| train_size_regimes | 73 | 54.492 | -0.63 [-0.81, -0.45] | 0.36867 | +0.0035 [+0.0000, +0.0070] | yes | borderline |
| **control: shuffled stacker labels** | 73 | 27.779 | -27.34 [-28.35, -26.38] | 0.61072 | +0.2456 [+0.2231, +0.2677] | yes | yes |

Per-condition loss ratios on A (lower is better):

| variant | stable | short_history | drift | shared_change |
|---|---|---|---|---|
| champion | .067 | .117 | .092 | .077 |
| nostack | .120 | .185 | .125 | .114 |
| nosig | .067 | .122 | .095 | .080 |
| no_size_experts | .112 | .131 | .123 | .105 |
| no_peer_evidence | .072 | **.166** | .088 | .082 |
| no_expert_prior | .070 | **.151** | .093 | .075 |
| single_lag_only | .836 | .986 | .851 | .800 |
| binary_categories_only | .104 | .120 | .110 | .108 |
| no_short_history_prior | .069 | **.150** | .094 | .080 |
| slower_forgetting | .159 | .144 | **.880** | **.921** |
| faster_forgetting | .101 | .126 | .106 | **.155** |
| train_size_regimes | .083 | .123 | .111 | .088 |
| control_shuffled | 1.180 | 1.179 | 1.178 | 1.102 |

## Reading against the pre-registered hypotheses

| variant | expected | observed | hypothesis |
|---|---|---|---|
| nostack | worse, large | -2.29, B confirms | held |
| nosig | A slightly worse, B unchanged | -0.12, B flat | held |
| no_size_experts | worse | -1.44, B confirms | held |
| no_peer_evidence | worse, mostly shared_change | worse **mostly short_history**; drift slightly *better*; B flat (slightly better) | **partly wrong** |
| no_expert_prior | worse, mostly short_history | -0.43, short_history .117 -> .151; B flat | held on A only |
| single_lag_only | worse, large | -23.0, B confirms | held |
| binary_categories_only | about equal | **-1.10** on A, B flat | **wrong on A** |
| no_short_history_prior | worse, short_history | short_history .117 -> .150; B flat | held on A only |
| slower_forgetting | worse, drift | drift and shared_change collapse (.88/.92) | held, larger than expected |
| faster_forgetting | worse, stable | worse everywhere, most in shared_change | partly |
| train_size_regimes | worse on A | -0.63, B borderline worse | held |
| control (shuffled labels) | much worse | 27.78, below nostack | held - harness is sensitive |

Takeaways:
1. **Structure that matters most** (both evaluations agree): lag-pair experts (-23 points without them),
   forgetting rate (lam .99 loses 16 points, mostly drift/shared_change), the stacker (-2.3), size experts
   (-1.4), and the forgetting rate not being too fast either (-1.7).
2. **Short-history helpers** (peer evidence, expert prior, short-history smoothing) each buy about 0.4-0.7 points
   on A, almost all in `short_history`, but none is confirmed by B. Their settings were tuned on validation,
   so part of that gain may be selection. B has few short-history queries per episode, so it is weak there.
3. The shuffled-label control scoring 27.8 (worse than no stacker at 52.8) shows the stacker learns real
   structure from historical rows, and also that a mis-fitted stacker is very harmful: keep the stacker
   training path under test (#2/#16).
4. Train-only size regimes cost 0.63 on A and are borderline worse on B. Relevant for the adaptation round,
   where validation-derived constants may no longer apply.

## Prioritized follow-ups (none promoted)

1. **Forgetting-rate sensitivity curve** (lam in 0.92-0.97) per condition, on B and on an episode-grouped CV
   inside train, before the adaptation round where drift patterns change.
2. **Short-history components under B-style evaluation with more power** (episode-grouped CV on train's
   historical rows) to see whether the 0.4-0.7 point A gains survive outside validation.
3. **Pair-context expansion**: pairs carry most of the signal; test lag triples or 0/1/2+ pairs only for top
   lags, with a strict runtime budget.
4. **Exposure-free size regimes** (HMM over size outcomes) to close the 0.63 gap without validation targets.
5. Register these trial IDs in the #8 registry once lane A publishes it.
