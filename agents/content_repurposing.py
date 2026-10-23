"""Agent 8: Content Repurposing Flow.

Preserved from Project_8_Content_Repurposing_Flow.ipynb.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any

from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from crewai.flow.flow import Flow, start, listen, and_
from crewai_tools import ScrapeWebsiteTool

from services.gemini import get_llm
from services.file_storage import FileStorageService


class RepurposingState(BaseModel):
    source: str = ""
    article_text: str = ""
    article_points: str = ""
    linkedin_post: str = ""
    twitter_thread: str = ""
    newsletter: str = ""
    output_files: Dict[str, str] = Field(default_factory=dict)


def read_article_source(source: str) -> str:
    """Extracts text from direct content, URL, or local file."""
    clean_source = source.strip()
    if not clean_source:
        raise ValueError("Please provide article text, a file upload, or a URL.")

    # 1. URL scraping
    if clean_source.startswith(("http://", "https://")):
        try:
            scraper = ScrapeWebsiteTool(website_url=clean_source)
            content = scraper.run()
            if not content or not str(content).strip():
                raise ValueError("Could not extract readable content from this URL.")
            return str(content).strip()
        except Exception as e:
            raise ValueError(f"Failed to scrape article URL: {e}") from e

    # 2. File path check
    try:
        path = Path(clean_source)
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                raise ValueError("The article file is empty.")
            return content
    except (OSError, ValueError) as e:
        if isinstance(e, ValueError) and str(e) == "The article file is empty.":
            raise

    # 3. Direct text payload
    if len(clean_source) < 50:
        raise ValueError(
            "Input is too short to be an article (minimum 50 characters required). "
            "Please provide article text, an uploaded .txt file, or a valid URL."
        )

    return clean_source


def create_linkedin_crew():
    llm = get_llm(temperature=0.4)
    agent = Agent(
        role="LinkedIn Content Strategist",
        goal="Create a compelling LinkedIn post of approximately 150 words.",
        backstory="You specialize in professional, engaging social content.",
        llm=llm,
        verbose=False,
    )
    task = Task(
        description=(
            "Using these article points:\n{article_points}\n\n"
            "Write a LinkedIn post of approximately 150 words. Start with a "
            "strong hook, use readable paragraphs, preserve the facts, and "
            "finish with a relevant question or call to action."
        ),
        expected_output="One polished LinkedIn post of approximately 150 words.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def create_twitter_crew():
    llm = get_llm(temperature=0.4)
    agent = Agent(
        role="Twitter/X Thread Writer",
        goal="Create an engaging six-tweet thread from the article.",
        backstory="You turn complex ideas into concise, readable tweets.",
        llm=llm,
        verbose=False,
    )
    task = Task(
        description=(
            "Using these article points:\n{article_points}\n\n"
            "Write exactly six numbered tweets. Tweet 1 must hook the reader. "
            "Arrange the ideas logically and finish with a useful takeaway. "
            "Keep tweets concise and do not invent facts."
        ),
        expected_output="Exactly six numbered tweets, from 1/6 to 6/6.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


def create_newsletter_crew():
    llm = get_llm(temperature=0.4)
    agent = Agent(
        role="Newsletter Writer",
        goal="Create a newsletter introduction and three key bullet points.",
        backstory="You write concise newsletters that highlight useful insights.",
        llm=llm,
        verbose=False,
    )
    task = Task(
        description=(
            "Using these article points:\n{article_points}\n\n"
            "Write a short newsletter introduction followed by exactly three "
            "informative bullet points. Preserve the source meaning and do "
            "not invent facts."
        ),
        expected_output="A newsletter introduction and exactly three bullets.",
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)


class ContentRepurposingFlow(Flow[RepurposingState]):
    """Parallel flow repurposing articles into LinkedIn, Twitter/X, and Newsletter formats."""

    def __init__(self, source: str, run_dir: Path):
        super().__init__()
        self.initial_source = source
        self.run_dir = run_dir

    @start()
    def load_article(self):
        self.state.source = self.initial_source
        self.state.article_text = read_article_source(self.state.source)
        if not self.state.article_text.strip():
            raise ValueError("The article contains no readable text.")

    @listen(load_article)
    def extract_points(self):
        llm = get_llm(temperature=0.4)
        agent = Agent(
            role="Article Insight Extractor",
            goal="Extract the central ideas and important supporting details.",
            backstory="You summarize source material accurately without inventing facts.",
            llm=llm,
            verbose=False,
        )
        task = Task(
            description=(
                "Extract the key ideas from this article:\n\n"
                f"{self.state.article_text}\n\n"
                "Return a structured list of the main argument, important "
                "supporting details, and conclusion. Do not add outside facts."
            ),
            expected_output="A concise list of key ideas and the main conclusion.",
            agent=agent,
        )
        result = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False).kickoff()
        self.state.article_points = str(result).strip()

    @listen(extract_points)
    def create_linkedin(self):
        crew = create_linkedin_crew()
        result = crew.kickoff(inputs={"article_points": self.state.article_points})
        self.state.linkedin_post = str(result).strip()

    @listen(extract_points)
    def create_twitter(self):
        crew = create_twitter_crew()
        result = crew.kickoff(inputs={"article_points": self.state.article_points})
        self.state.twitter_thread = str(result).strip()

    @listen(extract_points)
    def create_newsletter(self):
        crew = create_newsletter_crew()
        result = crew.kickoff(inputs={"article_points": self.state.article_points})
        self.state.newsletter = str(result).strip()

    @listen(and_(create_linkedin, create_twitter, create_newsletter))
    def publish_pack(self):
        outputs = {
            "linkedin_post.md": self.state.linkedin_post,
            "twitter_thread.md": self.state.twitter_thread,
            "newsletter.md": self.state.newsletter,
        }

        for filename, content in outputs.items():
            path = self.run_dir / filename
            path.write_text(content, encoding="utf-8")
            self.state.output_files[filename] = str(path)

        summary = {
            "source_type": "url" if self.state.source.startswith("http") else "text",
            "article_points": self.state.article_points,
            "output_files": list(outputs.keys()),
        }

        summary_path = self.run_dir / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.state.output_files["summary.json"] = str(summary_path)


async def run_content_repurposing(source_text_or_url: str) -> Dict[str, Any]:
    """Runs ContentRepurposingFlow and outputs individual markdown and summary JSON downloads."""
    clean_input = source_text_or_url.strip()
    if not clean_input:
        raise ValueError("Please provide an article text, uploaded .txt file, or URL.")

    run_id, run_dir = FileStorageService.create_run_dir("repurpose")

    flow = ContentRepurposingFlow(source=clean_input, run_dir=run_dir)
    await asyncio.to_thread(flow.kickoff)

    return {
        "run_id": run_id,
        "article_points": flow.state.article_points,
        "linkedin_post": flow.state.linkedin_post,
        "twitter_thread": flow.state.twitter_thread,
        "newsletter": flow.state.newsletter,
        "downloads": {
            "linkedin_post": f"/download/{run_id}/linkedin_post.md",
            "twitter_thread": f"/download/{run_id}/twitter_thread.md",
            "newsletter": f"/download/{run_id}/newsletter.md",
            "summary_json": f"/download/{run_id}/summary.json",
        },
    }
