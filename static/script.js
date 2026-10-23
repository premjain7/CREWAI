/**
 * CrewAI Multi-Agent Suite - Unified Frontend Script
 */

document.addEventListener("DOMContentLoaded", () => {
  initHealthCheck();
  initNavigation();
  initSampleData();

  // Initialize individual agent handlers
  initAgent1();
  initAgent2();
  initAgent3();
  initAgent4();
  initAgent5();
  initAgent6();
  initAgent7();
  initAgent8();
  initAgent9();
  initAgent10();
});

// -------------------------------------------------------------
// Markdown & Utility Helpers
// -------------------------------------------------------------
function renderMarkdown(content) {
  if (!content) return "";
  if (window.marked && typeof window.marked.parse === "function") {
    try {
      return window.marked.parse(content);
    } catch (e) {
      console.warn("Marked.js parse error:", e);
    }
  }
  // Fallback if marked is unavailable
  const div = document.createElement("div");
  div.textContent = content;
  return "<pre>" + div.innerHTML + "</pre>";
}

function setButtonLoading(button, isLoading, normalText = "Submit") {
  if (!button) return;
  const textEl = button.querySelector(".btn-text");
  const spinnerEl = button.querySelector(".spinner");

  button.disabled = isLoading;
  if (isLoading) {
    if (textEl) textEl.textContent = "Processing...";
    if (spinnerEl) spinnerEl.classList.remove("hidden");
  } else {
    if (textEl) textEl.textContent = normalText;
    if (spinnerEl) spinnerEl.classList.add("hidden");
  }
}

function copyToClipboard(button, text) {
  if (!navigator.clipboard) {
    alert("Clipboard not available in this browser.");
    return;
  }
  navigator.clipboard.writeText(text).then(() => {
    const originalText = button.textContent;
    button.textContent = "Copied!";
    setTimeout(() => {
      button.textContent = originalText;
    }, 2000);
  });
}

// -------------------------------------------------------------
// System Health Check
// -------------------------------------------------------------
async function initHealthCheck() {
  const statusEl = document.getElementById("system-status");
  const dot = statusEl.querySelector(".status-dot");
  const label = statusEl.querySelector(".status-label");

  try {
    const resp = await fetch("/health");
    if (resp.ok) {
      dot.className = "status-dot online";
      label.textContent = "Backend API: Online";
    } else {
      dot.className = "status-dot offline";
      label.textContent = "Backend API: Error";
    }
  } catch (err) {
    dot.className = "status-dot offline";
    label.textContent = "Backend API: Offline";
  }
}

// -------------------------------------------------------------
// Sidebar Navigation
// -------------------------------------------------------------
function initNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  const panels = document.querySelectorAll(".agent-panel");

  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const agentId = btn.getAttribute("data-agent");

      navButtons.forEach((b) => b.classList.remove("active"));
      panels.forEach((p) => p.classList.remove("active"));

      btn.classList.add("active");
      const targetPanel = document.getElementById(`panel-${agentId}`);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }
    });
  });
}

// -------------------------------------------------------------
// Project 1: Blog Post Crew
// -------------------------------------------------------------
function initAgent1() {
  const form = document.getElementById("form-agent-1");
  const btn = document.getElementById("btn-agent1");
  const outputEl = document.getElementById("output-agent1");
  const copyBtn = document.getElementById("copy-agent1");
  const downloadLink = document.getElementById("download-agent1");

  let currentContent = "";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = document.getElementById("agent1-topic").value.trim();
    if (!topic) return;

    setButtonLoading(btn, true, "Generate Blog Post");
    outputEl.innerHTML = `<div class="empty-state">Researching via DuckDuckGo, drafting, and editing blog post... This may take 30-60 seconds.</div>`;

    try {
      const resp = await fetch("/agent1", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Blog post generation failed.");
      }

      currentContent = data.data.content;
      outputEl.innerHTML = renderMarkdown(currentContent);

      copyBtn.classList.remove("hidden");
      downloadLink.href = data.data.download_url;
      downloadLink.classList.remove("hidden");
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Generate Blog Post");
    }
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentContent));
}

// -------------------------------------------------------------
// Project 2: Competitor Analysis Crew
// -------------------------------------------------------------
function initAgent2() {
  const form = document.getElementById("form-agent-2");
  const btn = document.getElementById("btn-agent2");
  const outputEl = document.getElementById("output-agent2");
  const copyBtn = document.getElementById("copy-agent2");
  const downloadLink = document.getElementById("download-agent2");

  let currentContent = "";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const c1 = document.getElementById("agent2-c1").value.trim();
    const c2 = document.getElementById("agent2-c2").value.trim();
    const c3 = document.getElementById("agent2-c3").value.trim();

    if (!c1 || !c2 || !c3) return;

    setButtonLoading(btn, true, "Run Competitor Analysis");
    outputEl.innerHTML = `<div class="empty-state">Auditing 3 competitors via DuckDuckGo and synthesizing comparative matrix...</div>`;

    try {
      const resp = await fetch("/agent2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ competitors: [c1, c2, c3] }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Competitor analysis failed.");
      }

      currentContent = data.data.content;
      outputEl.innerHTML = renderMarkdown(currentContent);

      copyBtn.classList.remove("hidden");
      downloadLink.href = data.data.download_url;
      downloadLink.classList.remove("hidden");
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Run Competitor Analysis");
    }
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentContent));
}

// -------------------------------------------------------------
// Project 3: Meeting Notes Crew
// -------------------------------------------------------------
function initAgent3() {
  const form = document.getElementById("form-agent-3");
  const btn = document.getElementById("btn-agent3");
  const transcriptArea = document.getElementById("agent3-transcript");
  const fileInput = document.getElementById("agent3-file");
  const sampleBtn = document.getElementById("btn-agent3-sample");
  const outputEl = document.getElementById("output-agent3");
  const copyBtn = document.getElementById("copy-agent3");
  const downloadLink = document.getElementById("download-agent3");

  let currentContent = "";

  sampleBtn.addEventListener("click", () => {
    transcriptArea.value = `Alex (PM): Welcome team. Today we need to decide on our database migration and assign sprint tasks.
Sarah (Tech Lead): I evaluated PostgreSQL vs MongoDB for the new telemetry pipeline. Given our structured queries and relational schema, Postgres with TimescaleDB is 40% faster.
Marcus (DevOps): Agreed. I will configure the staging PostgreSQL cluster by Thursday afternoon.
Alex: Great. Sarah, can you write the schema migration script by Friday?
Sarah: Yes, I will have the migration scripts tested and submitted in PR #142 by Friday noon.
Elena (QA): I need mock dataset fixtures before Monday to begin automated integration testing.
Marcus: I'll include synthetic seed data in the staging setup.
Alex: Decision made: We are adopting PostgreSQL for telemetry. Target deployment date is November 15th.`;
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();

    if (fileInput.files.length > 0) {
      formData.append("file", fileInput.files[0]);
    } else if (transcriptArea.value.trim()) {
      formData.append("transcript_text", transcriptArea.value.trim());
    } else {
      alert("Please paste a transcript or upload a .txt file.");
      return;
    }

    setButtonLoading(btn, true, "Extract Notes & Actions");
    outputEl.innerHTML = `<div class="empty-state">Multi-agent crew parsing summary, finding action items, and logging decisions...</div>`;

    try {
      const resp = await fetch("/agent3", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Meeting notes extraction failed.");
      }

      currentContent = data.data.content;
      outputEl.innerHTML = renderMarkdown(currentContent);

      copyBtn.classList.remove("hidden");
      downloadLink.href = data.data.download_url;
      downloadLink.classList.remove("hidden");
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Extract Notes & Actions");
    }
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentContent));
}

// -------------------------------------------------------------
// Project 4: Data Report Crew
// -------------------------------------------------------------
function initAgent4() {
  const form = document.getElementById("form-agent-4");
  const btn = document.getElementById("btn-agent4");
  const fileInput = document.getElementById("agent4-file");
  const sampleBtn = document.getElementById("btn-agent4-sample");
  const outputEl = document.getElementById("output-agent4");
  const metricsBox = document.getElementById("agent4-ground-truth");
  const metricsGrid = document.getElementById("agent4-metrics-grid");
  const copyBtn = document.getElementById("copy-agent4");
  const downloadLink = document.getElementById("download-agent4");
  const downloadCsvLink = document.getElementById("download-agent4-csv");

  let currentContent = "";
  let sampleBlob = null;

  sampleBtn.addEventListener("click", () => {
    const sampleCsv = `Product,Region,Units Sold,Revenue
Cloud Server Pro,North America,120,240000
Cloud Server Pro,Europe,85,170000
Database Starter,Asia-Pacific,310,93000
Database Starter,North America,220,66000
AI Inference Tier,North America,450,450000
AI Inference Tier,Europe,310,310000
AI Inference Tier,Asia-Pacific,200,200000
Security Suite,Europe,140,112000
Security Suite,Latin America,95,76000`;

    sampleBlob = new Blob([sampleCsv], { type: "text/csv" });
    alert("Sample Sales CSV loaded into memory! Click 'Generate Verified Report' to run.");
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();

    if (fileInput.files.length > 0) {
      formData.append("file", fileInput.files[0]);
    } else if (sampleBlob) {
      formData.append("file", sampleBlob, "sample_sales.csv");
    } else {
      alert("Please upload a CSV file or click 'Use Default Sample Sales CSV'.");
      return;
    }

    setButtonLoading(btn, true, "Generate Verified Report");
    outputEl.innerHTML = `<div class="empty-state">Computing verified ground truth via Pandas and synthesizing executive report...</div>`;
    metricsBox.classList.add("hidden");

    try {
      const resp = await fetch("/agent4", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Data report analysis failed.");
      }

      currentContent = data.data.content;
      outputEl.innerHTML = renderMarkdown(currentContent);

      // Render verified metrics
      const m = data.data.metrics;
      metricsGrid.innerHTML = `
        <div class="metric-item">
          <div class="metric-label">Total Revenue</div>
          <div class="metric-val">$${Number(m.total_revenue || 0).toLocaleString()}</div>
        </div>
        <div class="metric-item">
          <div class="metric-label">Total Units Sold</div>
          <div class="metric-val">${Number(m.total_units || 0).toLocaleString()}</div>
        </div>
        <div class="metric-item">
          <div class="metric-label">Top Product (Units)</div>
          <div class="metric-val">${m.top_product_by_units || "N/A"}</div>
        </div>
        <div class="metric-item">
          <div class="metric-label">Top Region (Revenue)</div>
          <div class="metric-val">${m.top_region_by_revenue || "N/A"}</div>
        </div>
      `;
      metricsBox.classList.remove("hidden");

      copyBtn.classList.remove("hidden");
      downloadLink.href = data.data.download_url;
      downloadLink.classList.remove("hidden");

      if (data.data.csv_download_url) {
        downloadCsvLink.href = data.data.csv_download_url;
        downloadCsvLink.classList.remove("hidden");
      }
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Generate Verified Report");
    }
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentContent));
}

// -------------------------------------------------------------
// Project 5: Customer Support Router Flow
// -------------------------------------------------------------
function initAgent5() {
  const form = document.getElementById("form-agent-5");
  const btn = document.getElementById("btn-agent5");
  const ticketInput = document.getElementById("agent5-ticket");
  const outputEl = document.getElementById("output-agent5");
  const copyBtn = document.getElementById("copy-agent5");

  let currentContent = "";

  // Quick sample pill buttons
  document.querySelectorAll("#form-agent-5 .pill-btn").forEach((pill) => {
    pill.addEventListener("click", () => {
      const type = pill.getAttribute("data-sample");
      if (type === "billing") {
        ticketInput.value = "I was double charged on invoice #INV-98211 for our Enterprise subscription this morning. Please reverse the duplicate payment immediately.";
      } else if (type === "tech") {
        ticketInput.value = "Our production API endpoints are returning HTTP 500 Internal Server Error after deploying commit 49fa2. The Redis connection pool appears exhausted.";
      } else {
        ticketInput.value = "Where can I find documentation on single sign-on (SSO) SAML integration with Okta for our enterprise tier?";
      }
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ticket_text = ticketInput.value.trim();
    if (!ticket_text) return;

    setButtonLoading(btn, true, "Route & Resolve Ticket");
    outputEl.innerHTML = `<div class="empty-state">Routing ticket category, analyzing severity, and generating response...</div>`;

    try {
      const resp = await fetch("/agent5", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticket_text }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Ticket routing failed.");
      }

      const res = data.data;
      let badgeClass = "badge-warm";
      if (res.priority && res.priority.toLowerCase() === "high") {
        badgeClass = "badge-hot";
      } else if (res.priority && res.priority.toLowerCase() === "low") {
        badgeClass = "badge-cold";
      }

      currentContent = `### Category: **${(res.category || "General").toUpperCase()}**
### Priority: <span class="category-badge ${badgeClass}">${res.priority || "Medium"}</span>

---

#### Proposed Ticket Resolution
${res.resolution || "No resolution provided."}`;

      outputEl.innerHTML = renderMarkdown(currentContent);
      copyBtn.classList.remove("hidden");
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Route & Resolve Ticket");
    }
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentContent));
}

// -------------------------------------------------------------
// Project 6: Resume Screening Flow
// -------------------------------------------------------------
function initAgent6() {
  const form = document.getElementById("form-agent-6");
  const btn = document.getElementById("btn-agent6");
  const filesInput = document.getElementById("agent6-files");
  const outputEl = document.getElementById("output-agent6");
  const downloadLink = document.getElementById("download-agent6");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!filesInput.files.length) {
      alert("Please select at least one PDF resume.");
      return;
    }

    const formData = new FormData();
    for (let i = 0; i < filesInput.files.length; i++) {
      formData.append("files", filesInput.files[i]);
    }

    setButtonLoading(btn, true, "Screen Resumes");
    outputEl.innerHTML = `<div class="empty-state">Screening resumes and generating advisory candidate assessments...</div>`;

    try {
      const resp = await fetch("/agent6", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Resume screening failed.");
      }

      const results = data.data.results || [];
      let html = `<p class="text-muted mb-2">Total candidates screened: <strong>${results.length}</strong></p>`;
      html += `<table>
        <thead>
          <tr>
            <th>Candidate / File</th>
            <th>Score</th>
            <th>Advisory Status</th>
            <th>Summary & Strengths</th>
          </tr>
        </thead>
        <tbody>`;

      results.forEach((r) => {
        let badge = "badge-warm";
        if (r.decision && r.decision.toLowerCase().includes("shortlist")) badge = "badge-cold";
        if (r.decision && r.decision.toLowerCase().includes("reject")) badge = "badge-hot";

        html += `
          <tr>
            <td><strong>${r.name}</strong></td>
            <td><strong>${r.score !== null ? r.score : "N/A"}</strong> / 100</td>
            <td><span class="category-badge ${badge}">${r.decision}</span></td>
            <td>
              <p>${r.summary || r.explanation || ""}</p>
              ${r.strengths && r.strengths.length ? `<small><strong>Strengths:</strong> ${r.strengths.join(", ")}</small><br>` : ""}
              ${r.rejection_email ? `<details><summary>View Draft Rejection Email</summary><pre><code>${r.rejection_email}</code></pre></details>` : ""}
            </td>
          </tr>
        `;
      });

      html += `</tbody></table>`;
      outputEl.innerHTML = html;

      downloadLink.href = data.data.download_url;
      downloadLink.classList.remove("hidden");
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Screen Resumes");
    }
  });
}

// -------------------------------------------------------------
// Project 7: Bug Triage Flow
// -------------------------------------------------------------
function initAgent7() {
  const form = document.getElementById("form-agent-7");
  const btn = document.getElementById("btn-agent7");
  const titleInput = document.getElementById("agent7-title");
  const bodyInput = document.getElementById("agent7-body");
  const outputEl = document.getElementById("output-agent7");
  const copyBtn = document.getElementById("copy-agent7");
  const downloadLink = document.getElementById("download-agent7");

  let currentContent = "";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = titleInput.value.trim();
    const body = bodyInput.value.trim();
    if (!title || !body) return;

    setButtonLoading(btn, true, "Triage Issue");
    outputEl.innerHTML = `<div class="empty-state">Routing issue into specialized crew and analyzing triage response...</div>`;

    try {
      const resp = await fetch("/agent7", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, body }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Bug triage failed.");
      }

      const res = data.data;
      let badgeClass = "badge-hot";
      if (res.category === "feature") badgeClass = "badge-warm";
      if (res.category === "question") badgeClass = "badge-cold";

      currentContent = `### Issue Type: <span class="category-badge ${badgeClass}">${(res.category || "bug").toUpperCase()}</span>
**Status:** ${res.reply_status || "Draft ready for review"}

**Classification Rationale:**
> ${res.classification_reason || "Automated classification"}

---

### Detailed Triage Report
${res.analysis || ""}`;

      outputEl.innerHTML = renderMarkdown(currentContent);

      copyBtn.classList.remove("hidden");
      downloadLink.href = data.data.download_url;
      downloadLink.classList.remove("hidden");
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Triage Issue");
    }
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentContent));
}

// -------------------------------------------------------------
// Project 8: Content Repurposing Flow
// -------------------------------------------------------------
function initAgent8() {
  const form = document.getElementById("form-agent-8");
  const btn = document.getElementById("btn-agent8");
  const sourceArea = document.getElementById("agent8-source");
  const fileInput = document.getElementById("agent8-file");
  const sampleBtn = document.getElementById("btn-agent8-sample");
  const outputEl = document.getElementById("output-agent8");
  const downloadsContainer = document.getElementById("agent8-downloads");
  const tabButtons = document.querySelectorAll(".channel-tab-btn");

  let channelData = {
    linkedin: "",
    twitter: "",
    newsletter: "",
    points: "",
  };

  sampleBtn.addEventListener("click", () => {
    sourceArea.value = `Autonomous AI agents are transforming modern software development.
Rather than simple single-prompt completions, agentic workflows use multi-agent collaboration, explicit tool usage, and deterministic state flows.
Key advantages include:
1. Division of labor: Specialists (researchers, coders, testers) outperform generalist models on complex tasks.
2. Self-correction: Automated critique loops eliminate hallucinations and code syntax bugs before execution.
3. Human-in-the-loop: Critical business decisions remain guarded by human reviews while routine work is automated.
Organizations adopting agentic architectures in 2026 report a 3x increase in developer throughput and higher software reliability.`;
  });

  tabButtons.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabButtons.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const target = tab.getAttribute("data-tab");
      outputEl.innerHTML = renderMarkdown(channelData[target] || "<p class='text-muted'>No content generated yet.</p>");
    });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData();

    if (fileInput.files.length > 0) {
      formData.append("file", fileInput.files[0]);
    } else if (sourceArea.value.trim()) {
      formData.append("source_text", sourceArea.value.trim());
    } else {
      alert("Please provide article text, upload a .txt file, or enter an article URL.");
      return;
    }

    setButtonLoading(btn, true, "Repurpose into 3 Formats");
    outputEl.innerHTML = `<div class="empty-state">Running parallel fan-out generation across LinkedIn, Twitter, and Newsletter...</div>`;
    downloadsContainer.innerHTML = "";

    try {
      const resp = await fetch("/agent8", {
        method: "POST",
        body: formData,
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Content repurposing failed.");
      }

      channelData.linkedin = data.data.linkedin_post || "";
      channelData.twitter = data.data.twitter_thread || "";
      channelData.newsletter = data.data.newsletter || "";
      channelData.points = data.data.article_points || "";

      // Render active tab (LinkedIn by default)
      outputEl.innerHTML = renderMarkdown(channelData.linkedin);

      // Render individual download badges (strictly NO zip!)
      const downloads = data.data.downloads || {};
      downloadsContainer.innerHTML = `
        <a href="${downloads.linkedin_post}" class="btn btn-sm btn-download" download>linkedin_post.md</a>
        <a href="${downloads.twitter_thread}" class="btn btn-sm btn-download" download>twitter_thread.md</a>
        <a href="${downloads.newsletter}" class="btn btn-sm btn-download" download>newsletter.md</a>
        <a href="${downloads.summary_json}" class="btn btn-sm btn-outline" download>summary.json</a>
      `;
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Repurpose into 3 Formats");
    }
  });
}

// -------------------------------------------------------------
// Project 9: Lead Qualification Flow
// -------------------------------------------------------------
function initAgent9() {
  const form = document.getElementById("form-agent-9");
  const btn = document.getElementById("btn-agent9");
  const nameInput = document.getElementById("agent9-name");
  const websiteInput = document.getElementById("agent9-website");
  const outputEl = document.getElementById("output-agent9");
  const copyBtn = document.getElementById("copy-agent9");
  const csvPills = document.getElementById("agent9-csv-pills");

  let currentContent = "";

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const lead_name = nameInput.value.trim();
    const website = websiteInput.value.trim();
    if (!lead_name || !website) return;

    setButtonLoading(btn, true, "Qualify & Enrich Lead");
    outputEl.innerHTML = `<div class="empty-state">Enriching domain via search, evaluating ICP fit, and generating outreach...</div>`;

    try {
      const resp = await fetch("/agent9", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead_name, website }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Lead qualification failed.");
      }

      const res = data.data;
      let badgeClass = "badge-warm";
      if (res.category === "hot") badgeClass = "badge-hot";
      if (res.category === "cold") badgeClass = "badge-cold";

      currentContent = `### Lead: **${res.lead_name}** (<a href="${res.website}" target="_blank">${res.website}</a>)
**Status:** <span class="category-badge ${badgeClass}">${(res.category || "warm").toUpperCase()}</span>

**Action Taken:** ${res.action || "Evaluated lead"}

**Qualification Reasoning:**
> ${res.reasoning || "Standard qualification"}

---

${res.outreach_email ? `### Personalized Outreach Email Draft\n${res.outreach_email}\n` : ""}
${res.nurture_tips ? `### Educational Nurture Content Plan\n${res.nurture_tips}\n` : ""}

---
#### Enrichment Notes
${res.enrichment || "No enrichment notes available."}`;

      outputEl.innerHTML = renderMarkdown(currentContent);
      copyBtn.classList.remove("hidden");

      // Render CSV download pills
      const downloads = res.downloads || {};
      const downloadKeys = Object.keys(downloads);
      if (downloadKeys.length > 0) {
        csvPills.innerHTML = downloadKeys
          .map((k) => `<a href="${downloads[k]}" class="csv-pill-link" download>&#11123; ${k}</a>`)
          .join(" ");
      } else {
        csvPills.innerHTML = `<span class="text-muted">No CSV exports generated.</span>`;
      }
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(btn, false, "Qualify & Enrich Lead");
    }
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentContent));
}

// -------------------------------------------------------------
// Project 10: Human-in-the-Loop Report Flow
// -------------------------------------------------------------
function initAgent10() {
  const startForm = document.getElementById("form-agent-10-start");
  const startBtn = document.getElementById("btn-agent10-start");
  const topicInput = document.getElementById("agent10-topic");
  const audienceInput = document.getElementById("agent10-audience");

  const stageStart = document.getElementById("agent10-stage-start");
  const stageReview = document.getElementById("agent10-stage-review");
  const stageComplete = document.getElementById("agent10-stage-complete");

  const sessionIdEl = document.getElementById("agent10-session-id");
  const revCountEl = document.getElementById("agent10-rev-count");
  const meterFill = document.getElementById("agent10-meter-fill");
  const feedbackInput = document.getElementById("agent10-feedback");
  const feedbackSection = document.getElementById("agent10-feedback-section");

  const btnApprove = document.getElementById("btn-agent10-approve");
  const btnReject = document.getElementById("btn-agent10-reject");
  const btnRevise = document.getElementById("btn-agent10-revise");
  const btnRestart = document.getElementById("btn-agent10-restart");

  const statusChip = document.getElementById("agent10-status-chip");
  const outputEl = document.getElementById("output-agent10");
  const copyBtn = document.getElementById("copy-agent10");
  const downloadLink = document.getElementById("download-agent10");

  const terminalTitle = document.getElementById("agent10-terminal-title");
  const terminalMsg = document.getElementById("agent10-terminal-msg");
  const terminalDownloads = document.getElementById("agent10-terminal-downloads");

  let currentSessionId = "";
  let currentDraft = "";
  let revisionCount = 0;
  const MAX_REVISIONS = 2;

  function updateStatus(status) {
    statusChip.className = "status-chip";
    if (status === "pending_review") {
      statusChip.classList.add("chip-pending");
      statusChip.textContent = "Pending Review";
    } else if (status === "approved") {
      statusChip.classList.add("chip-approved");
      statusChip.textContent = "Approved & Published";
    } else if (status === "rejected") {
      statusChip.classList.add("chip-rejected");
      statusChip.textContent = "Rejected";
    } else {
      statusChip.textContent = status;
    }
  }

  function updateRevisionMeter(count) {
    revisionCount = count;
    revCountEl.textContent = `${count} / ${MAX_REVISIONS}`;
    const pct = (count / MAX_REVISIONS) * 100;
    meterFill.style.width = `${pct}%`;

    if (count >= MAX_REVISIONS) {
      btnRevise.disabled = true;
      btnRevise.textContent = "Max Revisions Reached (2/2)";
      btnRevise.classList.add("btn-outline");
      feedbackSection.querySelector("label").textContent = "Maximum 2 revisions reached. Please Approve or Reject.";
      feedbackInput.disabled = true;
    } else {
      btnRevise.disabled = false;
      btnRevise.textContent = "Request Revision";
      btnRevise.classList.remove("btn-outline");
      feedbackInput.disabled = false;
    }
  }

  // Stage 1: Start Flow
  startForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const topic = topicInput.value.trim();
    const audience = audienceInput.value.trim();
    if (!topic) return;

    setButtonLoading(startBtn, true, "Generate Initial Draft");
    outputEl.innerHTML = `<div class="empty-state">Generating initial report draft for human review...</div>`;

    try {
      const resp = await fetch("/agent10/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, audience }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Failed to start approval report flow.");
      }

      const res = data.data;
      currentSessionId = res.session_id;
      currentDraft = res.draft;
      sessionIdEl.textContent = currentSessionId;

      updateStatus(res.status);
      updateRevisionMeter(res.revision_count || 0);

      outputEl.innerHTML = renderMarkdown(currentDraft);
      copyBtn.classList.remove("hidden");

      // Switch view to review controls
      stageStart.classList.add("hidden");
      stageReview.classList.remove("hidden");
      stageComplete.classList.add("hidden");
    } catch (err) {
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#9888;</div><div class="banner-text"><strong>Error:</strong> ${err.message}</div></div>`;
    } finally {
      setButtonLoading(startBtn, false, "Generate Initial Draft");
    }
  });

  // Decision 1: Approve
  btnApprove.addEventListener("click", async () => {
    if (!currentSessionId) return;
    setButtonLoading(btnApprove, true, "Approve & Publish");

    try {
      const resp = await fetch(`/agent10/${currentSessionId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: "approve" }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Approval submission failed.");
      }

      const res = data.data;
      updateStatus("approved");

      stageReview.classList.add("hidden");
      stageComplete.classList.remove("hidden");

      terminalTitle.textContent = "Report Approved & Published";
      terminalTitle.style.color = "var(--success)";
      terminalMsg.textContent = res.message;

      terminalDownloads.innerHTML = `
        <a href="${res.download_url}" class="btn btn-sm btn-download" download>Download Final Report (.md)</a>
        <a href="${res.audit_download_url}" class="btn btn-sm btn-outline" download>Audit Record (.json)</a>
      `;

      downloadLink.href = res.download_url;
      downloadLink.classList.remove("hidden");
    } catch (err) {
      alert(`Error approving report: ${err.message}`);
    } finally {
      setButtonLoading(btnApprove, false, "Approve & Publish");
    }
  });

  // Decision 2: Revise
  btnRevise.addEventListener("click", async () => {
    if (!currentSessionId) return;
    const feedback = feedbackInput.value.trim();
    if (!feedback) {
      alert("Please provide revision feedback explaining what changes are needed.");
      feedbackInput.focus();
      return;
    }

    setButtonLoading(btnRevise, true, "Request Revision");
    outputEl.innerHTML = `<div class="empty-state">Revising report using human feedback (Revision ${revisionCount + 1} of ${MAX_REVISIONS})...</div>`;

    try {
      const resp = await fetch(`/agent10/${currentSessionId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: "revise", feedback }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Revision request failed.");
      }

      const res = data.data;
      if (res.status === "rejected") {
        // Automatically rejected because limit was reached
        updateStatus("rejected");
        stageReview.classList.add("hidden");
        stageComplete.classList.remove("hidden");
        terminalTitle.textContent = "Report Rejected (Limit Reached)";
        terminalTitle.style.color = "var(--danger)";
        terminalMsg.textContent = res.message;
        terminalDownloads.innerHTML = `<a href="${res.audit_download_url}" class="btn btn-sm btn-outline" download>Audit Record (.json)</a>`;
        outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#10005;</div><div class="banner-text"><strong>Report Rejected:</strong> Reached maximum revision limit of 2. Rejected reports are never published.</div></div>`;
      } else {
        currentDraft = res.draft;
        outputEl.innerHTML = renderMarkdown(currentDraft);
        updateRevisionMeter(res.revision_count);
        feedbackInput.value = "";
      }
    } catch (err) {
      alert(`Error requesting revision: ${err.message}`);
      outputEl.innerHTML = renderMarkdown(currentDraft);
    } finally {
      setButtonLoading(btnRevise, false, "Request Revision");
    }
  });

  // Decision 3: Reject
  btnReject.addEventListener("click", async () => {
    if (!currentSessionId) return;
    const confirmed = confirm("Are you sure you want to reject this report? Rejected reports are never published.");
    if (!confirmed) return;

    setButtonLoading(btnReject, true, "Reject Report");
    const feedback = feedbackInput.value.trim() || "Rejected by reviewer.";

    try {
      const resp = await fetch(`/agent10/${currentSessionId}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: "reject", feedback }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || "Rejection failed.");
      }

      const res = data.data;
      updateStatus("rejected");

      stageReview.classList.add("hidden");
      stageComplete.classList.remove("hidden");

      terminalTitle.textContent = "Report Rejected";
      terminalTitle.style.color = "var(--danger)";
      terminalMsg.textContent = "This report draft was rejected and will not be published.";

      terminalDownloads.innerHTML = `
        <a href="${res.audit_download_url}" class="btn btn-sm btn-outline" download>Rejection Audit Record (.json)</a>
      `;

      downloadLink.classList.add("hidden");
      outputEl.innerHTML = `<div class="advisory-banner"><div class="banner-icon">&#10005;</div><div class="banner-text"><strong>Report Rejected:</strong> This document was rejected by human review and will not be published.</div></div>`;
    } catch (err) {
      alert(`Error rejecting report: ${err.message}`);
    } finally {
      setButtonLoading(btnReject, false, "Reject Report");
    }
  });

  // Restart Flow
  btnRestart.addEventListener("click", () => {
    currentSessionId = "";
    currentDraft = "";
    revisionCount = 0;
    updateRevisionMeter(0);
    updateStatus("idle");

    stageStart.classList.remove("hidden");
    stageReview.classList.add("hidden");
    stageComplete.classList.add("hidden");

    copyBtn.classList.add("hidden");
    downloadLink.classList.add("hidden");
    outputEl.innerHTML = `<div class="empty-state">Start a topic to generate an initial draft for human review.</div>`;
  });

  copyBtn.addEventListener("click", () => copyToClipboard(copyBtn, currentDraft));
}

function initSampleData() {
  // Global sample initializer placeholder if needed
}
