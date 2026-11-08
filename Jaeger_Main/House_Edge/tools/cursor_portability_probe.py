#!/usr/bin/env python3
"""Read-only structural verifier for a frozen House Edge submission pair.

The probe hashes and parses submission.csv and code.zip. It never writes those
paths, never extracts an archive into the submission directory, and never runs
the submission's training or inference command.

Row-sum tolerance is the organizer normalization contract, 1e-6
(slot_forecasting.schema.SUM_TOLERANCE and RULES.md). The separate reproduction
comparison tolerance is 1e-8. This tool does not rerun inference, so it records
REPRODUCTION_NOT_RERUN and SECOND_HOST_NOT_TESTED rather than applying 1e-8 to
a new forecast.

Reused organizer interfaces, when importable:
- slot_forecasting.io.read_queries
- slot_forecasting.io.read_submission
- slot_forecasting.submission_contract.inspect_archive
- slot_forecasting.submission_contract.safe_name
- slot_forecasting.schema.SUBMISSION_COLUMNS and SUM_TOLERANCE

Independent checks still run when those interfaces accept the files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import stat
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

DEFAULT_CSV_SHA256 = "b718f2d5e14a5a508d3c6c3658259042228a7a4d38e0221513e46e5590d9babf"
DEFAULT_ZIP_SHA256 = "9a8a9e0e18a8d21d30474b3e007156c1f19be4f693dd3b2235019be830d3001f"
DEFAULT_CSV_BYTES = 195579
DEFAULT_ZIP_BYTES = 8263

# RULES.md: "MB means 1,000,000 bytes." CSV up to 10 MB, ZIP up to 100 MB.
CSV_UPLOAD_LIMIT = 10_000_000
ZIP_UPLOAD_LIMIT = 100_000_000
REPRODUCTION_TOLERANCE = 1e-8
FALLBACK_SUM_TOLERANCE = 1e-6
FALLBACK_COLUMNS = ("query_id", "p_0", "p_1", "p_2", "p_5", "p_20")
FALLBACK_MAX_FILES = 5000
FALLBACK_MAX_EXPANDED = 512 * 1024 * 1024
README_LIMIT = 65536
PIN_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]*(?:\[[A-Za-z0-9_,.\-]+\])?==[A-Za-z0-9*][A-Za-z0-9.*+!_-]*$"
)
IMPORT_RE = re.compile(r"(?m)^(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)")
LOCAL_FILE_RE = re.compile(r"""[\"']([A-Za-z0-9_.-]+\.(?:py|json))[\"']""")
DEVICE_RE = re.compile(r"(?i)^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?$")

REQUIRED_CHECKS = (
    "queries_available",
    "csv_present",
    "csv_sha256",
    "csv_size",
    "csv_upload_limit",
    "zip_present",
    "zip_sha256",
    "zip_size",
    "zip_upload_limit",
    "csv_header",
    "csv_parse",
    "csv_row_count",
    "csv_duplicate_ids",
    "csv_query_id_set",
    "csv_probability_finite",
    "csv_probability_range",
    "csv_probability_sum",
    "organizer_read_submission",
    "zip_integrity",
    "zip_member_caps",
    "zip_safe_paths",
    "zip_required_members",
    "readme_nonempty",
    "reproduce_json",
    "reproduce_command",
    "zip_entrypoint",
    "entrypoint_local_files",
    "dependency_pins",
    "organizer_inspect_archive",
    "csv_unchanged",
    "zip_unchanged",
)


def default_queries_path() -> Path:
    return Path(__file__).resolve().parents[1] / "public" / "test" / "queries.csv"


def load_organizer():
    house = Path(__file__).resolve().parents[1]
    house_text = str(house)
    if house_text not in sys.path:
        sys.path.insert(0, house_text)
    try:
        from slot_forecasting.io import read_queries, read_submission
        from slot_forecasting.schema import SUBMISSION_COLUMNS, SUM_TOLERANCE, ValidationError
        from slot_forecasting.submission_contract import (
            MAX_EXPANDED,
            MAX_FILES,
            inspect_archive,
            safe_name,
        )
    except Exception as exc:  # importer failure is reported; independent checks still run
        return None, f"{type(exc).__name__}: {exc}"
    return SimpleNamespace(
        read_queries=read_queries,
        read_submission=read_submission,
        columns=tuple(SUBMISSION_COLUMNS),
        sum_tolerance=float(SUM_TOLERANCE),
        validation_error=ValidationError,
        max_files=MAX_FILES,
        max_expanded=MAX_EXPANDED,
        inspect_archive=inspect_archive,
        safe_name=safe_name,
    ), ""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_sha256(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if len(text) == 64 and all(character in "0123456789abcdef" for character in text):
        return text
    return None


def file_stat(path: Path):
    if not path.exists() or not path.is_file():
        return None
    info = path.stat()
    modified = datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat()
    return {
        "size": info.st_size,
        "mtime_ns": getattr(info, "st_mtime_ns", int(info.st_mtime * 1_000_000_000)),
        "mtime_utc": modified,
    }


def read_file(path: Path, limit: int):
    info = file_stat(path)
    if info is None:
        return info, None
    if info["size"] > limit:
        return info, None
    with path.open("rb") as handle:
        data = handle.read()
    if len(data) != info["size"]:
        info["size_read_mismatch"] = len(data)
    return info, data


def inside_directory(directory: Path, candidate: Path) -> bool:
    directory = directory.resolve()
    candidate = candidate.resolve()
    if candidate == directory or directory in candidate.parents:
        return True
    directory_key = str(directory).casefold().rstrip("\\/")
    candidate_key = str(candidate).casefold()
    return candidate_key == directory_key or candidate_key.startswith(directory_key + "\\") or candidate_key.startswith(directory_key + "/")


def unsafe_zip_member_reason(name: str) -> str | None:
    """Independent archive-path check. Does not trust a member enough to extract it."""
    if name == "":
        return "empty name"
    if "\x00" in name:
        return "null byte"
    if "\\" in name:
        return "backslash"
    if re.match(r"^[A-Za-z]:", name):
        return "windows drive prefix"
    if name.startswith("/") or name.startswith("//"):
        return "absolute path"
    parts = [part for part in name.split("/") if part != ""]
    if any(part == ".." for part in parts):
        return "parent directory traversal"
    if any(part == "." for part in parts):
        return "dot segment"
    if any(":" in part for part in parts):
        return "colon or drive marker"
    if any(part.endswith((" ", ".")) for part in parts):
        return "trailing dot or space"
    if any(DEVICE_RE.fullmatch(part) for part in parts):
        return "windows device name"
    if any(ord(character) < 32 for character in name):
        return "control character"
    return None


def _examples(items, limit=5) -> str:
    shown = list(items)[:limit]
    extra = len(items) - len(shown)
    text = ", ".join(str(item) for item in shown)
    if extra > 0:
        text += f" (+{extra} more)"
    return text or "none"


def load_query_ids(path: Path, organizer):
    if not path.is_file():
        return None, f"released test-query file is missing: {path}"
    if organizer is not None:
        try:
            queries = organizer.read_queries(path)
        except Exception as exc:
            return None, f"slot_forecasting.io.read_queries rejected {path}: {exc}"
        identifiers = [query.query_id for query in queries]
    else:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None or "query_id" not in reader.fieldnames:
                    return None, f"{path} has no query_id column"
                identifiers = [(row.get("query_id") or "").strip() for row in reader]
        except (OSError, UnicodeError, csv.Error) as exc:
            return None, f"could not read query ids from {path}: {exc}"
    if not identifiers:
        return None, f"{path} contains no query ids"
    duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicates:
        return None, f"released query file has duplicate ids: {_examples(duplicates)}"
    if any(not item for item in identifiers):
        return None, f"{path} contains a blank query_id"
    return identifiers, ""


def parse_submission(data: bytes, columns):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError as exc:
        return None, f"invalid UTF-8: {exc}"
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader, None)
        rows = []
        for line_no, row in enumerate(reader, start=2):
            rows.append((line_no, row))
    except csv.Error as exc:
        return None, f"invalid CSV: {exc}"
    if header is None:
        return None, "CSV has no header row"
    return {"header": header, "rows": rows}, ""


def member_names(infos):
    names = []
    for info in infos:
        raw = info.filename
        names.append(raw[:-1] if info.is_dir() and raw.endswith("/") else raw)
    return names


def special_member_reason(info) -> str | None:
    if info.flag_bits & 1:
        return "encrypted member"
    mode = stat.S_IFMT(info.external_attr >> 16)
    if mode not in (0, stat.S_IFREG, stat.S_IFDIR):
        return "symlink or special file"
    origin = getattr(info, "orig_filename", info.filename)
    if origin != info.filename:
        return "normalized or truncated path"
    return None


def parse_requirements(text: str, readme: str):
    pins = []
    errors = []
    seen = set()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("-") or "://" in line or line.startswith("git+") or "\\" in line:
            errors.append(f"line {line_no}: {raw.strip()!r} is not an exact pin")
            continue
        body = line.split(";", 1)[0].strip()
        body = body.split("--hash", 1)[0].strip()
        if any(operator in body for operator in (">=", "<=", "~=", ">", "<")) or not PIN_RE.fullmatch(body):
            errors.append(f"line {line_no}: {raw.strip()!r} is not an exact == pin")
            continue
        name, version = body.split("==", 1)
        key = name.casefold()
        if key in seen:
            errors.append(f"line {line_no}: duplicate pin {name}")
            continue
        seen.add(key)
        pins.append(f"{name}=={version}")
    if errors:
        return False, _examples(errors, 8)
    if pins:
        return True, f"{len(pins)} exact pins: {_examples(pins, 12)}"
    if "python standard library only" in readme.casefold():
        return True, "README declares Python standard library only and requirements.txt adds no packages"
    return False, "requirements.txt has no exact == pins"


def local_files_for_entrypoint(source: str, names: set[str]):
    missing = []
    referenced = []
    stdlib = getattr(sys, "stdlib_module_names", frozenset())
    for module_name in IMPORT_RE.findall(source):
        if module_name in stdlib:
            continue
        filename = module_name + ".py"
        referenced.append(filename)
        if filename not in names:
            missing.append(filename)
    for filename in LOCAL_FILE_RE.findall(source):
        if "/" in filename or "\\" in filename or filename.endswith(".py") and filename[:-3] in stdlib:
            continue
        referenced.append(filename)
        if filename not in names:
            missing.append(filename)
    ordered = []
    for item in referenced:
        if item not in ordered:
            ordered.append(item)
    missing_unique = []
    for item in missing:
        if item not in missing_unique:
            missing_unique.append(item)
    return ordered, missing_unique


def run_probe(
    csv_path,
    zip_path,
    *,
    queries_path=None,
    csv_sha256=DEFAULT_CSV_SHA256,
    zip_sha256=DEFAULT_ZIP_SHA256,
    csv_bytes=DEFAULT_CSV_BYTES,
    zip_bytes=DEFAULT_ZIP_BYTES,
) -> dict:
    organizer, import_error = load_organizer()
    columns = organizer.columns if organizer is not None else FALLBACK_COLUMNS
    sum_tolerance = organizer.sum_tolerance if organizer is not None else FALLBACK_SUM_TOLERANCE
    max_files = organizer.max_files if organizer is not None else FALLBACK_MAX_FILES
    max_expanded = organizer.max_expanded if organizer is not None else FALLBACK_MAX_EXPANDED
    checks = []

    def add(name, status, evidence):
        checks.append({"name": name, "status": status, "evidence": str(evidence)})

    csv_path = Path(csv_path)
    zip_path = Path(zip_path)
    queries = Path(queries_path) if queries_path is not None else default_queries_path()
    query_ids, query_error = load_query_ids(queries, organizer)
    if query_error:
        add("queries_available", "FAIL", query_error)
    else:
        add("queries_available", "PASS", f"{len(query_ids)} unique released test query ids from {queries}")

    before_csv = file_stat(csv_path)
    before_zip = file_stat(zip_path)
    csv_info, csv_data = read_file(csv_path, CSV_UPLOAD_LIMIT)
    zip_info, zip_data = read_file(zip_path, ZIP_UPLOAD_LIMIT)
    csv_hash = sha256_bytes(csv_data) if csv_data is not None else None
    zip_hash = sha256_bytes(zip_data) if zip_data is not None else None

    def identity(label, info, digest, expected_hash, expected_size):
        present = info is not None
        add(f"{label}_present", "PASS" if present else "FAIL", str(csv_path if label == "csv" else zip_path) if present else f"missing file: {csv_path if label == 'csv' else zip_path}")
        expected_digest = normalize_sha256(expected_hash)
        if not present or digest is None:
            reason = "file missing" if not present else f"file exceeds the read cap ({info['size']} bytes); hash not computed"
            add(f"{label}_sha256", "NOT_RUN" if not present else "FAIL", reason)
        elif expected_digest is None:
            add(f"{label}_sha256", "FAIL", "expected sha256 must be 64 hexadecimal characters")
        elif digest == expected_digest:
            add(f"{label}_sha256", "PASS", digest)
        else:
            add(f"{label}_sha256", "FAIL", f"actual {digest} != expected {expected_digest}")
        if not present:
            add(f"{label}_size", "NOT_RUN", "file missing")
            add(f"{label}_upload_limit", "NOT_RUN", "file missing")
            return
        if info["size"] == expected_size:
            add(f"{label}_size", "PASS", f"actual={info['size']} expected={expected_size}")
        else:
            add(f"{label}_size", "FAIL", f"actual={info['size']} expected={expected_size}")
        limit = CSV_UPLOAD_LIMIT if label == "csv" else ZIP_UPLOAD_LIMIT
        if info["size"] <= limit:
            add(f"{label}_upload_limit", "PASS", f"{info['size']} bytes <= {limit} bytes")
        else:
            add(f"{label}_upload_limit", "FAIL", f"{info['size']} bytes exceeds the {limit}-byte upload limit")

    identity("csv", csv_info, csv_hash, csv_sha256, csv_bytes)
    identity("zip", zip_info, zip_hash, zip_sha256, zip_bytes)

    parsed = None
    parse_error = "CSV was not read"
    if csv_data is None:
        parse_error = "CSV missing or over the read cap"
    else:
        parsed, parse_error = parse_submission(csv_data, columns)

    header_ok = False
    good_rows = []
    if parsed is None:
        add("csv_header", "NOT_RUN", parse_error)
        add("csv_parse", "FAIL" if csv_data is not None else "NOT_RUN", parse_error)
    else:
        header_ok = tuple(parsed["header"]) == tuple(columns)
        if header_ok:
            add("csv_header", "PASS", ",".join(columns))
        else:
            add("csv_header", "FAIL", f"actual={parsed['header']!r} expected={list(columns)!r}")
        width_errors = []
        for line_no, row in parsed["rows"]:
            if len(row) != len(columns) or any(not cell.strip() for cell in row):
                width_errors.append(line_no)
            elif header_ok:
                good_rows.append((line_no, row))
        if width_errors:
            add("csv_parse", "FAIL", f"malformed rows: {_examples(width_errors, 8)}")
        else:
            add("csv_parse", "PASS", f"{len(parsed['rows'])} data rows parsed")

    expected_count = len(query_ids) if query_ids is not None else None
    actual_count = len(parsed["rows"]) if parsed is not None else None
    if parsed is None or expected_count is None:
        add("csv_row_count", "NOT_RUN", "CSV or released query ids unavailable")
    elif actual_count == expected_count:
        add("csv_row_count", "PASS", f"{actual_count} rows == {expected_count} released test queries")
    else:
        add("csv_row_count", "FAIL", f"{actual_count} rows != {expected_count} released test queries")

    identifiers = []
    if header_ok:
        id_index = columns.index("query_id")
        for line_no, row in parsed["rows"]:
            if len(row) > id_index and row[id_index].strip():
                identifiers.append((line_no, row[id_index].strip()))
    if not header_ok or parsed is None:
        add("csv_duplicate_ids", "NOT_RUN", "header or CSV unavailable")
        add("csv_query_id_set", "NOT_RUN", "header, CSV, or released query ids unavailable")
    else:
        counts = {}
        for _line_no, identifier in identifiers:
            counts[identifier] = counts.get(identifier, 0) + 1
        duplicates = sorted(identifier for identifier, count in counts.items() if count > 1)
        if duplicates:
            add("csv_duplicate_ids", "FAIL", f"duplicate query_id values: {_examples(duplicates)}")
        else:
            add("csv_duplicate_ids", "PASS", f"{len(identifiers)} query ids, none repeated")
        if query_ids is None:
            add("csv_query_id_set", "NOT_RUN", "released query ids unavailable")
        else:
            actual_ids = {identifier for _line_no, identifier in identifiers}
            expected_ids = set(query_ids)
            missing = sorted(expected_ids - actual_ids)
            extra = sorted(actual_ids - expected_ids)
            if not missing and not extra and len(identifiers) == len(actual_ids) == len(expected_ids):
                add("csv_query_id_set", "PASS", f"exact match of {len(expected_ids)} query ids")
            else:
                add(
                    "csv_query_id_set",
                    "FAIL",
                    f"missing={_examples(missing)} unexpected={_examples(extra)}",
                )

    finite_errors = []
    range_errors = []
    sum_errors = []
    probability_indexes = [columns.index(name) for name in columns if name.startswith("p_")]
    if not header_ok:
        add("csv_probability_finite", "NOT_RUN", "blocked by csv_header or unreadable CSV")
        add("csv_probability_range", "NOT_RUN", "blocked by csv_header or unreadable CSV")
        add("csv_probability_sum", "NOT_RUN", "blocked by csv_header or unreadable CSV")
    elif not good_rows:
        add("csv_probability_finite", "NOT_RUN", "no well-formed data rows")
        add("csv_probability_range", "NOT_RUN", "no well-formed data rows")
        add("csv_probability_sum", "NOT_RUN", "no well-formed data rows")
    else:
        for line_no, row in good_rows:
            values = []
            numeric = True
            for index in probability_indexes:
                try:
                    number = float(row[index].strip())
                except (TypeError, ValueError):
                    numeric = False
                    finite_errors.append(f"row {line_no} query {row[0]!r} value {row[index]!r}")
                    break
                if isinstance(row[index], bool) or not math.isfinite(number):
                    numeric = False
                    finite_errors.append(f"row {line_no} query {row[0]!r} non-finite {row[index]!r}")
                    break
                values.append(number)
            if not numeric:
                sum_errors.append(f"row {line_no} query {row[0]!r} sum is not finite")
                continue
            if any(value < 0 or value > 1 for value in values):
                range_errors.append(f"row {line_no} query {row[0]!r} values={values}")
            total = math.fsum(values)
            if not math.isfinite(total) or abs(total - 1.0) > sum_tolerance:
                sum_errors.append(f"row {line_no} query {row[0]!r} sum={total:.12g}")
        add("csv_probability_finite", "FAIL" if finite_errors else "PASS", _examples(finite_errors) if finite_errors else f"all probability cells are finite ({len(good_rows)} rows)")
        add("csv_probability_range", "FAIL" if range_errors else "PASS", _examples(range_errors) if range_errors else f"all finite probabilities are inside [0, 1] ({len(good_rows)} rows)")
        add(
            "csv_probability_sum",
            "FAIL" if sum_errors else "PASS",
            _examples(sum_errors) if sum_errors else f"each row sums to 1 within {sum_tolerance:g} ({len(good_rows)} rows)",
        )

    def prior(name):
        for item in checks:
            if item["name"] == name:
                return item["status"]
        return "NOT_RUN"

    if organizer is None:
        gate = (
            "csv_header", "csv_parse", "csv_row_count", "csv_duplicate_ids", "csv_query_id_set",
            "csv_probability_finite", "csv_probability_range", "csv_probability_sum",
        )
        statuses = [prior(name) for name in gate]
        if any(status == "FAIL" for status in statuses) or any(status != "PASS" for status in statuses):
            failed = [name for name in gate if prior(name) != "PASS"]
            add("organizer_read_submission", "FAIL", f"organizer interface unavailable ({import_error}); independent CSV checks not all passing: {', '.join(failed)}")
        else:
            add("organizer_read_submission", "PASS", f"reimplemented CSV contract because organizer import failed ({import_error})")
    elif csv_data is None or query_ids is None:
        reason = "CSV was not read" if csv_data is None else "released query ids unavailable"
        add("organizer_read_submission", "NOT_RUN", f"organizer read_submission not run: {reason}")
    else:
        try:
            predictions = organizer.read_submission(csv_path, set(query_ids), content=csv_data)
        except Exception as exc:
            add("organizer_read_submission", "FAIL", f"slot_forecasting.io.read_submission: {exc}")
        else:
            add("organizer_read_submission", "PASS", f"slot_forecasting.io.read_submission accepted {len(predictions)} rows")

    archive_error = None
    infos = []
    payloads = {}
    if zip_data is None:
        archive_error = "ZIP missing or over the read cap"
        add("zip_integrity", "NOT_RUN", archive_error)
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as archive:
                infos = archive.infolist()
                uncompressed = sum(info.file_size for info in infos)
                over_cap = len(infos) > max_files or uncompressed > max_expanded
                if over_cap:
                    add("zip_integrity", "NOT_RUN", "member expansion skipped because declared size or count exceeds the cap")
                else:
                    try:
                        bad_member = archive.testzip()
                    except (RuntimeError, zipfile.BadZipFile, EOFError) as exc:
                        add("zip_integrity", "FAIL", f"zipfile.testzip failed: {exc}")
                    else:
                        if bad_member is None:
                            add("zip_integrity", "PASS", "zipfile.testzip reported no bad members")
                        else:
                            add("zip_integrity", "FAIL", f"zipfile.testzip found a bad member: {bad_member}")
                    for info in infos:
                        stored = info.filename[:-1] if info.is_dir() and info.filename.endswith("/") else info.filename
                        if info.is_dir() or unsafe_zip_member_reason(stored) is not None:
                            continue
                        if stored in {"README.md", "reproduce.json", "requirements.txt"} or stored.endswith(".py"):
                            payloads[stored] = archive.read(info)
        except (zipfile.BadZipFile, EOFError, OSError) as exc:
            archive_error = f"invalid ZIP: {exc}"
            if not any(item["name"] == "zip_integrity" for item in checks):
                add("zip_integrity", "FAIL", archive_error)

    if archive_error and not infos:
        for name in ("zip_member_caps", "zip_safe_paths", "zip_required_members", "readme_nonempty", "reproduce_json", "reproduce_command", "zip_entrypoint", "entrypoint_local_files", "dependency_pins"):
            add(name, "NOT_RUN", archive_error)
    else:
        uncompressed = sum(info.file_size for info in infos)
        if len(infos) > max_files or uncompressed > max_expanded:
            add("zip_member_caps", "FAIL", f"members={len(infos)} limit={max_files}; uncompressed={uncompressed} limit={max_expanded}")
        else:
            add("zip_member_caps", "PASS", f"members={len(infos)} uncompressed={uncompressed}")
        problems = []
        for info in infos:
            stored = info.filename[:-1] if info.is_dir() and info.filename.endswith("/") else info.filename
            origin = getattr(info, "orig_filename", stored)
            reason = unsafe_zip_member_reason(stored) or unsafe_zip_member_reason(origin) or special_member_reason(info)
            if reason:
                problems.append(f"{info.filename!r}: {reason}")
            elif organizer is not None:
                try:
                    organizer.safe_name(stored)
                except Exception as exc:
                    problems.append(f"{info.filename!r}: {exc}")
        folded = {}
        for info in infos:
            key = info.filename.casefold()
            folded[key] = folded.get(key, 0) + 1
        for key, count in folded.items():
            if count > 1:
                problems.append(f"duplicate member name {key!r} x{count}")
        if problems:
            add("zip_safe_paths", "FAIL", _examples(problems, 8))
        else:
            add("zip_safe_paths", "PASS", f"{len(infos)} member names accepted")

        names = set(member_names(infos))
        file_names = {info.filename for info in infos if not info.is_dir()}
        required = ("README.md", "reproduce.json", "requirements.txt")
        missing = [name for name in required if name not in file_names]
        if missing:
            add("zip_required_members", "FAIL", f"missing root members: {_examples(missing)}")
        else:
            add("zip_required_members", "PASS", "README.md, reproduce.json, requirements.txt")

        readme = payloads.get("README.md", b"")
        try:
            readme_text = readme.decode("utf-8")
        except UnicodeError as exc:
            readme_text = ""
            readme_error = f"README.md is not UTF-8: {exc}"
        else:
            readme_error = ""
        if "README.md" not in file_names:
            add("readme_nonempty", "NOT_RUN", "README.md missing")
        elif readme_error or not readme_text.strip() or len(readme) > README_LIMIT:
            add("readme_nonempty", "FAIL", readme_error or "README.md is empty or larger than 64 KiB")
        else:
            add("readme_nonempty", "PASS", f"README.md is {len(readme)} bytes of non-empty UTF-8")

        config = None
        config_error = ""
        if "reproduce.json" not in file_names:
            config_error = "reproduce.json missing"
        else:
            raw_config = payloads.get("reproduce.json", b"")
            if len(raw_config) > README_LIMIT:
                config_error = "reproduce.json is larger than 64 KiB"
            else:
                try:
                    config = json.loads(raw_config.decode("utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    config_error = f"reproduce.json is not UTF-8 JSON: {exc}"
                else:
                    if not isinstance(config, dict) or set(config) != {"image", "command"}:
                        config_error = f"reproduce.json keys must be exactly image and command; got {sorted(config) if isinstance(config, dict) else type(config).__name__}"
                    elif config.get("image") != "python":
                        config_error = f"image must be python; got {config.get('image')!r}"
                    elif not isinstance(config.get("command"), list):
                        config_error = "command must be a JSON array"
        if config_error:
            add("reproduce_json", "FAIL" if "reproduce.json" in file_names or config_error != "reproduce.json missing" else "NOT_RUN", config_error)
        else:
            add("reproduce_json", "PASS", 'image="python" and command is a JSON array; keys are exactly image and command')

        command = config.get("command") if isinstance(config, dict) else None
        command_error = ""
        if not isinstance(command, list):
            command_error = "command unavailable because reproduce.json did not parse"
        elif not 1 <= len(command) <= 64 or any(not isinstance(item, str) or not item or len(item) > 4096 or "\x00" in item for item in command):
            command_error = "command must contain 1 to 64 non-empty strings"
        elif "/output/submission.csv" not in command:
            command_error = "command does not include the required output argument /output/submission.csv"
        if command_error:
            status = "NOT_RUN" if command is None else "FAIL"
            add("reproduce_command", status, command_error)
        else:
            add("reproduce_command", "PASS", " ".join(command))

        scripts = []
        if isinstance(command, list):
            scripts = [item for item in command if isinstance(item, str) and item.endswith(".py") and "/" not in item and "\\" not in item]
        if not isinstance(command, list):
            add("zip_entrypoint", "NOT_RUN", "command unavailable")
            add("entrypoint_local_files", "NOT_RUN", "command unavailable")
        elif not scripts or any(script not in file_names for script in scripts):
            missing_scripts = [script for script in scripts if script not in file_names] or ["no root .py argument"]
            add("zip_entrypoint", "FAIL", f"missing entrypoint: {_examples(missing_scripts)}")
            add("entrypoint_local_files", "NOT_RUN", "entrypoint missing")
        else:
            add("zip_entrypoint", "PASS", f"root entrypoint present: {_examples(scripts)}")
            referenced = []
            missing_local = []
            entry_error = ""
            for script in scripts:
                blob = payloads.get(script, b"")
                try:
                    source = blob.decode("utf-8")
                except UnicodeError as exc:
                    entry_error = f"{script} is not UTF-8: {exc}"
                    break
                found, absent = local_files_for_entrypoint(source, file_names)
                referenced.extend(found)
                missing_local.extend(absent)
            if entry_error:
                add("entrypoint_local_files", "FAIL", entry_error)
            elif missing_local:
                add("entrypoint_local_files", "FAIL", f"entrypoint references missing root files: {_examples(missing_local)}")
            elif referenced:
                add("entrypoint_local_files", "PASS", f"local references present: {_examples(referenced, 12)}")
            else:
                add("entrypoint_local_files", "PASS", "entrypoint has no extra local .py or .json references")

        if "requirements.txt" not in file_names:
            add("dependency_pins", "FAIL", "requirements.txt missing")
        else:
            try:
                requirements_text = payloads.get("requirements.txt", b"").decode("utf-8")
            except UnicodeError as exc:
                add("dependency_pins", "FAIL", f"requirements.txt is not UTF-8: {exc}")
            else:
                pinned, detail = parse_requirements(requirements_text, readme_text)
                add("dependency_pins", "PASS" if pinned else "FAIL", detail)

    if organizer is None:
        gate = (
            "zip_integrity", "zip_member_caps", "zip_safe_paths", "zip_required_members",
            "readme_nonempty", "reproduce_json", "reproduce_command", "zip_entrypoint", "dependency_pins",
        )
        failed = [name for name in gate if prior(name) != "PASS"]
        if failed:
            add("organizer_inspect_archive", "FAIL", f"organizer interface unavailable ({import_error}); independent ZIP checks not all passing: {', '.join(failed)}")
        else:
            add("organizer_inspect_archive", "PASS", f"reimplemented archive contract because organizer import failed ({import_error})")
    elif zip_data is None:
        add("organizer_inspect_archive", "NOT_RUN", "ZIP was not read")
    else:
        try:
            inspected = organizer.inspect_archive(zip_data)
        except Exception as exc:
            add("organizer_inspect_archive", "FAIL", f"slot_forecasting.submission_contract.inspect_archive: {exc}")
        else:
            add("organizer_inspect_archive", "PASS", f"inspect_archive accepted image={inspected.get('image')!r} command_args={len(inspected.get('command', []))}")

    after_csv = file_stat(csv_path)
    after_zip = file_stat(zip_path)

    def unchanged(label, before, after, digest):
        if before is None or after is None or digest is None:
            add(f"{label}_unchanged", "NOT_RUN", "file missing or not hashed, so unchanged evidence is incomplete")
            return
        same = before["size"] == after["size"] and before["mtime_ns"] == after["mtime_ns"]
        reread = read_file(Path(csv_path if label == "csv" else zip_path), CSV_UPLOAD_LIMIT if label == "csv" else ZIP_UPLOAD_LIMIT)
        reread_hash = sha256_bytes(reread[1]) if reread[1] is not None else None
        if same and reread_hash == digest and after["size"] == before["size"]:
            add(f"{label}_unchanged", "PASS", f"size={after['size']} sha256={digest} mtime_utc={after['mtime_utc']}")
        elif reread_hash == digest and after["size"] == before["size"]:
            add(f"{label}_unchanged", "PASS", f"size and sha256 unchanged; mtime moved from {before['mtime_utc']} to {after['mtime_utc']}")
        else:
            add(f"{label}_unchanged", "FAIL", f"before size={before['size']} sha={digest}; after size={after['size']} sha={reread_hash}")

    unchanged("csv", before_csv, after_csv, csv_hash)
    unchanged("zip", before_zip, after_zip, zip_hash)

    names = [item["name"] for item in checks]
    if names != list(REQUIRED_CHECKS):
        raise RuntimeError("internal check-list drift: " + ", ".join(names))
    not_passed = [item["name"] for item in checks if item["status"] != "PASS"]
    queries_hash = None
    if queries.is_file():
        _query_info, query_bytes = read_file(queries, CSV_UPLOAD_LIMIT)
        if query_bytes is not None:
            queries_hash = sha256_bytes(query_bytes)
    reused = []
    reimplemented = [
        "SHA-256 and byte-size identity",
        "independent CSV header, row, duplicate, finite, range, and sum checks",
        "independent ZIP testzip, path safety, member caps, reproduce.json, entrypoint, and exact dependency pins",
    ]
    if organizer is not None:
        reused = [
            "slot_forecasting.io.read_queries",
            "slot_forecasting.io.read_submission",
            "slot_forecasting.submission_contract.inspect_archive",
            "slot_forecasting.submission_contract.safe_name",
            "slot_forecasting.schema.SUBMISSION_COLUMNS",
            "slot_forecasting.schema.SUM_TOLERANCE",
        ]
    else:
        reimplemented.append(f"organizer import failed ({import_error})")
    return {
        "ok": not not_passed,
        "not_passed": not_passed,
        "checks": checks,
        "artifacts": {
            "csv": {"path": str(csv_path), "exists": csv_info is not None, "size": None if csv_info is None else csv_info["size"], "sha256": csv_hash, "mtime_utc": None if csv_info is None else csv_info["mtime_utc"]},
            "zip": {"path": str(zip_path), "exists": zip_info is not None, "size": None if zip_info is None else zip_info["size"], "sha256": zip_hash, "mtime_utc": None if zip_info is None else zip_info["mtime_utc"]},
            "queries": {"path": str(queries), "count": None if query_ids is None else len(query_ids), "sha256": queries_hash},
        },
        "tolerances": {
            "normalization": sum_tolerance,
            "normalization_source": "slot_forecasting.schema.SUM_TOLERANCE" if organizer is not None else "RULES.md fallback 1e-6",
            "reproduction_comparison": REPRODUCTION_TOLERANCE,
            "reproduction_source": "RULES.md maximum normalized probability difference; not applied because inference was not rerun",
        },
        "interfaces": {"reused": reused, "reimplemented": reimplemented},
        "scope": {
            "executes_inference": False,
            "writes_submission_artifacts": False,
            "second_physical_host": False,
            "tokens": ["REPRODUCTION_NOT_RERUN", "SECOND_HOST_NOT_TESTED"],
        },
        "zip_members": member_names(infos) if infos else [],
    }


def render(result: dict) -> str:
    lines = [
        f"STRUCTURAL: {'PASS' if result['ok'] else 'FAIL'}",
        "This packaging check does not measure hidden-test score, leaderboard position, or organizer acceptance.",
        f"csv: {result['artifacts']['csv']['path']}",
        f"zip: {result['artifacts']['zip']['path']}",
        f"queries: {result['artifacts']['queries']['path']} count={result['artifacts']['queries']['count']}",
        (
            f"normalization_tolerance={result['tolerances']['normalization']:g} "
            f"reproduction_tolerance={result['tolerances']['reproduction_comparison']:g}"
        ),
        "REPRODUCTION_NOT_RERUN SECOND_HOST_NOT_TESTED",
    ]
    for check in result["checks"]:
        lines.append(f"[{check['status']}] {check['name']}: {check['evidence']}")
    lines.append("not_passed: " + (", ".join(result["not_passed"]) if result["not_passed"] else "none"))
    return "\n".join(lines) + "\n"


def refuse_output(csv_path: Path, zip_path: Path, output: Path) -> str | None:
    output = Path(output)
    protected = []
    for artifact in (Path(csv_path), Path(zip_path)):
        if output.resolve() == artifact.resolve():
            return f"refusing to overwrite submission artifact {artifact}"
        protected.append(artifact.parent)
    for directory in protected:
        if inside_directory(directory, output):
            return f"refusing to write {output} inside submission directory {directory}"
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only House Edge submission portability probe. It does not modify submission.csv or code.zip and does not run inference."
    )
    parser.add_argument("--csv", required=True, type=Path, help="Path to submission.csv. Opened read-only.")
    parser.add_argument("--zip", required=True, dest="zip_path", type=Path, help="Path to code.zip. Opened read-only and inspected in memory.")
    parser.add_argument("--queries", type=Path, default=None, help=f"Released test queries.csv. Default: {default_queries_path()}")
    parser.add_argument("--csv-sha256", default=DEFAULT_CSV_SHA256, help="Expected CSV SHA-256. Default is the frozen REVIEW_MAIN_9PM candidate.")
    parser.add_argument("--zip-sha256", default=DEFAULT_ZIP_SHA256, help="Expected ZIP SHA-256. Default is the frozen REVIEW_MAIN_9PM candidate.")
    parser.add_argument("--csv-bytes", type=int, default=DEFAULT_CSV_BYTES, help="Expected CSV size in bytes.")
    parser.add_argument("--zip-bytes", type=int, default=DEFAULT_ZIP_BYTES, help="Expected ZIP size in bytes.")
    parser.add_argument("--json", action="store_true", help="Print the JSON summary on stdout and the text summary on stderr.")
    parser.add_argument("--json-out", type=Path, default=None, help="Write the JSON summary to this path. Refuses the submission directory.")
    args = parser.parse_args(argv)
    result = run_probe(
        args.csv,
        args.zip_path,
        queries_path=args.queries,
        csv_sha256=args.csv_sha256,
        zip_sha256=args.zip_sha256,
        csv_bytes=args.csv_bytes,
        zip_bytes=args.zip_bytes,
    )
    text = render(result)
    payload = json.dumps(result, indent=2) + "\n"
    if args.json:
        sys.stderr.write(text)
        sys.stdout.write(payload)
    else:
        sys.stdout.write(text)
    if args.json_out is not None:
        refusal = refuse_output(args.csv, args.zip_path, args.json_out)
        if refusal:
            sys.stderr.write(refusal + "\n")
            return 2
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
