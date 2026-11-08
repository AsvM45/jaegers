import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.schema import (
    AttemptRecord,
    CalibrationBin,
    ComponentAblation,
    ConditionLosses,
    ExecutionLog,
    FeatureImportanceRecord,
    HypothesisRecord,
    PairedComparison,
    ProvenanceType,
    RarePayoutDiagnostic,
    TrialDetail,
    TrialRecord,
)


class TestDashboardSchema(unittest.TestCase):
    """Test suite for domain dataclasses and type definitions."""

    def test_provenance_type_parsing(self):
        self.assertEqual(ProvenanceType.from_str("PUBLIC_VALIDATION"), ProvenanceType.PUBLIC_VALIDATION)
        self.assertEqual(ProvenanceType.from_str("dev_exposed"), ProvenanceType.PUBLIC_VALIDATION)
        self.assertEqual(ProvenanceType.from_str("TRAIN_GROUP_CV"), ProvenanceType.TRAIN_GROUP_CV)
        self.assertEqual(ProvenanceType.from_str("sampled_outcome_group_cv"), ProvenanceType.TRAIN_GROUP_CV)
        self.assertEqual(ProvenanceType.from_str("VAL_TO_TRAIN"), ProvenanceType.VAL_TO_TRAIN)
        self.assertEqual(ProvenanceType.from_str("TEST_FORMAT_CHECK"), ProvenanceType.TEST_FORMAT_CHECK)
        self.assertEqual(ProvenanceType.from_str("DEMO_SYNTHETIC"), ProvenanceType.DEMO_SYNTHETIC)
        self.assertEqual(ProvenanceType.from_str("unknown_type"), ProvenanceType.TRAIN_GROUP_CV)

    def test_condition_losses_math(self):
        losses = ConditionLosses(
            stable=0.067316,
            short_history=0.116980,
            drift=0.092323,
            shared_change=0.077390,
        )
        expected_mean = (0.067316 + 0.116980 + 0.092323 + 0.077390) / 4.0
        self.assertAlmostEqual(losses.mean_ratio, expected_mean, places=6)
        expected_points = 60.0 / (1.0 + expected_mean)
        self.assertAlmostEqual(losses.points_60, expected_points, places=5)
        self.assertAlmostEqual(losses.points_60, 55.1216, places=4)

        d = losses.as_dict()
        self.assertEqual(set(d.keys()), {"stable", "short_history", "drift", "shared_change"})

    def test_frozen_immutability(self):
        rec = TrialRecord(
            trial_id="test_001",
            study_name="audit",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.PUBLIC_VALIDATION,
        )
        with self.assertRaises(FrozenInstanceError):
            rec.status = "FAILED"  # type: ignore

    def test_trial_record_serialization_roundtrip(self):
        losses = ConditionLosses(0.1, 0.2, 0.3, 0.4)
        rec = TrialRecord(
            trial_id="t123",
            study_name="study_a",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.PUBLIC_VALIDATION,
            is_champion=True,
            wall_seconds=12.5,
            official_points=55.12,
            condition_losses=losses,
            hyperparameters={"learning_rate": 0.05},
        )
        data = rec.to_dict()
        restored = TrialRecord.from_dict(data)

        self.assertEqual(restored.trial_id, rec.trial_id)
        self.assertEqual(restored.provenance, rec.provenance)
        self.assertTrue(restored.is_champion)
        self.assertAlmostEqual(restored.wall_seconds, 12.5)
        self.assertIsNotNone(restored.condition_losses)
        self.assertAlmostEqual(restored.condition_losses.mean_ratio, 0.25)
        self.assertEqual(restored.hyperparameters["learning_rate"], 0.05)

    def test_ablation_and_hypothesis_records(self):
        ab = ComponentAblation(
            variant_name="nostack",
            removed_component="GBDT stacker",
            hypothesis="GBDT stacker provides vital non-linear interaction",
            official_points=52.8362,
            official_points_delta=-2.2854,
            ci95_points=(-2.93, -1.71),
            supported=True,
            direction="worse",
        )
        self.assertTrue(ab.supported)
        self.assertEqual(ab.direction, "worse")

        hyp = HypothesisRecord(
            id="H1",
            preregistered_timestamp="2026-11-06T12:00:00Z",
            component="stacker",
            statement="Stacker helps",
            expected_direction="worse",
            verdict="CONFIRMED",
        )
        self.assertEqual(hyp.verdict, "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
