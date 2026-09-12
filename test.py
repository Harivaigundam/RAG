import asyncio
from mcp_client import get_tools

if __name__ == "__main__":
    query = "latest news about AI"
    asyncio.run(get_tools())
