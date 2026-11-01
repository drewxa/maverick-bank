"""Cross-platform CLI; stdout is JSON except when serving MCP."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from . import __version__
from .bank import Bank
from .config import default_root


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        prog="maverick-bank", description="Local, inspectable memory for Claude Code and Codex"
    )
    command.add_argument("--version", action="version", version=__version__)
    command.add_argument("--bank", type=Path)
    commands = command.add_subparsers(dest="command", required=True)

    def sub(name, help):
        item = commands.add_parser(name, help=help)
        item.add_argument("--bank", type=Path, default=argparse.SUPPRESS)
        return item

    init = sub("init", "Create a bank; repeated initialization preserves settings and notes")
    init.add_argument("--no-git", action="store_true")
    init.add_argument("--notes-dir")
    init.add_argument("--scope", help="Default scope; global unless explicitly set")
    init.add_argument("--review-days", type=int)
    sub("serve", "Run the stdio MCP server")
    remember = sub("remember", "Save an append-only sourced memory")
    remember.add_argument("--title", required=True)
    bodies = remember.add_mutually_exclusive_group(required=True)
    bodies.add_argument("--body")
    bodies.add_argument("--body-file", type=Path)
    remember.add_argument("--source", required=True)
    remember.add_argument("--scope")
    remember.add_argument("--kind", default="fact")
    remember.add_argument("--status", default="unverified")
    remember.add_argument("--supersedes")
    search = sub("search", "Search current scoped evidence")
    search.add_argument("query")
    search.add_argument("--scope")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--include-superseded", action="store_true")
    search.add_argument("--all-scopes", action="store_true", help="Explicitly search every scope")
    read = sub("read", "Read a current source span by memory ID")
    read.add_argument("memory_id")
    read.add_argument("--start-line", type=int)
    read.add_argument("--end-line", type=int)
    use = sub("record-use", "Record self-reported use, not measured benefit")
    use.add_argument("memory_id")
    use.add_argument("revision")
    use.add_argument("--agent", default="unknown")
    use.add_argument("--task-id", default="")
    use.add_argument("--outcome", default="unknown")
    for name in ("reindex", "audit", "stats", "status", "history"):
        sub(name, f"Show or perform {name}")
    doctor = sub("doctor", "Diagnose core prerequisites and optional semantic state")
    doctor.add_argument(
        "--mcp", action="store_true", help="Also launch an actual stdio MCP subprocess"
    )
    semantic = sub("semantic", "Explicitly provision a local semantic model")
    semantic.add_argument("action", choices=["install"])
    semantic.add_argument("--model")
    event_command = sub("events", "Manage local access-event retention")
    event_command.add_argument("action", choices=["prune"])
    for name in ("install", "uninstall"):
        install = sub(name, f"{name.title()} owned client configuration; memory is preserved")
        install.add_argument("--clients", nargs="+", choices=["codex", "claude"], required=True)
        install.add_argument("--scope", choices=["user", "project"], default="user")
        install.add_argument("--project", type=Path)
    return command


async def protocol_check(root: Path) -> dict:
    from mcp import Client, StdioServerParameters

    async with Client(
        StdioServerParameters(
            command=sys.executable, args=["-m", "maverick_bank", "serve", "--bank", str(root)]
        ),
        read_timeout_seconds=30,
    ) as client:
        result = await client.list_tools()
        response = await client.call_tool("memory_status", {})
        return {
            "connected": not response.is_error,
            "tools": [tool.name for tool in result.tools],
            "meaning": "Real protocol connection; not an authenticated agent recall test",
        }


def diagnose(bank: Bank, mcp: bool) -> dict:
    import asyncio

    from .embeddings import load_provider

    status = bank.status()
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE VIRTUAL TABLE check_fts USING fts5(text)")
    checks = {
        "fts5": True,
        "git": status["git_available"] or not status["git_enabled"],
        "history": not status["pending_operations"],
        "notes": not status["issues"],
    }
    result = {
        **status,
        "checks": checks,
        "ready": all(checks.values()),
        "semantic_status": "not_configured",
        "next": "Start a new agent session after install; verify scoped recall of a sourced note.",
    }
    if bank.config.semantic_enabled:
        try:
            load_provider(bank.state, bank.config.semantic_model, bank.config.semantic_cache_dir)
            result["semantic_status"] = "ready"
        except (ValueError, OSError, ImportError, RuntimeError) as exc:
            result["semantic_status"] = "unavailable"
            result["semantic_reason"] = str(exc)
            result["ready"] = False
    if mcp:
        result["mcp"] = asyncio.run(protocol_check(bank.root))
        result["ready"] = result["ready"] and result["mcp"]["connected"]
    return result


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    arguments = parser().parse_args(argv)
    root = (arguments.bank or default_root()).expanduser().resolve()
    try:
        if arguments.command == "init":
            settings = {}
            for argument, field in (
                ("notes_dir", "notes_dir"),
                ("scope", "default_scope"),
                ("review_days", "review_after_days"),
            ):
                if getattr(arguments, argument) is not None:
                    settings[field] = getattr(arguments, argument)
            if arguments.no_git:
                settings["git_enabled"] = False
            bank = Bank.initialize(root, **settings)
            result = {"initialized": True, **bank.status()}
        elif arguments.command == "serve":
            from .server import serve

            serve(root)
            return 0
        else:
            bank = Bank(root)
            match arguments.command:
                case "remember":
                    body = (
                        arguments.body
                        if arguments.body is not None
                        else arguments.body_file.read_text(encoding="utf-8")
                    )
                    result = bank.remember(
                        arguments.title,
                        body,
                        arguments.source,
                        arguments.scope,
                        arguments.kind,
                        arguments.status,
                        arguments.supersedes,
                    )
                case "search":
                    result = bank.search(
                        arguments.query,
                        arguments.limit,
                        arguments.scope,
                        arguments.include_superseded,
                        arguments.all_scopes,
                    )
                case "read":
                    result = bank.read(
                        arguments.memory_id, arguments.start_line, arguments.end_line
                    )
                case "record-use":
                    result = bank.record_use(
                        arguments.memory_id,
                        arguments.revision,
                        arguments.task_id,
                        arguments.agent,
                        arguments.outcome,
                    )
                case "reindex" | "audit" | "stats" | "status":
                    result = getattr(bank, arguments.command)()
                case "history":
                    with bank.locked():
                        result = bank.history.log()
                case "doctor":
                    result = diagnose(bank, arguments.mcp)
                case "semantic":
                    result = bank.provision_semantic(arguments.model)
                case "events":
                    result = bank.prune_events()
                case "install" | "uninstall":
                    from .integrations import install_clients, uninstall_clients

                    operation = (
                        install_clients if arguments.command == "install" else uninstall_clients
                    )
                    result = operation(root, arguments.clients, arguments.scope, arguments.project)
        # Escape non-ASCII only when a Windows console cannot represent it; source remains UTF-8.
        output = json.dumps(result, ensure_ascii=False, indent=2)
        try:
            print(output)
        except UnicodeEncodeError:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if arguments.command != "doctor" or result["ready"] else 1
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Cancelled; existing memory is preserved.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
