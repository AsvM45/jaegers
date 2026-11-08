---
name: jaegers-leakage-audit
description: Use when investigating signal-at-cutoff availability, train-validation contamination, historical pseudo-examples, or new temporal/cross-machine features.
---

# jaegers-leakage-audit

1. Make a lineage table for every candidate feature: input file, source split, timestamp visibility, transformation and dependence on true targets/conditions.
2. For historical example target tick t, require source payouts strictly <t for all machines; current organizer query `signal` is not historically available unless separate source proves it. Evaluate model without copied signal; don't simply zero it at inference without retraining.
3. Test remove-tick and injected-future mutations: prediction/features at t must remain unchanged. Missing tick must stay missing, not become payout 0 or previous observed row.
4. Split outer folds by whole `episode_id`; apply identical local adaptation to held-out episode's past without accessing query label. Keep forward-chaining as auxiliary diagnostic, not a substitute for episode grouping.
5. Label exposed public validation target constants as development evidence. Report code lines, actual executed fixtures and remaining uncertainty; do not assert rules violation from allowed public validation use without organizer evidence.
