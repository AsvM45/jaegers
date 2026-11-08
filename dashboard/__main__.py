"""Single-command CLI entrypoint for JAEGERS Experiment Analytics Dashboard.

Enables launching via:
    python -m dashboard
    python -m dashboard --port 8501 --headless --demo
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments for dashboard launcher."""
    parser = argparse.ArgumentParser(
        prog="python -m dashboard",
        description="JAEGERS House Edge Experiment Analytics Dashboard Launcher",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to bind the Streamlit web server (default: 8501)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Network address to bind the web server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run Streamlit in headless mode without automatically launching a browser window",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=False,
        help="Force demonstration mode with synthetic benchmark fixtures",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to experiment SQLite database or directory containing JSON trial outputs",
    )
    return parser.parse_args(args)


def build_streamlit_args(parsed_args: argparse.Namespace) -> List[str]:
    """Build the command-line argument list for Streamlit CLI invocation."""
    app_path = str(Path(__file__).parent / "app.py")

    cmd = [
        "streamlit",
        "run",
        app_path,
        f"--server.port={parsed_args.port}",
        f"--server.address={parsed_args.host}",
    ]
    if parsed_args.headless:
        cmd.append("--server.headless=true")

    return cmd


def main(args: Optional[List[str]] = None, dry_run: bool = False) -> int:
    """Main CLI entrypoint. Sets environment and launches Streamlit."""
    parsed = parse_args(args)

    # Propagate flags via environment variables to Streamlit process
    if parsed.demo:
        os.environ["JAEGERS_DASHBOARD_DEMO"] = "1"
    if parsed.path:
        os.environ["JAEGERS_DASHBOARD_PATH"] = str(Path(parsed.path).resolve())

    cmd = build_streamlit_args(parsed)

    if dry_run:
        return 0

    from streamlit.web.cli import main as st_cli_main

    # Replace sys.argv for Streamlit CLI runner
    sys.argv = cmd
    try:
        st_cli_main()
        return 0
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0


if __name__ == "__main__":
    sys.exit(main())
