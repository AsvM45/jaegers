# House Edge research methodology

The organizer asks for **probability forecasts** over gross payouts `0,1,2,5,20`; eight related machines share each episode cutoff. Only observed payouts strictly before cutoff, including siblings, can be features. Missing ticks aren't losses; don't reuse a cutoff query's signal on historical pseudo-training rows without proof it existed at that time.

## Evaluate correctly

- Training sampled labels → grouped by episode proper Brier.
- Public validation exact probability targets → official condition-normalized squared-error score (development, previously used in model selection).
- Public test → **format/ID checks only**, no true next-spin probability score.
- No agent has automatic organizer upload authority.

## Experiments

Use hashed source/config/split identities, bounded worker trials, feature groups/ablations, model-family comparisons, paired episode deltas and per-condition failure diagnostics. Preserve failed trials. Use the [research v7 synopsis](https://github.com/AsvM45/jaegers/blob/main/docs/research/EXPERIMENT_FACTORY_v7.md) as a design reference, not a false assertion that a warehouse/sweep is deployed.

## Collaboration

Every new finding should link to a GitHub Issue, PR, or Discussion (once enabled). Owners: see [board #18](https://github.com/AsvM45/jaegers/issues/18).