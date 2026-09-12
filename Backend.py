import os
import asyncio
import json
import re
import certifi
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from typing import TypedDict, Annotated
import operator
import uuid
import psycopg
from psycopg.rows import dict_row
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    AnyMessage
)
from langchain_groq import ChatGroq
from mcp_client import get_mcp_tavily_search, aviation_mcp_call


def get_database_url():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DB URL is missing")
    if "sslmode" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"
    return db_url


def _resolve_db_host(url):
    import socket
    from urllib.parse import urlparse, urlunparse
    import dns.resolver
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return url
    try:
        socket.getaddrinfo(hostname, 5432)
        return url
    except (socket.gaierror, OSError):
        pass
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["1.1.1.1"]
        resolver.timeout = 10
        resolver.lifetime = 10
        answers = resolver.resolve(hostname, "A")
        ip = str(list(answers)[0])
        print(f"[DNS] DB host {hostname} -> {ip}")
        return urlunparse(parsed._replace(netloc=parsed.netloc.replace(hostname, ip)))
    except Exception as e:
        print(f"[DNS] DB resolve failed: {e}")
        return url


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = os.getenv("MODEL")
if not GROQ_API_KEY:
    raise ValueError("GROQ API Key is missing")

llm = ChatGroq(model=MODEL, api_key=GROQ_API_KEY)


def _clean_model_output(content):
    if not isinstance(content, str):
        return content
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL)
    return content.strip()


def _format_hotel_results(result):
    payload = result
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if isinstance(payload, dict) and isinstance(payload.get("text"), str):
        try:
            payload = json.loads(payload["text"])
        except json.JSONDecodeError:
            return payload["text"]
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        hotels = []
        for item in payload["results"][:5]:
            hotels.append({
                "name": item.get("title", "Hotel result"),
                "url": item.get("url", ""),
                "details": item.get("content", "")[:500],
            })
        return json.dumps(hotels, ensure_ascii=False, indent=2)
    return str(payload)


class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_result: str
    hotel_result: str
    itinerary: str
    llm_calls: str

Flight_prompt = """
    You are s travel flight expert
    user Query:{query}
    Airport Information: {airline_data}
    Generate:
    1. Likely Departure airport
    2. Likely Arrival Airport
    3. Airlines Serving this route
    4. Typical flight duration
    5. Estimated airfare Range
    6. Peak Season Pricing Warning
    7. Booking advice
    Return concise travel guidence
    """

async def flight_agent(state: TravelState):
    
    
    query = state["user_query"]
    try:
        airports = asyncio.run(
            aviation_mcp_call("list_airports")
        )
        
        airline = asyncio.run(
            aviation_mcp_call("list_airline")
        )
        print("\n airports")
        print("\n airline")
        
        prompt = Flight_prompt(
            query = query,
            airport_data = str(airports)[:3000],
            airline_data = str(airline)[:3000]
        )
        
        response = llm.invoke(
            [
                SystemMessage(
                    content = "you are an expert travel flight planner"
                ),
                HumanMessage(content = prompt)
            ]
        )
        
        
        flight_data = response.content
    
    except Exception as e:
        flight_data =f"Flight info:{str(e)}"
        
    return {
        "flight_result": flight_data,
        "messages": [AIMessage(content="Flight results fetched.")],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


async def hotel_agent(state: TravelState):
    query = f"Best hotels for {state['user_query']}"
    hotel_result = await get_mcp_tavily_search(query)
    return {
        "hotel_result": _format_hotel_results(hotel_result),
        "messages": [AIMessage(content="Hotel information Fetched.")],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


async def itinerary_agent(state: TravelState):
    prompt = f"""create a complete travel itinerary.
user query: {state.get('user_query')}
Flight Results: {state.get('flight_result')}
Hotel Results: {state.get('hotel_result')}
Make the itinerary practical, budget aware and easy to follow."""
    response = await asyncio.to_thread(
        llm.invoke,
        [SystemMessage(content="you are an expert travel planner"), HumanMessage(content=prompt)]
    )
    clean_response = _clean_model_output(response.content)
    return {
        "itinerary": clean_response,
        "messages": [AIMessage(content=clean_response)],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


async def final_agent(state: TravelState):
    final_prompt = f"""generate the final response for the user
user Request: {state.get('user_query')}
Flights: {state.get('flight_result')}
Hotels: {state.get('hotel_result')}
Itinerary: {state.get('itinerary')}

Format beautifully: 1. Trip Summary 2. Flight Information 3. Hotel suggestions 4. Day by Day Itinerary 5. Estimated Budget 6. Final Recommendations

Be clear, practical, and useful for real travel planning."""
    response = await asyncio.to_thread(
        llm.invoke,
        [SystemMessage(content="You are an expert assistant composing a clear final reply."), HumanMessage(content=final_prompt)]
    )
    clean_response = _clean_model_output(response.content)
    return {
        "final_response": clean_response,
        "messages": [AIMessage(content=clean_response)],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


graph = StateGraph(TravelState)
graph.add_node("flight", flight_agent)
graph.add_node("hotel", hotel_agent)
graph.add_node("Itinerary", itinerary_agent)
graph.add_node("final", final_agent)
graph.add_edge(START, "flight")
graph.add_edge("flight", "hotel")
graph.add_edge("hotel", "Itinerary")
graph.add_edge("Itinerary", "final")
graph.add_edge("final", END)

DATABASE_URL = _resolve_db_host(get_database_url())

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

_cp = None
_cp_conn = None


async def _get_checkpointer():
    global _cp, _cp_conn
    if _cp is not None:
        return _cp
    _cp_conn = await psycopg.AsyncConnection.connect(
        DATABASE_URL, autocommit=True, row_factory=dict_row
    )
    _cp = AsyncPostgresSaver(_cp_conn)
    await _cp.setup()
    return _cp


async def run_travel(user_input, thread_id=None):
    if not thread_id:
        thread_id = f"user{uuid.uuid4().hex}"
    cp = await _get_checkpointer()
    compiled = graph.compile(checkpointer=cp)
    result = await compiled.ainvoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "flight_result": "",
            "hotel_result": "",
            "itinerary": "",
            "llm_calls": 0
        },
        config={"configurable": {"thread_id": thread_id}}
    )
    return {
        "thread_id": thread_id,
        "answer": result["messages"][-1].content,
        "flight_result": result.get("flight_result", ""),
        "hotel_result": result.get("hotel_result", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0)
    }
