#!/bin/bash
# Generate an interactive HTML dashboard from overnight review results
# Usage: bash scripts/generate-review-dashboard.sh
# Output: review-results/dashboard.html

RESULTS_DIR="review-results"
OUTPUT="$RESULTS_DIR/dashboard.html"

if [ ! -d "$RESULTS_DIR" ]; then
  echo "No review-results/ directory found. Run overnight-review.sh first."
  exit 1
fi

# Count findings by severity across all files
count_severity() {
  local sev="$1"
  grep -rci "$sev" "$RESULTS_DIR"/*.md 2>/dev/null | awk -F: '{s+=$2} END {print s+0}'
}

CRITICAL=$(count_severity "CRITICAL")
HIGH=$(count_severity "\\bHIGH\\b")
MEDIUM=$(count_severity "\\bMEDIUM\\b")
LOW=$(count_severity "\\bLOW\\b")
TOTAL=$((CRITICAL + HIGH + MEDIUM + LOW))
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")

# Read each report file, escape for JS
read_file_as_js_string() {
  local file="$1"
  if [ -f "$file" ]; then
    sed 's/\\/\\\\/g; s/`/\\`/g; s/\$/\\$/g' "$file"
  else
    echo "*Report not generated.*"
  fi
}

R1=$(read_file_as_js_string "$RESULTS_DIR/01-backend-security.md")
R2=$(read_file_as_js_string "$RESULTS_DIR/02-frontend-code-quality.md")
R3=$(read_file_as_js_string "$RESULTS_DIR/03-ui-ux-review.md")
R4=$(read_file_as_js_string "$RESULTS_DIR/04-css-tailwind.md")
R5=$(read_file_as_js_string "$RESULTS_DIR/05-database-migrations.md")
R6=$(read_file_as_js_string "$RESULTS_DIR/06-architecture-integration.md")

cat > "$OUTPUT" << 'HTMLSTART'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A-Stats Code Review Dashboard</title>
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface2: #1a1a26;
    --surface3: #22222f;
    --border: #2a2a3a;
    --text: #e4e4ef;
    --text2: #8888a0;
    --brand: #6366f1;
    --brand-dim: #6366f133;
    --critical: #ef4444;
    --critical-bg: #ef444418;
    --high: #f97316;
    --high-bg: #f9731618;
    --medium: #eab308;
    --medium-bg: #eab30818;
    --low: #3b82f6;
    --low-bg: #3b82f618;
    --green: #22c55e;
    --green-bg: #22c55e18;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
  }
  .header {
    border-bottom: 1px solid var(--border);
    padding: 24px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    backdrop-filter: blur(12px);
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--bg)ee;
  }
  .header h1 {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.02em;
  }
  .header h1 span { color: var(--brand); }
  .header .timestamp { color: var(--text2); font-size: 13px; }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px 32px; }

  /* Severity cards */
  .severity-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 32px;
  }
  .sev-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }
  .sev-card .count {
    font-size: 36px;
    font-weight: 800;
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 4px;
  }
  .sev-card .label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
  .sev-critical .count { color: var(--critical); }
  .sev-critical { background: var(--critical-bg); border-color: var(--critical)33; }
  .sev-high .count { color: var(--high); }
  .sev-high { background: var(--high-bg); border-color: var(--high)33; }
  .sev-medium .count { color: var(--medium); }
  .sev-medium { background: var(--medium-bg); border-color: var(--medium)33; }
  .sev-low .count { color: var(--low); }
  .sev-low { background: var(--low-bg); border-color: var(--low)33; }
  .sev-total .count { color: var(--text); }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
    overflow-x: auto;
  }
  .tab {
    padding: 10px 18px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    color: var(--text2);
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: all 0.15s;
    background: none;
    border-top: none;
    border-left: none;
    border-right: none;
  }
  .tab:hover { color: var(--text); }
  .tab.active {
    color: var(--brand);
    border-bottom-color: var(--brand);
  }
  .tab .badge {
    display: inline-block;
    background: var(--surface3);
    color: var(--text2);
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 99px;
    margin-left: 6px;
  }
  .tab.active .badge { background: var(--brand-dim); color: var(--brand); }

  /* Report content */
  .report { display: none; }
  .report.active { display: block; }
  .report-content {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 32px;
    font-size: 14px;
    line-height: 1.8;
    overflow-x: auto;
  }
  .report-content h1 { font-size: 22px; font-weight: 700; margin: 0 0 16px; color: var(--brand); }
  .report-content h2 { font-size: 18px; font-weight: 700; margin: 28px 0 12px; padding-top: 20px; border-top: 1px solid var(--border); }
  .report-content h3 { font-size: 15px; font-weight: 600; margin: 20px 0 8px; color: var(--text); }
  .report-content h4 { font-size: 14px; font-weight: 600; margin: 16px 0 4px; }
  .report-content p { margin: 8px 0; color: var(--text); }
  .report-content ul, .report-content ol { padding-left: 24px; margin: 8px 0; }
  .report-content li { margin: 4px 0; }
  .report-content code {
    background: var(--surface3);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
  }
  .report-content pre {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
    margin: 12px 0;
  }
  .report-content pre code {
    background: none;
    padding: 0;
    font-size: 13px;
    line-height: 1.6;
  }
  .report-content strong { color: var(--text); font-weight: 600; }
  .report-content table { width: 100%; border-collapse: collapse; margin: 12px 0; }
  .report-content th, .report-content td {
    text-align: left;
    padding: 8px 12px;
    border: 1px solid var(--border);
    font-size: 13px;
  }
  .report-content th { background: var(--surface2); font-weight: 600; }
  .report-content blockquote {
    border-left: 3px solid var(--brand);
    padding-left: 16px;
    margin: 12px 0;
    color: var(--text2);
  }
  .report-content hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }

  /* Severity highlighting in content */
  .report-content .sev-tag {
    display: inline-block;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
  }

  /* Search */
  .search-bar {
    margin-bottom: 20px;
    position: relative;
  }
  .search-bar input {
    width: 100%;
    padding: 10px 16px 10px 40px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color 0.15s;
  }
  .search-bar input:focus { border-color: var(--brand); }
  .search-bar input::placeholder { color: var(--text2); }
  .search-bar svg {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text2);
  }
  .no-results {
    text-align: center;
    padding: 40px;
    color: var(--text2);
  }

  @media (max-width: 768px) {
    .severity-grid { grid-template-columns: repeat(3, 1fr); }
    .container { padding: 16px; }
    .report-content { padding: 20px; }
  }
</style>
</head>
<body>

<div class="header">
  <h1><span>A-Stats</span> Code Review Dashboard</h1>
  <div class="timestamp" id="timestamp"></div>
</div>

<div class="container">
  <div class="severity-grid">
    <div class="sev-card sev-critical"><div class="count" id="cnt-critical">-</div><div class="label">Critical</div></div>
    <div class="sev-card sev-high"><div class="count" id="cnt-high">-</div><div class="label">High</div></div>
    <div class="sev-card sev-medium"><div class="count" id="cnt-medium">-</div><div class="label">Medium</div></div>
    <div class="sev-card sev-low"><div class="count" id="cnt-low">-</div><div class="label">Low</div></div>
    <div class="sev-card sev-total"><div class="count" id="cnt-total">-</div><div class="label">Total</div></div>
  </div>

  <div class="search-bar">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
    <input type="text" id="search" placeholder="Search findings... (e.g. XSS, auth, migration)" />
  </div>

  <div class="tabs" id="tabs"></div>
  <div id="reports"></div>
</div>

<script>
HTMLSTART

# Inject report data and dynamic values
cat >> "$OUTPUT" << JSDATA
const TIMESTAMP = "${TIMESTAMP}";
const SEVERITY_COUNTS = { critical: ${CRITICAL}, high: ${HIGH}, medium: ${MEDIUM}, low: ${LOW}, total: ${TOTAL} };

const REPORTS = [
  { id: "backend-security", title: "Backend Security", content: \`${R1}\` },
  { id: "frontend-quality", title: "Frontend Quality", content: \`${R2}\` },
  { id: "ui-ux", title: "UI / UX", content: \`${R3}\` },
  { id: "css-tailwind", title: "CSS & Tailwind", content: \`${R4}\` },
  { id: "database", title: "Database & Migrations", content: \`${R5}\` },
  { id: "architecture", title: "Architecture", content: \`${R6}\` },
];
JSDATA

cat >> "$OUTPUT" << 'HTMLEND'

// ── Init ──
document.getElementById("timestamp").textContent = `Generated ${TIMESTAMP}`;
document.getElementById("cnt-critical").textContent = SEVERITY_COUNTS.critical;
document.getElementById("cnt-high").textContent = SEVERITY_COUNTS.high;
document.getElementById("cnt-medium").textContent = SEVERITY_COUNTS.medium;
document.getElementById("cnt-low").textContent = SEVERITY_COUNTS.low;
document.getElementById("cnt-total").textContent = SEVERITY_COUNTS.total;

// ── Markdown renderer (lightweight) ──
function md(text) {
  let html = text
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><code class="lang-${lang}">${code.replace(/</g,'&lt;').replace(/>/g,'&gt;')}</code></pre>`)
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Headers
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // Bold and italic
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr>')
    // Tables
    .replace(/^\|(.+)\|$/gm, (match) => {
      const cells = match.split('|').filter(c => c.trim()).map(c => c.trim());
      if (cells.every(c => /^[-:]+$/.test(c))) return '<!--sep-->';
      return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
    })
    // Blockquotes
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // Unordered lists
    .replace(/^[*-] (.+)$/gm, '<li>$1</li>')
    // Line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');

  // Wrap tables
  html = html.replace(/(<tr>[\s\S]*?<\/tr>)/g, (match) => {
    return `<table>${match.replace(/<!--sep-->/g, '')}</table>`;
  });

  // Severity tags
  html = html.replace(/\b(CRITICAL)\b/g, '<span class="sev-tag" style="background:var(--critical-bg);color:var(--critical)">CRITICAL</span>');
  html = html.replace(/\b(HIGH)\b/g, '<span class="sev-tag" style="background:var(--high-bg);color:var(--high)">HIGH</span>');
  html = html.replace(/\b(MEDIUM)\b/g, '<span class="sev-tag" style="background:var(--medium-bg);color:var(--medium)">MEDIUM</span>');
  html = html.replace(/\b(LOW)\b/g, '<span class="sev-tag" style="background:var(--low-bg);color:var(--low)">LOW</span>');

  return `<p>${html}</p>`;
}

// ── Build tabs and reports ──
const tabsEl = document.getElementById("tabs");
const reportsEl = document.getElementById("reports");

function countInReport(text) {
  const c = (text.match(/CRITICAL/gi) || []).length;
  const h = (text.match(/\bHIGH\b/gi) || []).length;
  const m = (text.match(/\bMEDIUM\b/gi) || []).length;
  const l = (text.match(/\bLOW\b/gi) || []).length;
  return c + h + m + l;
}

REPORTS.forEach((r, i) => {
  const count = countInReport(r.content);
  const btn = document.createElement("button");
  btn.className = `tab${i === 0 ? " active" : ""}`;
  btn.innerHTML = `${r.title}<span class="badge">${count}</span>`;
  btn.onclick = () => switchTab(i);
  tabsEl.appendChild(btn);

  const div = document.createElement("div");
  div.className = `report${i === 0 ? " active" : ""}`;
  div.innerHTML = `<div class="report-content">${md(r.content)}</div>`;
  reportsEl.appendChild(div);
});

function switchTab(idx) {
  document.querySelectorAll(".tab").forEach((t, i) => t.classList.toggle("active", i === idx));
  document.querySelectorAll(".report").forEach((r, i) => r.classList.toggle("active", i === idx));
}

// ── Search ──
const searchInput = document.getElementById("search");
searchInput.addEventListener("input", (e) => {
  const q = e.target.value.toLowerCase();
  if (!q) {
    document.querySelectorAll(".report-content p, .report-content h2, .report-content h3, .report-content li, .report-content pre, .report-content tr, .report-content blockquote").forEach(el => {
      el.style.display = "";
    });
    return;
  }
  document.querySelectorAll(".report").forEach(report => {
    report.querySelectorAll("h2, h3, p, li, pre, tr, blockquote").forEach(el => {
      el.style.display = el.textContent.toLowerCase().includes(q) ? "" : "none";
    });
  });
});

// Keyboard shortcut: 1-6 to switch tabs
document.addEventListener("keydown", (e) => {
  if (e.target === searchInput) return;
  const n = parseInt(e.key);
  if (n >= 1 && n <= 6) switchTab(n - 1);
  if (e.key === "/") { e.preventDefault(); searchInput.focus(); }
});
</script>
</body>
</html>
HTMLEND

echo "Dashboard generated: $OUTPUT"
echo "Open in browser: start $OUTPUT"
