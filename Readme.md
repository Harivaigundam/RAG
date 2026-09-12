# VoyageAI — TripAgent

This repository implements a small multi-agent travel planner service (FastAPI + LangGraph) that finds flights, suggests hotels, builds a day-by-day itinerary, and returns a final recommendation assembled by an LLM-driven pipeline.

This README explains how to set up the development environment, run the app locally, and use the API. It also documents configuration (environment variables), common issues, and pointers to the main code.

---

## Quick start (Windows — recommended)

1. Create and activate a virtual environment (PowerShell):

```powershell
python -m venv travel
.\travel\Scripts\Activate.ps1
```

2. Upgrade pip and install Python dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirement.txt
```

3. Create a `.env` file in the project root and set the required keys (example):

```
# .env (DO NOT commit secrets)
GROQ_API_KEY=your_groq_api_key_here
MODEL=llama-3.3-70b-versatile   # example; adjust as needed
AVIATIONSTACK_API_KEY=your_aviationstack_key_here  # optional
DATABASE_URL=postgresql://user:pass@host:port/dbname  # optional for checkpointer
```

4. Run the app locally:

```powershell
# from project root
python app.py
# or use uvicorn directly
uvicorn app:app --reload
```

Open http://127.0.0.1:8000 in your browser.

---

## What the project contains

- `app.py` — FastAPI application exposing a simple frontend and API. Static files are served from `/static` and templates are in `templates/`.
- `Backend.py` — LangGraph workflow that composes the travel pipeline (`flight`, `hotel`, `itinerary`, `final`). The exported helper `run_travel(user_input, thread_id=None)` is used by the API.
- `tools/flight_tool.py` — flight lookup helper (calls Aviationstack by default). May require a plan-capable API key.
- `tools/tavily_tool.py` — wrapper used for hotel searches.
- `templates/index.html`, `static/style.css`, `static/script.js` — frontend UI used for demo and manual testing.
- `requirement.txt` — Python dependencies used by the project.

---

## API

- `GET /` — UI (index page).
- `POST /api/travel` — request travel planning. JSON body:

```json
{
  "user_query": "Plan a 3-day trip to Goa for 2 people...",
  "thread_id": "optional-thread-id"
}
```

Response (success):

```json
{
  "success": true,
  "thread_id": "...",
  "answer": "final LLM answer string",
  "flight_result": { /* flight data or empty */ },
  "hotel_result": { /* hotel data or empty */ },
  "itinerary": "...",
  "llm_calls": 3
}
```

- `GET /health` — simple health check.

Notes: the frontend sends `user_query` in the request body (the Pydantic model in `app.py` expects `user_query`).

---

## Environment variables and config

- `GROQ_API_KEY` (required) — API key for the LLM client used in `Backend.py`.
- `MODEL` (recommended) — model name used by `ChatGroq` in `Backend.py`.
- `AVIATIONSTACK_API_KEY` (optional) — API key for Aviationstack if you want real flight lookups.
- `DATABASE_URL` (optional) — Postgres connection string used by the LangGraph Postgres checkpointer. If not provided, the checkpointer setup may fail — you can mock or disable persistent checkpointing for local experiment.

Keep secrets out of version control. Use a `.env` (and add it to `.gitignore`).

---

## Known issues & troubleshooting

- Static assets 404: The app mounts static files at `/static`. Templates must reference `/static/style.css` and `/static/script.js`. If you see 404s for assets, confirm `static/` exists and the server is started from the project root.

- API payload mismatch: The frontend expects the backend to accept `user_query`; ensure `TravelRequest` in `app.py` defines `user_query: str` (already updated).

- Aviationstack `/v1/flights` 403 (function_access_restricted): Many users encounter a 403 error from Aviationstack for the `/flights` endpoint if the API subscription tier does not include that function. If you hit this:
  - Check your Aviationstack dashboard and subscription plan.
  - Use an alternative data source or mock flights for development. To mock, edit `tools/flight_tool.py` to return a sample dictionary instead of calling the real API.

- Database/checkpointer errors: If `DATABASE_URL` is not set or unreachable, the Postgres checkpointer will fail during `Backend.py` startup. For local development you can:
  - Provide a local Postgres and set `DATABASE_URL` appropriately; or
  - Modify `Backend.py` to bypass or conditionally initialize the checkpointer when no `DATABASE_URL` is provided.

---

## Development notes

- The project uses LangGraph to define a small state graph pipeline. See `Backend.py` for the node implementations: `flight_agent`, `hotel_agent`, `itinerary_agent`, and `final_agent`. Each node receives a `state` dict and returns updated keys. The canonical state keys are `flight_result`, `hotel_result`, `itinerary`, and `llm_calls`.

- The frontend is a simple static single-page UI that POSTs to `/api/travel`. The UI files are in `templates/` and `static/`.

---

## Example local test (curl)

```bash
curl -X POST http://127.0.0.1:8000/api/travel \
  -H "Content-Type: application/json" \
  -d '{"user_query":"Plan a 3-day trip to Goa for 2 people"}'
```

---

## Contributing

1. Fork and create a branch.
2. Add a test or manual verification for your change.
3. Submit a PR describing the change.

If you want me to produce a developer-friendly checklist (e.g., how to run with a local Postgres, or how to replace the flight provider), tell me which option you prefer and I will add it.

---

If you'd like, I can also:
- Add a `.env.example` file with variable names (no secrets). 
- Add a small `mock_flights.py` helper and wire it behind a DEBUG flag for local development.



MCP concepts
1. remote MCP

requirement
langchain-mcp-adapters==0.3.0
nest_asyncio==1.6.0
mcp==1.28.1

url
https://mcp.tavily.com/mcp/?tavilyApiKey=<your-api-key>