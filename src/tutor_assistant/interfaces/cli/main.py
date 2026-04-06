"""CLI entry point — argparse runner."""

from __future__ import annotations

import argparse
import asyncio

from tutor_assistant.infrastructure.database.engine import (
    async_session_factory,
    init_db,
)
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import format_student_list, html_strip
from tutor_assistant.interfaces.shared.messages import LIST_EMPTY, LIST_HEADER


def _print(text: str) -> None:
    print(html_strip(text))


async def _run(args: argparse.Namespace) -> None:
    await init_db()

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)

            if args.command == "list-students":
                from tutor_assistant.application.use_cases.students import list_students

                students = await list_students(repo, args.tutor_id)
                if not students:
                    _print(LIST_EMPTY)
                else:
                    _print(
                        LIST_HEADER.format(count=len(students))
                        + format_student_list(students)
                    )

            elif args.command == "add-student":
                from tutor_assistant.interfaces.cli.repl import run_add_student

                await run_add_student(repo, args.tutor_id)

            elif args.command == "change-student":
                from tutor_assistant.interfaces.cli.repl import run_change_student

                await run_change_student(repo, args.tutor_id)

            elif args.command == "delete-student":
                from tutor_assistant.interfaces.cli.repl import run_delete_student

                await run_delete_student(repo, args.tutor_id)

            elif args.command == "show-schedule":
                from tutor_assistant.interfaces.cli.repl import run_show_schedule

                await run_show_schedule(repo, args.tutor_id)

            else:
                from tutor_assistant.interfaces.cli.repl import run_repl

                await run_repl(repo, args.tutor_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m tutor_assistant cli",
        description="Tutor Assistant CLI",
    )
    parser.add_argument("--tutor-id", type=int, required=True, help="Tutor chat ID")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list-students")
    sub.add_parser("add-student")
    sub.add_parser("change-student")
    sub.add_parser("delete-student")
    sub.add_parser("show-schedule")

    args = parser.parse_args()
    asyncio.run(_run(args))
