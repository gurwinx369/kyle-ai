 # Kyle AI Microservice — API Integration & Developer Guide

This document provides a comprehensive, step-by-step implementation guide for engineers integrating the **Kyle AI FastAPI microservice** (`kyle-ai`) into the main **Ignitio Web Application** (`ignitio-main-app`).

---

## 1. System Architecture & Interaction Flow

The `kyle-ai` service acts as an isolated, high-performance AI engine responsible for Gemini-powered prompt engineering, rubrics evaluation, and behavioral statistical analysis. It does **not** connect directly to MongoDB; state management, user session tracking, locking rules, and history logs are maintained by `ignitio-main-app`.

### Architectural Layering

```mermaid
graph TD
    subgraph Client Layer
    A[Browser / Mobile Client]
    end

    subgraph Ignitio Main App (Next.js Gateway & Server)
    B[Next.js API Route Handlers /app/api/v2/kyle/...]
    C[(MongoDB / Mongoose)]
    D[Firebase Admin SDK]
    end

    subgraph Kyle AI Service (FastAPI)
    E[FastAPI Routers /api/v1/...]
    F[Firebase Auth Token Verifier]
    G[Behavior & Math Engine]
    H[Gemini AI Client Engine]
    end

    A -->|1. Client Request with Firebase JWT| B
    B -->|2. Validate Session & Check Cooldowns| C
    B -->|3. Forward Request + Bearer Token| E
    E -->|4. Verify JWT Signature| F
    E -->|5. Execute Logic / LLM Generation| H
    E -->|6. Calculate LLR & E_i Shrinkage| G
    E -->|7. Return JSON Output| B
    B -->|8. Persist Attempts & Mastery Stats| C
    B -->|9. Send Clean API Response| A
```

---

## 2. Environment Setup & Configuration

### A. Next.js (`ignitio-main-app`) Environment Configuration
Add the following configuration variables to your `.env.local` or production environment settings:

```ini
# FastAPI Service Base URL
FASTAPI_BASE_URL=http://127.0.0.1:8000

# Firebase Client & Admin SDK Configuration
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_CLIENT_EMAIL=your_firebase_client_email
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

### B. Kyle AI FastAPI (`kyle-ai`) Environment Configuration
Ensure `.env` inside `kyle-ai` contains the required AI keys and Firebase Admin configuration:

```ini
GEMINI_API_KEY=your_gemini_api_key_primary
GEMINI_API_KEY_ONE=your_gemini_api_key_backup_1
GEMINI_API_KEY_TWO=your_gemini_api_key_backup_2
GEMINI_MODEL=gemini-2.5-flash

FIREBASE_PROJECT_ID=your_firebase_project_id
FIREBASE_CLIENT_EMAIL=your_firebase_client_email
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
```

---

## 3. Authentication & Authorization Standard

Most endpoints exposed by `kyle-ai` enforce Firebase ID Token authentication via the standard HTTP `Authorization` header:

```http
Authorization: Bearer <FIREBASE_ID_TOKEN>
```

- Next.js server-side route handlers **must forward** the client's Firebase ID token or mint/pass a valid user token when calling `kyle-ai`.
- If the token is missing, expired, or invalid, `kyle-ai` returns an HTTP `401 Unauthorized` response:
  ```json
  { "detail": "Invalid or expired token" }
  ```

---

## 4. Complete API Endpoint Specifications

All endpoints are mounted under the `/api/v1` prefix.

### 4.1 Written Assignment Generation

Generates a customized, role-tailored written case study assignment based on all level transcripts completed in a day.

- **Endpoint**: `POST /api/v1/assignment/generate`
- **Auth Required**: Yes (`Bearer <token>`)
- **Headers**:
  ```http
  Authorization: Bearer <FIREBASE_ID_TOKEN>
  Content-Type: application/json
  ```

#### Request Schema (`AssignmentGenerateRequest`)
```json
{
  "role": "developer",
  "day_number": 1,
  "levels": [
    {
      "concept": "Variables and Declarations",
      "transcript": "In JavaScript, let allows reassignment while const creates immutable bindings."
    },
    {
      "concept": "Scope and Hoisting",
      "transcript": "Variables declared with var are function-scoped and hoisted, whereas let and const are block-scoped."
    }
  ]
}
```

- **Field Constraints**:
  - `role`: Must be one of `"student"`, `"developer"`, `"writer"`, `"designer"`, `"other"`.
  - `day_number`: Integer $\ge 1$.
  - `levels`: Non-empty list of level context objects containing non-empty `concept` and `transcript` strings.

#### Success Response (`200 OK`)
```json
{
  "assignment_prompt": "Scenario: You are refactoring a legacy JavaScript codebase. Analyze the scope issues introduced by 'var' in the provided code snippets and draft a step-by-step refactoring proposal using 'let' and 'const'."
}
```

---

### 4.2 Written Assignment Scoring

Evaluates a user's written submission against the day's curriculum concepts and user role using a multi-dimensional rubric.

- **Endpoint**: `POST /api/v1/assignment/score`
- **Auth Required**: Yes (`Bearer <token>`)

#### Request Schema (`AssignmentScoreRequest`)
```json
{
  "role": "developer",
  "day_number": 1,
  "levels": [
    {
      "concept": "Variables and Declarations",
      "transcript": "In JavaScript, let allows reassignment while const creates immutable bindings."
    }
  ],
  "assignment_prompt": "Scenario: You are refactoring a legacy JavaScript codebase...",
  "user_response": "I will replace all var declarations in loop counters with let to prevent variable leaking, and use const for configuration objects that do not change."
}
```

#### Success Response (`200 OK`)
```json
{
  "score": 8,
  "feedback": "Strong understanding of block scoping and const immutability. Excellent application of concepts to real-world code refactoring.",
  "passed": true,
  "breakdown": {
    "topic_relevance": 9,
    "concept_application": 8,
    "prompt_quality": 8,
    "role_aptitude": 8
  },
  "weaknesses": [
    "Could elaborate on the temporal dead zone (TDZ) behavior of let/const."
  ]
}
```

- **Passing Rule**: `passed` is `true` if `score >= 7`.

---

### 4.3 Mid-Video Quiz Generation

Generates a single multiple-choice question (with 3 shuffled options A, B, C) for instant mid-video testing.

- **Endpoint**: `POST /api/v1/quiz/generate`
- **Auth Required**: Yes (`Bearer <token>`)

#### Request Schema (`QuizGenerateRequest`)
```json
{
  "concept": "Arrow Functions & Lexical This",
  "transcript": "Arrow functions do not bind their own 'this' context; instead, they inherit 'this' lexically from the enclosing scope.",
  "role": "developer"
}
```

#### Success Response (`200 OK`)
```json
{
  "question": "How does an arrow function determine the value of 'this'?",
  "options": {
    "A": "It binds 'this' dynamically at execution time.",
    "B": "It inherits 'this' lexically from its enclosing scope.",
    "C": "It defaults to the global window object."
  },
  "correct_answer": "B",
  "explanation": "Arrow functions do not have their own 'this' binding. They capture the 'this' value of the enclosing context."
}
```

---

### 4.4 Instant Doubt Resolution

Answers learner questions in real-time, acting as Kyle (the AI mentor). Supports both `contextual` (lesson-specific) and `general` modes.

- **Endpoint**: `POST /api/v1/doubt`
- **Auth Required**: Yes (`Bearer <token>`)

#### Request Schema (`DoubtRequest`)
```json
{
  "mode": "contextual",
  "concept": "Closure and Scope Chains",
  "transcript": "A closure gives a function access to its outer scope even after the outer function has closed.",
  "role": "developer",
  "question": "Can a closure access variables defined in an outer outer function?"
}
```

- **Validation Rules**:
  - `question`: Non-empty string, maximum 500 characters.
  - If `mode` is `"contextual"`, both `concept` and `transcript` must be provided and non-empty.

#### Success Response (`200 OK`)
```json
{
  "answer": "Yes! Closures have access to the entire scope chain. This means an inner function can access variables from its immediate outer function as well as any higher-level enclosing scopes up to the global scope."
}
```

#### Service Busy Response (`503 Service Unavailable`)
If Gemini is experiencing high load, `kyle-ai` returns a structured retryable error:
```json
{
  "error": "Kyle is busy right now. Please try again in a few seconds.",
  "retryable": true
}
```

---

### 4.5 Behavior Quiz Session Creation

Initializes an out-of-band behavior evaluation session covering 3 target concepts, dynamically choosing difficulty tiers (`easy`, `medium`, `hard`) and calculating latency anchors ($E_i$).

- **Endpoint**: `POST /api/v1/behavior/session/create`
- **Auth Required**: No (Internal Next.js gateway caller)

#### Request Schema (`CreateSessionRequest`)
```json
{
  "userId": "usr_9981247",
  "modelVersion": "v1",
  "targetConcepts": [
    {
      "concept": "Closures",
      "transcriptContext": "Transcript text for closure level...",
      "levelContext": "Level 3 - Intermediate JS",
      "priorAccuracyRate": 0.85,
      "eiStats": {
        "hard": { "eiCurrent": 28000.0, "sampleCount": 4 }
      }
    },
    {
      "concept": "Event Loop",
      "transcriptContext": "Transcript text for event loop level...",
      "levelContext": "Level 4 - Asynchronous JS",
      "priorAccuracyRate": null,
      "eiStats": {}
    },
    {
      "concept": "Promises",
      "transcriptContext": "Transcript text for promise level...",
      "levelContext": "Level 5 - Async/Await",
      "priorAccuracyRate": 0.35,
      "eiStats": {}
    }
  ]
}
```

#### Success Response (`200 OK`)
```json
{
  "sessionId": "a82b9e64-771c-4b21-8f19-9231f82710da",
  "quizItems": [
    {
      "concept": "Closures",
      "difficultyTier": "hard",
      "question": "Which memory management leak risk is primarily associated with unreferenced closures?",
      "options": [
        "Retained lexical environment references in long-lived callbacks",
        "Stack overflow from recursive scope chains",
        "Garbage collection of immediate primitive parameters"
      ],
      "correctOption": "Retained lexical environment references in long-lived callbacks",
      "nOptions": 3,
      "eiSnapshot": 28000.0,
      "modelVersion": "v1"
    }
  ]
}
```

---

### 4.6 Behavior Quiz Session Grading

Grades submitted quiz attempts, calculates response time ratios, updates Empirical Bayes latency anchors ($E_i$), and computes Log-Likelihood Ratio (LLR) concept mastery verdicts.

- **Endpoint**: `POST /api/v1/behavior/session/grade`
- **Auth Required**: No (Internal Next.js gateway caller)

#### Request Schema (`GradeSessionRequest`)
```json
{
  "userId": "usr_9981247",
  "sessionId": "a82b9e64-771c-4b21-8f19-9231f82710da",
  "submittedAttempts": [
    {
      "concept": "Closures",
      "difficultyTier": "hard",
      "question": "Which memory management leak risk...",
      "selectedOption": "Retained lexical environment references in long-lived callbacks",
      "correctOption": "Retained lexical environment references in long-lived callbacks",
      "responseTimeMs": 14500,
      "nOptions": 3,
      "eiSnapshot": 28000.0,
      "modelVersion": "v1"
    }
  ],
  "priorAttemptsByConcept": {},
  "eiStatsByConceptTier": {
    "Closures::hard": { "eiCurrent": 28000.0, "sampleCount": 4 }
  }
}
```

#### Success Response (`200 OK`)
```json
{
  "gradedAttempts": [
    {
      "concept": "Closures",
      "difficultyTier": "hard",
      "question": "Which memory management leak risk...",
      "wasCorrect": true,
      "responseTimeMs": 14500,
      "speedBucket": "FAST",
      "rgbFlag": false,
      "llrContribution": 0.81,
      "nOptions": 3,
      "modelVersion": "v1"
    }
  ],
  "updatedEiStats": {
    "Closures::hard": { "eiCurrent": 26866.67, "sampleCount": 5 }
  },
  "conceptVerdicts": {
    "Closures": {
      "verdict": "MASTERY",
      "nAttempts": 5,
      "posterior": 0.88,
      "llr_total": 1.98,
      "pChance": 0.03,
      "rgbCount": 0
    }
  }
}
```

---

## 5. Next.js Integration Best Practices (`ignitio-main-app`)

Follow these strict design standards in `ignitio-main-app`:

1. **Feature-Based Architecture**: Organize all Next.js logic under `features/` (e.g., `features/kyle/`, `features/auth/`).
2. **Thin Route Handlers**: Keep `app/api/v2/kyle/...` files thin by delegating business logic to helper modules in `features/kyle/lib/`.
3. **Singleton Pattern**: Instantiate Firebase Admin SDK and HTTP Clients once.
4. **Conditional Styling**: Use the `cn()` utility (`clsx` + `tailwind-merge`) for UI styling.

### 5.1 FastAPI HTTP Client (`features/kyle/lib/kyleApiClient.js`)

```js
// features/kyle/lib/kyleApiClient.js
const FASTAPI_BASE_URL = process.env.FASTAPI_BASE_URL || "http://127.0.0.1:8000";

/**
 * Helper to execute HTTP requests from Next.js backend to Kyle AI FastAPI service.
 */
export async function callKyleAi({ endpoint, method = "POST", body, idToken }) {
  const headers = {
    "Content-Type": "application/json",
  };

  if (idToken) {
    headers["Authorization"] = `Bearer ${idToken}`;
  }

  const response = await fetch(`${FASTAPI_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.detail || errorData.error || "FastAPI request failed");
    error.status = response.status;
    error.retryable = errorData.retryable || false;
    throw error;
  }

  return response.json();
}
```

---

### 5.2 Next.js Written Assignment Submit Route (`app/api/v2/kyle/assignment/submit/route.js`)

```js
// app/api/v2/kyle/assignment/submit/route.js
import { NextResponse } from "next/server";
import { verifyFirebaseToken } from "@/lib/firebase/firebaseAdmin";
import { getKyleHistoryModel } from "@/models/v2/kyle.history.model";
import { callKyleAi } from "@/features/kyle/lib/kyleApiClient";

const ATTEMPT_LIMIT = 3;
const COOLDOWN_HOURS = 6;

export async function POST(request) {
  try {
    const authHeader = request.headers.get("authorization");
    if (!authHeader?.startsWith("Bearer ")) {
      return NextResponse.json({ data: null, error: "Unauthorized" }, { status: 401 });
    }

    const token = authHeader.split("Bearer ")[1];
    const decodedToken = await verifyFirebaseToken(token);
    const firebaseUID = decodedToken.uid;

    const body = await request.json();
    const { role, dayNumber, levels, assignmentPrompt, userResponse } = body;

    const KyleHistory = await getKyleHistoryModel();
    let historyDoc = await KyleHistory.findOne({ firebaseUID });

    if (!historyDoc) {
      historyDoc = await KyleHistory.create({ firebaseUID, assignmentHistory: [] });
    }

    // Locate existing assignment record for this day
    let assignment = historyDoc.assignmentHistory.find((a) => a.dayNumber === dayNumber);

    // Assert locking & cooldown status
    if (assignment) {
      if (assignment.passed) {
        return NextResponse.json(
          { data: null, error: "Assignment already passed for this day" },
          { status: 400 }
        );
      }

      if (assignment.locked && assignment.lockedUntil) {
        const now = new Date();
        if (now < new Date(assignment.lockedUntil)) {
          return NextResponse.json(
            {
              data: null,
              error: "Assignment locked due to 3 failed attempts. Please wait for cooldown.",
              lockedUntil: assignment.lockedUntil,
            },
            { status: 423 }
          );
        }
      }
    }

    // Call FastAPI service to score assignment
    const aiResponse = await callKyleAi({
      endpoint: "/api/v1/assignment/score",
      body: {
        role,
        day_number: dayNumber,
        levels,
        assignment_prompt: assignmentPrompt,
        user_response: userResponse,
      },
      idToken: token,
    });

    const { score, feedback, passed, breakdown, weaknesses } = aiResponse;

    // Update state in MongoDB
    if (!assignment) {
      assignment = {
        dayNumber,
        role,
        assignmentPrompt,
        attempts: [],
        attemptCount: 0,
        passed: false,
        locked: false,
        lockedUntil: null,
      };
      historyDoc.assignmentHistory.push(assignment);
      assignment = historyDoc.assignmentHistory[historyDoc.assignmentHistory.length - 1];
    }

    assignment.attempts.push({ userResponse, score, feedback, passed, submittedAt: new Date() });
    assignment.attemptCount += 1;

    if (passed) {
      assignment.passed = true;
      assignment.locked = false;
      assignment.lockedUntil = null;
      historyDoc.assignmentsPassed += 1;
    } else if (assignment.attemptCount >= ATTEMPT_LIMIT) {
      assignment.locked = true;
      const unlockTime = new Date();
      unlockTime.setHours(unlockTime.getHours() + COOLDOWN_HOURS);
      assignment.lockedUntil = unlockTime;
    }

    await historyDoc.save();

    const attemptsRemaining = Math.max(0, ATTEMPT_LIMIT - assignment.attemptCount);

    return NextResponse.json({
      data: {
        score,
        feedback,
        passed,
        attemptsRemaining: assignment.passed ? 0 : attemptsRemaining,
        lockedUntil: assignment.lockedUntil,
        breakdown,
        weaknesses,
      },
      error: null,
    });
  } catch (err) {
    console.error("Assignment submission error:", err);
    return NextResponse.json(
      { data: null, error: err.message || "Internal server error" },
      { status: err.status || 500 }
    );
  }
}
```

---

### 5.3 Frontend Client Integration Example (React Client Component)

```jsx
// features/kyle/components/AssignmentSubmitForm.js
"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";

export default function AssignmentSubmitForm({ dayNumber, role, levels, assignmentPrompt }) {
  const { user } = useAuth();
  const [userResponse, setUserResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");

    try {
      const idToken = await user.getIdToken();
      const res = await fetch("/api/v2/kyle/assignment/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${idToken}`,
        },
        body: JSON.stringify({
          role,
          dayNumber,
          levels,
          assignmentPrompt,
          userResponse,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        if (res.status === 423) {
          throw new Error(`Assignment locked until ${new Date(json.lockedUntil).toLocaleTimeString()}`);
        }
        throw new Error(json.error || "Submission failed");
      }

      setResult(json.data);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 rounded-xl bg-slate-900 p-6 text-white shadow-xl">
      <h3 className="text-xl font-bold">Day {dayNumber} Written Assignment</h3>
      <p className="text-slate-300">{assignmentPrompt}</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <textarea
          rows={6}
          className="w-full rounded-lg bg-slate-800 p-3 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          value={userResponse}
          onChange={(e) => setUserResponse(e.target.value)}
          placeholder="Write your response here..."
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-lg bg-indigo-600 px-5 py-2.5 font-semibold transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {loading ? "Evaluating with Kyle AI..." : "Submit Assignment"}
        </button>
      </form>

      {errorMsg && (
        <div className="rounded-lg bg-rose-950/80 p-4 text-rose-300 border border-rose-800">
          {errorMsg}
        </div>
      )}

      {result && (
        <div className="space-y-3 rounded-lg bg-slate-800 p-4 border border-slate-700">
          <div className="flex items-center justify-between">
            <span className="text-lg font-semibold">
              Score: <span className={result.passed ? "text-emerald-400" : "text-amber-400"}>{result.score}/10</span>
            </span>
            <span className={`px-3 py-1 text-xs font-bold rounded-full ${result.passed ? "bg-emerald-900/60 text-emerald-300" : "bg-amber-900/60 text-amber-300"}`}>
              {result.passed ? "PASSED" : "RETRY NEEDED"}
            </span>
          </div>
          <p className="text-sm text-slate-300">{result.feedback}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 6. Comprehensive Error Matrix & Resiliency Handling

| HTTP Code | Error Condition | Root Cause | Recommended Action in Next.js Gateway |
| :--- | :--- | :--- | :--- |
| **`401`** | Unauthorized | Missing or expired Firebase JWT token | Prompt user re-authentication; refresh token using `user.getIdToken(true)`. |
| **`422`** | Unprocessable Entity | Pydantic schema validation failed (e.g., negative `day_number`, empty string) | Inspect request body; sanitize client payload before forwarding. |
| **`423`** | Locked | User has failed assignment 3 times | Block submission; return `lockedUntil` timestamp to UI and display countdown timer. |
| **`429`** | Too Many Requests | Mid-video quiz already answered for `levelId` | Prevent duplicate submission; return cached attempt result to client. |
| **`503`** | Service Unavailable | Gemini API quota exceeded or high demand | Retry request up to 3 times with exponential backoff (0.5s, 1s, 2s). |
| **`500`** | Internal Server Error | Unhandled exception in FastAPI / LLM parser | Log traceback on server; return generic human-readable message to client. |

---

## 7. Production Deployment & Security Checklist

- [x] **CORS Restrictions**: In `app/main.py`, restrict `allow_origins` to your production frontend domain (e.g., `https://app.ignitio.com`) instead of `["*"]`.
- [x] **Environment Secrets**: Never commit Firebase private keys or Gemini API keys to repository version control. Use secret managers (Vercel Secrets, AWS Secrets Manager, or Railway Environment Variables).
- [x] **Private Key Formatting**: Ensure `FIREBASE_PRIVATE_KEY` handles literal `\n` characters correctly via `os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n")`.
- [x] **Timeout Limits**: Set Next.js route handler timeouts (`export const maxDuration = 30;` on Vercel) to accommodate Gemini LLM generation latencies (typically 3–8 seconds).
