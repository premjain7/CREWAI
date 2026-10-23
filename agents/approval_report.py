"""Agent 10: Approval Report Flow.

Preserved from Project_10_Approval_Report_Flow.ipynb.
Multi-step stateful human-in-the-loop workflow.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from crewai import Agent, Task, Crew, Process
from ddgs import DDGS

from services.gemini import get_llm
from services.file_storage import BASE_OUTPUT_DIR, FileStorageService
from services.workflow_store import WorkflowStore


def web_search_ddg(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo for public web pages."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return "\n\n".join(
            f"Title: {item.get('title', '')}\n"
            f"URL: {item.get('href', '')}\n"
            f"Snippet: {item.get('body', '')}"
            for item in results
        ) or "No search results found."
    except Exception as exc:
        return f"Search unavailable: {exc}"


async def run_crew_helper(
    role: str,
    goal: str,
    backstory: str,
    task_description: str,
    expected_output: str,
) -> str:
    """Executes a single-agent crew step asynchronously.

    Runs the synchronous crew.kickoff() in a thread pool so it does not
    block the asyncio event loop when called from async FastAPI handlers.
    """
    def _run_sync() -> str:
        llm = get_llm(temperature=0.4)
        agent = Agent(
            role=role,
            goal=goal,
            backstory=backstory,
            llm=llm,
            verbose=False,
        )
        task = Task(
            description=task_description,
            expected_output=expected_output,
            agent=agent,
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
        return str(crew.kickoff()).strip()

    return await asyncio.to_thread(_run_sync)


# Backward compatibility alias
run_crew_step = run_crew_helper


async def start_approval_report(topic: str, audience: str = "General audience") -> Dict[str, Any]:
    """Step 1: Performs research and generates the initial report draft for human review."""
    clean_topic = topic.strip()
    clean_audience = audience.strip() or "General audience"

    if not clean_topic:
        raise ValueError("The report topic cannot be empty.")

    session_id, session_dir = FileStorageService.create_run_dir("approval")

    # 1. Web research
    search_results = web_search_ddg(
        f"{clean_topic} key facts recent developments",
        max_results=5,
    )
    if not search_results.strip() or "No search results found" in search_results:
        search_results = "No usable search results were found. Clearly identify information gaps."

    research_task_desc = f"""
Research the following topic for a report.

Topic: {clean_topic}
Target audience: {clean_audience}

Available web search results:
{search_results}

Instructions:
- Summarize the most relevant findings.
- Identify important facts, trends, and implications.
- Use only information supported by the supplied results.
- Include relevant source URLs where available.
- Clearly identify gaps instead of inventing facts.
"""
    research = await run_crew_helper(
        role="Research Analyst",
        goal="Prepare an evidence-based research brief.",
        backstory="You carefully analyze information and distinguish evidence from uncertainty.",
        task_description=research_task_desc,
        expected_output="A concise research brief with findings and source URLs.",
    )

    # 2. Draft report
    draft_task_desc = f"""
Write a professional Markdown report using the research below.

Topic: {clean_topic}
Audience: {clean_audience}

Research:
{research}

Include:
1. Title
2. Executive summary
3. Introduction and background
4. Main findings with clear headings
5. Analysis and implications
6. Recommendations or conclusion
7. References with URLs from the research, when available

Requirements:
- Write clearly for the specified audience.
- Do not fabricate statistics, quotations, or references.
- Distinguish verified findings from uncertain information.
- Return the report itself in Markdown.
"""
    draft = await run_crew_helper(
        role="Report Writer",
        goal="Produce a clear, accurate, review-ready report.",
        backstory="You are a professional writer who creates structured, evidence-based reports.",
        task_description=draft_task_desc,
        expected_output="A complete Markdown report ready for human review.",
    )

    # Save initial draft to session directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_path = session_dir / f"draft_{timestamp}.md"
    draft_path.write_text(draft, encoding="utf-8")

    # Store state
    session_data = WorkflowStore.create_session(
        session_id=session_id,
        topic=clean_topic,
        audience=clean_audience,
        research=research,
        draft=draft,
        max_revisions=2,
    )

    return {
        "session_id": session_id,
        "topic": clean_topic,
        "audience": clean_audience,
        "draft": draft,
        "revision_count": 0,
        "max_revisions": 2,
        "status": "pending_review",
        "message": "Report draft generated. Please review and approve, revise, or reject.",
    }


async def submit_review_decision(
    session_id: str, decision: str, feedback: Optional[str] = None
) -> Dict[str, Any]:
    """Step 2: Handles human decision ('approve', 'revise', or 'reject'). Enforces 2-revision limit."""
    session = WorkflowStore.get_session(session_id)
    if not session:
        raise ValueError(f"Approval session '{session_id}' not found or expired.")

    clean_decision = decision.strip().lower()
    if clean_decision in ("approve", "approved", "a"):
        clean_decision = "approved"
    elif clean_decision in ("reject", "rejected", "r"):
        clean_decision = "rejected"
    elif clean_decision in ("revise", "revision", "v"):
        clean_decision = "revise"
    else:
        raise ValueError("Invalid choice. Decision must be 'approve', 'revise', or 'reject'.")

    run_dir = FileStorageService.get_run_dir(session_id)
    if not run_dir:
        run_dir = BASE_OUTPUT_DIR / session_id
        run_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. APPROVE
    if clean_decision == "approved":
        final_filename = f"final_report_{timestamp}.md"
        final_path = run_dir / final_filename
        final_path.write_text(session["draft"], encoding="utf-8")

        audit_filename = f"approval_record_{timestamp}.json"
        audit_path = run_dir / audit_filename
        audit_data = {
            "topic": session["topic"],
            "audience": session["audience"],
            "decision": "approved",
            "status": "approved",
            "revision_count": session["revision_count"],
            "final_report_file": final_filename,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        audit_path.write_text(json.dumps(audit_data, indent=2, ensure_ascii=False), encoding="utf-8")

        WorkflowStore.update_session(
            session_id,
            {
                "decision": "approved",
                "status": "approved",
                "final_path": final_filename,
                "audit_record_path": audit_filename,
            },
        )

        return {
            "session_id": session_id,
            "status": "approved",
            "decision": "approved",
            "revision_count": session["revision_count"],
            "draft": session["draft"],
            "final_report_filename": final_filename,
            "download_url": f"/download/{session_id}/{final_filename}",
            "audit_download_url": f"/download/{session_id}/{audit_filename}",
            "message": "Report successfully approved and published.",
        }

    # 2. REVISE
    elif clean_decision == "revise":
        current_rev = session["revision_count"]
        max_rev = session["max_revisions"]

        if current_rev >= max_rev:
            # Maximum revisions exceeded -> automatic rejection as required
            rejection_filename = f"rejection_record_{timestamp}.json"
            audit_path = run_dir / rejection_filename
            audit_data = {
                "topic": session["topic"],
                "audience": session["audience"],
                "decision": "rejected",
                "status": "rejected",
                "feedback": "Maximum revision limit reached (2/2).",
                "revision_count": current_rev,
                "final_report_saved": False,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }
            audit_path.write_text(json.dumps(audit_data, indent=2, ensure_ascii=False), encoding="utf-8")

            WorkflowStore.update_session(
                session_id,
                {
                    "decision": "rejected",
                    "status": "rejected",
                    "feedback": "Maximum revision limit reached (2/2).",
                    "audit_record_path": rejection_filename,
                },
            )

            return {
                "session_id": session_id,
                "status": "rejected",
                "decision": "rejected",
                "revision_count": current_rev,
                "message": "Maximum revision limit (2) reached. Report rejected.",
                "audit_download_url": f"/download/{session_id}/{rejection_filename}",
            }

        clean_feedback = (feedback or "").strip()
        if not clean_feedback:
            raise ValueError("Please provide specific revision feedback explaining what changes are required.")

        new_rev_count = current_rev + 1

        revision_task_desc = f"""
Revise the report using the reviewer's feedback.

Topic: {session['topic']}
Audience: {session['audience']}

Original report:
{session['draft']}

Research brief:
{session['research']}

Reviewer feedback:
{clean_feedback}

Preserve accurate content and relevant source URLs.
Apply the feedback carefully. Do not invent facts or citations.
Return the complete revised report in Markdown.
"""
        revised_draft = await run_crew_helper(
            role="Report Editor",
            goal="Improve the report according to human feedback.",
            backstory="You are a meticulous editor who preserves factual accuracy.",
            task_description=revision_task_desc,
            expected_output="The complete revised Markdown report.",
        )

        rev_filename = f"revision_{new_rev_count}.md"
        rev_path = run_dir / rev_filename
        rev_path.write_text(revised_draft, encoding="utf-8")

        WorkflowStore.update_session(
            session_id,
            {
                "draft": revised_draft,
                "revision_count": new_rev_count,
                "feedback": clean_feedback,
                "status": "pending_review",
            },
        )

        return {
            "session_id": session_id,
            "status": "pending_review",
            "decision": "revised",
            "revision_count": new_rev_count,
            "max_revisions": max_rev,
            "draft": revised_draft,
            "message": f"Revision {new_rev_count}/{max_rev} completed. Please review the updated draft.",
        }

    # 3. REJECT
    else:
        rejection_filename = f"rejection_record_{timestamp}.json"
        audit_path = run_dir / rejection_filename
        clean_feedback = (feedback or "").strip() or "Rejected by reviewer."

        audit_data = {
            "topic": session["topic"],
            "audience": session["audience"],
            "decision": "rejected",
            "status": "rejected",
            "feedback": clean_feedback,
            "revision_count": session["revision_count"],
            "final_report_saved": False,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        audit_path.write_text(json.dumps(audit_data, indent=2, ensure_ascii=False), encoding="utf-8")

        WorkflowStore.update_session(
            session_id,
            {
                "decision": "rejected",
                "status": "rejected",
                "feedback": clean_feedback,
                "audit_record_path": rejection_filename,
            },
        )

        return {
            "session_id": session_id,
            "status": "rejected",
            "decision": "rejected",
            "revision_count": session["revision_count"],
            "message": "Report rejected. Rejected reports are never published.",
            "audit_download_url": f"/download/{session_id}/{rejection_filename}",
        }
