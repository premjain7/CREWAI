"""Agent 2: Competitor Analysis Crew.

Preserved from Project_2_Competitor_Analysis_Crew.ipynb.
"""

from pathlib import Path
from typing import List, Dict, Any

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from crewai_tools import ScrapeWebsiteTool, FileWriterTool
from ddgs import DDGS

from services.gemini import get_llm
from services.file_storage import FileStorageService


@tool("DuckDuckGo Search")
def duckduckgo_search(query: str) -> str:
    """Search the web and return titles, snippets, and URLs."""
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No search results found."
        output = []
        for i, item in enumerate(results, start=1):
            output.append(
                f"Result {i}\n"
                f"Title: {item.get('title', 'N/A')}\n"
                f"Snippet: {item.get('body', 'N/A')}\n"
                f"URL: {item.get('href', 'N/A')}"
            )
        return "\n\n".join(output)
    except Exception as e:
        return f"Search error: {type(e).__name__}: {e}"


def create_competitor_crew(output_file_path: Path):
    """Creates the hierarchical competitor analysis crew."""
    llm = get_llm(temperature=0.2, max_tokens=4096)
    scraper = ScrapeWebsiteTool()

    site_scraper = Agent(
        role="Site Scraper",
        goal="Extract useful company and product information from the competitor websites provided.",
        backstory="You carefully inspect company websites and report only information supported by the page content.",
        tools=[scraper],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    pricing_analyst = Agent(
        role="Pricing Analyst",
        goal="Compare competitors' pricing plans, features, and publicly listed prices.",
        backstory="You are a pricing researcher. Clearly distinguish listed prices from unavailable or unclear pricing.",
        tools=[scraper],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    news_analyst = Agent(
        role="News Analyst",
        goal="Find relevant recent announcements and developments about the competitors.",
        backstory="You research company news and provide source URLs. You never invent news or dates.",
        tools=[duckduckgo_search],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    strategist = Agent(
        role="Competitive Strategist",
        goal="Combine the research into a useful competitor comparison and SWOT analysis.",
        backstory="You are a business strategist who turns verified research into practical competitive insights.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    manager = Agent(
        role="Research Manager",
        goal="Coordinate the specialist agents, delegate research, and ensure a complete and consistent competitor report.",
        backstory="You manage competitive research projects and assign the right work to each specialist.",
        llm=llm,
        allow_delegation=True,
        verbose=False,
    )

    analysis_task = Task(
        description="""
Analyze these three competitors:
{competitors}

## Research Instructions

1. **Official sources first**: For each competitor, visit their official website,
   pricing page (/pricing), features page (/features), and product documentation.
   Use the site scraper on these specific sub-pages, not only the homepage.

2. **Source attribution**: Attach the direct URL of the specific page supporting
   each claim, placed immediately after the claim.
   Example: "The Pro plan costs $49/month (https://example.com/pricing)."

3. **Pricing is time-sensitive**: Include an "As of [Month Year]" note wherever
   pricing or feature availability is reported. If a price is not publicly listed,
   write: "Pricing: Not publicly listed."

4. **Separate facts from analysis**:
   - Verified fact: cite the direct source URL
   - Analyst inference: label as [ESTIMATE]
   - Unavailable information: label as [UNVERIFIED — not found on official pages]

5. **Do not invent**: Never fabricate pricing figures, launch dates, market share,
   customer counts, or revenue. If evidence is unavailable, state that explicitly.

6. **Handle scrape failures**: If a page returns no content or an error, note the
   failure and attempt an alternative DuckDuckGo search. Do not substitute invented data.

7. **Recency**: Recommend that the user verify time-sensitive claims directly on
   the company's official pages, since pricing changes frequently.
        """,
        expected_output="""
A structured competitor analysis report containing:
- Executive summary (2-3 paragraphs)
- Side-by-side comparison table (features, pricing with "as of" date, target market)
- Pricing analysis with direct source URLs and explicit [UNVERIFIED] labels where needed
- Recent news and announcements (with direct source URLs)
- SWOT analysis for each competitor
- Strategic recommendations
- Sources section listing all URLs consulted

All factual claims must cite the direct URL of the specific page consulted.
Unverified, estimated, or unavailable information must be clearly labeled.
        """,
        agent=manager,
        output_file=str(output_file_path),
    )

    return Crew(
        agents=[site_scraper, pricing_analyst, news_analyst, strategist],
        tasks=[analysis_task],
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=False,
    )


async def run_competitor_analysis(competitor_urls: List[str]) -> Dict[str, Any]:
    """Validates URLs, executes the Competitor Analysis Crew, and returns results."""
    clean_urls = [u.strip() for u in competitor_urls if u and u.strip()]
    if len(clean_urls) != 3:
        raise ValueError("Please provide exactly three competitor website URLs.")

    for i, url in enumerate(clean_urls, start=1):
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"Competitor {i} ('{url}') must be a valid HTTP or HTTPS URL.")

    run_id, run_dir = FileStorageService.create_run_dir("competitor")
    output_path = run_dir / "report.md"

    crew = create_competitor_crew(output_path)
    crew_output = await crew.kickoff_async(inputs={"competitors": "\n".join(clean_urls)})

    report_content = str(crew_output).strip()
    if not output_path.exists() or output_path.stat().st_size == 0:
        output_path.write_text(report_content, encoding="utf-8")
    else:
        report_content = output_path.read_text(encoding="utf-8")

    return {
        "run_id": run_id,
        "competitors": clean_urls,
        "content": report_content,
        "filename": "report.md",
        "download_url": f"/download/{run_id}/report.md",
    }
