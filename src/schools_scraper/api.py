"""FastAPI web server for the schools scraper frontend."""

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from schools_scraper.gpt import GPTClient

app = FastAPI(title="Schools Scraper API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class QuestionRequest(BaseModel):
    """Request model for asking questions."""

    question: str
    mat_id: str = "west"
    max_newsletters: int = 20
    max_chars: int = 10000


class QuestionResponse(BaseModel):
    """Response model for questions."""

    answer: str
    question: str
    sources: Optional[List[Dict[str, str]]] = None


class MAT(BaseModel):
    """Multi-Academy Trust model."""

    id: str
    name: str
    logo_url: Optional[str] = None


# MAT data (currently just WeST)
MATS = [
    MAT(
        id="west",
        name="Westcountry Schools Trust",
        logo_url="/static/logos/default-logo.svg",  # Placeholder - you can add actual logo
    )
]


@app.get("/api/mats", response_model=List[MAT])
async def list_mats() -> List[MAT]:
    """List all Multi-Academy Trusts."""
    return MATS


@app.get("/api/mats/{mat_id}", response_model=MAT)
async def get_mat(mat_id: str) -> MAT:
    """Get a specific MAT by ID."""
    mat = next((m for m in MATS if m.id == mat_id), None)
    if not mat:
        raise HTTPException(status_code=404, detail="MAT not found")
    return mat


@app.post("/api/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest) -> QuestionResponse:
    """Ask a question about a MAT's newsletters."""
    try:
        client = GPTClient()
        answer, sources = client.answer_question(
            question=request.question,
            table_name="newsletters",
            model="gpt-4o-mini",
            max_newsletters=request.max_newsletters,
            max_chars=request.max_chars,
        )
        return QuestionResponse(question=request.question, answer=answer, sources=sources)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


# Serve static files (frontend)
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
static_dir = frontend_dir / "static"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML."""
    frontend_file = frontend_dir / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

