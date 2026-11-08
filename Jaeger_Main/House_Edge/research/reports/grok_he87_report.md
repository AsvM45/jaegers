# HE-87 feature, model-family and mixture results

Status: MEASURED_NOT_PROMOTED. No champion was replaced and no organizer file was written.

## Evaluation

- Source: sampled-outcome episode-grouped CV. Official points: none. Public-validation peeks: 0.
- Folds: 4 via `research.dataset.episode_folds, condition-stratified, digest order, index modulo fold_count`.
- Fold manifest SHA-256: `84f2aa3282c5dc8f394bdd06179f0adac2ec3865804dda99285d1b5c7e4ccc0e`.
- Queries: 768. Episodes: 96. Class counts [0,1,2,5,20]: [431, 161, 115, 49, 12].
- Supervision: one labeled row per train query; features and count experts use ticks < cutoff only.
- Signal: default matrix ignores signal; logistic_full_plus_own_query_signal uses that query's own signal and never copies it onto another tick.
- Wall seconds: 316.683. Tracemalloc peak bytes: 111907365.
- Primary hyperparameters are the protocol values. Grids and the top-three pairwise follow-up are sensitivity checks on the same folds, not a held-out confirmation and not a public-validation search.

## Measured reading

- The frozen champion reference is included for comparison. Its parameter file already carries older public-validation exposure. This run did not open validation files.
- Point estimates: champion 0.362291, factorized size 0.563578, static mixture 0.565484.
- Causal adapter mean Brier: 0.364293.
- No train query has fewer than 8 observed ticks, so the preregistered short-count regime bit does not fire on this split. Mean observed ticks: 182.21875. Exact lag 1 is known for fraction 1.0.
- Logistic one-factor groups that reduced Brier: ['win_size']. Groups that increased it: ['changepoint', 'entropy', 'rarity20', 'sparse', 'discounted', 'interactions', 'transitions', 'sibling'].
- Static mixture minus factorized size: 0.001905 with 95% interval [0.000021, 0.003802].
- Outer-test pairwise error correlations among mixture members range from 0.956 to 0.999.
- Calibrated static mixture Brier 0.565529 versus uncalibrated 0.565484; 20x ECE 0.0003 versus 0.0023.
- Dirichlet sensitivity minimum on these same folds is strength 5.0 and decay 0.97 at Brier 0.561639. That grid point was not the preregistered primary and is not a second test.
- Fold manifest SHA-256 matches the published 35-configuration screen split.
- Elastic-net fits emitted 4 convergence warnings. Its score is a completed but unconverged trial.
- The one-step exact-lag and last-observed Markov tables in this campaign are not the HE-09 multi-lag mixture.

## Leakage controls

- future_tick_inert: True
- other_episode_inert: True
- peer_cutoff_excluded: True
- signal_block_changes_when_requested: True
- signal_inert: True

## Candidates

| Candidate | Mean Brier | Log loss | 20x predicted | 20x ECE | Fit seconds | Fold SD |
|---|---:|---:|---:|---:|---:|---:|
| jaeger_frozen_params | 0.362291 | 0.722750 | 0.0139 | 0.0017 | 118.451 | 0.025389 |
| jaeger_causal_adapter | 0.364293 | 0.725189 | 0.0139 | 0.0018 | 107.896 | 0.024852 |
| factorized_size | 0.563578 | 1.086142 | 0.0133 | 0.0023 | 1.078 | 0.007343 |
| moe_regime_cells | 0.563876 | 1.083146 | 0.0137 | 0.0020 | 4.715 | 0.007019 |
| moe_static | 0.565484 | 1.087193 | 0.0133 | 0.0023 | 4.715 | 0.006374 |
| moe_static_calibrated | 0.565529 | 1.087012 | 0.0159 | 0.0003 | 4.715 | 0.006337 |
| moe_regime_softmax | 0.566091 | 1.086765 | 0.0132 | 0.0024 | 4.715 | 0.006736 |
| peer_shrink | 0.566562 | 1.087449 | 0.0132 | 0.0024 | 1.078 | 0.007568 |
| drift_switch | 0.567096 | 1.092890 | 0.0134 | 0.0022 | 1.078 | 0.005694 |
| dirichlet_long | 0.567397 | 1.091370 | 0.0132 | 0.0024 | 1.078 | 0.007891 |
| extra_trees_full | 0.569847 | 1.085322 | 0.0155 | 0.0010 | 1.892 | 0.011675 |
| frequency_default | 0.570530 | 1.095981 | 0.0132 | 0.0024 | 2.233 | 0.008111 |
| dirichlet_short | 0.572960 | 1.114926 | 0.0134 | 0.0026 | 1.078 | 0.003236 |
| markov_last_observed | 0.581670 | 1.110777 | 0.0130 | 0.0026 | 1.078 | 0.009619 |
| markov_exact_lag1 | 0.581777 | 1.110972 | 0.0129 | 0.0027 | 1.078 | 0.009572 |
| type_prior_only | 0.583800 | 1.113920 | 0.0131 | 0.0025 | 1.078 | 0.008835 |
| hist_boost_full | 0.600729 | 1.168895 | 0.0075 | 0.0113 | 6.827 | 0.021388 |
| logistic_base_plus_win_size | 0.612971 | 1.222305 | 0.0167 | 0.0131 | 0.343 | 0.018422 |
| logistic_type_exact_lags | 0.619002 | 1.247919 | 0.0169 | 0.0108 | 0.274 | 0.015109 |
| logistic_base_plus_win_size_and_changepoint | 0.621235 | 1.259563 | 0.0144 | 0.0151 | 0.314 | 0.022498 |
| logistic_base_plus_changepoint | 0.621427 | 1.271364 | 0.0152 | 0.0119 | 0.288 | 0.019865 |
| logistic_base_plus_entropy | 0.622155 | 1.255096 | 0.0188 | 0.0141 | 0.306 | 0.014791 |
| logistic_base_plus_rarity20 | 0.622493 | 1.260559 | 0.0170 | 0.0152 | 0.266 | 0.014714 |
| logistic_base_plus_sparse | 0.623026 | 1.262002 | 0.0188 | 0.0145 | 0.248 | 0.023194 |
| logistic_base_plus_discounted | 0.624665 | 1.296726 | 0.0177 | 0.0190 | 0.498 | 0.020622 |
| logistic_base_plus_win_size_and_entropy | 0.624942 | 1.252278 | 0.0197 | 0.0189 | 0.318 | 0.013946 |
| logistic_base_plus_interactions | 0.625657 | 1.272097 | 0.0178 | 0.0118 | 0.375 | 0.024703 |
| logistic_base_plus_transitions | 0.625869 | 1.283059 | 0.0208 | 0.0174 | 0.306 | 0.020572 |
| logistic_base_plus_changepoint_and_entropy | 0.628091 | 1.287847 | 0.0173 | 0.0180 | 0.276 | 0.016654 |
| logistic_base_plus_sibling | 0.631814 | 1.287481 | 0.0201 | 0.0157 | 0.332 | 0.019164 |
| elastic_net_full | 0.649338 | 1.321525 | 0.0169 | 0.0139 | 8.789 | 0.019651 |
| logistic_full | 0.671209 | 1.421976 | 0.0170 | 0.0194 | 0.723 | 0.016493 |
| logistic_full_plus_own_query_signal | 0.672867 | 1.442307 | 0.0194 | 0.0207 | 0.719 | 0.021453 |
| logistic_label_permutation | 0.735502 | 1.644630 | 0.0260 | 0.0295 | 0.712 | 0.008351 |

Lowest observed mean Brier in this run: `jaeger_frozen_params` at 0.362291.

## Paired comparisons versus the anchor

Anchor: `frequency_default`. Negative delta means the candidate has lower Brier.

| Candidate | Delta Brier | 95% CI | Episodes better | Episodes worse | Supported improvement |
|---|---:|---|---:|---:|---|
| logistic_type_exact_lags | 0.048472 | [0.028623, 0.068321] | 25 | 71 | False |
| logistic_base_plus_sparse | 0.052496 | [0.032405, 0.073097] | 24 | 72 | False |
| logistic_base_plus_discounted | 0.054135 | [0.034397, 0.074438] | 28 | 68 | False |
| logistic_base_plus_sibling | 0.061284 | [0.039374, 0.083547] | 22 | 74 | False |
| logistic_base_plus_transitions | 0.055339 | [0.033779, 0.074823] | 23 | 73 | False |
| logistic_base_plus_entropy | 0.051625 | [0.032525, 0.070201] | 24 | 72 | False |
| logistic_base_plus_changepoint | 0.050897 | [0.032395, 0.069929] | 26 | 70 | False |
| logistic_base_plus_win_size | 0.042441 | [0.021394, 0.062808] | 29 | 67 | False |
| logistic_base_plus_rarity20 | 0.051963 | [0.032081, 0.071857] | 26 | 70 | False |
| logistic_base_plus_interactions | 0.055127 | [0.034560, 0.076041] | 22 | 74 | False |
| logistic_base_plus_win_size_and_changepoint | 0.050705 | [0.031206, 0.069332] | 26 | 70 | False |
| logistic_base_plus_win_size_and_entropy | 0.054412 | [0.033355, 0.075630] | 27 | 69 | False |
| logistic_base_plus_changepoint_and_entropy | 0.057561 | [0.039218, 0.075985] | 26 | 70 | False |
| logistic_full | 0.100679 | [0.075818, 0.126097] | 20 | 76 | False |
| logistic_full_plus_own_query_signal | 0.102337 | [0.076071, 0.129145] | 21 | 75 | False |
| elastic_net_full | 0.078808 | [0.056653, 0.100917] | 20 | 76 | False |
| extra_trees_full | -0.000683 | [-0.012822, 0.010003] | 47 | 49 | False |
| hist_boost_full | 0.030199 | [0.010886, 0.050491] | 34 | 62 | False |
| logistic_label_permutation | 0.164972 | [0.138589, 0.190841] | 11 | 85 | False |
| dirichlet_long | -0.003133 | [-0.005127, -0.001162] | 56 | 40 | True |
| dirichlet_short | 0.002430 | [-0.008596, 0.013324] | 48 | 48 | False |
| markov_exact_lag1 | 0.011247 | [0.000727, 0.020752] | 34 | 62 | False |
| markov_last_observed | 0.011140 | [0.000610, 0.020599] | 35 | 61 | False |
| factorized_size | -0.006952 | [-0.013762, -0.000145] | 52 | 44 | True |
| peer_shrink | -0.003968 | [-0.006350, -0.001645] | 62 | 34 | True |
| drift_switch | -0.003434 | [-0.012868, 0.005944] | 47 | 49 | False |
| type_prior_only | 0.013270 | [0.003179, 0.022756] | 35 | 61 | False |
| moe_static | -0.005046 | [-0.010498, 0.000286] | 51 | 45 | False |
| moe_regime_softmax | -0.004439 | [-0.010132, 0.001192] | 53 | 43 | False |
| moe_regime_cells | -0.006654 | [-0.013664, 0.000077] | 50 | 46 | False |
| moe_static_calibrated | -0.005001 | [-0.010449, 0.000345] | 50 | 46 | False |
| jaeger_frozen_params | -0.208239 | [-0.228766, -0.186895] | 92 | 4 | True |
| jaeger_causal_adapter | -0.206237 | [-0.227736, -0.184312] | 91 | 5 | True |

## Feature ranking

One-factor delta is added-group Brier minus type+exact-lag logistic Brier. Negative means the group helped. Baseline groups have no one-factor delta.

| Group | One-factor delta | Mean abs logistic coef | ExtraTrees importance | Helps |
|---|---:|---:|---:|---|
| win_size | -0.006031 | 0.262033 | 0.017527 | True |
| changepoint | 0.002425 | 0.165908 | 0.012078 | False |
| entropy | 0.003153 | 0.225874 | 0.010660 | False |
| rarity20 | 0.003491 | 0.181270 | 0.005494 | False |
| sparse | 0.004024 | 0.039094 | 0.000522 | False |
| discounted | 0.005663 | 0.269505 | 0.013078 | False |
| interactions | 0.006655 | 0.180902 | 0.004142 | False |
| transitions | 0.006867 | 0.133606 | 0.007279 | False |
| sibling | 0.012812 | 0.172492 | 0.009073 | False |
| type |  | 0.276573 | 0.011150 | None |
| exact_lags |  | 0.127854 | 0.005458 | None |

## Pairwise follow-up

Interaction beyond main effects is `B(base+a+b) - B(base) - (B(base+a)-B(base)) - (B(base+b)-B(base))`. Negative means the pair beat the sum of the one-factor gains.

- win_size + changepoint: Brier 0.621235, delta 0.002233, interaction 0.005839.
- win_size + entropy: Brier 0.624942, delta 0.005940, interaction 0.008819.
- changepoint + entropy: Brier 0.628091, delta 0.009089, interaction 0.003511.

## Mixture of experts

- Members: dirichlet_long, dirichlet_short, markov_exact_lag1, factorized_size, peer_shrink.
- Static Brier 0.565484; regime softmax 0.566091; regime cells 0.563876; calibrated static 0.565529.
- Mean static weights: {'dirichlet_long': 0.21982662763724714, 'dirichlet_short': 0.21271287064659236, 'factorized_size': 0.2563978670055797, 'markov_exact_lag1': 0.08104778124528984, 'peer_shrink': 0.23001485346529088}.
- Effective static experts (1/sum w^2): 4.570677341763833.
- Own-query-signal delta versus full logistic: 0.001658.

Outer-test error correlation of the mixture members:

| | dirichlet_long | dirichlet_short | markov_exact_lag1 | factorized_size | peer_shrink |
|---|---:|---:|---:|---:|---:|
| dirichlet_long | 1.000 | 0.961 | 0.965 | 0.990 | 0.999 |
| dirichlet_short | 0.961 | 1.000 | 0.956 | 0.984 | 0.962 |
| markov_exact_lag1 | 0.965 | 0.956 | 1.000 | 0.976 | 0.967 |
| factorized_size | 0.990 | 0.984 | 0.976 | 1.000 | 0.990 |
| peer_shrink | 0.999 | 0.962 | 0.967 | 0.990 | 1.000 |

## Condition-specific sampled Brier for the best observed row

- drift: 0.320406
- shared_change: 0.316763
- short_history: 0.445301
- stable: 0.366695

Query-level strata for that same row:

- type balanced: 0.384070
- type jackpot: 0.325117
- type steady: 0.370834
- history lag1_known: 0.362291
- history lag1_missing: n/a
- history long_>=32: 0.362291
- history mid_8_31: n/a
- history short_<8: n/a

## Hyperparameter checks

- {"C": 0.1, "class_20_ece": 0.008971844542442708, "convergence_warnings": 0, "family": "logistic_full", "fit_seconds": 0.3235058999962348, "mean_brier": 0.6217049598937688}
- {"C": 1.0, "class_20_ece": 0.019391275781640398, "convergence_warnings": 0, "family": "logistic_full", "fit_seconds": 0.7215947000004235, "mean_brier": 0.6712086593804283}
- {"C": 10.0, "class_20_ece": 0.027114344427557703, "convergence_warnings": 0, "family": "logistic_full", "fit_seconds": 1.2868277999987185, "mean_brier": 0.7185189650271431}
- {"class_20_ece": 0.004680004754284628, "decay": 0.9, "family": "dirichlet", "fit_seconds": 0.06610860000000685, "mean_brier": 0.5715738613528253, "strength": 5.0}
- {"class_20_ece": 0.0030606040458235236, "decay": 0.97, "family": "dirichlet", "fit_seconds": 0.04531879999922239, "mean_brier": 0.5616391668667674, "strength": 5.0}
- {"class_20_ece": 0.0024176130663066692, "decay": 0.995, "family": "dirichlet", "fit_seconds": 0.07664769999973942, "mean_brier": 0.5673435452036786, "strength": 5.0}
- {"class_20_ece": 0.0024051549778445116, "decay": 0.9, "family": "dirichlet", "fit_seconds": 0.046972799998911796, "mean_brier": 0.5716882481364521, "strength": 20.0}
- {"class_20_ece": 0.0022991126681823505, "decay": 0.97, "family": "dirichlet", "fit_seconds": 0.06180859999949462, "mean_brier": 0.5635782867443401, "strength": 20.0}
- {"class_20_ece": 0.0024431828685057, "decay": 0.995, "family": "dirichlet", "fit_seconds": 0.050870600000052946, "mean_brier": 0.5673965233210355, "strength": 20.0}
- {"class_20_ece": 0.0024915437547853494, "decay": 0.9, "family": "dirichlet", "fit_seconds": 0.05145199999969918, "mean_brier": 0.5784346004044589, "strength": 80.0}
- {"class_20_ece": 0.0024262279429943887, "decay": 0.97, "family": "dirichlet", "fit_seconds": 0.04723100000046543, "mean_brier": 0.5718246102433696, "strength": 80.0}
- {"class_20_ece": 0.002487209831586309, "decay": 0.995, "family": "dirichlet", "fit_seconds": 0.052156500001729, "mean_brier": 0.5700763489925024, "strength": 80.0}
- {"class_20_ece": 0.002441135185247195, "family": "peer_shrink", "fit_seconds": 0.8162448000002769, "kappa": 2.0, "mean_brier": 0.5671244502554329}
- {"class_20_ece": 0.00243577366312348, "family": "peer_shrink", "fit_seconds": 0.9293628999985231, "kappa": 8.0, "mean_brier": 0.5665619688569565}
- {"class_20_ece": 0.0024220099949022276, "family": "peer_shrink", "fit_seconds": 0.9130834999996296, "kappa": 32.0, "mean_brier": 0.5664511388183073}
- {"class_20_ece": 0.00208308034359775, "family": "drift_switch", "fit_seconds": 0.8561558000001241, "mean_brier": 0.5723453743702918, "tau": 0.15}
- {"class_20_ece": 0.0022005308691554117, "family": "drift_switch", "fit_seconds": 0.9185823999978311, "mean_brier": 0.5670956363024977, "tau": 0.25}
- {"class_20_ece": 0.0023653270883039913, "family": "drift_switch", "fit_seconds": 0.9367835000011837, "mean_brier": 0.5640759207052062, "tau": 0.4}

## Negative results kept

- logistic_label_permutation: Training labels were permuted inside each fit fold. A score near the full logistic model would indicate leakage.
- moe_static_calibrated: Inner-OOF temperature and 20x logit bias did not reduce outer-fold sampled Brier versus the uncalibrated static mixture.

## Prior studies cited, not rerun

- chat_runtime_screen: 35 configurations, 13 families; jaeger mean Brier 0.361702, best non-jaeger stat_markov 0.417735, extra_trees 0.535957
- HE-09: Dirichlet, decay BMA and Markov were not promoted; Markov was the strongest of the three
- HE-15: stat_temporal_hmm sampled Brier 0.5544 and was not rerun; factorized size improved 20x calibration but stayed below the champion
- Note: frequency_default is the repository FrequencyModel with default strength 20, decay 1, peer 0.
- Note: Frozen jaegers_entry/params.json is development-exposed from earlier public-validation work. This run did not open validation labels. jaeger_causal_adapter sets short-history lambda and prior equal to the long values and drops stacker column 13; it does not remove every champion as-of caveat.

## Commands

From `Jaeger_Main/House_Edge`:

```
py -3.13 -m pytest tests/test_grok_he87_research.py -q
py -3.13 -m research.challengers.grok_he87_experiment --config research/configs/grok_he87_protocol.json --out-dir research/reports
```

Resume without the frozen champion reference:

```
py -3.13 -m research.challengers.grok_he87_experiment --config research/configs/grok_he87_protocol.json --out-dir research/reports --skip-champion
```

