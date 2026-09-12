from langchain_mcp_adapters.client import MultiServerMCPClient
import os
import certifi
from dotenv import load_dotenv
import json
from langchain_groq import ChatGroq
import asyncio

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

#load api key
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise ValueError ("TAVILY_API_KEY is Error")

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
if not AVIATIONSTACK_API_KEY:
    raise ValueError ("AVIATIONSTACK_API_KEY is Error")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OPENWEATHER_API_KEY:
    raise ValueError ("OPENWEATHER_API_KEY is Error")

MODEL = os.getenv("MODEL")
if not MODEL:
    raise ValueError("MODEL is Error")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is Error")

#llm invoke

llm = ChatGroq(model=MODEL, api_key=GROQ_API_KEY)

#client Creation
client = MultiServerMCPClient(
    {
        "tavily":{
            "transport": "streamable_http",
            "url":f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },
                "Aviationstack": {
                    "transport":"stdio",
                    "command": "uvx",
                    "args": [
                        "--with",
                        "mcp==1.28.1",
                        "aviationstack-mcp"
                    ],
                    "env": {
                        "AVIATION_STACK_API_KEY": AVIATIONSTACK_API_KEY
                    }
                },
        "weather":{
            "transport":"stdio",
            "command": r"C:\MAgents\TripAgent\travel\Scripts\python.exe",
            "args":[r"C:\MAgents\TripAgent\mcp_server.py"],
            "env":{
                "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY
                }
        }
    }
)

#First Tool want to design in the Remote and custom

async def get_all_tools():
    tools = await client.get_tools()
    
    for t in tools:
        print(t.name)
        

search_tool = None
aviation_tool = None

async def initalize_mcp():
    global search_tool
    global aviation_tool
    
    if search_tool is not None and aviation_tool:
        return
    
    tools = await client.get_tools()
    
    search_tool = next(tool for tool in tools if tool.name == "tavily_search")
    
    aviation_tool = {
        tool.name : tool
        for tool in tools
        if tool.name != "tavily_search"
    }
        
async def get_mcp_tavily_search(query):
        tools = await client.get_tools()
        print(f"Tools: {[t.name for t in tools]}")
        tool = next((t for t in tools if t.name == "tavily_search"), None)
        if tool is None:
            raise RuntimeError("tavily_search not found")
        result = await tool.ainvoke({"query": query})
        return result

async def aviation_mcp_call(
    tool_name: str,
    tool_args:dict = None):
        tools = await client.get_tools()
        
        tool = next(t for t in tools if t.name == tool.name)
        
        result = await tool.ainvoke(
            tool_args or {}
        )
        
        return result
    
    

if __name__ == "__main__":
    print("run")
    asyncio.run(get_all_tools())