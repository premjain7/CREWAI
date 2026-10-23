"""FastAPI web application unifying 10 CrewAI projects into a deployable website."""

import asyncio
import os
from pathlib import Path
from typing import List, Optional

from fastapi import (
    FastAPI,
    Request,
    UploadFile,
    File,
    Form,
    HTTPException,
    status,
)
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from services.file_storage import FileStorageService
from services.workflow_store import WorkflowStore
from agents.blog_post import run_blog_post
from agents.competitor_analysis import run_competitor_analysis
from agents.meeting_notes import run_meeting_notes
from agents.data_report import run_data_report
from agents.customer_support import run_customer_support
from agents.resume_screening import run_resume_screening
from agents.bug_triage import run_bug_triage
from agents.content_repurposing import run_content_repurposing
from agents.lead_qualification import run_lead_qualification
from agents.approval_report import (
    start_approval_report,
    submit_review_decision,
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="CrewAI Multi-Agent Suite",
    description="Unified web dashboard for 10 audited CrewAI and Flow projects.",
    version="1.0.0",
)

# Mount static files
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class BlogPostRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300, description="Topic for the blog post")


class CompetitorAnalysisRequest(BaseModel):
    competitors: List[str] = Field(..., min_length=3, max_length=3, description="3 competitor website URLs")


class MeetingNotesRequest(BaseModel):
    transcript: str = Field(..., min_length=10, description="Meeting transcript text")


class CustomerSupportRequest(BaseModel):
    ticket_text: str = Field(..., min_length=3, description="Customer support issue description")


class BugTriageRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Bug title")
    body: str = Field(..., min_length=10, description="Detailed bug description")


class ContentRepurposingRequest(BaseModel):
    source: str = Field(..., min_length=10, description="Article text or website URL")


class LeadQualificationRequest(BaseModel):
    lead_name: str = Field(..., min_length=2, max_length=200, description="Company or lead name")
    website: str = Field(..., min_length=5, description="Complete website URL (https://...)")


class ApprovalStartRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200, description="Report topic")
    audience: Optional[str] = Field("General audience", max_length=150, description="Target audience")


class ApprovalReviewRequest(BaseModel):
    decision: str = Field(..., description="Decision: 'approve', 'revise', or 'reject'")
    feedback: Optional[str] = Field(None, description="Revision feedback (required if decision is 'revise')")


# ---------------------------------------------------------
# Core Web Routes
# ---------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Renders the main unified dashboard."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health_check():
    """Lightweight health check endpoint. Does NOT invoke LLMs."""
    return {"status": "ok", "app": "CrewAI Multi-Agent Suite", "version": "1.0.0"}


@app.get("/download/{run_id}/{filename}")
async def download_file(run_id: str, filename: str):
    """Secure, path-traversal protected download endpoint."""
    file_path = FileStorageService.get_file_path(run_id, filename)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file not found or invalid path.",
        )
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


# ---------------------------------------------------------
# Agent Endpoints
# ---------------------------------------------------------

# --- Agent 1: Blog Post Crew ---
@app.post("/agent1")
@app.post("/api/agent1")
async def api_blog_post(payload: BlogPostRequest):
    try:
        result = await run_blog_post(payload.topic)
        return {"success": True, "agent": 1, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Blog Post generation failed: {exc}")


# --- Agent 2: Competitor Analysis Crew ---
@app.post("/agent2")
@app.post("/api/agent2")
async def api_competitor_analysis(payload: CompetitorAnalysisRequest):
    try:
        result = await run_competitor_analysis(payload.competitors)
        return {"success": True, "agent": 2, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Competitor Analysis failed: {exc}")


# --- Agent 3: Meeting Notes Crew ---
@app.post("/agent3")
@app.post("/api/agent3")
async def api_meeting_notes(
    transcript_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    try:
        transcript = ""
        if file and file.filename:
            if not file.filename.lower().endswith(".txt"):
                raise ValueError("Meeting transcript upload must be a .txt file.")
            content = await file.read()
            transcript = content.decode("utf-8", errors="replace").strip()
        elif transcript_text:
            transcript = transcript_text.strip()

        if not transcript:
            raise ValueError("Please provide a meeting transcript as text or upload a .txt file.")

        result = await run_meeting_notes(transcript)
        return {"success": True, "agent": 3, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Meeting Notes generation failed: {exc}")


# --- Agent 4: Data Report Crew ---
@app.post("/agent4")
@app.post("/api/agent4")
async def api_data_report(file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise ValueError("Data Report Crew requires a valid .csv file upload.")

        content = await file.read()
        if not content:
            raise ValueError("Uploaded CSV file is empty.")

        result = await run_data_report(content)
        return {"success": True, "agent": 4, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Data Report analysis failed: {exc}")


# --- Agent 5: Customer Support Flow ---
@app.post("/agent5")
@app.post("/api/agent5")
async def api_customer_support(payload: CustomerSupportRequest):
    try:
        result = await asyncio.to_thread(run_customer_support, payload.ticket_text)
        return {"success": True, "agent": 5, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Customer Support classification failed: {exc}")


# --- Agent 6: Resume Screening Flow ---
@app.post("/agent6")
@app.post("/api/agent6")
async def api_resume_screening(files: List[UploadFile] = File(...)):
    try:
        if not files:
            raise ValueError("Please upload at least one PDF resume.")

        file_payloads = []
        for f in files:
            if f.filename and f.filename.lower().endswith(".pdf"):
                bytes_data = await f.read()
                file_payloads.append((f.filename, bytes_data))

        if not file_payloads:
            raise ValueError("No valid .pdf files found in upload.")

        result = await run_resume_screening(file_payloads)
        return {"success": True, "agent": 6, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Resume Screening failed: {exc}")


# --- Agent 7: Bug Triage Flow ---
@app.post("/agent7")
@app.post("/api/agent7")
async def api_bug_triage(payload: BugTriageRequest):
    try:
        result = await run_bug_triage(payload.title, payload.body)
        return {"success": True, "agent": 7, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Bug Triage failed: {exc}")


# --- Agent 8: Content Repurposing Flow ---
@app.post("/agent8")
@app.post("/api/agent8")
async def api_content_repurposing(
    source_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    try:
        source = ""
        if file and file.filename:
            if not file.filename.lower().endswith(".txt"):
                raise ValueError("Article file upload must be a .txt file.")
            content = await file.read()
            source = content.decode("utf-8", errors="replace").strip()
        elif source_text:
            source = source_text.strip()

        if not source:
            raise ValueError("Please provide article text, an uploaded .txt file, or a URL.")

        result = await run_content_repurposing(source)
        return {"success": True, "agent": 8, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Content Repurposing failed: {exc}")


# --- Agent 9: Lead Qualification Flow ---
@app.post("/agent9")
@app.post("/api/agent9")
async def api_lead_qualification(payload: LeadQualificationRequest):
    try:
        result = await run_lead_qualification(payload.lead_name, payload.website)
        return {"success": True, "agent": 9, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lead Qualification failed: {exc}")


# --- Agent 10: Approval Report Flow (Multi-Step) ---
@app.post("/agent10")
@app.post("/api/agent10")
@app.post("/agent10/start")
@app.post("/api/agent10/start")
async def api_approval_start(payload: ApprovalStartRequest):
    try:
        result = await start_approval_report(payload.topic, payload.audience or "General audience")
        return {"success": True, "agent": 10, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Approval report start failed: {exc}")


@app.post("/agent10/{session_id}/review")
@app.post("/api/agent10/{session_id}/review")
async def api_approval_review(session_id: str, payload: ApprovalReviewRequest):
    try:
        result = await submit_review_decision(session_id, payload.decision, payload.feedback)
        return {"success": True, "agent": 10, "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Approval review decision failed: {exc}")


@app.get("/agent10/{session_id}")
@app.get("/api/agent10/{session_id}")
async def api_approval_status(session_id: str):
    session = WorkflowStore.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found.")
    return {"success": True, "agent": 10, "data": session}
