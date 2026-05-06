# ABC Energy – AI Lead Qualification System (Strategic Lead Matrix)

A production-style Proof of Concept that combines **LLM-powered extraction**, **deterministic orchestration**, **real-time streaming**, and **PostgreSQL persistence** to qualify commercial energy leads through natural dialogue.

---

## Problem Statement

Build an autonomous agent that:

* Conducts a discovery conversation
* Extracts **7 key variables**
* Applies a **multi-variable qualification matrix**
* Classifies leads into priority tiers (Tier 1–3)

Includes **logic fallbacks** (e.g., estimate usage from square footage when unknown).

---

## Key Capabilities

* **Conversational Qualification** with structured extraction (function calling)
* **Deterministic Orchestration** (LLM is *not* in control of flow)
* **Logic Fallbacks** (sqft → usage estimation)
* **Streaming UX** (token-by-token updates via SSE)
* **Persistent Storage** (final lead + full transcript)
* **Idempotent Writes** (no duplicate saves per session)

---

## Qualification Matrix (Explicit Business Rules)

| Segment    | Annual Usage (MWh) | Contract Status      | Facility Detail      | Result                        |
| ---------- | ------------------ | -------------------- | -------------------- | ----------------------------- |
| Industrial | > 500              | Expiring < 6 months  | Any                  | **Tier 1 (Instant Priority)** |
| Industrial | 100–500            | Expiring < 12 months | Building Age < 5 yrs | **Tier 2 (Follow-up)**        |
| Commercial | > 50               | Month-to-Month       | Any                  | **Tier 1 (Instant Priority)** |
| Commercial | 20–50              | Fixed Term           | Building Age < 2 yrs | **Tier 3 (Nurture)**          |
| Any        | Any                | No Current Provider  | Any                  | **Tier 1 (Instant Priority)** |

> If **annual_usage_mwh** is unknown, the system **falls back** to `square_footage` to estimate usage before evaluation.

---

## The 7 Key Variables

1. `business_segment` (Industrial / Commercial)
2. `annual_usage_mwh` (or derived)
3. `square_footage` (fallback input)
4. `contract_status` (e.g., fixed, month-to-month)
5. `months_to_expiry`
6. `building_age`
7. `has_current_provider`

---

## Architecture

```text
React (TypeScript UI)
        ↓  (SSE streaming)
FastAPI Backend (async)
        ↓
Orchestrator (state machine + rules)
        ↓
PostgreSQL (Docker, SQLModel)
```

---

## Tech Stack

| Layer     | Technology                         |
| --------- | ---------------------------------- |
| Frontend  | React + TypeScript                 |
| Backend   | FastAPI (async)                    |
| AI        | OpenAI (gpt-4o-mini, tool calling) |
| DB        | PostgreSQL (Docker)                |
| ORM       | SQLModel                           |
| Streaming | Server-Sent Events (SSE)           |

---

## System Flow

1. User sends a message
2. Backend calls LLM with **tool schema** (`update_lead_info`)
3. LLM returns:

   * natural language tokens (streamed)
   * structured tool arguments (extracted fields)
4. Backend:

   * merges extracted fields into `current_state`
   * applies **fallback logic** (sqft → MWh)
   * checks **completion gates**
5. If complete → evaluate tier → persist to DB
6. Else → ask **next missing field**

---

## Orchestration Design (Deterministic)

* LLM is used **only for extraction**, not control flow
* Backend enforces:

  * required fields
  * next-question logic
  * completion criteria
  * tier evaluation

### Completion Gate (example)

```python
def is_complete(state):
    if not state.get("business_segment"):
        return False
    if not state.get("annual_usage_mwh") and not state.get("square_footage"):
        return False
    if state.get("months_to_expiry") is None:
        return False
    if state.get("building_age") is None:
        return False
    return True
```

---

## Logic Fallback (Sqft → Usage)

If the user does not know their annual energy usage, the system estimates it using square footage.

### Estimation Model

- Industrial: **0.15 MWh per sq ft**
- Commercial: **0.08 MWh per sq ft**

```python
def calculate_usage_from_sqft(sqft: float, segment: str) -> float:
    if not sqft:
        return 0

    multiplier = 0.15 if segment == "Industrial" else 0.08
    return round(sqft * multiplier, 2)
```    
> Note: Multipliers are heuristic estimates and can be refined using real-world energy datasets.
---

## API Design

### `POST /chat`

**Request**

```json
{
  "message": "string",
  "session_id": "string"
}
```

**Response**

* `text/event-stream` (SSE)
* Emits:

  * `data: <token>` (LLM text chunks)
  * `data: [METADATA]{...}` (state updates for UI)

---

## Database Schema

### `Lead`

* `session_id`
* `business_segment`
* `annual_usage_mwh`
* `tier`
* `created_at`

### `ConversationState`

* `session_id`
* `raw_transcript`
* `extracted_data_json`

> Writes occur **once per session** using a guard (`lead_saved`) to ensure idempotency.

---

## Project Structure

```text
backend/
  app/
    main.py
    orchestrator.py
    models/
      database.py
    services/
      evaluation.py
      estimation.py

frontend/
  src/
    components/
    hooks/
      useChat.ts
    pages/
```

---

## Observability & Debugging

* Structured logs for:

  * state transitions
  * tool call payloads
  * completion triggers
* Network-level inspection of SSE stream (browser DevTools)
* DB verification via psql / DBeaver
* Guardrails to prevent:

  * infinite loops
  * premature classification

---

## Performance

* Async FastAPI endpoints
* Streaming reduces **Time-to-First-Token (TTFT)**
* Minimal payloads (incremental updates)
* Connection reuse via DB sessions

---

## Evaluation Strategy (Agent Quality)

* Deterministic matrix → **verifiable outcomes**
* Test cases:

  * known inputs → expected tier
  * fallback scenarios (sqft only)
  * edge cases (missing fields)
* Compare:

  * extracted vs expected fields
  * final tier vs matrix rules

---

## Scaling Strategy (1000+ Sessions)

* Stateless API with external session store (Redis)
* Horizontal scaling (containers / Kubernetes)
* Async workers (Uvicorn + Gunicorn)
* DB connection pooling (pgBouncer)
* Streaming optimization (chunk batching)
* Rate limiting & backpressure handling

---

## Running with Docker (DB)

```bash
docker run -d \
  --name abc-energy-db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=energy_leads \
  -p 5432:5432 \
  postgres:15
```

---

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
```

`.env`

```env
DATABASE_URL=postgresql://user:password@localhost:5432/energy_leads
OPENAI_API_KEY=your_key
```

```bash
python -m app.main
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Example Interaction

```
User: I run a manufacturing plant
→ Segment: Industrial

User: 20000 sq ft
→ Usage estimated

User: 6 months
User: 2 years

→ Lead classified as Tier 1
```

---

## Design Decisions

* **Hybrid AI + Rules** → reliability over hallucination
* **Stateful Orchestrator** → guarantees completeness
* **Streaming UX** → improved perceived performance
* **DB Persistence** → auditability + analytics

---

## Future Enhancements

* CRM integrations (Salesforce / HubSpot)
* RAG for tariff insights
* Fine-tuning / LoRA for domain extraction
* Dashboard for lead analytics
* CI/CD + containerized deployment

---

## Scaling Strategy (1000+ Concurrent Sessions)

To support high concurrency and real-time interactions, the system is designed to scale horizontally with a stateless backend architecture.

### 1. Stateless Backend + External Session Store
- Move in-memory `current_state` to **Redis**
- Enables multiple backend instances to share session data
- Required for horizontal scaling

---

### 2. Horizontal Scaling (API Layer)
- Deploy FastAPI using:
  - **Uvicorn + Gunicorn workers**
- Run multiple instances behind a load balancer (NGINX / cloud LB)
- Each instance handles independent streaming requests

---

### 3. Asynchronous Streaming Optimization
- Use **async generators** for non-blocking streaming
- Minimize Time-to-First-Token (TTFT)
- Ensure each request does not block others

---

### 4. Database Scaling
- Use **connection pooling** (pgBouncer)
- Optimize writes:
  - Batch inserts if needed
  - Avoid duplicate writes (idempotency guard)
- Add indexes on:
  - `session_id`
  - `created_at`

---

### 5. Queue-Based Processing (Optional Upgrade)
- Introduce **Redis / Kafka queue** for:
  - LLM requests
  - background processing
- Prevent API overload during spikes

---

### 6. Rate Limiting & Backpressure
- Apply rate limiting per session/user
- Gracefully degrade under heavy load
- Prevent LLM API bottlenecks

---

### 7. Caching Layer
- Cache:
  - repeated prompts
  - static responses
- Reduces LLM cost and latency

---

### 8. Containerization & Deployment
- Use Docker for all services
- Deploy via:
  - Kubernetes / ECS / Cloud Run
- Enable autoscaling based on:
  - CPU / memory
  - request throughput

---

### 9. Observability & Monitoring
- Add:
  - structured logging
  - request tracing
  - metrics (latency, errors, throughput)
- Tools:
  - Prometheus + Grafana
  - OpenTelemetry

---

### 10. Fault Tolerance
- Retry failed LLM calls
- Circuit breakers for external APIs
- Graceful fallback responses

---

## Result

This architecture supports:
- 1000+ concurrent real-time sessions
- Low latency streaming responses
- High availability and fault tolerance

---


## Author

Maaz G
Full Stack Developer | AI Engineer

---

## Summary

A **production-style AI system** demonstrating:

* Real-time conversational UX
* Deterministic orchestration
* Structured data extraction
* Scalable backend design
* Persistent lead intelligence

Designed to mirror real-world AI SaaS architecture.
