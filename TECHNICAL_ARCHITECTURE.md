# VendorSentry: Technical Architecture & Implementation Details

This document outlines the technical architecture, design decisions, feature implementations, and engineering challenges resolved during the development of the VendorSentry platform.

## 1. Technology Stack

### Frontend
* **Core:** React 18, TypeScript, Vite
* **Styling:** Tailwind CSS, Custom institutional design system
* **State Management:** React Context, Custom Hooks
* **Markdown/UI:** `react-markdown`, `remark-gfm`, Framer Motion (micro-animations)

### Backend
* **Core:** Python 3.11, FastAPI
* **Database:** PostgreSQL, SQLAlchemy (ORM), Alembic (Migrations)
* **Task Queue:** Celery, Redis (Broker & Result Backend)
* **AI Integration:** Groq API (Llama 3.1 8B Instant, Qwen fallbacks)

---

## 2. Feature Directory & Implementation Details

### 2.1 Backend & Infrastructure Features
* **Deterministic Risk Scoring Engine:** A pure-code, weighted scoring algorithm (`app/services/scoring/`) evaluating four parameters: Breach History, Data Access Scope, Compliance Maturity, and Financial Stability. AI is intentionally excluded from the calculation to prevent non-deterministic outcomes.
* **Automated Monitoring Sweeps:** Background Celery Beat tasks (`cert_watcher`, `contract_watcher`, `assessment_watcher`) that run continuously to monitor vendor compliance degradation (e.g., certifications expiring within 30 days).
* **Smart Alert Routing & Deduplication:** When monitoring sweeps detect anomalies, the system generates alerts. It utilizes hash-based deduplication keys to prevent database flooding from identical daily warnings.
* **Breach Detection Integration:** A polling service designed to query external breach databases (e.g., HaveIBeenPwned) and cross-reference them against internal vendor domains, automatically triggering a risk rescore upon a match.
* **AI Tool-Use API Layer:** A secure execution loop that translates LLM intent into strictly governed, read-only internal PostgreSQL queries. It returns JSON objects to the frontend Copilot, guaranteeing zero data hallucination.
* **Authentication & Authorization:** JWT-based login mechanism securing the API, ensuring only authorized personnel can access sensitive third-party risk intelligence.
* **CSV Data Ingestion & Seeding:** Fault-tolerant ingestion scripts capable of importing hundreds of legacy vendor records from spreadsheets, gracefully handling and logging partial row failures.

### 2.2 Frontend & UI Features
* **Portfolio Dashboard:** A high-level visual command center featuring a risk heatmap (Red/Yellow/Green distribution), historical risk trends, and an immediate feed of critical alerts.
* **Vendor Registry Grid:** A comprehensive, filterable, and sortable data table of all active vendors, displaying their composite scores, risk tiers, and next assessment dates.
* **Vendor Details Profile:** An in-depth drill-down view for individual vendors. It surfaces the granular score breakdown, exact data access scope (e.g., PII vs. Financial), active certifications, and full breach history.
* **Interactive AI Copilot:** A sliding side-drawer AI assistant that allows users to query the live database using natural language. Features include dynamic table generation, fullscreen layout expansion for dense data, and mandatory data provenance citations (showing exactly which API endpoints were used).
* **Alert Management Center:** A dedicated interface for reviewing incoming risk anomalies. Users can investigate the root cause of an alert and mark it as "Acknowledged" or "Resolved".
* **Automated Report Generation:** A one-click export feature that compiles comprehensive, markdown-based audit reports for either a specific vendor or the entire portfolio, suitable for immediate delivery to compliance regulators.
* **Document Extraction UI:** An interface allowing analysts to upload unstructured vendor contracts or SOC2 reports, kicking off an asynchronous background job for LLM-based structured data extraction.

---

## 3. Engineering Challenges & Resolutions

### 3.1 LLM Tool Schema Validation Failures
* **Challenge:** Advanced models (e.g., Llama 3.3 70B) occasionally failed strict API schema validation by returning stringified integers (e.g., `"limit": "5"`) or malformed JSON payloads.
* **Resolution:** 
  1. **Schema Simplification:** Removed problematic data types (enums, integers) from the LLM tool manifest.
  2. **Hardcoded Safeguards:** Shifted pagination and limit logic entirely to the backend execution layer.
  3. **Auto-Repair:** Implemented a regex-based `_repair_json()` middleware to intercept and correct malformed LLM tool arguments before execution.

### 3.2 AI Provider Rate Limiting
* **Challenge:** High token consumption on 70B parameter models led to HTTP 429 (Too Many Requests) errors, causing the Copilot to crash mid-query.
* **Resolution:** 
  1. Downgraded the primary reasoning engine to the highly efficient `llama-3.1-8b-instant`, which successfully handles complex tool calling at a fraction of the token cost.
  2. Implemented an automatic retry block with a fallback model (`qwen/qwen3-32b`) to gracefully handle unexpected service degradation.

### 3.3 UI Constraints with Dynamic Data Tables
* **Challenge:** Copilot queries returning large datasets generated dense Markdown tables that caused horizontal overflow and broke the standard 520px sidebar layout.
* **Resolution:** 
  1. Built custom `react-markdown` component renderers enforcing horizontal scroll wrappers and sticky `thead` elements.
  2. Engineered a layout expansion toggle, allowing the Copilot panel to transition from a drawer to a 100vw fullscreen view dynamically.

---

## 4. Security & Compliance Posture
* **Data Isolation:** The LLM only receives database subsets explicitly queried via the tool manifest. No bulk database dumps are passed into the context window.
* **Alert Deduplication:** Hash-based deduplication keys are generated for all system alerts to prevent alert fatigue during high-frequency Celery polling sweeps. 
