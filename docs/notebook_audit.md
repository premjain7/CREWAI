# Audit Document: Ten Audited CrewAI Notebooks

**Audit Date:** October 2026  
**Workspace:** `D:\projects\Agentic AI\CREWAI\Notebooks`  
**Target Architecture:** FastAPI + CrewAI + Gemini API + Vanilla Modern Frontend

---

## 1. Executive Summary

All ten notebooks in `Notebooks/` were inspected in detail. Each project implements a distinct CrewAI pattern:
- **Projects 1–4:** CrewAI `Crew` with `Process.sequential` or `Process.hierarchical`, executing specialist agents with specific tasks.
- **Projects 5–10:** CrewAI `Flow` with event-driven architecture (`@start`, `@listen`, `@router`, `or_`, `and_`), combining lightweight LLM calls, deterministic routers, and embedded Crews for specific sub-tasks.

Every notebook originally targeted Google Colab (`google.colab.userdata` for API keys, `google.colab.files.upload()` and `files.download()`, standard `input()` blocks, and local working directories `/content/...`). None of the notebooks contained hardcoded API keys. All can be adapted cleanly into asynchronous FastAPI endpoints, backed by unified Gemini LLM configuration, isolated per-request storage, and a responsive web dashboard.

---

## 2. Comprehensive Project-by-Project Audit

### Project 1: Blog Post Crew
- **File:** `Project_01_Blog_Post_Crew.ipynb`
- **Execution Paradigm:** Sequential Crew (`Crew(process=Process.sequential)`)
- **Agents:**
  1. `researcher`: Role: *Research Specialist*, Tools: `duckduckgo_search` (using `ddgs` library).
  2. `writer`: Role: *Professional Blog Writer*, writes ~600 words in Markdown.
  3. `editor`: Role: *Blog Editor*, Tools: `FileWriterTool`, edits draft and writes `blog_post.md`.
- **Inputs:** `topic` (string, e.g. "indian cricket performance 2026").
- **Outputs:** Markdown content displayed; downloadable `blog_post.md`.
- **External Tools / Dependencies:** `ddgs` (`DDGS().text`), `crewai_tools.FileWriterTool`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.2, max_tokens 4096.
- **Colab Patterns to Replace:** `input()`, `files.download("blog_post.md")`, `/content/blog_post.md`.
- **Concurrency & State Adaptations:** Safe per-run output directory to prevent concurrent executions from clobbering `blog_post.md`. Pass isolated file paths into `FileWriterTool` or write final crew output directly.

---

### Project 2: Competitor Analysis Crew
- **File:** `Project_2_Competitor_Analysis_Crew.ipynb`
- **Execution Paradigm:** Hierarchical Crew (`Crew(process=Process.hierarchical, manager_agent=manager)`)
- **Agents:**
  1. `manager`: Role: *Research Manager* (delegation enabled).
  2. `site_scraper`: Role: *Site Scraper*, Tools: `ScrapeWebsiteTool`.
  3. `pricing_analyst`: Role: *Pricing Analyst*, Tools: `ScrapeWebsiteTool`.
  4. `news_analyst`: Role: *News Analyst*, Tools: `duckduckgo_search` (`ddgs`).
  5. `strategist`: Role: *Competitive Strategist*.
- **Tasks:** Single comprehensive `analysis_task` coordinated by the manager agent.
- **Inputs:** 3 competitor website URLs (`https://...` or `http://...`).
- **Outputs:** Structured Markdown competitor analysis report (Executive summary, comparison table, pricing/features, news, SWOT, recommendations, source URLs) saved to `report.md`.
- **External Tools / Dependencies:** `ddgs`, `crewai_tools.ScrapeWebsiteTool`, `crewai_tools.FileWriterTool`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.2, max_tokens 4096.
- **Colab Patterns to Replace:** Three interactive `input()` loops, `files.download("report.md")`.
- **Concurrency & State Adaptations:** Isolate output filename per request (`run_id/report.md`). Handle web-scraping timeouts and rate limits gracefully.

---

### Project 3: Meeting Notes Crew
- **File:** `Project_3_Meeting_Notes_Crew.ipynb`
- **Execution Paradigm:** Sequential Crew with Parallel Asynchronous Subtasks (`async_execution=True` on initial tasks, context aggregation in final formatter task)
- **Agents:**
  1. `summarizer`: Role: *Meeting Summarizer* (5 concise bullet points).
  2. `action_finder`: Role: *Action Item Extractor* (tasks, owners, deadlines in structured list).
  3. `decision_logger`: Role: *Decision Logger* (confirmed decisions vs. suggestions).
  4. `formatter`: Role: *Meeting Notes Formatter* (combines summary, action table, decisions, milestones into Markdown report).
- **Tasks:**
  - `summary_task` (`async_execution=True`)
  - `action_task` (`async_execution=True`)
  - `decision_task` (`async_execution=True`)
  - `format_task` (`context=[summary_task, action_task, decision_task]`, outputs to `notes.md`)
- **Inputs:** Meeting transcript as plain text or an uploaded `.txt` file.
- **Outputs:** Markdown meeting notes report saved to `notes.md`.
- **External Tools / Dependencies:** `crewai_tools.FileReadTool`, `crewai_tools.FileWriterTool`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.2.
- **Colab Patterns to Replace:** `files.upload()`, `files.download("notes.md")`.
- **Concurrency & State Adaptations:** Accept either text payload or `.txt` file upload; avoid fixed file path `transcript.txt` by feeding string directly to inputs dict `{"transcript": transcript}`.

---

### Project 4: Data Report Crew
- **File:** `Project_4_Data_Report_Crew.ipynb`
- **Execution Paradigm:** Sequential Crew with Python-verified ground-truth metrics
- **Agents:**
  1. `data_analyst`: Role: *Sales Data Analyst*, Tools: `FileReadTool`, Pydantic output `SalesReport`.
  2. `insight_writer`: Role: *Business Insight Writer*, generates narrative performance analysis and 3 practical recommendations.
  3. `reviewer`: Role: *Sales Report Reviewer*, audits report against ground truth metrics and writes `report.md`.
- **Inputs:** CSV dataset containing sales records (Date, Product, Region, Units_Sold, Unit_Price, Revenue, etc.).
- **Outputs:** Markdown sales performance report (`report.md`) with numerical metrics and business recommendations.
- **External Tools / Dependencies:** `pandas`, `pydantic`, `crewai_tools.FileReadTool`, `crewai_tools.FileWriterTool`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.2.
- **Key Insight from Notebook:** The audited notebook calculates verified metrics using `pandas` in Python (sum of units, total revenue, best selling product, highest revenue region, average revenue) to prevent hallucinations, injecting `{verified_metrics}` into the task description.
- **Colab Patterns to Replace:** `input()` CSV paste, hardcoded `sales.csv` in working directory, `files.download()`.
- **Concurrency & State Adaptations:** Save uploaded CSV safely to run-specific directory, compute pandas verified metrics, execute crew, save `report.md` in run folder.

---

### Project 5: Customer Support Flow
- **File:** `Project_5_Customer_Support_Flow.ipynb`
- **Execution Paradigm:** Event-driven Flow (`Flow[TicketState]`)
- **State Model:** `TicketState(ticket_text, category, priority, resolution)`
- **Routing:**
  - `@start() receive_ticket`: captures support issue.
  - `@listen(receive_ticket) categorize_ticket`: prompts LLM to classify into `billing`, `account_access`, or `other`.
  - `@router(categorize_ticket) route_by_category`: routes event to category handler.
  - `@listen("billing") handle_billing`: Priority "High", Billing Support resolution.
  - `@listen("account_access") handle_access`: Priority "High", Account Access Support resolution.
  - `@listen("other") handle_other`: Priority "Medium", General Support resolution.
  - `@listen(or_(handle_billing, handle_access, handle_other)) resolve_ticket`: formats and returns final resolution dictionary.
- **Inputs:** Customer ticket description text.
- **Outputs:** JSON object `{ticket, category, priority, resolution}`.
- **External Tools / Dependencies:** Core `crewai.flow`, `pydantic`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.1 (`llm.call(prompt)`).
- **Colab Patterns to Replace:** `input("Enter the customer's support issue: ")`.
- **Concurrency & State Adaptations:** Instantiate fresh `CustomerSupportFlow` per request; pass ticket text via state initialization rather than `input()`.

---

### Project 6: Resume Screening Flow
- **File:** `Project_6_Resume_Screening_Flow.ipynb`
- **Execution Paradigm:** Flow-based Router + Specialist Crew (`Flow[ResumeScreeningState]`)
- **State Model:** `ResumeScreeningState(resumes, current_resume, score, explanation, status, results)`
- **Routing & Business Logic:**
  - Scoring criteria: 0–10 integer scale based strictly on resume evidence (no job description!).
  - Score threshold: 7.
  - If `score >= 7`: Shortlist branch -> executes `summary_crew` with `Resume Summary Assistant` agent.
  - If `score < 7`: Reject branch -> calls LLM to draft polite, professional rejection email (for human review; no internal score disclosed; never auto-sent).
  - If scoring fails/invalid: routes to "Manual review required".
  - Results compiled into CSV (`results.csv`).
- **Inputs:** PDF resume file(s).
- **Outputs:** Candidate score, explanation, strengths, areas to improve, summary or draft rejection email, and downloadable `results.csv`.
- **External Tools / Dependencies:** `pypdf.PdfReader`, `pandas`, `json`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.1.
- **Colab Patterns to Replace:** `google.colab.files.upload()`, `files.download("results.csv")`.
- **Concurrency & State Adaptations:** Isolate PDF extraction and CSV storage per request. Clearly display human advisory notice in frontend.

---

### Project 7: Bug Triage Flow
- **File:** `Project_7_Bug_Triage_Flow.ipynb`
- **Execution Paradigm:** Flow router branching to 3 specialist Crews (`Flow[BugTriageState]`)
- **State Model:** `BugTriageState(issue_title, issue_body, issue_type, classification_reason, result)`
- **Routing & Branches:**
  - `@listen(read_issue) classify_issue`: classifies issue into `bug`, `feature`, or `question`.
  - `@router(classify_issue) route_type`: routes to matching crew.
  - `@listen("bug") bug_crew`: Agent: *Bug Triage Specialist* (suggests severity, steps to reproduce, expected vs actual, missing info).
  - `@listen("feature") feature_crew`: Agent: *Product Analyst* (user story, acceptance criteria, clarifying questions).
  - `@listen("question") answer_crew`: Agent: *Issue Support Assistant* (drafts helpful technical answer).
  - `@listen(or_(...)) post_reply`: sets `reply_status = "Draft ready for human review"`, writes `bug_triage_result.json`.
- **Inputs:** Issue title and issue description.
- **Outputs:** JSON triage record (`category`, `title`, `analysis`, `classification_reason`, `reply_status`).
- **External Tools / Dependencies:** `crewai.flow`, `json`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.1.
- **Colab Patterns to Replace:** `input()`, fixed `/content/bug_triage_result.json`, `files.download()`.
- **Concurrency & State Adaptations:** Per-request isolated flow instance and output path.

---

### Project 8: Content Repurposing Flow
- **File:** `Project_8_Content_Repurposing_Flow.ipynb`
- **Execution Paradigm:** Multi-Branch Parallel Flow (`Flow[RepurposingState]` with `and_`)
- **State Model:** `RepurposingState(source, article_text, article_points, linkedin_post, twitter_thread, newsletter, output_files)`
- **Workflow:**
  1. `load_article`: accepts URL (scraped via `ScrapeWebsiteTool`), file path, or direct text.
  2. `extract_points`: Agent: *Article Insight Extractor* (main argument, supporting points, conclusion).
  3. Parallel branches:
     - `create_linkedin`: Crew with *LinkedIn Content Strategist* (~150 words).
     - `create_twitter`: Crew with *Twitter/X Thread Writer* (exactly 6 numbered tweets 1/6–6/6).
     - `create_newsletter`: Crew with *Newsletter Writer* (intro + 3 bullet points).
  4. `@listen(and_(create_linkedin, create_twitter, create_newsletter)) publish_pack`: writes:
     - `linkedin_post.md`
     - `twitter_thread.md`
     - `newsletter.md`
     - `summary.json`
- **Inputs:** Article text, uploaded `.txt`, or article URL.
- **Outputs:** Three separate Markdown downloads (`linkedin_post.md`, `twitter_thread.md`, `newsletter.md`) and summary JSON. (No ZIP packaging, as instructed).
- **External Tools / Dependencies:** `crewai_tools.ScrapeWebsiteTool`, `urllib`, `pathlib`, `json`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.4.
- **Colab Patterns to Replace:** Interactive choice `input()`, fixed `/content/content_repurposing_output`, `files.download()`.
- **Concurrency & State Adaptations:** Isolate run directory by `run_id`. Provide distinct download endpoints for all 3 Markdown files and the JSON file.

---

### Project 9: Lead Qualification Flow
- **File:** `Project_9_Lead_Qualification_Flow.ipynb`
- **Execution Paradigm:** Flow-based Enrichment, Classification, and CSV Pipeline (`Flow[LeadQualificationState]`)
- **State Model:** `LeadQualificationState(lead_name, website, website_content, enrichment, category, reasoning, action, outreach_email, nurture_tips, error)`
- **Workflow:**
  1. `capture_lead`: company name and website URL.
  2. `enrich_lead`: scrapes website with `ScrapeWebsiteTool`, summarizes with *Lead Research Analyst* crew, saves `enriched_lead.json` & `enriched_lead.csv`.
  3. `score_lead`: *Lead Qualification Specialist* classifies lead as `HOT`, `WARM`, or `COLD`.
  4. Conditional routing:
     - `hot`: *Personalized Sales Outreach Writer* drafts first-contact email; saves `hot_lead_outreach.json` & `hot_lead_outreach.csv`.
     - `warm`: *Lead Nurture Content Planner* produces 3 weekly educational tips; appends to `nurture_list.csv`.
     - `cold`: Archives lead without outreach; appends to `archived_leads.csv`.
  5. `log_lead`: appends all leads to master `leads.csv`.
- **Inputs:** Company/lead name and website URL.
- **Outputs:** Display qualification result; generate/update CSVs: `leads.csv`, `nurture_list.csv`, `archived_leads.csv`, `enriched_lead.csv`, `hot_lead_outreach.csv`. Provide tabular view and individual CSV downloads.
- **External Tools / Dependencies:** `crewai_tools.ScrapeWebsiteTool`, `csv`, `json`, `datetime`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.4.
- **Colab Patterns to Replace:** `input()`, fixed `/content/lead_qualification_output`.
- **Concurrency & State Adaptations:** Maintain an isolated or session-scoped storage directory so runs do not cross-contaminate lead tables.

---

### Project 10: Approval Report Flow
- **File:** `Project_10_Approval_Report_Flow.ipynb`
- **Execution Paradigm:** Multi-turn Human-in-the-Loop Flow (`Flow[ApprovalReportState]`)
- **State Model:** `ApprovalReportState(topic, audience, research, draft, feedback, decision, revision_count, max_revisions=2, final_path, status)`
- **Multi-Step Lifecycle:**
  - **Step 1 (Start):** User provides `topic` and `audience`.
  - **Step 2 (Research & Draft):** System runs web search (`DDGS`), executes *Research Analyst* crew, then executes *Report Writer* crew to generate Markdown draft.
  - **Step 3 (Human Review):** Report is paused and presented to the human reviewer in the UI.
  - **Step 4 (Decision Loop):**
    - **Approve:** status -> "approved", final report saved as `final_report_{timestamp}.md`, records `approval_record_{timestamp}.json`. Downloadable `.md` made available.
    - **Revise:** reviewer submits feedback; `revision_count` incremented (capped at 2). *Report Editor* crew revises draft. Returns to Step 3. If revisions exceed 2, automatically rejects.
    - **Reject:** status -> "rejected", records `rejection_record_{timestamp}.json`. Final report is **never** saved or published.
- **Inputs:** Initial: `topic`, `audience`. Step 2: `decision` ("approve", "revise", "reject"), `feedback` (optional for reject, required for revise).
- **Outputs:** Draft preview, final Markdown download (only if approved), JSON approval/rejection audit record.
- **External Tools / Dependencies:** `ddgs`, `json`, `datetime`.
- **Gemini Config:** `gemini/gemini-3.1-flash-lite-preview`, temp 0.4.
- **Critical Architecture Requirement:** In HTTP, a blocking `while True: input()` crashes or times out. Must be implemented as a stateful session workflow (`/agent10/start`, `/agent10/{session_id}/review`, `/agent10/{session_id}/status`) backed by a persistent/in-memory workflow store.

---

## 3. Summary Audit Table

| # | Project Name | Input Format | Execution Entry Point | Output Format | Key Dependencies | Required Web/Backend Adaptations |
|---|---|---|---|---|---|---|
| 1 | Blog Post Crew | Topic (JSON text) | `blog_crew.kickoff_async(inputs={"topic": ...})` | Markdown text + `blog_post.md` download | `ddgs`, `FileWriterTool` | Replace `input()` and Colab download with REST POST and file download endpoint. |
| 2 | Competitor Analysis Crew | 3 URLs (JSON array/form) | `competitor_crew.kickoff_async(inputs={"competitors": ...})` | Markdown report + `report.md` download | `ddgs`, `ScrapeWebsiteTool`, `FileWriterTool` | Replace 3x `input()`; handle scrape timeouts; isolate output file path. |
| 3 | Meeting Notes Crew | Plain text or `.txt` upload (Multipart / JSON) | `meeting_crew.kickoff_async(inputs={"transcript": ...})` | Markdown report + `notes.md` download | `crewai`, `FileReadTool`, `FileWriterTool` | Support file upload and text field; parallel tasks; file isolation. |
| 4 | Data Report Crew | CSV file upload (Multipart) | Pandas verification + `sales_crew.kickoff_async()` | Markdown sales report + `report.md` download | `pandas`, `pydantic` | Multipart CSV parsing; compute ground-truth metrics; render tables. |
| 5 | Customer Support Flow | Support issue (JSON text) | `CustomerSupportFlow().kickoff()` | JSON `{category, priority, resolution}` | `crewai.flow`, `pydantic` | Replace `input()`; return JSON structure to frontend. |
| 6 | Resume Screening Flow | PDF file(s) upload (Multipart) | `ResumeScreeningFlow().kickoff()` | JSON score + summary/rejection draft + `results.csv` | `pypdf`, `pandas`, `json` | PDF file upload; score threshold 7 routing; advisory human-review banner; CSV download. |
| 7 | Bug Triage Flow | Title & Body (JSON text) | `BugTriageFlow().kickoff()` | JSON triage analysis + `bug_triage_result.json` download | `crewai.flow`, `json` | Form inputs; route to bug/feature/question crew; JSON download. |
| 8 | Content Repurposing Flow | Text, `.txt` file, or URL | `ContentRepurposingFlow().kickoff()` | 3 Markdown files (`linkedin_post.md`, `twitter_thread.md`, `newsletter.md`) + `summary.json` | `ScrapeWebsiteTool`, `urllib` | Parallel branches (`and_`); individual Markdown downloads without ZIP. |
| 9 | Lead Qualification Flow | Company name + website URL (JSON) | `LeadQualificationFlow().kickoff()` | Category (HOT/WARM/COLD) + CSV tables (`leads.csv`, etc.) | `ScrapeWebsiteTool`, `csv`, `json` | Scrape validation; generate CSV conversions for JSONs; CSV download endpoints. |
| 10 | Approval Report Flow | Topic & Audience (Start), Decision & Feedback (Review) | `ApprovalReportFlow` multi-step session | Draft preview; Approved Markdown report; JSON audit record | `ddgs`, `json`, session store | Multi-turn stateful HTTP endpoints (`/start`, `/review`); enforce max 2 revisions; never publish rejected reports. |

---

## 4. Key Gaps, Technical Risks & Mitigation Plan

1. **State Persistence Across HTTP Requests (Project 10):**
   - *Risk:* In Colab, human-in-the-loop uses a blocking `while True: input()`. In FastAPI, HTTP requests are request-response cycles.
   - *Mitigation:* Implement a dedicated `WorkflowStore` service with a unique `session_id` per run. The initial `/agent10/start` runs research and draft generation, stores draft state, and returns to the client. The user reviews the draft on the web interface and calls `/agent10/{session_id}/review` with `approve`, `revise`, or `reject`. Max 2 revisions strictly enforced.

2. **File System Isolation & Concurrency:**
   - *Risk:* Multiple simultaneous users writing to hardcoded paths like `report.md` or `leads.csv` will collide and corrupt data.
   - *Mitigation:* `FileStorageService` creates an isolated run folder `outputs/{run_id}/` for every execution. Download endpoints validate `run_id` and filename against path-traversal attacks.

3. **External Search & Scraping Reliability:**
   - *Risk:* `ddgs` or `ScrapeWebsiteTool` can intermittently fail, block, or timeout.
   - *Mitigation:* Wrap all search and scrape invocations in robust try-except fallbacks (as already pioneered in the audited notebooks) to ensure the agent flow degrades gracefully with clear informational notes instead of crashing the server.

4. **Gemini API Configuration:**
   - *Risk:* Hardcoded models or missing environment variables.
   - *Mitigation:* Centralized `services/gemini.py` loading `GEMINI_API_KEY` from environment, instantiating `crewai.LLM` with model `gemini/gemini-2.5-flash` or `gemini/gemini-1.5-flash` / `gemini/gemini-3.1-flash-lite-preview` with graceful quota and error handling. Mock LLM for test suite.
