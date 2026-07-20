# Kyle AI Service

Stateless FastAPI backend service for **Ignitio's** AI-driven mentor layer. It powers student assignments, mid-video concept quizzes, and cognitive behavior quizzes using Google Gemini AI, reaction latency models, and Log-Likelihood Ratio (LLR) analysis.

---

## 🏗️ Architecture & Philosophy

The Kyle AI Service is designed to be **entirely stateless**. 

*   **Stateless Execution**: The FastAPI server holds no database connection, user history, or session state. It receives all historical attempts, E_i time anchors, and request parameters directly in the payload, performs inference or math operations, and returns the updated state.
*   **Next.js Gateway**: The Next.js frontend application acts as the coordinator and database gateway. Next.js reads state from MongoDB, constructs the payload, calls FastAPI, receives the response, and atomically commits the updated metrics back to MongoDB.

```
┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
│                 │   HTTPS     │   Next.js API   │   HTTPS     │   FastAPI       │
│  Frontend Client│  ────────>  │   Gateway       │  ────────>  │   Inference     │
│                 │             │  (Reads Mongo)  │             │   (Stateless)   │
└─────────────────┘             └────────┬────────┘             └────────┬────────┘
        ▲                                │                               │
        │         Atomic Write           │                               │ Gemini API
        └────────────────────────────────┘                               ▼
                                                                 ┌───────────────┐
                                                                 │   Google      │
                                                                 │   Gemini AI   │
                                                                 └───────────────┘
```

---

## 📂 Project Directory Structure

```
D:/projects/kyle-ai/
├── app/
│   └── main.py                     # FastAPI application setup, CORS, and routing registry
├── core/
│   ├── behavior_engine.py          # Math formulas (Bayes shrinkage, Speed bucketing, LLR, Mastery classification)
│   ├── gemini_client.py            # Gemini SDK client with thread-safe multi-API-key rotation
│   └── config.py                   # Environment variable loader
├── features/
│   ├── kyle_assignment/            # Daily curriculum assignments (generate & scoring service)
│   ├── kyle_quiz/                  # Mid-video conceptual quizzes (generate service)
│   ├── kyle_behavior_quiz/         # Out-of-band behavioral sessions (create session & grade endpoints)
│   └── kyle_doubt/                 # Doubt clearance chat features (generate service)
├── schemas/
│   ├── assignment.py               # Pydantic models for assignments
│   ├── quiz.py                     # Pydantic models for regular quizzes
│   ├── behavior_quiz.py            # Pydantic models for behavior quizzes
│   ├── doubt.py                    # Pydantic models for doubts
│   └── common.py                   # RoleEnum and common types
├── utils/
│   ├── firebase/
│   │   ├── firebase_admin.py       # Firebase Admin initialization
│   │   └── token_auth.py           # Dependency injection for Bearer token verification
│   └── prompts/
│       ├── role_context.py         # Role context strings (developer, designer, writer, etc.)
│       └── system_prompts.py       # Prompt templates for Gemini generation and grading
├── pyproject.toml                  # UV project configuration
└── requirements.txt                # Pip requirements lock
```

---

## ⚙️ Core Modules & Math Models

### 1. Behavior Quiz Engine (`core/behavior_engine.py`)
Distinguishes active conceptual mastery from lucky guessing by tracking latency ratios ($r_i = t_{\text{observed}} / E_i$):
*   **Empirical Bayes Shrinkage**: Blends the user's prior median time anchor with difficulty-tier anchors (Easy = 12s, Medium = 20s, Hard = 32s) using weight $w=10$:
    $$E_{i,\text{new}} = \frac{E_{i,\text{current}} \times (10 + n) + t_{\text{observed}}}{10 + n + 1}$$
*   **Speed Bucketing**: Maps user response times to `FAST` ($r_i \le 0.5$), `MEDIUM` ($r_i \le 1.3$), `SLOW` ($r_i > 1.3$), and `GRACE` ($t_i \ge 60$s).
*   **LLR Math**: Uses predefined likelihoods for speed/accuracy pairs to compute the log-odds of a student knowing the concept vs guessing.
*   **Mastery Verdicts**: Requires a pooled posterior probability $\ge 0.75$ and a Binomial luck reject test ($p_{\text{chance}} < 0.05$ based on number of options and correct answers).

### 2. Gemini API Client with Key Rotation (`core/gemini_client.py`)
To prevent quota exhaustion (`RESOURCE_EXHAUSTED` / `429` errors), the client manages up to 4 Gemini API keys:
*   Automatically rotates keys sequentially upon catching rate limit errors.
*   Retries transient `503 Service Unavailable` errors with random jittered delays.
*   Offloads blocking synchronous SDK calls to a background thread pool via `asyncio.to_thread`.

---

## 🔄 Core Flow Diagrams

### Mid-Video Quiz Flow
```mermaid
sequenceDiagram
    autonumber
    actor User as Student
    participant FE as Frontend Client
    participant GW as Next.js Gateway
    participant BE as FastAPI Service
    participant Gemini as Gemini AI
    database DB as MongoDB (KyleHistory)

    User->>FE: Completes Video Level
    FE->>GW: POST /api/v2/kyle/quiz/generate
    GW->>BE: POST /api/v1/quiz/generate (with Firebase JWT)
    BE->>BE: verify_token()
    BE->>Gemini: Generate Quiz Question (Temp 0)
    Gemini-->>BE: Returns raw JSON
    BE->>BE: Shuffle options (A/B/C) & adjust correctAnswer
    BE-->>GW: Return Quiz (with correctAnswer & explanation)
    GW-->>FE: Return Quiz data
    User->>FE: Selects Option
    FE->>FE: Compares selection to correctAnswer (Instant feedback)
    FE->>GW: POST /api/v2/kyle/quiz/submit (Silent background write)
    GW->>DB: 429 duplicate check & push to quizHistory
```

### Behavior Quiz Flow (Session Creation & Grading)
```mermaid
sequenceDiagram
    autonumber
    actor User as Student
    participant FE as Frontend Client
    participant GW as Next.js Gateway
    participant BE as FastAPI Service
    participant Gemini as Gemini AI
    database DB as MongoDB (BehaviorQuizHistory)

    User->>FE: Completes Concept (Every 3rd triggers quiz)
    FE->>GW: POST /api/v2/kyle/behavior-quiz/trigger
    GW->>DB: Fetch user E_i anchors, counts & prior mastery levels
    GW->>BE: POST /api/v1/behavior/session/create
    BE->>BE: Select difficulty tier per concept
    BE->>Gemini: Generate 3 questions concurrently (asyncio.gather)
    Gemini-->>BE: Returns questions
    BE-->>GW: Return sessionId & quizItems
    GW->>DB: Save session shell (status: "in_progress")
    GW-->>FE: Return questions & correctAnswer keys
    Note over FE,User: User answers questions while local timer measures latency (ms)
    FE->>FE: Display immediate correct/wrong feedback
    FE->>GW: POST /api/v2/kyle/behavior-quiz/submit (silent payload)
    GW->>DB: Fetch stored session shell & prior attempts for pooling
    GW->>BE: POST /api/v1/behavior/session/grade
    BE->>BE: Evaluate Speed Buckets, LLR, update E_i, Classify Mastery
    BE-->>GW: Return graded attempts, updated E_i, & conceptVerdicts
    GW->>DB: Atomic write expectedTime & conceptMastery
    GW-->>FE: Finish session successfully
```

---

## 🚀 Getting Started

### 📋 Prerequisites
*   Python 3.10+
*   [uv](https://github.com/astral-sh/uv) (recommended) or `pip`

### 🔧 Configuration
Create a `.env` file in the root of the `D:/projects/kyle-ai` directory:

```env
# Server settings
PORT=8000
HOST=127.0.0.1

# Gemini AI Keys (Configured for Rotation)
GEMINI_API_KEY=AIzaSyPrimary...
GEMINI_API_KEY_ONE=AIzaSySecondary1...
GEMINI_API_KEY_TWO=AIzaSySecondary2...
GEMINI_API_KEY_THREE=AIzaSySecondary3...
GEMINI_MODEL=gemini-2.5-flash

# Firebase Admin SDK Credentials
FIREBASE_PROJECT_ID=ignitio-firebase-project-id
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@ignitio.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQ...\n-----END PRIVATE KEY-----\n"
```

### 🏃 Running Locally

Using **uv**:
```bash
# Install dependencies
uv pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

Using standard **pip/virtualenv**:
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

---

## 🧪 API Verification & Health Checks

Verify your setup by running:
```bash
curl http://127.0.0.1:8000/health
```
**Expected Response**:
```json
{"status": "healthy"}
```

To run behavior grading locally without Firebase header authentication bypass, check out the documentation files inside the **[docs/](file:///D:/projects/kyle-ai/docs/)** folder.
