# CrewAI Multi-Agent Suite

A unified, production-ready web application consolidating 10 audited **CrewAI** and **Flow** projects into an interactive, deployable dashboard powered by **FastAPI** and **Google Gemini**.

---

## 🚀 Live Demo & Project Overview

This repository transforms 10 specialized AI systems originally prototyped in Google Colab into a single cohesive full-stack web application. Every project retains its original agent roles, backstories, tools, flow topologies, and state machines while providing a modern web UI, isolated per-run file storage, and REST API endpoints.

### The 10 Integrated Projects

| # | Project Name | Architecture | Agents / Tools / Mechanics | Primary Output |
|---|--------------|--------------|---------------------------|----------------|
| **1** | **Blog Post Crew** | Sequential Crew | `Researcher` (DuckDuckGo search), `Writer`, `Editor` (FileWriterTool) | Markdown blog post (`blog_post.md`) |
| **2** | **Competitor Analysis** | Sequential Crew | 3-URL DuckDuckGo market audit, competitive matrix | Markdown report (`report.md`) |
| **3** | **Meeting Notes Crew** | Sequential Crew | `Summarizer`, `Action Finder`, `Decision Logger`, `Formatter` | Executive notes (`notes.md`) |
| **4** | **Data Report Crew** | Verified Crew | Python Pandas ground truth calculation + `Data Analyst`, `Insight Writer`, `Reviewer` | Verified report (`report.md`) & CSV |
| **5** | **Customer Support** | Conditional Flow | `@router` ticket classifier (Technical, Billing, General) + priority escalation | Formatted resolution & triage |
| **6** | **Resume Screening** | Advisory Flow | PDF text extraction + `@listen` router (Shortlist / Reject / Manual Review) | Results CSV (`results.csv`) & drafts |
| **7** | **Bug Triage Flow** | Branching Flow | Issue classifier + specialized crews (`bug_crew`, `feature_crew`, `answer_crew`) | Triage JSON (`bug_triage_result.json`) |
| **8** | **Content Repurposing** | Parallel Flow | Parallel fan-out (`and_` execution) generating LinkedIn, Twitter, and Newsletter | Individual `.md` files + `summary.json` |
| **9** | **Lead Qualification** | Pipeline Flow | B2B domain enrichment + ICP classifier (`HOT`, `WARM`, `COLD`) + outreach drafts | Tabular preview & dedicated CSVs |
| **10**| **HITL Report Flow** | Stateful Review Flow | Multi-step human-in-the-loop review, strict 2-revision limit, never publishes rejected drafts | Final report (`.md`) + audit JSON |

---

## 🏛️ System Architecture

```
CREWAI/
├── agents/                      # Clean Python modules for all 10 agents
│   ├── __init__.py
│   ├── blog_post.py             # Project 1: Sequential blog generation
│   ├── competitor_analysis.py   # Project 2: DuckDuckGo competitor audit
│   ├── meeting_notes.py         # Project 3: Transcript summarizer & action items
│   ├── data_report.py           # Project 4: Ground-truth Pandas + CrewAI analysis
│   ├── customer_support.py      # Project 5: Support ticket classification flow
│   ├── resume_screening.py      # Project 6: Advisory PDF screening flow
│   ├── bug_triage.py            # Project 7: Issue triage & severity router flow
│   ├── content_repurposing.py   # Project 8: Parallel 3-channel content fan-out
│   ├── lead_qualification.py    # Project 9: B2B lead enrichment & outreach
│   └── approval_report.py       # Project 10: Multi-turn human-in-the-loop flow
├── services/                    # Shared core infrastructure
│   ├── __init__.py
│   ├── gemini.py                # Lazy LLM factory with fallback model
│   ├── file_storage.py          # Isolated per-run storage & path traversal guard
│   └── workflow_store.py        # Thread-safe HITL session store with disk backup
├── static/                      # Frontend assets
│   ├── style.css                # Responsive dark slate design
│   └── script.js                # Asynchronous API handlers, state management, UI
├── templates/
│   └── index.html               # Jinja2 dashboard template for all 10 projects
├── tests/                       # Automated test suite (Zero paid LLM calls)
│   ├── __init__.py
│   └── test_api.py              # Mocked route, validation, and HITL lifecycle tests
├── docs/
│   └── notebook_audit.md        # Complete audit report of original notebooks
├── Notebooks/                   # Pristine copies of original Colab notebooks
├── outputs/                     # Isolated output directory (git ignored)
├── app.py                       # FastAPI application & REST routing
├── requirements.txt             # Pinned Python package dependencies
├── render.yaml                  # Render Blueprint deployment definition
├── Procfile                     # Process file for cloud PaaS deployments
├── .env.example                 # Environment configuration template
└── README.md                    # Project documentation
```

---

## 🔒 Key Design Guarantees

1. **Zero LLM Execution on Startup / Test:**
   LLM clients are lazily instantiated inside individual agent workflows. Importing `app.py` or running unit tests makes **no live API calls** and incurs **no API charges**.
2. **Safe File Isolation & Security:**
   Each execution generates an isolated directory in `outputs/{run_id}/`. Download paths are strictly validated against directory traversal attacks (`../` or `..\`).
3. **Project 6 Human Oversight:**
   Resume scores are displayed alongside a prominent advisory notice emphasizing that scores are screening aids only, and rejection emails are drafts requiring human review.
4. **Project 8 Individual Downloads:**
   Repurposed assets are downloaded individually (`linkedin_post.md`, `twitter_thread.md`, `newsletter.md`, `summary.json`). No bundling into ZIP archives.
5. **Project 10 Stateful Revision Limit:**
   The human-in-the-loop workflow strictly limits revisions to **two**. If a third revision is attempted, the report is automatically marked `rejected`. Rejected drafts are **never published**.

---

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Google Gemini API key (obtainable free from [Google AI Studio](https://aistudio.google.com/))
- Git

### 1. Clone & Navigate
```bash
git clone https://github.com/<your-username>/CREWAI.git
cd CREWAI
```

### 2. Create and Activate Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to supply your Gemini API key:
```ini
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 5. Run the Server
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
Visit `http://localhost:8000` in your browser.

---

## 🧪 Running Automated Tests

The test suite runs 100% offline using `unittest.mock` to mock CrewAI and LLM calls. No API key or internet access is required.

```bash
pytest tests/ -v
```

Tests cover:
- Health check (`/health`) and index dashboard (`/`).
- Validation errors and input constraints for all 10 agents.
- Path traversal protection on `/download/{run_id}/{filename}`.
- Project 10 multi-step state transitions, revision counter enforcement, and rejection safeguards.

---

## 📡 REST API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | `GET` | Serves unified HTML dashboard |
| `/health` | `GET` | Health check (returns 200 OK) |
| `/download/{run_id}/{filename}` | `GET` | Secure file download |
| `/agent1` | `POST` | Blog Post Generation |
| `/agent2` | `POST` | Competitor Analysis (requires 3 URLs) |
| `/agent3` | `POST` | Meeting Notes (form text or `.txt` upload) |
| `/agent4` | `POST` | Data Report (multipart `.csv` upload) |
| `/agent5` | `POST` | Customer Support Ticket Router |
| `/agent6` | `POST` | Resume Screening (multipart `.pdf` upload) |
| `/agent7` | `POST` | Bug Triage Flow (title and body) |
| `/agent8` | `POST` | Content Repurposing (article text, `.txt`, or URL) |
| `/agent9` | `POST` | Lead Qualification & Outreach (name and URL) |
| `/agent10/start` | `POST` | Starts Human-in-the-Loop Report session |
| `/agent10/{session_id}/review` | `POST` | Submits human review (`approve`, `revise`, `reject`) |
| `/agent10/{session_id}` | `GET` | Queries approval session status |

---

## ☁️ Deployment Guide (Render)

Deploying to [Render](https://render.com/) is straightforward via Web Service or Blueprint.

### Option A: Manual Web Service Setup (Recommended)

1. **Push your code to GitHub:**
   Ensure all changes are committed and pushed to your GitHub repository `CREWAI`.
2. **Log in to Render:**
   Navigate to [dashboard.render.com](https://dashboard.render.com/) and click **New +** > **Web Service**.
3. **Connect Repository:**
   Select your `CREWAI` repository.
4. **Configure Service:**
   - **Name:** `crewai-multi-agent-suite`
   - **Environment:** `Python 3`
   - **Region:** Any (e.g., Oregon, Frankfurt)
   - **Branch:** `main`
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn app:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type:** `Free`
5. **Set Environment Variables:**
   Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: *(Paste your Gemini API key)*
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `PYTHON_VERSION`: `3.11.8`
6. **Deploy:**
   Click **Create Web Service**. Render will build dependencies and launch your application. Once deployed, the status will show **Live** with a public `https://<service-name>.onrender.com` URL.

### Option B: Render Blueprint (`render.yaml`)

This repository contains a pre-configured `render.yaml` file:
1. In the Render Dashboard, click **New +** > **Blueprint**.
2. Connect your `CREWAI` repository.
3. Supply your `GEMINI_API_KEY` when prompted in the dashboard.
4. Click **Apply**.

---

## 📄 License & Attribution

Original agent workflows and architectures created during the CrewAI project series. Unification and web framework engineered for enterprise demonstration and deployment.
