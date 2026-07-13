from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from features.kyle_assignment.generate.router import router as assignment_gen_router
from features.kyle_assignment.score.router import router as assignment_score_router
from features.kyle_quiz.generate.router import router as quiz_gen_router
from features.kyle_doubt.generate.router import router as doubt_router
from features.kyle_behavior_quiz.generate.router import router as behavior_gen_router
from features.kyle_behavior_quiz.submit.router import router as behavior_submit_router

app = FastAPI(
    title="Kyle AI Service",
    description="FastAPI backend for Ignitio's AI mentor",
    version="1.0.0",
)

# In production, restrict this to the actual ignitio-main-app domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assignment_gen_router, prefix="/api/v1", tags=["Assignment"])
app.include_router(assignment_score_router, prefix="/api/v1", tags=["Assignment"])
app.include_router(quiz_gen_router, prefix="/api/v1", tags=["Quiz"])
app.include_router(doubt_router, prefix="/api/v1", tags=["Doubt"])
app.include_router(behavior_gen_router, prefix="/api/v1", tags=["Behavior Quiz"])
app.include_router(behavior_submit_router, prefix="/api/v1", tags=["Behavior Quiz"])

@app.get("/")
def entry_route():
    return {"status": "FAST API IS UP AND RUNNING!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
