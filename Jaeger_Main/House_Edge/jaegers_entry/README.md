# JAEGERS House Edge ? main-round entry

Python 3.13. Exact tested runtime dependencies are in `requirements.txt`.
The verified reference environment is CPython 3.13.18 Linux; see the repository's
`docs/CURRENT_STATE.md` for current measured evidence and artifact locations.

## Reproduce

From this entry directory, after provisioning dependencies:

```sh
python predict.py --data /data --out /output/submission.csv
```

The command reads `/data/train` to fit an expert prior and a gradient-boosted win
stacker, then reads `/data/test` to forecast every query. It deterministically refits;
there is no saved checkpoint. Settings are in `params.json`. Stacker random_state=0,
early_stopping=False. Prediction never downloads packages or calls external APIs.

Organizers provision dependencies before inference. The entry and data are read-only;
only `/tmp` and `/output` are writable. Budget: two CPUs, 16 GiB RAM, 30 minutes.
A reference cold Linux run completed in about 42 seconds with about 251 MiB peak
child RSS. Measurements apply to that recorded machine/runtime, not every host.

Generate reference forecasts in Linux. Windows and Linux builds produced materially
different predictions despite matching package versions; do not upload a Windows CSV
with an unverified Linux reproducer. Compare actual normalized probabilities <=1e-8.

From the House Edge kit directory, score public validation with:

```sh
python jaegers_entry/predict.py --data public --split validation --out validation.csv
python check_submission.py validation.csv --data public --split validation
```

Test checking verifies schema and IDs only. Build the source ZIP with the supplied
`build_entry.py`; keep generated CSVs and ZIPs separate and preserve their hashes.

## Model and provenance

The existing model combines 73 lag-context experts, recency-discounted win counts,
sibling expert evidence, short-history smoothing, conditional payout-size regimes,
size-context experts, and a HistGradientBoostingClassifier stacker.

Size regimes and parameter selection used released public validation targets, so
public scores are development-exposed. Historical stacker rows also reuse final
query-time signal, whose earlier availability is unresolved. These facts are recorded
for independent audit; code reproduction does not establish organizer eligibility or
receipt. The original model and parameters remain unchanged and separately frozen.
