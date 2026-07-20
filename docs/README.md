# Kyle AI & Ignitio Integration Documentation Index

Welcome! This folder contains minimal, structured developer documentation for the pipelines connecting the Next.js frontend, MongoDB, and the FastAPI service.

---

## 📂 Documentation Directory

1.  **[Onboarding Flow Pipeline](file:///D:/projects/kyle-ai/docs/onboarding_pipeline.md)**
    *   *Focus*: Mapping selected user tech interests into standard database roles (`developer`, `designer`, `other`) and profile creation.
2.  **[Assignments & Mid-Video Quizzes Pipeline](file:///D:/projects/kyle-ai/docs/assignments_and_quizzes_pipeline.md)**
    *   *Focus*: Regular lesson Progression, Gemini-driven written question grading, attempts thresholds (3), and 6-hour cooldown locks.
3.  **[Behavior Quiz Pipeline](file:///D:/projects/kyle-ai/docs/behavior_quiz_pipeline.md)**
    *   *Focus*: Statistical modeling of user mastery (LLR calculations, Speed-bucket confidence adjustments, and Bayes shrinkage time triggers).

---

## 🛠️ Environment Configuration

Make sure the following variables are configured in the frontend (`.env` or `.env.local`):

```ini
# Next.js Frontend Configuration
NEXT_PUBLIC_FIREBASE_API_KEY=your_firebase_api_key

# Fast API Backend endpoint
# Defaults to localhost:8000 for local development, or your production backend domain
FASTAPI_BASE_URL=http://127.0.0.1:8000
```

---

## 🚀 How to Run Locally

### 1. Launch FastAPI Backend
Ensure your virtual environment is active in `D:/projects/kyle-ai`:
```powershell
# Active virtual environment
.venv\Scripts\Activate.ps1

# Run FastAPI with hot-reloading (uvicorn)
uvicorn app.main:app --reload --port 8000
```
Verify the API is running by navigating to `http://127.0.0.1:8000/`. You should see:
```json
{"status": "FAST API IS UP AND RUNNING!"}
```

### 2. Launch Next.js Frontend
From the `d:/projects/ignitio-main-app` folder:
```bash
npm run dev
```

---

## 🩺 Debugging & Troubleshooting Checklist

*   **Firebase Authentication (JWT) Failures**: If you get a `401 Unauthorized` response from Next.js routes, verify the client is sending the ID token in the authorization header as `Bearer <token>` (do NOT send the raw user object or UID).
*   **502 Bad Gateway**: Next.js route is unable to connect to the FastAPI instance. Check that FastAPI is running on `127.0.0.1:8000`.
*   **429 Too Many Requests (Quizzes)**: Next.js has identified a prior attempt for the requested `levelId` in the `KyleHistory` collection. Clear the Mongoose document in database to re-test.
*   **423 Locked (Assignments)**: The user has either already passed the assignment or failed 3 times. Verify `lockedUntil` is expired or modify the values in `KyleHistory.assignmentHistory` for testing.
