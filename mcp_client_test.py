import os
import json
import certifi
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY is missing from .env")

_HOST = "mcp.tavily.com"
_DNS_SERVER = "1.1.1.1"

def _resolve(hostname):
    import dns.resolver
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [_DNS_SERVER]
    resolver.timeout = 10
    resolver.lifetime = 10
    answers = resolver.resolve(hostname, "A")
    ip = str(list(answers)[0])
    print(f"[DNS] {hostname} -> {ip}")
    return ip

_resolved_ip = _resolve(_HOST)

import anyio._core._sockets as _as
_orig = _as.getaddrinfo
async def _gai(host, port, *, family=0, type=0, proto=0, flags=0):
    if isinstance(host, str) and host == _HOST:
        host = _resolved_ip
    return await _orig(host, port, family=family, type=type, proto=proto, flags=flags)
_as.getaddrinfo = _gai

from langchain_mcp_adapters.client import MultiServerMCPClient

_client = MultiServerMCPClient({
    "tavily": {
        "transport": "streamable_http",
        "url": f"https://{_HOST}/mcp/?tavilyApiKey={TAVILY_API_KEY}",
    }
})

_tool = None

async def get_mcp_tavily_search(query):
    global _tool
    if _tool is None:
        print("Connecting to Tavily MCP...")
        tools = await _client.get_tools()
        print(f"Tools: {[t.name for t in tools]}")
        _tool = next((t for t in tools if t.name == "tavily_search"), None)
        if _tool is None:
            raise RuntimeError("tavily_search not found")
    result = await _tool.ainvoke({"query": query})
    return result
