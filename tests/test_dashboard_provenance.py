import sys
import unittest
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.provenance import (
    calculate_official_points,
    get_provenance_badge,
    get_provenance_meta,
    is_comparable,
    validate_comparison_compatibility,
)
from dashboard.schema import ConditionLosses, ProvenanceType, TrialRecord


class TestDashboardProvenance(unittest.TestCase):
    """Test suite for evaluation provenance validation."""

    def setUp(self):
        self.champ = TrialRecord(
            trial_id="champ_001",
            study_name="val",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.PUBLIC_VALIDATION,
            is_champion=True,
            official_points=55.1216,
            per_episode_errors={"ep1": 0.05, "ep2": 0.08},
            episode_conditions={"ep1": "stable", "ep2": "drift"},
        )
        self.nosig = TrialRecord(
            trial_id="nosig_002",
            study_name="val",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.PUBLIC_VALIDATION,
            official_points=55.0001,
            per_episode_errors={"ep1": 0.052, "ep2": 0.081},
            episode_conditions={"ep1": "stable", "ep2": "drift"},
        )
        self.cv_run = TrialRecord(
            trial_id="cv_003",
            study_name="cv",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.TRAIN_GROUP_CV,
            mean_brier=0.354,
            per_episode_errors={"ep1": 0.35, "ep2": 0.36},
            episode_conditions={"ep1": "stable", "ep2": "drift"},
        )
        self.test_run = TrialRecord(
            trial_id="test_004",
            study_name="test",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.TEST_FORMAT_CHECK,
        )

    def test_official_points_formula(self):
        losses = ConditionLosses(
            stable=0.067316,
            short_history=0.116980,
            drift=0.092323,
            shared_change=0.077390,
        )
        pts = calculate_official_points(losses, max_points=60.0)
        self.assertAlmostEqual(pts, 55.121615, places=5)

    def test_badges_and_metadata(self):
        self.assertEqual(get_provenance_badge(ProvenanceType.PUBLIC_VALIDATION), "[DEV-EXPOSED]")
        self.assertEqual(get_provenance_badge(ProvenanceType.TRAIN_GROUP_CV), "[TRAIN-GROUP-CV]")
        self.assertEqual(get_provenance_badge(ProvenanceType.DEMO_SYNTHETIC), "[DEMO-SYNTHETIC]")

        meta = get_provenance_meta(ProvenanceType.PUBLIC_VALIDATION)
        self.assertTrue(meta["scored"])
        self.assertIn("60", meta["formula"])

        cv_meta = get_provenance_meta(ProvenanceType.TRAIN_GROUP_CV)
        self.assertFalse(cv_meta["scored"])

    def test_same_provenance_comparison_allowed(self):
        valid, reason = validate_comparison_compatibility(self.nosig, self.champ)
        self.assertTrue(valid)
        self.assertIsNone(reason)
        self.assertTrue(is_comparable(self.nosig, self.champ))

    def test_cross_provenance_comparison_blocked(self):
        valid, reason = validate_comparison_compatibility(self.cv_run, self.champ)
        self.assertFalse(valid)
        self.assertIsNotNone(reason)
        self.assertIn("Incompatible evaluation provenance", reason)
        self.assertFalse(is_comparable(self.cv_run, self.champ))

    def test_self_comparison_blocked(self):
        valid, reason = validate_comparison_compatibility(self.champ, self.champ)
        self.assertFalse(valid)
        self.assertIn("Cannot compare a trial to itself", reason)

    def test_test_format_check_comparison_blocked(self):
        valid, reason = validate_comparison_compatibility(self.test_run, self.champ)
        self.assertFalse(valid)
        self.assertIn("Incompatible evaluation provenance", reason)

        test_run_2 = TrialRecord(
            trial_id="test_005",
            study_name="test",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.TEST_FORMAT_CHECK,
        )
        valid2, reason2 = validate_comparison_compatibility(test_run_2, self.test_run)
        self.assertFalse(valid2)
        self.assertIn("TEST_FORMAT_CHECK runs have no ground truth", reason2)

    def test_disjoint_episodes_blocked(self):
        disjoint_candidate = TrialRecord(
            trial_id="disjoint_001",
            study_name="val",
            family="jaeger",
            status="SUCCEEDED",
            provenance=ProvenanceType.PUBLIC_VALIDATION,
            per_episode_errors={"ep99": 0.05, "ep100": 0.08},
            episode_conditions={"ep99": "stable", "ep100": "drift"},
        )
        valid, reason = validate_comparison_compatibility(disjoint_candidate, self.champ)
        self.assertFalse(valid)
        self.assertIn("disjoint held-out episodes", reason)


if __name__ == "__main__":
    unittest.main()
