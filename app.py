import uvicorn
from fastapi import FastAPI, Request,HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from Backend import run_travel

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

#define API

app = FastAPI(
    title = "TravelAgent",
    description="Langgraph Multi-Agent Travel Planner with Fast API",
    version="1.0.0"
)

#mount static files

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR/"static")),
    name="static"
)

#templates

templates = Jinja2Templates(
    directory=str(BASE_DIR/"templates")
)


class TravelRequest(BaseModel):
    user_query: str
    thread_id: str | None = None
    
#default route
@app.get("/", response_class=HTMLResponse)
async def home (request:Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )



@app.post("/api/travel")
async def travel(request: TravelRequest):

    try:

        # Validate user input
        user_input = request.user_query.strip()

        if not user_input:
            raise HTTPException(
                status_code=400,
                detail="Travel query cannot be empty."
            )

        # Call your LangGraph wrapper
        result = await run_travel(
            user_input=user_input,
            thread_id=request.thread_id
        )

        # Return result to frontend
        return {
            "success": True,
            "thread_id": result["thread_id"],
            "answer": result["answer"],
            "flight_result": result.get(
                "flight_result",
                ""
            ),
            "hotel_result": result.get(
                "hotel_result",
                ""
            ),
            "itinerary": result.get(
                "itinerary",
                ""
            ),
            "llm_calls": result.get(
                "llm_calls",
                0
            )
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            f"Travel API Error: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Travel planning failed: {str(e)}"
        )
    
@app.get("/health")
async def health_check():
    return{"status": "200ok", "message":"AI Travel agent is running"}

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})
    
if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )