"""Agent 6: Resume Screening Flow.

Preserved from Project_6_Resume_Screening_Flow.ipynb.
"""

import asyncio
import json
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any, Tuple

import pandas as pd
from pydantic import BaseModel, Field
from pypdf import PdfReader
from crewai import Agent, Task, Crew
from crewai.flow.flow import Flow, start, listen, router

from services.gemini import get_llm
from services.file_storage import FileStorageService

HIGH_SCORE_THRESHOLD = 7


class ResumeScreeningState(BaseModel):
    resumes: List[Dict[str, Any]] = Field(default_factory=list)
    current_resume: Dict[str, Any] = Field(default_factory=dict)
    score: Any = 0
    explanation: str = ""
    status: str = ""
    results: List[Dict[str, Any]] = Field(default_factory=list)


class ResumeScreeningFlow(Flow[ResumeScreeningState]):
    """Event-driven resume screening flow scoring against evidence without job descriptions."""

    def __init__(self, initial_resumes: List[Dict[str, str]], run_dir: Path):
        super().__init__()
        self.initial_resumes = initial_resumes
        self.run_dir = run_dir

    @start()
    def load_resumes(self):
        self.state.resumes = self.initial_resumes
        self.state.results = []
        if not self.state.resumes:
            raise ValueError("No readable PDF resumes were provided.")
        return "resumes_loaded"

    @listen(load_resumes)
    def score_resumes(self, _):
        llm = get_llm(temperature=0.1)

        for resume in self.state.resumes:
            prompt = f"""
Evaluate the overall quality of this resume on a scale from 0 to 10.

Consider:
- Clarity and organization
- Demonstrated skills
- Projects and practical experience
- Education and relevant achievements
- Evidence of technical or professional ability

Do not use or assume any job description.
Use only evidence present in the resume.

RESUME:
{resume['text']}

Return ONLY valid JSON:
{{
  "score": 0,
  "explanation": "Brief evidence-based explanation",
  "strengths": ["strength 1", "strength 2"],
  "areas_to_improve": ["area 1", "area 2"]
}}

The score must be an integer between 0 and 10.
"""
            try:
                raw = str(llm.call(prompt)).strip()
                raw = raw.replace("```json", "").replace("```", "").strip()
                data = json.loads(raw)

                score = int(data["score"])
                if not 0 <= score <= 10:
                    raise ValueError("Score must be between 0 and 10.")

                explanation = str(data["explanation"])
                strengths = data.get("strengths", [])
                areas_to_improve = data.get("areas_to_improve", [])
            except Exception as e:
                score = None
                explanation = f"Scoring failed; manual review required. Details: {e}"
                strengths = []
                areas_to_improve = []

            result = {
                "name": resume["name"],
                "score": score,
                "explanation": explanation,
                "strengths": strengths,
                "areas_to_improve": areas_to_improve,
                "resume_text": resume["text"],
                "status": "Pending routing",
                "summary": "",
                "rejection_email": "",
            }
            self.state.results.append(result)

        return "scoring_completed"

    @router(score_resumes)
    def check_score(self):
        pending = next(
            (r for r in self.state.results if r["status"] == "Pending routing"),
            None,
        )
        if pending is None:
            return "all_processed"

        self.state.current_resume = pending
        self.state.score = pending["score"]
        self.state.explanation = pending["explanation"]

        if self.state.score is None:
            pending["status"] = "Manual review required"
            return "manual_review"

        if self.state.score >= HIGH_SCORE_THRESHOLD:
            return "shortlist"

        return "reject"

    @listen(check_score)
    def process_shortlist(self, route):
        if route != "shortlist":
            return

        result = self.state.current_resume
        llm = get_llm(temperature=0.1)

        summary_agent = Agent(
            role="Resume Summary Assistant",
            goal="Summarize resume strengths and areas for improvement",
            backstory=(
                "You prepare concise, evidence-based resume summaries "
                "to help people review candidate qualifications."
            ),
            llm=llm,
            verbose=False,
        )

        summary_task = Task(
            description=f"""
Prepare a concise summary of this resume.

RESUME:
{result['resume_text']}

SCREENING SCORE: {result['score']}/10
INITIAL ASSESSMENT: {result['explanation']}

Include:
1. Key skills demonstrated
2. Projects and experience
3. Strengths supported by resume evidence
4. Gaps, missing details, or areas to improve

Do not invent qualifications or make unsupported claims.
""",
            expected_output=(
                "A concise summary covering skills, projects, strengths, and areas to improve."
            ),
            agent=summary_agent,
        )

        summary_crew = Crew(agents=[summary_agent], tasks=[summary_task], verbose=False)
        result["summary"] = str(summary_crew.kickoff()).strip()
        result["status"] = "Shortlisted for further review"

    @listen(check_score)
    def process_reject(self, route):
        if route != "reject":
            return

        result = self.state.current_resume
        llm = get_llm(temperature=0.1)

        prompt = f"""
Draft a polite, professional rejection email following an initial resume screening.

RESUME NAME: {result['name']}
SCREENING SCORE: {result['score']}/10
INITIAL ASSESSMENT: {result['explanation']}

Requirements:
- Use a respectful and professional tone.
- Do not disclose an internal score.
- Do not make unsupported claims about the candidate.
- Keep the message concise.
- Do not invent a company name, role, or recruiter's name.
- Return the email subject and body.
"""
        result["rejection_email"] = str(llm.call(prompt)).strip()
        result["status"] = "Rejection email drafted"

    @listen(check_score)
    def process_manual_review(self, route):
        if route != "manual_review":
            return
        result = self.state.current_resume
        result["status"] = "Manual review required"

    @listen(process_shortlist)
    def continue_after_shortlist(self, _):
        return "resume_processed"

    @listen(process_reject)
    def continue_after_reject(self, _):
        return "resume_processed"

    @listen(process_manual_review)
    def continue_after_manual_review(self, _):
        return "resume_processed"

    @listen(continue_after_shortlist)
    def save_after_shortlist(self, _):
        self.save_results()

    @listen(continue_after_reject)
    def save_after_reject(self, _):
        self.save_results()

    @listen(continue_after_manual_review)
    def save_after_manual_review(self, _):
        self.save_results()

    def save_results(self):
        rows = []
        for result in self.state.results:
            rows.append({
                "Resume": result["name"],
                "Score": result["score"] if result["score"] is not None else "",
                "Decision": result["status"],
                "Explanation": result["explanation"],
                "Strengths": "; ".join(str(x) for x in result.get("strengths", [])),
                "Areas to Improve": "; ".join(str(x) for x in result.get("areas_to_improve", [])),
                "Summary": result.get("summary", ""),
                "Rejection Email": result.get("rejection_email", ""),
            })

        out_csv = self.run_dir / "results.csv"
        pd.DataFrame(rows).to_csv(out_csv, index=False)


def extract_text_from_pdf(pdf_bytes: bytes, filename: str = "resume.pdf") -> str:
    """Extracts text from a single PDF byte stream."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(pages_text).strip()
        if not full_text:
            raise ValueError(f"No extractable text found in {filename}.")
        return full_text
    except Exception as e:
        raise ValueError(f"Could not parse PDF '{filename}': {e}")


async def run_resume_screening(files: List[Tuple[str, bytes]]) -> Dict[str, Any]:
    """Processes uploaded PDF resumes, runs scoring flow, and outputs results.csv."""
    if not files:
        raise ValueError("Please upload at least one PDF resume.")

    loaded_resumes = []
    for filename, content in files:
        if not filename.lower().endswith(".pdf"):
            continue
        try:
            text = extract_text_from_pdf(content, filename)
            loaded_resumes.append({"name": filename, "text": text})
        except Exception:
            continue

    if not loaded_resumes:
        raise ValueError("No valid or readable PDF resumes could be extracted.")

    run_id, run_dir = FileStorageService.create_run_dir("resume")

    # Run flow in a thread pool to avoid blocking the asyncio event loop.
    # CrewAI Flows only support synchronous kickoff().
    flow = ResumeScreeningFlow(initial_resumes=loaded_resumes, run_dir=run_dir)
    await asyncio.to_thread(flow.kickoff)
    # Ensure results are persisted (save_results is also called by flow listeners)
    flow.save_results()

    results_data = []
    for r in flow.state.results:
        results_data.append({
            "name": r["name"],
            "score": r["score"],
            "decision": r["status"],
            "explanation": r["explanation"],
            "strengths": r.get("strengths", []),
            "areas_to_improve": r.get("areas_to_improve", []),
            "summary": r.get("summary", ""),
            "rejection_email": r.get("rejection_email", ""),
        })

    return {
        "run_id": run_id,
        "results": results_data,
        "total_screened": len(results_data),
        "advisory_notice": (
            "Automated resume scores are advisory screening aids only and require "
            "independent human review. Rejection emails are drafts for human consideration "
            "and are never sent automatically."
        ),
        "filename": "results.csv",
        "download_url": f"/download/{run_id}/results.csv",
    }
