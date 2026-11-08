"""Adversarial stress-testing suite for JAEGERS Experiment Analytics Dashboard.

Empirically tests:
1. Empty directory handling (non-existent, empty, factory fallbacks).
2. Corrupted data handling (truncated JSON, binary garbage, malformed schemas).
3. SQLite read-only enforcement, concurrency, and file handle leak detection.
4. Paired bootstrap edge cases (N=1, zero-variance, constant delta, discordant sets).
5. Rare payout tail metrics with zero occurrences of 20x jackpot.
"""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

import numpy as np

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dashboard.adapter import (
    DirectoryStore,
    SQLiteStore,
    SyntheticDemoStore,
    _sqlite_connect_ro,
    get_experiment_store,
)
from dashboard.schema import ProvenanceType
from dashboard.stats import (
    analyze_rare_payout_tail,
    calculate_calibration_curve,
    paired_episode_bootstrap,
)


class TestEmptyDirectoryAdversarial(unittest.TestCase):
    """Adversarial challenge: Empty and non-existent directory edge cases."""

    def test_non_existent_directory_handling(self) -> None:
        """Verify DirectoryStore on non-existent path handles all methods without crashing."""
        non_existent = Path(tempfile.gettempdir()) / "jaegers_adversarial_non_existent_987654"
        if non_existent.exists():
            non_existent.rmdir()

        store = DirectoryStore(non_existent)
        self.assertFalse(store.is_demo_mode)
        self.assertFalse(store.has_runs())
        self.assertEqual(store.list_trials(), [])
        self.assertEqual(store.list_trials(study="any_study"), [])
        self.assertEqual(store.list_trials(provenance=ProvenanceType.PUBLIC_VALIDATION), [])
        self.assertIsNone(store.get_trial("non_existent_id"))
        self.assertIsNone(store.get_champion())
        self.assertEqual(store.list_hypotheses(), [])
        self.assertEqual(store.list_ablations(), [])
        self.assertEqual(store.get_calibration_bins(), [])
        self.assertIsNone(store.get_rare_payout_diagnostic())
        self.assertEqual(store.get_execution_logs(), [])

    def test_empty_directory_handling(self) -> None:
        """Verify DirectoryStore on clean empty directory returns honest zero states."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = DirectoryStore(tmp_dir)
            self.assertFalse(store.is_demo_mode)
            self.assertFalse(store.has_runs())
            self.assertEqual(store.list_trials(), [])
            self.assertIsNone(store.get_champion())
            self.assertEqual(store.get_execution_logs(), [])
            self.assertEqual(store.list_hypotheses(), [])
            self.assertEqual(store.list_ablations(), [])
            self.assertEqual(store.get_calibration_bins(), [])
            self.assertIsNone(store.get_rare_payout_diagnostic())

    def test_factory_fallback_matrix(self) -> None:
        """Verify factory get_experiment_store routes empty and non-existent inputs correctly."""
        with tempfile.TemporaryDirectory() as empty_dir:
            # Explicit empty directory -> DirectoryStore with has_runs() == False
            store_dir = get_experiment_store(source_path=empty_dir)
            self.assertIsInstance(store_dir, DirectoryStore)
            self.assertFalse(store_dir.is_demo_mode)
            self.assertFalse(store_dir.has_runs())
            self.assertEqual(store_dir.list_trials(), [])

        # Non-existent path -> falls back to SyntheticDemoStore
        non_existent = Path(tempfile.gettempdir()) / "jaegers_ne_factory_45678"
        store_fallback = get_experiment_store(source_path=non_existent)
        self.assertIsInstance(store_fallback, SyntheticDemoStore)
        self.assertTrue(store_fallback.is_demo_mode)
        self.assertTrue(store_fallback.has_runs())


class TestCorruptedDataAdversarial(unittest.TestCase):
    """Adversarial challenge: Corrupted JSON, truncated streams, and malformed files."""

    def test_corrupted_result_json_syntax(self) -> None:
        """Verify malformed result.json is captured as CORRUPTED status without crash."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            trial_dir = Path(tmp_dir) / "trials" / "malformed_trial_01"
            trial_dir.mkdir(parents=True)
            res_file = trial_dir / "result.json"

            # 1. Truncated JSON
            res_file.write_text('{"mean_brier": 0.35, "by_condition": {', encoding="utf-8")
            store = DirectoryStore(tmp_dir)
            trials = store.list_trials()
            self.assertEqual(len(trials), 1)
            self.assertEqual(trials[0].trial_id, "malformed_trial_01")
            self.assertEqual(trials[0].status, "CORRUPTED")
            self.assertIn("Corrupted or partially written", trials[0].error_message or "")

            # Verify execution log captures this corrupted trial
            logs = store.get_execution_logs()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].trial_id, "malformed_trial_01")
            self.assertEqual(logs[0].status, "CORRUPTED")

    def test_corrupted_binary_garbage_vulnerability(self) -> None:
        """Adversarial vulnerability probe: non-UTF8 binary garbage raises UnicodeDecodeError.
        
        This tests an adversarial edge case: when result.json contains raw non-UTF8 binary garbage,
        the adapter's `except (json.JSONDecodeError, OSError):` fails to catch `UnicodeDecodeError`
        (a subclass of ValueError, not JSONDecodeError or OSError), causing an unhandled crash.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            trial_dir = Path(tmp_dir) / "trials" / "binary_garbage_02"
            trial_dir.mkdir(parents=True)
            res_file = trial_dir / "result.json"

            res_file.write_bytes(b"\x00\xff\xfe\x01\x02\x03\x80\x90\xaa")
            store = DirectoryStore(tmp_dir)
            with self.assertRaises(UnicodeDecodeError):
                store.list_trials()

    def test_corrupted_registry_json(self) -> None:
        """Verify broken top-level registry.json does not abort scanning."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            reg_file = Path(tmp_dir) / "registry.json"
            reg_file.write_text("NOT_JSON_AT_ALL_<<<>>>", encoding="utf-8")

            # Also add a valid trial subfolder to test resilience
            valid_dir = Path(tmp_dir) / "trials" / "valid_trial_01"
            valid_dir.mkdir(parents=True)
            valid_res = valid_dir / "result.json"
            valid_res.write_text(
                json.dumps({
                    "mean_brier": 0.32,
                    "by_condition": {
                        "stable": 0.08,
                        "short_history": 0.12,
                        "drift": 0.10,
                        "shared_change": 0.09,
                    },
                    "evaluation_source": "public_validation",
                }),
                encoding="utf-8",
            )

            store = DirectoryStore(tmp_dir)
            trials = store.list_trials()
            # The valid trial is still loaded despite broken registry.json
            self.assertEqual(len(trials), 1)
            self.assertEqual(trials[0].trial_id, "valid_trial_01")
            self.assertEqual(trials[0].status, "SUCCEEDED")

    def test_sqlite_artifact_corrupted_json(self) -> None:
        """Verify SQLiteStore gracefully handles a corrupted artifact result.json."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "registry.sqlite"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE trials (id TEXT PRIMARY KEY, study TEXT, config TEXT, identity TEXT, "
                "status TEXT, attempt INT, artifact TEXT, mean_brier REAL, wall_seconds REAL, "
                "error TEXT, created_at TEXT, finished_at TEXT)"
            )
            conn.execute(
                "INSERT INTO trials VALUES ('sq_trial_01', 'study', '{}', 'jaeger', 'SUCCEEDED', "
                "1, 'artifact_01', 0.28, 5.0, NULL, '2026-11-08', '2026-11-08')"
            )
            conn.commit()
            conn.close()

            art_dir = Path(tmp_dir) / "artifact_01"
            art_dir.mkdir()
            (art_dir / "result.json").write_text("{broken json...", encoding="utf-8")

            store = SQLiteStore(db_path)
            self.assertTrue(store.has_runs())
            trials = store.list_trials()
            self.assertEqual(len(trials), 1)
            self.assertEqual(trials[0].trial_id, "sq_trial_01")
            self.assertAlmostEqual(trials[0].mean_brier, 0.28)
            # Artifact details could not be parsed, condition_losses is None
            self.assertIsNone(trials[0].condition_losses)


class TestSQLiteConcurrencyAndFileHandles(unittest.TestCase):
    """Adversarial challenge: SQLite read-only mode, concurrency, and handle leaks."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "concurrent.sqlite"

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "CREATE TABLE trials (id TEXT PRIMARY KEY, study TEXT, config TEXT, identity TEXT, "
            "status TEXT, attempt INT, artifact TEXT, mean_brier REAL, wall_seconds REAL, "
            "error TEXT, created_at TEXT, finished_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE attempts (trial_id TEXT, attempt INT, artifact TEXT, status TEXT, error TEXT)"
        )
        for i in range(10):
            conn.execute(
                f"INSERT INTO trials VALUES ('t_{i:02d}', 'study_c', '{{}}', 'jaeger', 'SUCCEEDED', "
                f"1, '', {0.30 + i * 0.01}, 10.0, NULL, '2026-11-08', '2026-11-08')"
            )
            conn.execute(
                f"INSERT INTO attempts VALUES ('t_{i:02d}', 1, '', 'SUCCEEDED', NULL)"
            )
        conn.commit()
        conn.close()

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_sqlite_strict_readonly_enforcement(self) -> None:
        """Verify that attempting to mutate the database through read-only connection fails."""
        with _sqlite_connect_ro(self.db_path) as db:
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM trials")
            self.assertEqual(cur.fetchone()[0], 10)

            # Mutating operations must raise sqlite3.OperationalError
            with self.assertRaises(sqlite3.OperationalError):
                cur.execute("INSERT INTO trials VALUES ('fail', 's', '{}', 'j', 'F', 1, '', 0, 0, NULL, '', '')")

            with self.assertRaises(sqlite3.OperationalError):
                cur.execute("UPDATE trials SET status = 'MUTATED'")

            with self.assertRaises(sqlite3.OperationalError):
                cur.execute("DROP TABLE trials")

    def test_sqlite_concurrency_and_no_handle_leaks(self) -> None:
        """Run 40 concurrent reader threads and verify that the file handle is never locked/leaked."""
        store = SQLiteStore(self.db_path)

        def worker_query(thread_id: int) -> int:
            runs_ok = store.has_runs()
            trials = store.list_trials()
            t_detail = store.get_trial(f"t_{thread_id % 10:02d}")
            logs = store.get_execution_logs()
            return len(trials) if (runs_ok and t_detail is not None) else -1

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_query, i) for i in range(40)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), 40)
        for count in results:
            self.assertEqual(count, 10)

        # On Windows, open SQLite handles cause PermissionError upon unlink / rename.
        # We test that creating a separate SQLiteStore and querying it closes properly.
        test_db = Path(self.tmp_dir.name) / "leak_test.sqlite"
        shutil_conn = sqlite3.connect(test_db)
        shutil_conn.execute("CREATE TABLE trials (id TEXT PRIMARY KEY, study TEXT, config TEXT, identity TEXT, status TEXT, attempt INT, artifact TEXT, mean_brier REAL, wall_seconds REAL, error TEXT, created_at TEXT, finished_at TEXT)")
        shutil_conn.commit()
        shutil_conn.close()

        store2 = SQLiteStore(test_db)
        _ = store2.has_runs()
        _ = store2.list_trials()

        # Unlink the file. If _sqlite_connect_ro leaked any handle, Windows raises PermissionError!
        try:
            test_db.unlink()
            deleted_cleanly = True
        except PermissionError:
            deleted_cleanly = False
        self.assertTrue(deleted_cleanly, "File handle was leaked by SQLiteStore on Windows!")


class TestPairedBootstrapAdversarial(unittest.TestCase):
    """Adversarial challenge: N=1, zero-variance, constant deltas, discordant sets."""

    def test_single_episode_n_equals_1(self) -> None:
        """Verify N=1 handles candidate better, worse, and equal without division-by-zero."""
        # Case A: candidate better
        res_better = paired_episode_bootstrap(
            candidate_errors={"ep_single": 0.20},
            baseline_errors={"ep_single": 0.35},
            episode_conditions={"ep_single": "drift"},
            n_resamples=500,
            seed=42,
        )
        self.assertEqual(res_better.n_episodes, 1)
        self.assertAlmostEqual(res_better.mean_delta, -0.15)
        self.assertAlmostEqual(res_better.ci95_low, -0.15)
        self.assertAlmostEqual(res_better.ci95_high, -0.15)
        self.assertEqual(res_better.p_improvement, 1.0)
        self.assertFalse(res_better.supported_improvement)  # Cannot claim supported improvement with N=1

        # Case B: candidate worse
        res_worse = paired_episode_bootstrap(
            candidate_errors={"ep_single": 0.40},
            baseline_errors={"ep_single": 0.35},
            episode_conditions={"ep_single": "drift"},
            n_resamples=500,
            seed=42,
        )
        self.assertAlmostEqual(res_worse.mean_delta, 0.05)
        self.assertEqual(res_worse.p_improvement, 0.0)
        self.assertFalse(res_worse.supported_improvement)

        # Case C: candidate equal
        res_equal = paired_episode_bootstrap(
            candidate_errors={"ep_single": 0.35},
            baseline_errors={"ep_single": 0.35},
            episode_conditions={"ep_single": "drift"},
            n_resamples=500,
            seed=42,
        )
        self.assertAlmostEqual(res_equal.mean_delta, 0.0)
        self.assertEqual(res_equal.p_improvement, 0.0)
        self.assertFalse(res_equal.supported_improvement)

    def test_zero_variance_identical_errors(self) -> None:
        """Verify dataset where candidate and baseline errors are identical across all episodes."""
        n_eps = 40
        candidate = {f"ep_{i}": 0.35 for i in range(n_eps)}
        baseline = {f"ep_{i}": 0.35 for i in range(n_eps)}
        conditions = {f"ep_{i}": "stable" for i in range(n_eps)}

        res = paired_episode_bootstrap(
            candidate_errors=candidate,
            baseline_errors=baseline,
            episode_conditions=conditions,
            n_resamples=1000,
            seed=0,
        )
        self.assertEqual(res.n_episodes, 40)
        self.assertAlmostEqual(res.mean_delta, 0.0)
        self.assertAlmostEqual(res.ci95_low, 0.0)
        self.assertAlmostEqual(res.ci95_high, 0.0)
        self.assertEqual(res.p_improvement, 0.0)
        self.assertFalse(res.supported_improvement)
        self.assertFalse(np.isnan(res.mean_delta))
        self.assertFalse(np.isnan(res.ci95_low))

    def test_constant_non_zero_delta(self) -> None:
        """Verify constant improvement across all episodes produces zero CI spread."""
        n_eps = 50
        candidate = {f"ep_{i}": 0.30 for i in range(n_eps)}
        baseline = {f"ep_{i}": 0.35 for i in range(n_eps)}
        conditions = {f"ep_{i}": "short_history" if i % 2 == 0 else "drift" for i in range(n_eps)}

        res = paired_episode_bootstrap(
            candidate_errors=candidate,
            baseline_errors=baseline,
            episode_conditions=conditions,
            n_resamples=1000,
            seed=1,
        )
        self.assertAlmostEqual(res.mean_delta, -0.05)
        self.assertAlmostEqual(res.ci95_low, -0.05)
        self.assertAlmostEqual(res.ci95_high, -0.05)
        self.assertEqual(res.p_improvement, 1.0)
        self.assertTrue(res.supported_improvement)

    def test_discordant_and_disjoint_episode_sets(self) -> None:
        """Verify behavior with partial overlap and disjoint sets."""
        cand = {f"ep_{i}": 0.30 for i in range(10)}  # 0..9
        base = {f"ep_{i}": 0.35 for i in range(5, 15)}  # 5..14
        conds = {f"ep_{i}": "stable" for i in range(15)}

        # Relaxed mode: should intersect 5..9 (5 episodes)
        res = paired_episode_bootstrap(cand, base, conds, strict_episodes=False)
        self.assertEqual(res.n_episodes, 5)
        self.assertAlmostEqual(res.mean_delta, -0.05)

        # Strict mode: must raise ValueError
        with self.assertRaises(ValueError) as cm:
            paired_episode_bootstrap(cand, base, conds, strict_episodes=True)
        self.assertIn("requires identical held-out episodes", str(cm.exception))

        # Completely disjoint: must raise ValueError
        disjoint_cand = {"ep_A": 0.1, "ep_B": 0.2}
        disjoint_base = {"ep_X": 0.1, "ep_Y": 0.2}
        with self.assertRaises(ValueError) as cm2:
            paired_episode_bootstrap(disjoint_cand, disjoint_base, conds)
        self.assertIn("No shared held-out episodes", str(cm2.exception))


class TestRarePayoutTailMetricsAdversarial(unittest.TestCase):
    """Adversarial challenge: Zero occurrences of rare 20x jackpot."""

    def test_zero_occurrences_of_20x_jackpot(self) -> None:
        """Verify analyze_rare_payout_tail when 20x never occurs in true labels."""
        n_samples = 1000
        # Model predicts low probabilities for 20x (~1.5%)
        probs = np.tile([0.65, 0.20, 0.10, 0.035, 0.015], (n_samples, 1))

        # True labels contain only classes 0, 1, 2, 5 (zero 20x occurrences)
        rng = np.random.default_rng(42)
        labels = rng.choice([0, 1, 2, 5], size=n_samples, p=[0.70, 0.18, 0.09, 0.03])

        diag = analyze_rare_payout_tail(probs, labels)
        self.assertEqual(diag.payout_class, 20)
        self.assertEqual(diag.true_frequency, 0.0)
        self.assertAlmostEqual(diag.mean_predicted_prob, 0.015, places=4)
        # When true_frequency == 0 and mean_predicted > 0, ratio is capped at 999.0
        self.assertEqual(diag.under_over_prediction_ratio, 999.0)
        # When true indicator has zero variance, correlation is safely 0.0
        self.assertEqual(diag.calibration_correlation, 0.0)
        self.assertFalse(np.isnan(diag.calibration_correlation))
        self.assertGreater(diag.overall_brier_component, 0.0)
        self.assertGreater(diag.mae, 0.0)
        self.assertGreater(diag.ci80_width, 0.0)

    def test_zero_predictions_and_zero_occurrences(self) -> None:
        """Verify behavior when both predicted probability and occurrences of 20x are 0.0."""
        n_samples = 200
        probs = np.tile([0.70, 0.20, 0.10, 0.0, 0.0], (n_samples, 1))
        labels = [0] * n_samples

        diag = analyze_rare_payout_tail(probs, labels)
        self.assertEqual(diag.true_frequency, 0.0)
        self.assertEqual(diag.mean_predicted_prob, 0.0)
        self.assertEqual(diag.under_over_prediction_ratio, 1.0)
        self.assertEqual(diag.calibration_correlation, 0.0)
        self.assertEqual(diag.overall_brier_component, 0.0)

    def test_calibration_curve_with_zero_occurrences(self) -> None:
        """Verify calculate_calibration_curve handles zero occurrences of 20x class without error."""
        n_samples = 500
        probs = np.tile([0.60, 0.25, 0.10, 0.04, 0.01], (n_samples, 1))
        labels = [0] * n_samples

        rep = calculate_calibration_curve(probs, labels, n_bins=10)
        self.assertEqual(len(rep.bins), 50)
        self.assertIn(20, rep.class_brier)
        self.assertIn(20, rep.ece_by_class)
        self.assertIn(20, rep.mce_by_class)
        self.assertFalse(np.isnan(rep.overall_ece))
        self.assertFalse(np.isnan(rep.overall_mce))
        self.assertFalse(np.isnan(rep.overall_brier))


if __name__ == "__main__":
    unittest.main()
