"""Agent 7: Bug Triage Flow.

Preserved from Project_7_Bug_Triage_Flow.ipynb.
"""

import json
from pathlib import Path
from typing import Dict, Any

from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew
from crewai.flow.flow import Flow, start, listen, router, or_

from services.gemini import get_llm
from services.file_storage import FileStorageService


class BugTriageState(BaseModel):
    issue_title: str = ""
    issue_body: str = ""
    issue_type: str = "question"
    classification_reason: str = ""
    result: Dict[str, Any] = Field(default_factory=dict)


class BugTriageFlow(Flow[BugTriageState]):
    """Event-driven bug triage flow routing between Bug, Feature, and Question specialist crews."""

    def __init__(self, title: str, body: str, run_dir: Path):
        super().__init__()
        self.initial_title = title
        self.initial_body = body
        self.run_dir = run_dir

    @start()
    def read_issue(self):
        self.state.issue_title = self.initial_title.strip()
        self.state.issue_body = self.initial_body.strip()
        return "issue_loaded"

    @listen(read_issue)
    def classify_issue(self, _):
        llm = get_llm(temperature=0.1)

        prompt = f"""
Classify the following software issue into exactly one category:
bug, feature, or question.

Title:
{self.state.issue_title}

Body:
{self.state.issue_body}

Rules:
- bug: existing behavior is broken, incorrect, or crashes.
- feature: requests new or enhanced functionality.
- question: asks for information or help without reporting
  a software defect or requesting a feature.

Return ONLY valid JSON:
{{
  "issue_type": "bug",
  "reason": "Brief explanation"
}}
"""
        response = llm.call(prompt)

        try:
            raw = str(response).strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            issue_type = str(data["issue_type"]).lower().strip()

            if issue_type not in {"bug", "feature", "question"}:
                raise ValueError("Invalid issue category")

            self.state.issue_type = issue_type
            self.state.classification_reason = str(data["reason"])
        except Exception:
            self.state.issue_type = "question"
            self.state.classification_reason = (
                "Classification could not be parsed; manual review is required."
            )

        return self.state.issue_type

    @router(classify_issue)
    def route_type(self):
        category = self.state.issue_type
        if category == "bug":
            return "bug"
        elif category == "feature":
            return "feature"
        return "question"

    @listen("bug")
    def bug_crew(self):
        llm = get_llm(temperature=0.1)
        agent = Agent(
            role="Bug Triage Specialist",
            goal="Analyze bugs and suggest reproduction steps",
            backstory=(
                "You help software teams understand defects, "
                "severity, and steps to reproduce them."
            ),
            llm=llm,
            verbose=False,
        )

        task = Task(
            description=f"""
Analyze this reported bug.

Title: {self.state.issue_title}
Body: {self.state.issue_body}

Classification reason: {self.state.classification_reason}

Provide:
1. Suggested severity: low, medium, high, or critical
2. Steps to reproduce based on the supplied information
3. Expected versus actual behavior
4. Missing information that needs verification

Do not invent technical details.
""",
            expected_output="A structured bug triage report.",
            agent=agent,
        )

        result = str(Crew(agents=[agent], tasks=[task], verbose=False).kickoff()).strip()
        self.state.result = {
            "category": "bug",
            "title": self.state.issue_title,
            "analysis": result,
        }
        return "bug_completed"

    @listen("feature")
    def feature_crew(self):
        llm = get_llm(temperature=0.1)
        agent = Agent(
            role="Product Analyst",
            goal="Convert feature requests into clear user stories",
            backstory=(
                "You help product teams define user needs "
                "and acceptance criteria."
            ),
            llm=llm,
            verbose=False,
        )

        task = Task(
            description=f"""
Turn this feature request into a draft user story.

Title: {self.state.issue_title}
Body: {self.state.issue_body}

Include:
1. User story in the format As a..., I want..., so that...
2. Acceptance criteria
3. Clarifying questions

Do not invent requirements that are not supported by the issue.
""",
            expected_output="A user story with acceptance criteria.",
            agent=agent,
        )

        result = str(Crew(agents=[agent], tasks=[task], verbose=False).kickoff()).strip()
        self.state.result = {
            "category": "feature",
            "title": self.state.issue_title,
            "analysis": result,
        }
        return "feature_completed"

    @listen("question")
    def answer_crew(self):
        llm = get_llm(temperature=0.1)
        agent = Agent(
            role="Issue Support Assistant",
            goal="Draft a helpful response to the reported question",
            backstory=(
                "You help users understand software behavior "
                "without inventing undocumented facts."
            ),
            llm=llm,
            verbose=False,
        )

        task = Task(
            description=f"""
Draft a concise, helpful response to this issue.

Title: {self.state.issue_title}
Body: {self.state.issue_body}

If documentation or technical details are missing, clearly
state what information is needed. Do not invent product facts.
""",
            expected_output="A clear draft support response.",
            agent=agent,
        )

        result = str(Crew(agents=[agent], tasks=[task], verbose=False).kickoff()).strip()
        self.state.result = {
            "category": "question",
            "title": self.state.issue_title,
            "analysis": result,
        }
        return "question_completed"

    @listen(or_(bug_crew, feature_crew, answer_crew))
    def post_reply(self, _):
        self.state.result["classification_reason"] = self.state.classification_reason
        self.state.result["reply_status"] = "Draft ready for human review"

        output_path = self.run_dir / "bug_triage_result.json"
        output_path.write_text(
            json.dumps(self.state.result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(output_path)


async def run_bug_triage(title: str, body: str) -> Dict[str, Any]:
    """Runs BugTriageFlow and returns category, analysis, reason, and JSON output details."""
    clean_title = title.strip()
    clean_body = body.strip()

    if not clean_title or not clean_body:
        raise ValueError("Please provide both an issue title and a detailed description.")

    run_id, run_dir = FileStorageService.create_run_dir("bug_triage")

    flow = BugTriageFlow(title=clean_title, body=clean_body, run_dir=run_dir)
    flow.kickoff()

    return {
        "run_id": run_id,
        "category": flow.state.result.get("category", flow.state.issue_type),
        "title": clean_title,
        "classification_reason": flow.state.classification_reason,
        "analysis": flow.state.result.get("analysis", ""),
        "reply_status": flow.state.result.get("reply_status", "Draft ready for human review"),
        "filename": "bug_triage_result.json",
        "download_url": f"/download/{run_id}/bug_triage_result.json",
    }
