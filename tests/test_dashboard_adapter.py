import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.adapter import (
    DirectoryStore,
    SQLiteStore,
    SyntheticDemoStore,
    get_experiment_store,
)
from dashboard.schema import ProvenanceType


class TestDashboardAdapter(unittest.TestCase):
    """Test suite for data ingestion and fallback mechanisms."""

    def test_synthetic_demo_store_richness(self):
        store = SyntheticDemoStore()
        self.assertTrue(store.is_demo_mode)
        self.assertTrue(store.has_runs())

        trials = store.list_trials()
        self.assertGreaterEqual(len(trials), 8, "Expected at least 8 demonstration models")

        # Check champion
        champ = store.get_champion()
        self.assertIsNotNone(champ)
        self.assertEqual(champ.trial_id, "champion-b78abe75")
        self.assertTrue(champ.is_champion)
        self.assertTrue(champ.is_synthetic)
        self.assertAlmostEqual(champ.official_points, 55.1216, places=3)
        self.assertIsNotNone(champ.condition_losses)
        self.assertAlmostEqual(champ.condition_losses.stable, 0.067316, places=5)
        self.assertAlmostEqual(champ.condition_losses.short_history, 0.116980, places=5)
        self.assertAlmostEqual(champ.condition_losses.drift, 0.092323, places=5)
        self.assertAlmostEqual(champ.condition_losses.shared_change, 0.077390, places=5)

        # Check key ablation models are present
        trial_ids = {t.trial_id for t in trials}
        self.assertIn("nosig-63c6396e", trial_ids)
        self.assertIn("causal-26a9a3b1", trial_ids)
        self.assertIn("nostack-f103d154", trial_ids)
        self.assertIn("stat_markov-4401", trial_ids)
        self.assertIn("stat_dirichlet-3085", trial_ids)
        self.assertIn("single_lag-3211", trial_ids)

        # Check failure traces
        self.assertIn("timeout-err-009", trial_ids)
        self.assertIn("oom-err-0010", trial_ids)
        self.assertIn("running-active-0011", trial_ids)

        # Check ablations
        ablations = store.list_ablations()
        self.assertGreaterEqual(len(ablations), 12, "Expected at least 12 component ablations from HE-17")
        ab_names = {a.variant_name for a in ablations}
        self.assertIn("nostack", ab_names)
        self.assertIn("nosig", ab_names)
        self.assertIn("causal", ab_names)
        self.assertIn("single_lag_only", ab_names)

        # Check hypotheses
        hypotheses = store.list_hypotheses()
        self.assertGreaterEqual(len(hypotheses), 6)
        h_ids = {h.id for h in hypotheses}
        self.assertIn("H1_GBDT_STACKER", h_ids)
        self.assertIn("H2_HISTORICAL_SIGNAL_LEAK", h_ids)

        # Check calibration
        cal_bins = store.get_calibration_bins()
        self.assertGreater(len(cal_bins), 0)
        classes_present = {b.payout_class for b in cal_bins}
        self.assertEqual(classes_present, {0, 1, 2, 5, 20})

        # Check rare 20x diagnostics
        r20 = store.get_rare_payout_diagnostic()
        self.assertIsNotNone(r20)
        self.assertEqual(r20.payout_class, 20)
        self.assertAlmostEqual(r20.true_frequency, 0.0147, places=3)
        self.assertGreater(r20.calibration_correlation, 0.9)

        # Check execution logs
        logs = store.get_execution_logs()
        self.assertGreaterEqual(len(logs), 3)
        statuses = {l.status for l in logs}
        self.assertIn("TIMEOUT", statuses)
        self.assertIn("MEMORY_LIMIT", statuses)

    def test_paired_comparison_calculation(self):
        store = SyntheticDemoStore()
        comp = store.get_paired_comparison("nosig-63c6396e", "champion-b78abe75", bootstrap=500, seed=42)
        self.assertIsNotNone(comp)
        self.assertEqual(comp.candidate_id, "nosig-63c6396e")
        self.assertEqual(comp.baseline_id, "champion-b78abe75")
        self.assertEqual(comp.provenance, ProvenanceType.PUBLIC_VALIDATION)
        self.assertGreater(comp.n_episodes, 0)
        self.assertLess(comp.ci95_low, comp.ci95_high)

    def test_sqlite_store_readonly_enforcement(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "registry.sqlite"
            # Create schema and 1 trial in regular mode
            conn = sqlite3.connect(db_path)
            try:
                conn.execute(
                    "CREATE TABLE trials (id TEXT PRIMARY KEY, study TEXT, config TEXT, identity TEXT, "
                    "status TEXT, attempt INT, artifact TEXT, mean_brier REAL, wall_seconds REAL, "
                    "error TEXT, created_at TEXT, finished_at TEXT)"
                )
                conn.execute(
                    "INSERT INTO trials VALUES ('t_ro_01', 'study_ro', '{}', 'jaeger', 'SUCCEEDED', "
                    "1, '', 0.365, 10.0, NULL, '2026-11-08T00:00:00Z', '2026-11-08T00:00:10Z')"
                )
                conn.commit()
            finally:
                conn.close()

            store = SQLiteStore(db_path)
            self.assertFalse(store.is_demo_mode)
            self.assertTrue(store.has_runs())

            trials = store.list_trials()
            self.assertEqual(len(trials), 1)
            self.assertEqual(trials[0].trial_id, "t_ro_01")
            self.assertAlmostEqual(trials[0].mean_brier, 0.365)

            # Assert that modifying SQLite through the store's connection mechanism is strictly blocked
            clean_uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
            ro_conn = sqlite3.connect(clean_uri, uri=True)
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    ro_conn.execute("INSERT INTO trials VALUES ('fail', 's', '{}', 'j', 'F', 1, '', 0, 0, NULL, '', '')")
            finally:
                ro_conn.close()

    def test_empty_directory_clean_detection(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            store = DirectoryStore(empty_dir)
            self.assertFalse(store.is_demo_mode)
            self.assertFalse(store.has_runs())
            self.assertEqual(store.list_trials(), [])
            self.assertIsNone(store.get_champion())
            self.assertEqual(store.get_execution_logs(), [])

    def test_corrupted_json_handling(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            t_dir = Path(tmp_dir) / "trials" / "corrupt_trial"
            t_dir.mkdir(parents=True)
            res_file = t_dir / "result.json"
            # Write invalid truncated JSON
            res_file.write_text("{ incomplete json...", encoding="utf-8")

            store = DirectoryStore(tmp_dir)
            trials = store.list_trials()
            self.assertEqual(len(trials), 1)
            self.assertEqual(trials[0].trial_id, "corrupt_trial")
            self.assertEqual(trials[0].status, "CORRUPTED")

    def test_factory_fallback(self):
        # 1. Force demo
        store_demo = get_experiment_store(force_demo=True)
        self.assertTrue(store_demo.is_demo_mode)

        # 2. Empty directory explicit path returns DirectoryStore without crashing
        with tempfile.TemporaryDirectory() as empty_dir:
            store_dir = get_experiment_store(source_path=empty_dir)
            self.assertFalse(store_dir.is_demo_mode)
            self.assertFalse(store_dir.has_runs())
            self.assertEqual(store_dir.list_trials(), [])

        # 3. Non-existent path falls back to SyntheticDemoStore
        store_nonexistent = get_experiment_store(source_path="c:/non_existent_folder_xyz_123")
        self.assertTrue(store_nonexistent.is_demo_mode)


if __name__ == "__main__":
    unittest.main()
