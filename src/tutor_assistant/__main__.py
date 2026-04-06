"""
Entry point for Tutor Assistant.

    python -m tutor_assistant                    # Telegram bot (default)
    python -m tutor_assistant cli --tutor-id ID  # CLI REPL
    python -m tutor_assistant cli --tutor-id ID add-student
    python -m tutor_assistant cli --tutor-id ID list-students
    python -m tutor_assistant cli --tutor-id ID change-student
    python -m tutor_assistant cli --tutor-id ID delete-student
    python -m tutor_assistant cli --tutor-id ID show-schedule
"""

from __future__ import annotations

import argparse
import asyncio
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m tutor_assistant",
        description="Tutor Assistant",
    )
    sub = parser.add_subparsers(dest="mode")
    sub.add_parser("cli", help="Run CLI without Telegram")

    args, remaining = parser.parse_known_args()

    if args.mode == "cli":
        sys.argv = [sys.argv[0]] + remaining
        from tutor_assistant.interfaces.cli.main import main as cli_main

        cli_main()
    else:
        from tutor_assistant.interfaces.telegram.app import build_application

        asyncio.set_event_loop(asyncio.new_event_loop())
        build_application().run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
