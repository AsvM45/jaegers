# JAEGERS — House Edge (main round)

- Team: JAEGERS
- Round: main
- Season ID: 5fffdc4d0c700bbf61c3f911
- Environment: `python` image (Python 3.13) + `numpy==2.5.3` (requirements.txt)

## Recreate the forecast

Run from the folder containing `predict.py`:

```sh
python predict.py --data /data --out /output/submission.csv
```

- Reads `/data/test/queries.csv` and `/data/test/history.csv`; writes the CSV to `--out`.
- Required files: `jaeger_model.py`, `params.json` (settings chosen on public validation).
- No training step and no randomness: fully deterministic. Runtime ~5 s on 1 CPU.
- Validation check: `python predict.py --data public --split validation --out val.csv`
  then `python check_submission.py val.csv --split validation` (≈51.1 / 60).

## Method (short)

P(payout) = P(win) × P(size | win). P(win) comes from an online mixture of
"lag-context experts" (single lags and lag pairs 1–8, binary or 0/1/2+ categories):
each keeps exponentially forgotten win counts per context on the machine's own
history; experts are weighted by forgotten log-likelihood on that machine plus its
episode siblings. P(size | win) mixes the two size regimes per machine type using a
forgotten likelihood ratio from the machine's recent wins. Only ticks strictly
before each cutoff are used; missing ticks are treated as unknown.
