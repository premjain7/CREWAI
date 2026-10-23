"""Unit tests for the CrewAI Multi-Agent Suite FastAPI application.

All LLM and Crew calls are mocked to ensure:
1. Fast, offline test execution.
2. Zero paid LLM API calls during testing.
3. Deterministic verification of routes, validation, and workflow state logic.
"""

import io
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app import app
from services.file_storage import FileStorageService
from services.workflow_store import WorkflowStore

client = TestClient(app)


# -------------------------------------------------------------
# 1. Health & Core Routes
# -------------------------------------------------------------
def test_health_endpoint():
    """Verify health check responds without LLM invocation."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "CrewAI" in data["app"]


def test_index_dashboard():
    """Verify index template serves HTML dashboard containing all 10 projects."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "CrewAI Suite" in response.text
    assert "Blog Post Crew" in response.text
    assert "HITL Report Flow" in response.text


# -------------------------------------------------------------
# 2. File Download Security & Path Traversal Guards
# -------------------------------------------------------------
def test_file_storage_path_traversal_protection():
    """Verify FileStorageService prevents directory traversal attacks."""
    # Attempt to traverse upward to access app.py or system root
    traversal_path = FileStorageService.get_file_path("test_run", "../../app.py")
    assert traversal_path is None

    windows_traversal = FileStorageService.get_file_path("test_run", "..\\..\\app.py")
    assert windows_traversal is None


def test_download_file_not_found():
    """Verify non-existent download returns 404."""
    response = client.get("/download/nonexistent_run_9999/secret.md")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# -------------------------------------------------------------
# 3. Agent 1: Blog Post Crew
# -------------------------------------------------------------
@patch("app.run_blog_post", new_callable=AsyncMock)
def test_agent1_blog_post_success(mock_run):
    mock_run.return_value = {
        "run_id": "blog_123",
        "topic": "AI in 2026",
        "content": "# AI in 2026\nAgentic AI is growing fast.",
        "filename": "blog_post.md",
        "download_url": "/download/blog_123/blog_post.md",
    }

    response = client.post("/agent1", json={"topic": "AI in 2026"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["run_id"] == "blog_123"
    # The API must return the full article content, NOT a file-saved status message.
    assert "content" in data["data"]
    assert len(data["data"]["content"]) > 10
    assert "blog_post.md" in data["data"]["download_url"]
    mock_run.assert_awaited_once_with("AI in 2026")


def test_agent1_blog_post_validation():
    """Verify topic is required and validated."""
    response = client.post("/agent1", json={"topic": ""})
    assert response.status_code == 422


# -------------------------------------------------------------
# 4. Agent 2: Competitor Analysis Crew
# -------------------------------------------------------------
@patch("app.run_competitor_analysis", new_callable=AsyncMock)
def test_agent2_competitor_analysis_success(mock_run):
    mock_run.return_value = {
        "run_id": "comp_123",
        "competitors": ["https://a.com", "https://b.com", "https://c.com"],
        "content": "# Market Audit Report",
        "filename": "report.md",
        "download_url": "/download/comp_123/report.md",
    }

    urls = ["https://asana.com", "https://monday.com", "https://clickup.com"]
    response = client.post("/agent2", json={"competitors": urls})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["competitors"]) == 3


def test_agent2_competitor_analysis_validation():
    """Must provide exactly 3 competitor URLs."""
    response = client.post("/agent2", json={"competitors": ["https://onlyone.com"]})
    assert response.status_code == 422


# -------------------------------------------------------------
# 5. Agent 3: Meeting Notes Crew
# -------------------------------------------------------------
@patch("app.run_meeting_notes", new_callable=AsyncMock)
def test_agent3_meeting_notes_text(mock_run):
    mock_run.return_value = {
        "run_id": "meet_123",
        "content": "# Meeting Summary\nDecision: Approved",
        "filename": "notes.md",
        "download_url": "/download/meet_123/notes.md",
    }

    response = client.post(
        "/agent3",
        data={"transcript_text": "Alex: Let's adopt Postgres.\nSarah: Agreed."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "notes.md" in data["data"]["download_url"]


@patch("app.run_meeting_notes", new_callable=AsyncMock)
def test_agent3_meeting_notes_file_upload(mock_run):
    mock_run.return_value = {
        "run_id": "meet_456",
        "content": "# Meeting Notes from Upload",
        "filename": "notes.md",
        "download_url": "/download/meet_456/notes.md",
    }

    file_content = b"John: Deploy on Friday.\nMary: Confirmed."
    response = client.post(
        "/agent3",
        files={"file": ("transcript.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_agent3_meeting_notes_invalid_extension():
    response = client.post(
        "/agent3",
        files={"file": ("notes.pdf", io.BytesIO(b"fake pdf"), "application/pdf")},
    )
    assert response.status_code == 400
    assert "must be a .txt file" in response.json()["detail"].lower()


# -------------------------------------------------------------
# 6. Agent 4: Data Report Crew
# -------------------------------------------------------------
@patch("app.run_data_report", new_callable=AsyncMock)
def test_agent4_data_report_csv_upload(mock_run):
    mock_run.return_value = {
        "run_id": "data_123",
        "metrics": {"total_revenue": 500000, "total_units": 1000},
        "content": "# Sales Report",
        "filename": "report.md",
        "download_url": "/download/data_123/report.md",
        "csv_download_url": "/download/data_123/sales.csv",
    }

    csv_data = b"Product,Region,Units Sold,Revenue\nWidget,East,100,5000\n"
    response = client.post(
        "/agent4",
        files={"file": ("sales.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["metrics"]["total_revenue"] == 500000


def test_agent4_data_report_invalid_extension():
    response = client.post(
        "/agent4",
        files={"file": ("sales.json", io.BytesIO(b"{}"), "application/json")},
    )
    assert response.status_code == 400
    assert "requires a valid .csv file" in response.json()["detail"].lower()


# -------------------------------------------------------------
# 7. Agent 5: Customer Support Flow
# -------------------------------------------------------------
@patch("app.run_customer_support")
def test_agent5_customer_support(mock_run):
    mock_run.return_value = {
        "ticket": "Need refund on duplicate charge",
        "category": "billing",
        "priority": "high",
        "resolution": "Processed refund for duplicate transaction.",
    }

    response = client.post("/agent5", json={"ticket_text": "Need refund on duplicate charge"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["category"] == "billing"
    assert data["data"]["priority"] == "high"


# -------------------------------------------------------------
# 8. Agent 6: Resume Screening Flow
# -------------------------------------------------------------
@patch("app.run_resume_screening", new_callable=AsyncMock)
def test_agent6_resume_screening_pdf(mock_run):
    mock_run.return_value = {
        "run_id": "resume_123",
        "results": [
            {
                "name": "candidate.pdf",
                "score": 85,
                "decision": "Shortlisted for interview",
                "explanation": "Solid engineering background.",
            }
        ],
        "total_screened": 1,
        "advisory_notice": "Automated resume scores are advisory screening aids only.",
        "filename": "results.csv",
        "download_url": "/download/resume_123/results.csv",
    }

    fake_pdf = b"%PDF-1.4 Mock PDF Stream"
    response = client.post(
        "/agent6",
        files=[("files", ("candidate.pdf", io.BytesIO(fake_pdf), "application/pdf"))],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["total_screened"] == 1
    assert "advisory" in data["data"]["advisory_notice"].lower()


def test_agent6_resume_screening_no_pdf():
    response = client.post(
        "/agent6",
        files=[("files", ("document.docx", io.BytesIO(b"fake doc"), "application/octet-stream"))],
    )
    assert response.status_code == 400
    assert "no valid .pdf files" in response.json()["detail"].lower()


# -------------------------------------------------------------
# 9. Agent 7: Bug Triage Flow
# -------------------------------------------------------------
@patch("app.run_bug_triage", new_callable=AsyncMock)
def test_agent7_bug_triage(mock_run):
    mock_run.return_value = {
        "run_id": "bug_123",
        "category": "bug",
        "title": "500 Error on Checkout",
        "classification_reason": "Stack trace indicates crash.",
        "analysis": "Suggested severity: High.",
        "reply_status": "Draft ready for human review",
        "filename": "bug_triage_result.json",
        "download_url": "/download/bug_123/bug_triage_result.json",
    }

    payload = {"title": "500 Error on Checkout", "body": "Checkout button crashes with 500 error on iOS."}
    response = client.post("/agent7", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["category"] == "bug"


# -------------------------------------------------------------
# 10. Agent 8: Content Repurposing Flow
# -------------------------------------------------------------
@patch("app.run_content_repurposing", new_callable=AsyncMock)
def test_agent8_content_repurposing(mock_run):
    mock_run.return_value = {
        "run_id": "rep_123",
        "article_points": "1. Point one\n2. Point two",
        "linkedin_post": "Engaging LinkedIn post...",
        "twitter_thread": "1/5 Thread starter...",
        "newsletter": "Hello Subscribers...",
        "downloads": {
            "linkedin_post": "/download/rep_123/linkedin_post.md",
            "twitter_thread": "/download/rep_123/twitter_thread.md",
            "newsletter": "/download/rep_123/newsletter.md",
            "summary_json": "/download/rep_123/summary.json",
        },
    }

    response = client.post(
        "/agent8",
        data={"source_text": "Agentic AI is revolutionizing software development by introducing collaboration."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "linkedin_post" in data["data"]["downloads"]
    # Verify NO zip download is present
    assert "zip" not in str(data["data"]["downloads"]).lower()


# -------------------------------------------------------------
# 11. Agent 9: Lead Qualification Flow
# -------------------------------------------------------------
@patch("app.run_lead_qualification", new_callable=AsyncMock)
def test_agent9_lead_qualification(mock_run):
    mock_run.return_value = {
        "run_id": "lead_123",
        "lead_name": "Supabase",
        "website": "https://supabase.com",
        "category": "hot",
        "reasoning": "High ICP alignment.",
        "action": "Drafted personalized outreach email",
        "outreach_email": "Subject: Scaling database tier\nHi team...",
        "nurture_tips": "",
        "enrichment": "Open source Firebase alternative.",
        "table_preview": [{"Company": "Supabase", "Status": "hot"}],
        "downloads": {
            "leads.csv": "/download/lead_123/leads.csv",
            "hot_lead_outreach.csv": "/download/lead_123/hot_lead_outreach.csv",
        },
    }

    response = client.post(
        "/agent9",
        json={"lead_name": "Supabase", "website": "https://supabase.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["category"] == "hot"
    assert "leads.csv" in data["data"]["downloads"]


# -------------------------------------------------------------
# 12. Agent 10: Human-in-the-Loop Report Flow (Stateful)
# -------------------------------------------------------------
@patch("app.start_approval_report", new_callable=AsyncMock)
def test_agent10_hitl_start(mock_start):
    mock_start.return_value = {
        "session_id": "sess_hitl_001",
        "topic": "AI in Medicine",
        "audience": "Physicians",
        "draft": "# AI in Medicine Initial Draft",
        "revision_count": 0,
        "max_revisions": 2,
        "status": "pending_review",
        "message": "Report draft generated.",
    }

    response = client.post(
        "/agent10/start",
        json={"topic": "AI in Medicine", "audience": "Physicians"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["session_id"] == "sess_hitl_001"
    assert data["data"]["status"] == "pending_review"
    assert data["data"]["revision_count"] == 0


@patch("app.submit_review_decision", new_callable=AsyncMock)
def test_agent10_hitl_approve(mock_review):
    mock_review.return_value = {
        "session_id": "sess_hitl_001",
        "status": "approved",
        "decision": "approved",
        "revision_count": 0,
        "draft": "# Approved Report",
        "final_report_filename": "final_report.md",
        "download_url": "/download/sess_hitl_001/final_report.md",
        "audit_download_url": "/download/sess_hitl_001/approval_record.json",
        "message": "Report successfully approved and published.",
    }

    response = client.post(
        "/agent10/sess_hitl_001/review",
        json={"decision": "approve"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "approved"
    assert "download_url" in data["data"]


@patch("app.submit_review_decision", new_callable=AsyncMock)
def test_agent10_hitl_reject_never_published(mock_review):
    """Verify rejected reports are never published."""
    mock_review.return_value = {
        "session_id": "sess_hitl_001",
        "status": "rejected",
        "decision": "rejected",
        "revision_count": 1,
        "message": "Report rejected. Rejected reports are never published.",
        "audit_download_url": "/download/sess_hitl_001/rejection_record.json",
    }

    response = client.post(
        "/agent10/sess_hitl_001/review",
        json={"decision": "reject", "feedback": "Quality insufficient."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "rejected"
    assert "download_url" not in data["data"]


# -------------------------------------------------------------
# 13. Project 10 State & 2-Revision Limit Verification
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent10_revision_limit_enforcement(tmp_path):
    """Direct verification of WorkflowStore and submit_review_decision logic."""
    from agents.approval_report import submit_review_decision

    test_session_id = "test_limit_sess_999"
    WorkflowStore.create_session(
        session_id=test_session_id,
        topic="Edge Computing",
        audience="DevOps Engineers",
        draft="Initial draft content.",
    )

    # Revision 1 (with mock LLM)
    # run_crew_helper is now async; use AsyncMock to patch it correctly.
    with patch("agents.approval_report.run_crew_helper", new_callable=AsyncMock, return_value="Draft after Revision 1"):
        res1 = await submit_review_decision(test_session_id, "revise", "Please add edge gateway architecture.")
        assert res1["status"] == "pending_review"
        assert res1["revision_count"] == 1

    # Revision 2
    with patch("agents.approval_report.run_crew_helper", new_callable=AsyncMock, return_value="Draft after Revision 2"):
        res2 = await submit_review_decision(test_session_id, "revise", "Please include latency benchmarks.")
        assert res2["status"] == "pending_review"
        assert res2["revision_count"] == 2

    # Attempt Revision 3 -> MUST trigger automatic rejection because limit is 2
    res3 = await submit_review_decision(test_session_id, "revise", "One more change.")
    assert res3["status"] == "rejected"
    assert "maximum revision limit" in res3["message"].lower()
    assert "final_report_filename" not in res3


# -------------------------------------------------------------
# 14. Project 1: Additional Blog Post Content Correctness Tests
# -------------------------------------------------------------

@patch("app.run_blog_post", new_callable=AsyncMock)
def test_agent1_content_field_is_article_not_status_message(mock_run):
    """The 'content' field must contain the article, not a file-saved status message."""
    ARTICLE_CONTENT = "# The Future of AI\n\nArtificial intelligence is transforming industries...\n\n## Key Trends\n\nResearch shows significant progress.\n"
    mock_run.return_value = {
        "run_id": "blog_abc",
        "topic": "The Future of AI",
        "content": ARTICLE_CONTENT,
        "filename": "blog_post.md",
        "download_url": "/download/blog_abc/blog_post.md",
    }

    response = client.post("/agent1", json={"topic": "The Future of AI"})
    assert response.status_code == 200
    data = response.json()
    content = data["data"]["content"]
    # Must not be the file-saved status message
    assert not content.lower().startswith("the edited article has been saved")
    # Must contain actual article headings/paragraphs
    assert "#" in content or len(content) > 100


@patch("app.run_blog_post", new_callable=AsyncMock)
def test_agent1_empty_content_raises_error(mock_run):
    """If the article content is empty, the API should propagate a 500 error."""
    mock_run.side_effect = RuntimeError(
        "Blog post generation did not produce article content."
    )

    response = client.post("/agent1", json={"topic": "Test Topic"})
    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "blog post generation" in detail.lower() or "failed" in detail.lower()


def test_agent1_topic_too_short_fails_validation():
    """Topic shorter than 2 characters should fail with HTTP 422."""
    response = client.post("/agent1", json={"topic": "A"})
    assert response.status_code == 422


@patch("app.run_blog_post", new_callable=AsyncMock)
def test_agent1_download_url_in_response(mock_run):
    """Download URL must be present so the frontend can offer a download."""
    mock_run.return_value = {
        "run_id": "blog_download_test",
        "topic": "Test Download URL",
        "content": "# Test Article\n\nContent here.",
        "filename": "blog_post.md",
        "download_url": "/download/blog_download_test/blog_post.md",
    }

    response = client.post("/agent1", json={"topic": "Test Download URL"})
    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data["data"]
    download_url = data["data"]["download_url"]
    # Must point to the download endpoint, not a raw local file path
    assert download_url.startswith("/download/")
    assert "blog_post.md" in download_url


def test_agent1_no_os_startfile_in_blog_module():
    """Verify blog_post.py does not call os.startfile or subprocess to open editors."""
    import ast, pathlib

    source = pathlib.Path("agents/blog_post.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_calls = {"startfile", "Popen", "call", "run", "check_call", "check_output"}
    dangerous_imports = {"subprocess", "webbrowser"}

    # Check no dangerous import statements
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            module = getattr(node, "module", "") or ""
            for name in names + [module]:
                assert name not in dangerous_imports, (
                    f"blog_post.py must not import '{name}' (risk of opening editor)"
                )

    # Check no os.startfile calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in forbidden_calls:
                # Allow generic attribute access, flag only specific dangerous ones
                if func.attr == "startfile":
                    pytest.fail("blog_post.py must not call os.startfile()")


# -------------------------------------------------------------
# 15. Project 10: Additional HITL Async & State Tests
# -------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent10_start_approval_report_returns_draft():
    """start_approval_report must return draft content and pending_review status."""
    from agents.approval_report import start_approval_report

    expected_draft = "# AI in Healthcare\n\nExecutive Summary: ..."

    with patch("agents.approval_report.web_search_ddg", return_value="Search results about AI in healthcare."), \
         patch("agents.approval_report.run_crew_helper", new_callable=AsyncMock) as mock_helper:
        # First call is research, second call is draft writing
        mock_helper.side_effect = [
            "Research findings: AI improves diagnostics.",
            expected_draft,
        ]

        result = await start_approval_report("AI in Healthcare", "Physicians")

    assert result["status"] == "pending_review"
    assert result["draft"] == expected_draft
    assert "session_id" in result
    assert result["revision_count"] == 0
    assert result["max_revisions"] == 2


@pytest.mark.asyncio
async def test_agent10_create_session_signature_consistency():
    """WorkflowStore.create_session must accept all required keyword arguments."""
    session_id = "test_sig_consistency_001"
    # This call matches the exact signature used in start_approval_report().
    # If the signature changes, this test will catch the mismatch.
    session = WorkflowStore.create_session(
        session_id=session_id,
        topic="Test Topic",
        audience="Test Audience",
        research="Test Research",
        draft="Test Draft",
        max_revisions=2,
    )
    assert session["session_id"] == session_id
    assert session["status"] == "pending_review"
    assert session["revision_count"] == 0
    assert session["max_revisions"] == 2
    assert session["draft"] == "Test Draft"
    assert session["research"] == "Test Research"

    # Cleanup
    WorkflowStore._sessions.pop(session_id, None)


def test_agent10_invalid_session_returns_404():
    """Status check on a non-existent session must return 404."""
    response = client.get("/agent10/nonexistent_session_xyz_99999")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "not found" in detail.lower()


@patch("app.submit_review_decision", new_callable=AsyncMock)
def test_agent10_revise_passes_feedback(mock_review):
    """Revision request must include the human's feedback in the response."""
    mock_review.return_value = {
        "session_id": "sess_feedback_test",
        "status": "pending_review",
        "decision": "revised",
        "revision_count": 1,
        "max_revisions": 2,
        "draft": "# Revised Draft\n\nUpdated content based on feedback.",
        "message": "Revision 1/2 completed.",
    }

    response = client.post(
        "/agent10/sess_feedback_test/review",
        json={"decision": "revise", "feedback": "Please add more detail about edge cases."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "pending_review"
    assert data["data"]["revision_count"] == 1
    assert "draft" in data["data"]
    # Verify submit_review_decision was called with the correct feedback
    mock_review.assert_awaited_once_with(
        "sess_feedback_test",
        "revise",
        "Please add more detail about edge cases.",
    )


@patch("app.submit_review_decision", new_callable=AsyncMock)
def test_agent10_rejected_draft_has_no_publish_url(mock_review):
    """A rejected report must never include a download URL for the final report."""
    mock_review.return_value = {
        "session_id": "sess_no_publish",
        "status": "rejected",
        "decision": "rejected",
        "revision_count": 0,
        "message": "Report rejected. Rejected reports are never published.",
        "audit_download_url": "/download/sess_no_publish/rejection_record.json",
    }

    response = client.post(
        "/agent10/sess_no_publish/review",
        json={"decision": "reject", "feedback": "Content is inaccurate."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "rejected"
    # Must NOT have a final report download URL (only an audit record)
    assert "download_url" not in data["data"]
    assert "final_report_filename" not in data["data"]


@pytest.mark.asyncio
async def test_agent10_approve_produces_final_report():
    """Approval must write a final report file and return its download URL."""
    from agents.approval_report import submit_review_decision

    session_id = "test_approve_final_001"
    WorkflowStore.create_session(
        session_id=session_id,
        topic="Cloud Security",
        audience="CISOs",
        draft="# Cloud Security Report\n\nThis is the approved content.",
        max_revisions=2,
    )

    result = await submit_review_decision(session_id, "approve")

    assert result["status"] == "approved"
    assert result["decision"] == "approved"
    assert "final_report_filename" in result
    assert "download_url" in result
    assert result["download_url"].startswith(f"/download/{session_id}/")
    # Cleanup
    WorkflowStore._sessions.pop(session_id, None)


@pytest.mark.asyncio
async def test_agent10_revise_empty_feedback_raises():
    """Revision with no feedback must raise ValueError, not silently succeed."""
    from agents.approval_report import submit_review_decision

    session_id = "test_empty_feedback_001"
    WorkflowStore.create_session(
        session_id=session_id,
        topic="Data Privacy",
        audience="Legal Team",
        draft="# Draft",
        max_revisions=2,
    )

    import pytest
    with pytest.raises(ValueError, match="feedback"):
        await submit_review_decision(session_id, "revise", "")  # empty feedback

    # Cleanup
    WorkflowStore._sessions.pop(session_id, None)
