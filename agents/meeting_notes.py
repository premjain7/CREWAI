"""Agent 3: Meeting Notes Crew.

Preserved from Project_3_Meeting_Notes_Crew.ipynb.
"""

from pathlib import Path
from typing import Dict, Any

from crewai import Agent, Task, Crew, Process

from services.gemini import get_llm
from services.file_storage import FileStorageService


def create_meeting_notes_crew(output_file_path: Path):
    """Instantiates the Meeting Notes Crew with parallel subtasks and final formatting."""
    llm = get_llm(temperature=0.2)

    summarizer = Agent(
        role="Meeting Summarizer",
        goal="Summarize the meeting transcript in exactly five concise bullet points.",
        backstory="You are skilled at extracting the most important discussion points from meetings.",
        llm=llm,
        verbose=False,
    )

    action_finder = Agent(
        role="Action Item Extractor",
        goal="Identify all action items, responsible people, and deadlines from the transcript.",
        backstory="You carefully track commitments and never invent missing owners or deadlines.",
        llm=llm,
        verbose=False,
    )

    decision_logger = Agent(
        role="Decision Logger",
        goal="Identify the decisions explicitly made during the meeting.",
        backstory="You maintain accurate decision records and distinguish confirmed decisions from suggestions.",
        llm=llm,
        verbose=False,
    )

    formatter = Agent(
        role="Meeting Notes Formatter",
        goal="Combine the meeting summary, action items, and decisions into a clear Markdown report.",
        backstory="You create accurate, professional meeting minutes that are easy to read and act upon.",
        llm=llm,
        verbose=False,
    )

    summary_task = Task(
        description="""
Read the following meeting transcript:

{transcript}

Summarize the main discussion in exactly five concise bullet points.
Include important dates, project goals, and key updates.
Do not add information that is not in the transcript.
        """,
        expected_output="Exactly five concise bullet points summarizing the meeting.",
        agent=summarizer,
        async_execution=True,
    )

    action_task = Task(
        description="""
Analyze the meeting transcript:

{transcript}

Extract every action item. For each item, identify:
- Task
- Responsible person
- Deadline

If an owner or deadline is not stated, write 'Not specified'.
Do not invent information.
        """,
        expected_output="A structured list of action items, owners, and deadlines.",
        agent=action_finder,
        async_execution=True,
    )

    decision_task = Task(
        description="""
Analyze the meeting transcript:

{transcript}

List the decisions explicitly agreed upon.
Distinguish confirmed decisions from suggestions.
If there are no confirmed decisions, state that clearly.
        """,
        expected_output="A concise list of confirmed meeting decisions.",
        agent=decision_logger,
        async_execution=True,
    )

    format_task = Task(
        description="""
Create complete meeting notes using the outputs from the
previous tasks provided in your task context.

Combine the meeting summary, action items, and decisions into
one clear, professional Markdown report.

Organize the report using these headings:

# Meeting Notes
## Executive Summary
## Key Discussion Points
## Action Items
## Decisions Made
## Upcoming Milestones

Requirements:
- Use a Markdown table for action items.
- Include task, owner, and deadline in the table.
- Preserve all facts and dates from the transcript.
- Do not invent missing information.
- Avoid repeating the same information unnecessarily.
        """,
        expected_output="A complete, well-formatted Markdown meeting notes report.",
        agent=formatter,
        context=[summary_task, action_task, decision_task],
        output_file=str(output_file_path),
    )

    return Crew(
        agents=[summarizer, action_finder, decision_logger, formatter],
        tasks=[summary_task, action_task, decision_task, format_task],
        process=Process.sequential,
        verbose=False,
    )


async def run_meeting_notes(transcript: str) -> Dict[str, Any]:
    """Validates transcript, executes the Meeting Notes Crew, and returns results."""
    clean_transcript = transcript.strip()
    if not clean_transcript:
        raise ValueError("Please provide a valid, non-empty meeting transcript.")

    run_id, run_dir = FileStorageService.create_run_dir("meeting")
    output_path = run_dir / "notes.md"

    crew = create_meeting_notes_crew(output_path)
    crew_output = await crew.kickoff_async(inputs={"transcript": clean_transcript})

    notes_content = str(crew_output).strip()
    if not output_path.exists() or output_path.stat().st_size == 0:
        output_path.write_text(notes_content, encoding="utf-8")
    else:
        notes_content = output_path.read_text(encoding="utf-8")

    return {
        "run_id": run_id,
        "content": notes_content,
        "filename": "notes.md",
        "download_url": f"/download/{run_id}/notes.md",
    }
