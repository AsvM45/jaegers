# HE-03 audit: `SIZE_REGIMES` validation-target exposure

Issue: AsvM45/jaegers#3. Champion source unchanged (`jaeger_model.py` sha256 `10da55e6…2fa0c3`).

## Provenance

`jaeger_model.py:35-41` hard-codes two size-given-win distributions over (1x, 2x, 5x, 20x) per
machine type, with the comment "read off the public validation targets". They feed every size
prediction (`:115-116`, `:124`, `:276-277`) and the size experts. The params in `params.json` were
also tuned against public validation. **Every public-validation score of this model (55.12/60) is
therefore a development / selection score, not independent evidence.** The kit's `RULES.md`
says public validation "is available for model selection", so this is a reporting issue, not a
demonstrated rule violation.

## Can the constants be recovered without validation targets?

The working `jaegers_entry/README.md` claims they are "recovered from train win frequencies alone
(fit error under 1%)". I could not reproduce that with a simple method:

- Method: per type, cut each train machine's pre-cutoff history into 32-tick windows (>= 3 wins),
  fit a two-component multinomial mixture by EM (20 restarts, best likelihood).
- Max absolute error vs the constants: steady 0.117, balanced 0.109, jackpot 0.067.
- Plugging those train-estimated shapes into the unchanged champion pipeline (fit on train)
  scores **54.49** on validation vs 55.12 (-0.63; stable .0826, short_history .1230, drift .1113,
  shared_change .0875).

Windows that straddle a regime switch blur the two components, so a better estimator (per-tick
latent regime, i.e. an HMM over size outcomes) may close most of the gap. Until someone shows that
with code, treat the "under 1%" claim as unverified and remove it from the README (#4 owner).

## Recommendation

- Keep the constants for the main release (allowed model-selection use), but label the 55.12 as
  a development score everywhere (README, #18 status, any Devpost text).
- Record `validation_target_exposure=true` for the champion in the trial registry (#8).
- For an exposure-free estimate (useful for the adaptation round, where the regimes may change):
  build a train-only HMM regime estimator as a challenger and report its validation score next to
  54.49 and 55.12.
