"""Agent 1: Blog Post Crew.

Preserved from Project_01_Blog_Post_Crew.ipynb.
"""

from pathlib import Path
from typing import Dict, Any, Tuple

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from crewai_tools import FileWriterTool
from ddgs import DDGS

from services.gemini import get_llm
from services.file_storage import FileStorageService


@tool("DuckDuckGo Search")
def duckduckgo_search(query: str) -> str:
    """Search the web and return relevant results with titles, snippets, and source URLs."""
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "No search results found for this query."
        output = []
        for index, result in enumerate(results, start=1):
            output.append(
                f"Result {index}\n"
                f"Title: {result.get('title', 'N/A')}\n"
                f"Snippet: {result.get('body', 'N/A')}\n"
                f"URL: {result.get('href', 'N/A')}"
            )
        return "\n\n".join(output)
    except Exception as e:
        return f"Search failed: {type(e).__name__}: {e}"


def create_blog_post_crew(output_file_path: Path):
    """Instantiates the Blog Post Crew with isolated output path."""
    llm = get_llm(temperature=0.2, max_tokens=4096)
    file_writer = FileWriterTool()

    # Agent 1: Researcher
    researcher = Agent(
        role="Research Specialist",
        goal="Research the given topic using web search and collect relevant facts, useful insights, and source URLs.",
        backstory="You are a careful research specialist. You distinguish evidence from assumptions and never invent sources.",
        tools=[duckduckgo_search],
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=5,
    )

    # Agent 2: Writer
    writer = Agent(
        role="Professional Blog Writer",
        goal="Write an engaging blog post of approximately 600 words using the research provided.",
        backstory="You are a professional content writer who turns research into clear, engaging, well-structured articles.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )

    # Agent 3: Editor
    editor = Agent(
        role="Blog Editor",
        goal="Edit the draft for readability, tone, structure, and factual consistency, and save the final article.",
        backstory="You are a meticulous editor. Preserve supported facts, remove unsupported claims, improve clarity, and use the file-writing tool to save the final Markdown article.",
        tools=[file_writer],
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )

    # Task 1: Research
    research_task = Task(
        description=(
            "Research the topic: {topic}\n\n"
            "Use DuckDuckGo search to investigate the topic. "
            "Collect the key facts, recent developments where relevant, "
            "useful examples, and at least three relevant source URLs "
            "when available. Return organized research notes and clearly "
            "distinguish verified information from uncertainty."
        ),
        expected_output=(
            "Organized research notes containing key findings, useful "
            "examples, and source titles and URLs. Do not invent citations."
        ),
        agent=researcher,
    )

    # Task 2: Writing
    writing_task = Task(
        description=(
            "Write a blog post of approximately 600 words about {topic}, "
            "using the research supplied by the preceding task. Include "
            "an engaging title, introduction, logical section headings, "
            "examples where useful, and a conclusion. Preserve source URLs "
            "for factual claims and avoid unsupported statistics."
        ),
        expected_output=(
            "A complete blog post draft of approximately 600 words in "
            "Markdown, with a title, headings, conclusion, and source links."
        ),
        agent=writer,
    )

    # Task 3: Editing
    editing_task = Task(
        description=(
            "Edit the draft produced by the preceding task about {topic}. "
            "Improve grammar, readability, tone, organization, and factual "
            "consistency. Preserve useful source links. Do not invent facts "
            "or claim that a statement is verified without supporting evidence. "
            f"Save the final edited article using FileWriterTool with "
            f"directory='{str(output_file_path.parent)}' and filename='{output_file_path.name}'. "
            "The file must contain the article itself, not a discussion of the task."
        ),
        expected_output=(
            "The final edited Markdown blog post, with a clear title, "
            "well-organized sections, conclusion, and relevant source links."
        ),
        agent=editor,
        output_file=str(output_file_path),
    )

    return Crew(
        agents=[researcher, writer, editor],
        tasks=[research_task, writing_task, editing_task],
        process=Process.sequential,
        verbose=False,
    )


async def run_blog_post(topic: str) -> Dict[str, Any]:
    """Executes the Blog Post Crew and returns the result and file details."""
    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("Please provide a valid topic for the blog post.")

    run_id, run_dir = FileStorageService.create_run_dir("blog")
    output_path = run_dir / "blog_post.md"

    crew = create_blog_post_crew(output_path)
    crew_output = await crew.kickoff_async(inputs={"topic": clean_topic})

    # Prefer reading the file saved by FileWriterTool in the run directory.
    # Fall back to checking the root-level blog_post.md if FileWriterTool
    # resolved the path relative to CWD instead of the run directory.
    # Only use str(crew_output) as a last resort (it may be a "saved to..." message).
    blog_content = ""
    if output_path.exists() and output_path.stat().st_size > 0:
        blog_content = output_path.read_text(encoding="utf-8").strip()
    else:
        # FileWriterTool may have saved to CWD; move it into the run directory.
        cwd_file = Path("blog_post.md")
        if cwd_file.exists() and cwd_file.stat().st_size > 0:
            cwd_content = cwd_file.read_text(encoding="utf-8").strip()
            # Only use if it looks like actual article content, not a status message
            if len(cwd_content) > 200 and not cwd_content.lower().startswith("the edited article"):
                blog_content = cwd_content
                output_path.write_text(blog_content, encoding="utf-8")

    # If we still don't have article content, use crew_output only if it's substantive
    if not blog_content:
        raw_output = str(crew_output).strip()
        if len(raw_output) > 200 and not raw_output.lower().startswith("the edited article"):
            blog_content = raw_output
        else:
            raise RuntimeError(
                "Blog post generation did not produce article content. "
                "The editor agent may have failed to write the file. "
                f"Raw output was: {raw_output[:300]!r}"
            )

    # Ensure file is persisted in the run directory for download
    if not output_path.exists() or output_path.stat().st_size == 0:
        output_path.write_text(blog_content, encoding="utf-8")

    return {
        "run_id": run_id,
        "topic": clean_topic,
        "content": blog_content,
        "filename": "blog_post.md",
        "download_url": f"/download/{run_id}/blog_post.md",
    }
