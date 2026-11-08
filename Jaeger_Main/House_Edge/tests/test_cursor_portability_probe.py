"""Adversarial tests for the read-only House Edge portability probe.

The probe module is loaded by path so this file does not require a tests package
or a packaging change. Synthetic archives and CSVs stay in a temp directory.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cursor_portability_probe.py"
SPEC = importlib.util.spec_from_file_location("cursor_portability_probe", TOOL)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)

EVEN = ("0.2", "0.2", "0.2", "0.2", "0.2")
README = b"House Edge structural fixture.\nThe declared command recreates the forecast offline.\n"
REPRODUCE = {
    "image": "python",
    "command": ["python", "predict.py", "--data", "/data", "--out", "/output/submission.csv"],
}
REQUIREMENTS = b"numpy==2.5.4\r\nscikit-learn==1.9.1\r\n"
PREDICT = b"# structural entrypoint\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def queries_text(identifiers) -> bytes:
    lines = ["query_id,episode_id,machine_id,machine_type,signal,cutoff"]
    for index, identifier in enumerate(identifiers):
        lines.append(f"{identifier},episode{index},machine{index},steady,0,30")
    return ("\n".join(lines) + "\n").encode()


def submission_text(rows) -> bytes:
    lines = ["query_id,p_0,p_1,p_2,p_5,p_20"]
    for identifier, values in rows:
        lines.append(identifier + "," + ",".join(values))
    return ("\n".join(lines) + "\n").encode()


def raw_stored_zip(members) -> bytes:
    """Build a stored ZIP from raw filename bytes, including names ZipFile would sanitize."""
    local_parts = []
    central_parts = []
    offset = 0
    for name, data in members:
        crc = zlib.crc32(data) & 0xFFFFFFFF
        local = (
            b"PK\x03\x04"
            + struct.pack("<HHHHHIIIHH", 20, 0, 0, 0, 0, crc, len(data), len(data), len(name), 0)
            + name
            + data
        )
        central = (
            b"PK\x01\x02"
            + struct.pack("<HHHHHHIIIHHHHHII", 20, 20, 0, 0, 0, 0, crc, len(data), len(data), len(name), 0, 0, 0, 0, 0, offset)
            + name
        )
        local_parts.append(local)
        central_parts.append(central)
        offset += len(local)
    central_directory = b"".join(central_parts)
    local_blob = b"".join(local_parts)
    end = b"PK\x05\x06" + struct.pack("<HHHHIIH", 0, 0, len(members), len(members), len(central_directory), len(local_blob), 0)
    return local_blob + central_directory + end


def zip_bytes(members) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            info = zipfile.ZipInfo(filename=name)
            archive.writestr(info, payload)
    return buffer.getvalue()


def valid_members(predict=PREDICT) -> dict:
    return {
        "README.md": README,
        "reproduce.json": (json.dumps(REPRODUCE, indent=2) + "\n").encode(),
        "requirements.txt": REQUIREMENTS,
        "predict.py": predict,
    }


class ProbeTests(unittest.TestCase):
    def status(self, result, name):
        matches = [item for item in result["checks"] if item["name"] == name]
        self.assertEqual(len(matches), 1, name)
        return matches[0]["status"]

    def evidence(self, result, name):
        return next(item["evidence"] for item in result["checks"] if item["name"] == name)

    def run_case(self, directory, csv_data, zip_data, identifiers, **overrides):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        csv_path = directory / "submission.csv"
        zip_path = directory / "code.zip"
        query_path = directory / "queries.csv"
        if csv_data is not None:
            csv_path.write_bytes(csv_data)
        if zip_data is not None:
            zip_path.write_bytes(zip_data)
        query_path.write_bytes(queries_text(identifiers))
        csv_exists = csv_path.is_file()
        zip_exists = zip_path.is_file()
        before = (csv_path.read_bytes() if csv_exists else None, zip_path.read_bytes() if zip_exists else None)
        result = PROBE.run_probe(
            csv_path,
            zip_path,
            queries_path=query_path,
            csv_sha256=overrides.get("csv_sha256", sha256(csv_path.read_bytes()) if csv_exists else "0" * 64),
            zip_sha256=overrides.get("zip_sha256", sha256(zip_path.read_bytes()) if zip_exists else "0" * 64),
            csv_bytes=overrides.get("csv_bytes", csv_path.stat().st_size if csv_exists else 0),
            zip_bytes=overrides.get("zip_bytes", zip_path.stat().st_size if zip_exists else 0),
        )
        if csv_exists:
            self.assertEqual(csv_path.read_bytes(), before[0])
        if zip_exists:
            self.assertEqual(zip_path.read_bytes(), before[1])
        self.assertEqual([item["name"] for item in result["checks"]], list(PROBE.REQUIRED_CHECKS))
        return result

    def valid_result(self, directory, identifiers=("q1", "q2"), rows=None, members=None, **overrides):
        rows = rows if rows is not None else [(identifier, EVEN) for identifier in identifiers]
        members = valid_members() if members is None else members
        return self.run_case(directory, submission_text(rows), zip_bytes(members), identifiers, **overrides)

    def test_default_identity_is_the_frozen_candidate(self):
        self.assertEqual(PROBE.DEFAULT_CSV_SHA256, "b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf")
        self.assertEqual(PROBE.DEFAULT_ZIP_SHA256, "9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f")
        self.assertEqual(PROBE.DEFAULT_CSV_BYTES, 195579)
        self.assertEqual(PROBE.DEFAULT_ZIP_BYTES, 8263)
        self.assertEqual(PROBE.REPRODUCTION_TOLERANCE, 1e-8)
        self.assertLessEqual(PROBE.FALLBACK_SUM_TOLERANCE, 1e-6)

    def test_valid_fixture_passes_and_records_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.valid_result(temporary)
        self.assertTrue(result["ok"], result["not_passed"])
        self.assertEqual(result["not_passed"], [])
        self.assertIn("slot_forecasting.io.read_submission", result["interfaces"]["reused"])
        self.assertIn("slot_forecasting.submission_contract.inspect_archive", result["interfaces"]["reused"])
        self.assertEqual(result["tolerances"]["normalization"], 1e-6)
        self.assertEqual(result["tolerances"]["reproduction_comparison"], 1e-8)
        self.assertEqual(result["scope"]["tokens"], ["REPRODUCTION_NOT_RERUN", "SECOND_HOST_NOT_TESTED"])
        self.assertFalse(result["scope"]["executes_inference"])
        self.assertFalse(result["scope"]["writes_submission_artifacts"])
        text = PROBE.render(result)
        self.assertIn("STRUCTURAL: PASS", text)
        self.assertIn("SECOND_HOST_NOT_TESTED", text)
        self.assertIn("does not measure hidden-test score", text)

    def test_default_frozen_hash_rejects_a_different_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.valid_result(
                temporary,
                csv_sha256=PROBE.DEFAULT_CSV_SHA256,
                zip_sha256=PROBE.DEFAULT_ZIP_SHA256,
                csv_bytes=PROBE.DEFAULT_CSV_BYTES,
                zip_bytes=PROBE.DEFAULT_ZIP_BYTES,
            )
        self.assertFalse(result["ok"])
        self.assertEqual(self.status(result, "csv_sha256"), "FAIL")
        self.assertEqual(self.status(result, "zip_sha256"), "FAIL")

    def test_incorrect_hash_keeps_the_size_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.valid_result(temporary, csv_sha256="0" * 64)
        self.assertEqual(self.status(result, "csv_sha256"), "FAIL")
        self.assertEqual(self.status(result, "csv_size"), "PASS")
        self.assertFalse(result["ok"])

    def test_missing_csv_and_missing_zip_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            missing_csv = self.run_case(directory / "a", None, zip_bytes(valid_members()), ("q1", "q2"))
            missing_zip = self.run_case(directory / "b", submission_text([("q1", EVEN), ("q2", EVEN)]), None, ("q1", "q2"))
        self.assertEqual(self.status(missing_csv, "csv_present"), "FAIL")
        self.assertIn(self.status(missing_csv, "csv_header"), {"NOT_RUN", "FAIL"})
        self.assertFalse(missing_csv["ok"])
        self.assertEqual(self.status(missing_zip, "zip_present"), "FAIL")
        self.assertEqual(self.status(missing_zip, "zip_integrity"), "NOT_RUN")
        self.assertFalse(missing_zip["ok"])

    def test_bad_header_non_numeric_duplicate_and_row_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad_header = self.run_case(
                root / "header",
                b"id,p0,p1,p2,p5,p20\nq1,0.2,0.2,0.2,0.2,0.2\nq2,0.2,0.2,0.2,0.2,0.2\n",
                zip_bytes(valid_members()),
                ("q1", "q2"),
            )
            duplicate = self.valid_result(root / "duplicate", rows=[("q1", EVEN), ("q1", EVEN)])
            short = self.valid_result(root / "short", rows=[("q1", EVEN)])
            words = self.valid_result(root / "words", rows=[("q1", ("nope", "0.2", "0.2", "0.2", "0.2")), ("q2", EVEN)])
        self.assertEqual(self.status(bad_header, "csv_header"), "FAIL")
        self.assertEqual(self.status(bad_header, "organizer_read_submission"), "FAIL")
        self.assertEqual(self.status(duplicate, "csv_duplicate_ids"), "FAIL")
        self.assertEqual(self.status(short, "csv_row_count"), "FAIL")
        self.assertEqual(self.status(short, "csv_query_id_set"), "FAIL")
        self.assertEqual(self.status(words, "csv_probability_finite"), "FAIL")
        self.assertFalse(words["ok"])

    def test_invalid_probability_vectors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            negative = self.valid_result(root / "negative", rows=[("q1", ("-0.1", "0.3", "0.3", "0.2", "0.3")), ("q2", EVEN)])
            above = self.valid_result(root / "above", rows=[("q1", ("1.5", "0", "0", "0", "0")), ("q2", EVEN)])
            nan = self.valid_result(root / "nan", rows=[("q1", ("nan", "0", "0", "0", "0")), ("q2", EVEN)])
            infinite = self.valid_result(root / "inf", rows=[("q1", ("inf", "0", "0", "0", "0")), ("q2", EVEN)])
            off_sum = self.valid_result(root / "sum", rows=[("q1", ("0.2", "0.2", "0.2", "0.2", "0.1")), ("q2", EVEN)])
            boundary = self.valid_result(root / "edge", rows=[("q1", ("0.5", "0.5", "0", "0", "0.000001")), ("q2", EVEN)])
            over_tolerance = self.valid_result(root / "over", rows=[("q1", ("0.5", "0.5", "0", "0", "0.0000011")), ("q2", EVEN)])
        self.assertEqual(self.status(negative, "csv_probability_range"), "FAIL")
        self.assertEqual(self.status(negative, "csv_probability_sum"), "PASS")
        self.assertEqual(self.status(negative, "csv_probability_finite"), "PASS")
        self.assertEqual(self.status(above, "csv_probability_range"), "FAIL")
        self.assertEqual(self.status(nan, "csv_probability_finite"), "FAIL")
        self.assertEqual(self.status(infinite, "csv_probability_finite"), "FAIL")
        self.assertEqual(self.status(off_sum, "csv_probability_range"), "PASS")
        self.assertEqual(self.status(off_sum, "csv_probability_sum"), "FAIL")
        self.assertEqual(self.status(boundary, "csv_probability_sum"), "PASS")
        self.assertEqual(self.status(over_tolerance, "csv_probability_sum"), "FAIL")

    def test_missing_members_pins_command_and_local_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            members = valid_members()
            del members["requirements.txt"]
            missing = self.valid_result(root / "missing", members=members)
            unpinned = valid_members()
            unpinned["requirements.txt"] = b"numpy\nscikit-learn>=1.9\n"
            pins = self.valid_result(root / "pins", members=unpinned)
            command = dict(REPRODUCE)
            command = {
                "image": "python",
                "command": ["python", "predict.py", "--data", "/data", "--out", "/tmp/not-the-contract.csv"],
            }
            bad_command_members = valid_members()
            bad_command_members["reproduce.json"] = (json.dumps(command) + "\n").encode()
            declared = self.valid_result(root / "command", members=bad_command_members)
            local = valid_members(predict=b"from jaeger_model import predict\n")
            unresolved = self.valid_result(root / "local", members=local)
            empty_readme = valid_members()
            empty_readme["README.md"] = b" \n"
            blank = self.valid_result(root / "readme", members=empty_readme)
        self.assertEqual(self.status(missing, "zip_required_members"), "FAIL")
        self.assertEqual(self.status(missing, "dependency_pins"), "FAIL")
        self.assertEqual(self.status(pins, "dependency_pins"), "FAIL")
        self.assertIn("not an exact", self.evidence(pins, "dependency_pins"))
        self.assertEqual(self.status(declared, "reproduce_command"), "FAIL")
        self.assertEqual(self.status(unresolved, "entrypoint_local_files"), "FAIL")
        self.assertIn("jaeger_model.py", self.evidence(unresolved, "entrypoint_local_files"))
        self.assertEqual(self.status(blank, "readme_nonempty"), "FAIL")

    def test_unsafe_archive_paths(self):
        dangerous = ("../evil.txt", "/tmp/evil.txt", "C:/evil.txt", "..\\evil.txt", "foo/../../evil.txt")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in dangerous:
                with self.subTest(name=name):
                    self.assertIsNotNone(PROBE.unsafe_zip_member_reason(name))
                    members = valid_members()
                    members[name] = b"bad"
                    payload = zip_bytes(members)
                    result = self.run_case(
                        root / str(abs(hash(name))),
                        submission_text([("q1", EVEN), ("q2", EVEN)]),
                        payload,
                        ("q1", "q2"),
                    )
                    stored = zipfile.ZipFile(io.BytesIO(payload)).infolist()
                    unsafe_stored = [
                        info.filename
                        for info in stored
                        if PROBE.unsafe_zip_member_reason(info.filename)
                        or PROBE.unsafe_zip_member_reason(getattr(info, "orig_filename", ""))
                        or info.orig_filename != info.filename
                    ]
                    self.assertTrue(unsafe_stored, [info.filename for info in stored])
                    self.assertEqual(self.status(result, "zip_safe_paths"), "FAIL", [info.filename for info in stored])
                    self.assertEqual(self.status(result, "organizer_inspect_archive"), "FAIL")
                    self.assertFalse(result["ok"])

    def test_null_byte_member_is_rejected(self):
        members = [(name.encode(), payload) for name, payload in valid_members().items()]
        members.append((b"evil\x00.txt", b"bad"))
        payload = raw_stored_zip(members)
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_case(
                temporary,
                submission_text([("q1", EVEN), ("q2", EVEN)]),
                payload,
                ("q1", "q2"),
            )
        self.assertEqual(self.status(result, "zip_safe_paths"), "FAIL")
        self.assertIn("null", self.evidence(result, "zip_safe_paths").casefold())
        self.assertEqual(self.status(result, "organizer_inspect_archive"), "FAIL")
        self.assertFalse(result["ok"])

    def test_symlink_member_is_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, payload in valid_members().items():
                archive.writestr(name, payload)
            info = zipfile.ZipInfo("link.txt")
            info.external_attr = stat.S_IFLNK << 16
            archive.writestr(info, b"target")
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_case(
                temporary,
                submission_text([("q1", EVEN), ("q2", EVEN)]),
                buffer.getvalue(),
                ("q1", "q2"),
            )
        self.assertIn(self.status(result, "zip_safe_paths"), {"FAIL", "PASS"})
        if self.status(result, "zip_safe_paths") == "PASS":
            self.assertEqual(self.status(result, "organizer_inspect_archive"), "FAIL")
        self.assertFalse(result["ok"])

    def test_truncated_and_corrupt_archives_and_garbled_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            intact = zip_bytes(valid_members())
            truncated = self.run_case(
                root / "truncated",
                submission_text([("q1", EVEN), ("q2", EVEN)]),
                intact[:-30],
                ("q1", "q2"),
            )
            corrupted = bytearray(intact)
            corrupted[min(80, len(corrupted) - 1)] ^= 0xFF
            corrupt = self.run_case(
                root / "corrupt",
                submission_text([("q1", EVEN), ("q2", EVEN)]),
                bytes(corrupted),
                ("q1", "q2"),
            )
            garbled = self.run_case(
                root / "garbled",
                b"\xff\xfe\xfa this is not a csv\n\x00",
                intact,
                ("q1", "q2"),
            )
            partial = self.run_case(
                root / "partial",
                b"query_id,p_0,p_1,p_2,p_5,p_20\nq1,0.2",
                intact,
                ("q1", "q2"),
            )
        self.assertEqual(self.status(truncated, "zip_integrity"), "FAIL")
        self.assertNotEqual(self.status(corrupt, "zip_integrity"), "PASS")
        self.assertFalse(corrupt["ok"])
        self.assertEqual(self.status(garbled, "csv_parse"), "FAIL")
        self.assertIn(self.status(partial, "csv_parse"), {"FAIL", "PASS"})
        self.assertFalse(partial["ok"])

    def test_member_count_cap(self):
        members = valid_members()
        for index in range(PROBE.FALLBACK_MAX_FILES):
            members[f"extra-{index}.txt"] = b"x"
        with tempfile.TemporaryDirectory() as temporary:
            result = self.valid_result(temporary, members=members)
        self.assertEqual(self.status(result, "zip_member_caps"), "FAIL")
        self.assertFalse(result["ok"])

    def test_cli_exit_codes_and_refuses_artifact_directory_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact_dir = root / "artifacts"
            artifact_dir.mkdir()
            query_path = root / "queries.csv"
            identifiers = ("q1", "q2")
            csv_data = submission_text([(identifier, EVEN) for identifier in identifiers])
            archive = zip_bytes(valid_members())
            csv_path = artifact_dir / "submission.csv"
            zip_path = artifact_dir / "code.zip"
            csv_path.write_bytes(csv_data)
            zip_path.write_bytes(archive)
            query_path.write_bytes(queries_text(identifiers))
            report = root / "reports" / "probe.json"
            passed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--csv",
                    str(csv_path),
                    "--zip",
                    str(zip_path),
                    "--queries",
                    str(query_path),
                    "--csv-sha256",
                    sha256(csv_data),
                    "--zip-sha256",
                    sha256(archive),
                    "--csv-bytes",
                    str(len(csv_data)),
                    "--zip-bytes",
                    str(len(archive)),
                    "--json-out",
                    str(report),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertIn("STRUCTURAL: PASS", passed.stdout)
            self.assertIn("REPRODUCTION_NOT_RERUN", passed.stdout)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["ok"])
            refused = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--csv",
                    str(csv_path),
                    "--zip",
                    str(zip_path),
                    "--queries",
                    str(query_path),
                    "--csv-sha256",
                    sha256(csv_data),
                    "--zip-sha256",
                    sha256(archive),
                    "--csv-bytes",
                    str(len(csv_data)),
                    "--zip-bytes",
                    str(len(archive)),
                    "--json-out",
                    str(artifact_dir / "probe.json"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(refused.returncode, 2, refused.stderr)
            self.assertFalse((artifact_dir / "probe.json").exists())
            self.assertEqual(csv_path.read_bytes(), csv_data)
            self.assertEqual(zip_path.read_bytes(), archive)
            failed = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--csv",
                    str(csv_path),
                    "--zip",
                    str(zip_path),
                    "--queries",
                    str(query_path),
                    "--csv-sha256",
                    "ab" * 32,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(failed.returncode, 1, failed.stdout)
            self.assertIn("[FAIL] csv_sha256", failed.stdout)

    def test_probe_source_does_not_extract_archives(self):
        source = TOOL.read_text(encoding="utf-8")
        self.assertNotIn("extractall", source)
        self.assertNotIn("extract_archive", source)
        self.assertNotIn("submission.csv\", \"w", source)
        self.assertNotIn("code.zip\", \"w", source)


if __name__ == "__main__":
    unittest.main()
