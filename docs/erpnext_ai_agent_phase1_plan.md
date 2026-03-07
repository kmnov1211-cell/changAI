# ERPNext AI Agent — Build It Yourself (From Scratch) Phase‑1 Blueprint

This document is written for your exact requirement: **you want to build the AI agent yourself from scratch** (not just explore existing code).

---

## 1) Phase‑1 objective (what to deliver by deadline)

Build and run a local AI agent connected to ERPNext that can answer at least these baseline business questions reliably:

1. Customer count
2. Employee count
3. Monthly purchase totals
4. Monthly sales totals

### Minimum success definition

- Runs on your local machine
- Produces read-only SQL (`SELECT` only)
- Returns correct answers for above KPI set on your ERPNext site
- Has basic logging (question, SQL, result, error)

---

## 2) What to build (clean architecture)

Build your own thin pipeline with these modules:

1. **Intent + entity parser**
   - Understand what metric is requested and any filters/date range.
2. **Schema retriever**
   - Fetch only relevant table/field metadata for the question.
3. **SQL generator**
   - LLM converts question + schema context to SQL.
4. **SQL safety validator**
   - Reject non-SELECT, dangerous keywords, invalid tables.
5. **Query executor**
   - Execute against ERPNext MariaDB in read-only mode.
6. **Response formatter**
   - Return natural-language summary + tabular payload.

Keep each module separate so debugging is easy.

---

## 3) Build order (day-by-day)

## Day 1 — Data access and SQL baseline (no AI yet)

- Connect to ERPNext DB (or via frappe.db.sql API if inside app context).
- Manually create and test SQL for 4 KPI questions.
- Validate correct table names and date fields on your real instance.

**Output:** a `kpi_queries.sql` baseline and expected answers.

You can start with this runnable baseline script in this repository: `scripts/day1_kpi_baseline.py`.

If your bench/site is `site1.local`, follow: `docs/site1_local_bench_setup.md`.

## Day 2 — API skeleton in Frappe app

Create a new API module (your own endpoint) with one whitelisted method:

- Input: `question`, optional `session_id`
- Output: `answer`, `sql`, `rows`, `status`

Start with rule-based mapping for KPI questions before LLM integration.

**Output:** endpoint returns correct KPI responses for fixed prompts.

## Day 3 — Add LLM SQL generation

- Add prompt template for SQL generation.
- Inject minimal schema context.
- Add strict validator before execution.

**Output:** free-text question -> SQL -> DB result -> response.

## Day 4 — Robustness and logging

- Add retries for malformed SQL generation.
- Add guardrails and friendly errors.
- Save logs for each request (prompt, SQL, duration, status).

**Output:** stable run with clear observability.

## Day 5 — Demo and handoff

- Run 20-question evaluation set.
- Record demo video (local hosted).
- Prepare handoff: setup steps + limitations + next phase items.

**Output:** Phase‑1 demo package.

---

## 4) Recommended folder structure (if building inside this repo)

```text
changai/changai/api/custom_agent/
  __init__.py
  endpoint.py              # whitelisted API method
  intent_parser.py         # optional (rule-based first)
  schema_context.py        # schema fetch / retrieval
  sql_generator.py         # LLM prompt + generation
  sql_validator.py         # read-only + safety checks
  db_executor.py           # execute query
  formatter.py             # answer formatting
  logger.py                # request/response logs
  prompts/
    sql_system_prompt.txt
```

---

## 5) SQL safety rules (must-have for Phase‑1)

Reject query if any of these are true:

- Not starting with `SELECT`
- Contains: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`
- Contains multiple statements (`;` in the middle)
- References tables outside allow-list

Also apply:

- Row cap (example `LIMIT 500`) for non-aggregate queries
- Timeout for query execution

---

## 6) KPI question set you should validate

Use this list during testing:

1. How many active customers do we have?
2. What is total employee count?
3. Show monthly purchase amount for last 12 months.
4. Show monthly sales amount for last 12 months.
5. Compare this month purchase vs sales.
6. Customer count by territory.
7. Employee count by department.
8. Purchase total this quarter.
9. Sales total this quarter.
10. Top 10 customers by sales in current FY.

---

## 7) Testing checklist (what your lead will care about)

- Correctness: 4 mandatory KPI questions return correct totals
- Stability: 20-question run, >= 85% valid answers
- Safety: all non-SELECT attempts blocked
- Speed: each response in acceptable time on local machine
- Usability: understandable answer text, not raw JSON only

---

## 8) Local hosting checklist

- ERPNext bench running
- LLM server running locally (Ollama or equivalent)
- API keys/config in settings doc
- Endpoint reachable from ERPNext UI or API client
- Basic logs available for troubleshooting

---

## 9) Suggested update email to your technical lead

> Hi <Lead Name>,
>
> I have started building the ERPNext AI Agent from scratch for Phase‑1 on local hosting.
>
> My first milestone is to deliver reliable answers for:
> 1) customer count,
> 2) employee count,
> 3) monthly purchase totals,
> 4) monthly sales totals.
>
> I am implementing a safe read-only text-to-SQL pipeline (intent parsing, SQL generation, validation, execution, and logging) and will share a demo plus test matrix by the deadline.
>
> Please confirm the final deadline date since the original note mentions both next Friday and 13/03/2026.

---

## 10) Phase‑2 ideas (after this deadline)

- Role/permission-aware SQL
- Chart and KPI card responses
- Scheduled KPI digests
- Regression test harness for prompt accuracy
