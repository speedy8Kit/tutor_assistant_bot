import argparse
import asyncio

from tutor_assistant.application.handlers.cli.repl import (
    _HELP,
    cmd_add_student,
    cmd_list_students,
)
from tutor_assistant.infrastructure.database.engine import init_db


async def repl(tutor_id: int) -> None:
    print(f"Tutor CLI (tutor_id={tutor_id}). Введи 'help' для справки.")
    while True:
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if cmd in ("exit", "quit", "q"):
            break
        elif cmd in ("list", "ls"):
            await cmd_list_students(tutor_id)
        elif cmd == "add":
            await cmd_add_student(tutor_id)
        elif cmd in ("help", "h", "?"):
            print(_HELP)
        elif cmd == "":
            continue
        else:
            print(f"Неизвестная команда: '{cmd}'. Введи 'help'.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tutor-cli",
        description="Управление учениками без Telegram.",
    )
    parser.add_argument(
        "--tutor-id", type=int, required=True, help="Telegram chat ID репетитора"
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("add-student", help="Добавить ученика (one-shot)")
    sub.add_parser("list-students", help="Список учеников (one-shot)")

    args = parser.parse_args()

    async def _run() -> None:
        await init_db()
        if args.command == "add-student":
            await cmd_add_student(args.tutor_id)
        elif args.command == "list-students":
            await cmd_list_students(args.tutor_id)
        else:
            await repl(args.tutor_id)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
