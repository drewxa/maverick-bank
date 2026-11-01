"""Run from an installed package environment, never from private memory."""

import asyncio
import json
import tempfile
import time
from pathlib import Path

from maverick_bank.bank import Bank
from maverick_bank.cli import protocol_check


def main():
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="maverick-smoke-") as temporary:
        bank = Bank.initialize(Path(temporary) / "Memory with spaces")
        note = bank.remember("Smoke preference", "Put the next action first", source="test:smoke")
        result = bank.search("next action")
        assert result["results"][0]["id"] == note["id"]
        assert bank.read(note["id"])["body"] == "Put the next action first"
        protocol = asyncio.run(protocol_check(bank.root))
        assert protocol["connected"]
        print(
            json.dumps(
                {
                    "ok": True,
                    "seconds": round(time.monotonic() - start, 3),
                    "mode": result["mode"],
                    "mcp": protocol,
                    "evidence": "Installed package + real protocol, not authenticated host/model recall",
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
