import sys

import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_real_stdio_process_exposes_tools_and_roundtrips_memory(tmp_path, mode):
    from mcp import Client, StdioServerParameters
    from test_bank import bank_class

    root = tmp_path / "MCP память with spaces"
    bank_class().initialize(root)
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "maverick_bank", "serve", "--bank", str(root)]
    )
    async with Client(params, read_timeout_seconds=30, mode=mode) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert names >= {
            "memory_search",
            "memory_read",
            "memory_remember",
            "memory_record_use",
            "memory_audit",
            "memory_status",
        }
        result = await client.call_tool(
            "memory_remember",
            {"title": "Database", "body": "SQLite stays local", "source": "user:mcp"},
        )
        assert not result.is_error
        saved = result.structured_content
        result = await client.call_tool("memory_search", {"query": "SQLite"})
        assert not result.is_error
        assert result.structured_content["results"][0]["id"] == saved["id"]
        result = await client.call_tool("memory_read", {"memory_id": saved["id"]})
        assert result.structured_content["body"] == "SQLite stays local"
        error = await client.call_tool("memory_read", {"memory_id": "../private"})
        assert error.is_error
