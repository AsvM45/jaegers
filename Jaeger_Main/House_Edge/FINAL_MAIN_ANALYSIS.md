# House Edge: canonical main and final analysis

Prepared 2026-11-08 for the owner's imminent submission. Analysed implementation:
`20642efa9c1c4d46936bb095d42968e1c4dc5527`. This report adds documentation only;
the submission model, frozen artifacts and other challenges are unchanged.

## Integration decision

`main` contains the reviewed House Edge work. Normal serial merge order was
**#83 governance -> #79 full regression CI -> #93 measured research -> #91 finite
planner -> #92 registry/evaluation/dashboard**. Source heads and merge commits are
recorded in [the final integration record](https://github.com/AsvM45/jaegers/issues/89#issuecomment-6724690493).

The final #92 source is `c848cae915638cdeabe44c2a3c68b0bf453a75d7`.
Independent review found and then verified the repair of a successful-result
corruption gap. Its 60 focused tests and three separate corruption/coverage probes
passed before the protected-main merge. A pending required ownership check blocked
the first merge attempt; the normal merge succeeded only after that check passed.

Two PRs remain outside main:

| PR | Exact source | Reason |
|---|---|---|
| #90 | `c03c3994ff6f95317cb7cd60d280ac37d0753ff1` | BLOCKED_REVIEW: conflicting purported live-run metrics, sampled-outcome loss mislabeled official validation, new ridge candidate labeled champion, missing-value/provenance fabrication, and ranking across unmatched contexts. Passing offline tests does not establish truthful live evidence. |
| #81 | `b8c955ded79b153cda237fb666b8497c2a7088c1` | Empty draft: zero changed files, additions and deletions; no QA implementation to integrate. |

All 51 remote branches were classified: 45 already represented by ancestry or
exact merged-PR head, two open-PR branches, one superseded adaptation branch, two
mixed/Hitachi branches outside scope, and main. Branches were preserved. Historical
branch existence is not evidence of an unintegrated model. Hitachi was not edited,
checked out or merged during this work.

## Exact local submission pair: fresh read-only witness

These files exist in the original populated local checkout, under
`Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/`. They are ignored local
artifacts; a GitHub clone does not contain them.

| File | Bytes | SHA-256 |
|---|---:|---|
| `submission.csv` | 195579 | `b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf` |
| `code.zip` | 8263 | `9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f` |

The fresh official test-format checker passed: **1536 unique queries**, main/test,
season `5fffdc4d0c700bbf61c3f911`. Independent CSV inspection found maximum simplex
error `2.220446049250313e-16`, minimum probability `0.000055705798918439647`, and
maximum probability `0.9700000000000002`. Mean predicted 20x probability was
`0.012360011999415783`; this is a prediction aggregate, not observed test frequency
or evidence of calibration.

ZIP CRC validation passed. Its six root entries are `README.md`, `jaeger_model.py`,
`params.json`, `predict.py`, `reproduce.json`, and `requirements.txt`. **The frozen
ZIP's model, parameters and predictor match the corresponding main entry files
byte for byte.** The ZIP pins NumPy 2.5.4, scikit-learn 1.9.1, SciPy 1.18.1,
joblib 1.6.0, threadpoolctl 3.8.0, cloudpickle 3.1.2, and narwhals 2.28.0.
Its reproduction command pins the documented Linux CPU-dispatch/OpenBLAS policy
and two threads. Do not substitute a different runtime policy or mix artifact pairs.

The existing release record reports two exact cold Linux reproductions on one
physical host and **55.0908150083/60 development-exposed public validation** for
this CPU-pinned pair. Those cold runs and public score were not rerun for this
fresh hash/format witness. Earlier Windows/default-Linux packages failed parity;
the source's approximately 55.12 score is a different runtime observation.
No hidden score, universal hardware portability, strict-as-of certification,
organizer acceptance or upload is established by this witness. Frozen files were
not regenerated, replaced or uploaded.

## Scientific results: what the evidence supports

All Brier values below are **train-only sampled-label episode-grouped CV**, with
96 episodes, 768 query labels, four matched folds, and seed 0. They are not official
true-probability validation points. Fold manifest:
`84f2aa3282c5dc8f394bdd06179f0adac2ec3865804dda99285d1b5c7e4ccc0e`.
The 34-candidate campaign opened no validation files and made zero public-validation
peeks. Its exact source, data, protocol and fold hashes, all 34 candidate scores and
every per-episode loss matched an independent 273.2914-second reproduction.

| Configuration | Mean sampled Brier | Interpretation |
|---|---:|---|
| Frozen champion reference | 0.3622911451 | Numerically strongest reference; historical signal/feature-prior and older validation-exposure caveats remain. |
| Partial causal adapter | 0.364293 | Removes selected skew mechanisms, not every champion caveat; not a certified strict-as-of fallback. |
| Default frequency | 0.5705298414 | Existing simple baseline, strength 20 / decay 1 / peer 0. |
| Frequency, strength 10 / decay .97 / peer .1 | 0.5662851961 | Acceptance-study improvement interval includes zero. |
| Preregistered factorized-size/count configuration | 0.5635782867 | Better than frequency in this paired development study; equals normalized Dirichlet at identical strength/decay, so no independent factorization novelty is established. |
| Static expert mixture | 0.5654836125 | Worse than its strongest component. |
| Calibrated static mixture | 0.5655287253 | Calibration did not improve overall outer-fold Brier. |
| Query logistic: base / +lags / +peers | 0.571754 / 0.603083 / 0.608400 | Added lag/peer blocks harmed this acceptance configuration; negative results retained. |

Frequency decay/peer minus default: **-0.00424465**, paired 95% interval
**[-0.01328735, 0.00430544]**, includes zero. Factorized/count minus frequency:
**-0.00695155**, interval **[-0.01376197, -0.00014547]**. Static mixture minus its
strongest factorized/count member: **+0.001905**, interval **[0.000021, 0.003802]**.
These exploratory intervals are not adjusted for multiple comparisons; a
same-fold sensitivity winner is not a fresh confirmatory test. The lower grid
score 0.561639 at strength 5 / decay .97 was not the preregistered primary.

Mixture-member outer-fold error correlations were approximately **0.956-0.999**;
highly correlated errors explain the limited diversification benefit. The
calibrated mixture's reported 20x ECE improved while total Brier slightly worsened:
a rare-class diagnostic alone does not justify promotion.

Only **12 observed 20x labels** occur among the 768 held-out queries. All queries
had exact lag 1 and peer observations; the short-count regime bit never fired
under its fewer-than-eight-observations definition. Thus this campaign cannot
establish gains from that sparse regime. Mean observed history was 182.21875 ticks.
Win/positive-size features helped the one-factor logistic screen; changepoint,
entropy, rarity, sparse, discounted, interactions, transitions and sibling additions
did not. These are configuration-specific findings, not universal feature bans.

**No challenger promotion follows from these results.** The champion's numerical
advantage does not resolve historical-feature compliance questions, and the new
causal adapter is explicitly incomplete. Preserve the frozen fallback and the
separate source/metric/exposure labels.

## Engineering verification and final dashboard

At the analysed main SHA, **312 House Edge tests + five subtests passed in 133.47s**
and **167 root tests passed in 32.98s**. Nine research warnings were retained:
one deliberate negative-control log1p warning and eight tiny-fixture logistic
convergence warnings. [Final implementation CI](https://github.com/AsvM45/jaegers/actions/runs/42504719867)
passed 312 + five research subtests and 92 dashboard tests; smoke/docs workflows
were green. Root tests used an isolated CWD because an existing private canonical
registry changes two legacy demo-fallback assumptions in the populated checkout.

The main Streamlit AppTest rendered **six tabs, six genuine full-evidence registry
trials and 34 separately labeled source-checked aggregate candidates**, with zero
exceptions/errors. Ten full-evidence charts and two aggregate charts cover cost,
trajectory, conditions, features/parameters, paired uncertainty and calibration.
The audit verifies result contents and existing artifact seals; missing historical
seals are explicit unavailable coverage. All six original acceptance attempts
were seal-VERIFIED with no findings. The original six-trial run took 102.8471s;
resume took .9465s and preserved all 324 attempt artifact files.

New local offline report:
`research_runs/he89_integrated_report/index.html`; report content seal:
`093238ed5589f259c4f6c446f78e74d7dd052e5b8d1ee0c16bab2a5ed7f31cee`.
It includes CSV/JSON/Markdown exports. Whole-trial wall cost is not inference
latency; raw-feature drift cannot be established from prediction-only exports.

Use a fresh checkout with repository-standard LF bytes for source verification.
The older populated checkout has CRLF train CSV bytes; the source reader correctly
rejects their hashes against an LF-run report. The fresh checkout of the same main
SHA passed. Original data were preserved and provenance checks were not weakened.

## Reproduce and next priorities

From the populated repository root, verify the frozen pair without rebuilding:

```powershell
Get-FileHash Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/submission.csv -Algorithm SHA256
Get-FileHash Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/code.zip -Algorithm SHA256
python Jaeger_Main/House_Edge/check_submission.py Jaeger_Main/House_Edge/research_runs/REVIEW_MAIN_9PM/submission.csv --data Jaeger_Main/House_Edge/public --split test
```

For the bounded study/report/dashboard use the pinned Python 3.13 setup and exact
commands in [the integration matrix](../../docs/ops/HE88_INTEGRATION_MATRIX.md).
The study prepares only unless `--execute` is supplied; choose a fresh output
directory after source changes. The dashboard starts from repository root:

```powershell
python -m streamlit run dashboard/he88_app.py --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
```

Immediate engineering priorities are the AGY owner's #90 provenance corrections,
the real #80 regression implementation, and #88 measured inference latency and
raw-feature drift. Submission selection/receipt remains the human owner's action.
No changes to Hitachi, no paid cloud computation, no branch retirement and no
organizer uploads were performed for this analysis.
