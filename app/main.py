import importlib.util
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load routers via importlib because hyphenated directories cannot be imported normally
def load_router(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parent.parent / rel_path
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.router


assignment_gen_router = load_router(
    "_assignment_gen_router", "features/kyle-assignment/generate/router.py"
)
assignment_score_router = load_router(
    "_assignment_score_router", "features/kyle-assignment/score/router.py"
)
quiz_gen_router = load_router(
    "_quiz_gen_router", "features/kyle-quiz/generate/router.py"
)
doubt_router = load_router(
    "_doubt_router", "features/kyle-doubt/generate/router.py"
)


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


@app.get("/health")
def health_check():
    return {"status": "healthy"}
