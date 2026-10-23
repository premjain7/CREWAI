"""Agent 9: Lead Qualification Flow.

Preserved from Project_9_Lead_Qualification_Flow.ipynb.
"""

import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from crewai.flow.flow import Flow, start, listen, router, or_
from crewai_tools import ScrapeWebsiteTool

from services.gemini import get_llm
from services.file_storage import FileStorageService


class LeadQualificationState(BaseModel):
    lead_name: str = ""
    website: str = ""
    website_content: str = ""
    enrichment: str = ""
    category: str = ""
    reasoning: str = ""
    action: str = ""
    outreach_email: str = ""
    nurture_tips: List[str] = Field(default_factory=list)
    error: str = ""


def run_crew_helper(
    agent_role: str,
    goal: str,
    backstory: str,
    task_description: str,
    expected_output: str,
) -> str:
    """Helper to run a focused single-agent Crew."""
    llm = get_llm(temperature=0.4)
    agent = Agent(
        role=agent_role,
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


def append_csv_row(csv_path: Path, row: Dict[str, Any], fieldnames: List[str]):
    """Appends a row to a CSV file, avoiding identical duplicate rows."""
    file_exists = csv_path.exists() and csv_path.stat().st_size > 0

    if file_exists:
        try:
            existing_df = pd.read_csv(csv_path)
            # Check for identical lead_name + website
            if not existing_df.empty:
                dup_mask = (
                    (existing_df.get("lead_name") == row.get("lead_name"))
                    & (existing_df.get("website") == row.get("website"))
                )
                if dup_mask.any():
                    # Lead already present in table; update instead of duplicating
                    existing_df.loc[dup_mask, list(row.keys())] = list(row.values())
                    existing_df.to_csv(csv_path, index=False)
                    return
        except Exception:
            pass

    with open(csv_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


class LeadQualificationFlow(Flow[LeadQualificationState]):
    """Event-driven lead qualification, web enrichment, classification, and CSV logging."""

    def __init__(self, lead_name: str, website: str, run_dir: Path):
        super().__init__()
        self.initial_lead_name = lead_name
        self.initial_website = website
        self.run_dir = run_dir

    @start()
    def capture_lead(self):
        self.state.lead_name = self.initial_lead_name.strip()
        self.state.website = self.initial_website.strip()

        if not self.state.lead_name:
            raise ValueError("Lead name cannot be empty.")
        if not self.state.website.startswith(("https://", "http://")):
            raise ValueError("Enter a complete website URL beginning with https:// or http://")

    @listen(capture_lead)
    def enrich_lead(self):
        try:
            clean_url = self.state.website.strip()
            if clean_url.startswith("[") and "](" in clean_url:
                clean_url = clean_url.split("](", 1)[1].rstrip(")")
            self.state.website = clean_url

            scraper = ScrapeWebsiteTool(website_url=clean_url)
            scraped_content = scraper.run()
            self.state.website_content = str(scraped_content)[:10000]

            self.state.enrichment = run_crew_helper(
                agent_role="Lead Research Analyst",
                goal="Summarize the lead using evidence from its website.",
                backstory="You are a careful B2B research analyst. You distinguish facts from assumptions.",
                task_description=f"""
Analyze this prospective lead.

Company/lead name: {self.state.lead_name}
Website: {self.state.website}

Website content:
{self.state.website_content}

Extract:
1. What the organization does.
2. Its products or services.
3. Its likely target customers.
4. Any evidence relevant to B2B qualification.
5. Information that is missing or uncertain.

Use only the supplied website content.
Do not invent revenue, budget, purchasing intent, or contacts.
""",
                expected_output="A concise, evidence-based company profile with clear notes about missing information.",
            )
        except Exception as e:
            self.state.website_content = ""
            self.state.enrichment = (
                f"Website enrichment failed. Manual verification is required. Details: {str(e)[:400]}"
            )
            self.state.error = str(e)[:400]

        # Save enriched_lead.json and enriched_lead.csv
        enriched_data = {
            "lead_name": self.state.lead_name,
            "website": self.state.website,
            "enrichment": self.state.enrichment,
            "error": self.state.error,
        }
        (self.run_dir / "enriched_lead.json").write_text(
            json.dumps(enriched_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        append_csv_row(
            self.run_dir / "enriched_lead.csv",
            enriched_data,
            ["lead_name", "website", "enrichment", "error"],
        )

    @router(enrich_lead)
    def score_lead(self):
        result = run_crew_helper(
            agent_role="Lead Qualification Specialist",
            goal="Classify leads fairly using available evidence.",
            backstory="You qualify leads for a sales team. You never treat missing information as proof of low interest.",
            task_description=f"""
Classify the following lead as exactly HOT, WARM, or COLD.

Lead: {self.state.lead_name}
Website: {self.state.website}
Website analysis: {self.state.enrichment}

Rules:
- HOT: Strong, specific evidence of relevant fit and a credible near-term buying signal.
- WARM: Potential fit, but intent or key qualification details are missing or need follow-up.
- COLD: Clear evidence of poor fit against the configured business context, not merely missing website information.

No target customer profile or product offering has been provided.
Therefore, do not invent one. If fit or buying intent cannot be
established from the available evidence, classify as WARM.

Return exactly this structure:
CATEGORY: HOT, WARM, or COLD
REASON: concise evidence-based explanation
""",
            expected_output="A CATEGORY line containing HOT, WARM, or COLD and a REASON line.",
        )

        upper_result = result.upper()
        if "CATEGORY: HOT" in upper_result or "HOT" in upper_result[:25]:
            self.state.category = "hot"
        elif "CATEGORY: COLD" in upper_result or "COLD" in upper_result[:25]:
            self.state.category = "cold"
        else:
            self.state.category = "warm"

        self.state.reasoning = result
        return self.state.category

    @listen("hot")
    def hot_outreach(self):
        self.state.outreach_email = run_crew_helper(
            agent_role="Personalized Sales Outreach Writer",
            goal="Draft a relevant and respectful first-contact email.",
            backstory="You write concise B2B emails grounded in verified company information and avoid fabricated personalization.",
            task_description=f"""
Draft an email for this lead.

Lead: {self.state.lead_name}
Website: {self.state.website}
Research: {self.state.enrichment}
Qualification result: {self.state.reasoning}

Requirements:
- Include a subject line, greeting, short body, and sign-off.
- Personalize only with supported facts.
- Do not claim that the lead requested contact.
- Do not invent the sender's name, product, results, or pricing.
- Use placeholders where sender/product details are unknown.
- Make the email professional and low-pressure.
""",
            expected_output="A complete email draft with a subject line.",
        )
        self.state.action = "Drafted personalized outreach email"

        hot_data = {
            "lead_name": self.state.lead_name,
            "website": self.state.website,
            "category": self.state.category,
            "reasoning": self.state.reasoning,
            "email_draft": self.state.outreach_email,
        }
        (self.run_dir / "hot_lead_outreach.json").write_text(
            json.dumps(hot_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        append_csv_row(
            self.run_dir / "hot_lead_outreach.csv",
            hot_data,
            ["lead_name", "website", "category", "reasoning", "email_draft"],
        )

    @listen("warm")
    def add_to_nurture(self):
        result = run_crew_helper(
            agent_role="Lead Nurture Content Planner",
            goal="Suggest useful educational content for a potential lead.",
            backstory="You create helpful, non-pushy B2B educational content.",
            task_description=f"""
Create three weekly educational tips or content ideas for this lead.

Lead: {self.state.lead_name}
Website: {self.state.website}
Research: {self.state.enrichment}

Return exactly three numbered tips.
Keep them relevant to verified information where possible.
If the lead's needs are unclear, make the uncertainty explicit.
Do not claim that the lead consented to receive marketing emails.
Use only information supported by the supplied research.
If website enrichment failed, do not invent company-specific needs,
current initiatives, technology choices, or business priorities.
Generate general educational ideas and explicitly state that
the company's specific needs remain unverified.
""",
            expected_output="Three numbered educational tips.",
        )
        self.state.nurture_tips = [
            line.strip() for line in result.splitlines() if line.strip()
        ][:3]
        self.state.action = "Added lead to nurture list"

        append_csv_row(
            self.run_dir / "nurture_list.csv",
            {
                "lead_name": self.state.lead_name,
                "website": self.state.website,
                "reasoning": self.state.reasoning,
                "weekly_tips": " | ".join(self.state.nurture_tips),
            },
            ["lead_name", "website", "reasoning", "weekly_tips"],
        )

    @listen("cold")
    def archive_lead(self):
        self.state.action = "Archived for review; no outreach drafted"
        append_csv_row(
            self.run_dir / "archived_leads.csv",
            {
                "lead_name": self.state.lead_name,
                "website": self.state.website,
                "reasoning": self.state.reasoning,
                "archived_at": datetime.now(timezone.utc).isoformat(),
            },
            ["lead_name", "website", "reasoning", "archived_at"],
        )

    @listen(or_(hot_outreach, add_to_nurture, archive_lead))
    def log_lead(self):
        append_csv_row(
            self.run_dir / "leads.csv",
            {
                "lead_name": self.state.lead_name,
                "website": self.state.website,
                "category": self.state.category,
                "reasoning": self.state.reasoning,
                "action": self.state.action,
                "logged_at": datetime.now(timezone.utc).isoformat(),
            },
            ["lead_name", "website", "category", "reasoning", "action", "logged_at"],
        )


async def run_lead_qualification(lead_name: str, website: str) -> Dict[str, Any]:
    """Runs LeadQualificationFlow and returns qualification data with CSV download links."""
    clean_name = lead_name.strip()
    clean_url = website.strip()

    if not clean_name or not clean_url:
        raise ValueError("Please provide both a lead/company name and a valid website URL.")

    run_id, run_dir = FileStorageService.create_run_dir("lead")

    flow = LeadQualificationFlow(lead_name=clean_name, website=clean_url, run_dir=run_dir)
    await asyncio.to_thread(flow.kickoff)

    # Collect generated CSVs
    csv_downloads = {}
    for csv_file in [
        "leads.csv",
        "nurture_list.csv",
        "archived_leads.csv",
        "enriched_lead.csv",
        "hot_lead_outreach.csv",
    ]:
        p = run_dir / csv_file
        if p.exists() and p.stat().st_size > 0:
            csv_downloads[csv_file] = f"/download/{run_id}/{csv_file}"

    # Build preview rows
    leads_csv_path = run_dir / "leads.csv"
    table_preview = []
    if leads_csv_path.exists():
        try:
            df = pd.read_csv(leads_csv_path)
            table_preview = df.to_dict(orient="records")
        except Exception:
            pass

    return {
        "run_id": run_id,
        "lead_name": flow.state.lead_name,
        "website": flow.state.website,
        "category": flow.state.category,
        "reasoning": flow.state.reasoning,
        "action": flow.state.action,
        "outreach_email": flow.state.outreach_email,
        "nurture_tips": flow.state.nurture_tips,
        "enrichment": flow.state.enrichment,
        "table_preview": table_preview,
        "downloads": csv_downloads,
    }
