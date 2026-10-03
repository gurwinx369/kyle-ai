from schemas.funfact import FunFactRequest
from core.gemini_client import generate
from utils.prompts.role_context import get_role_context

async def generate_fun_fact(request: FunFactRequest) -> str:
    role_ctx = get_role_context(request.user_profession or "student")

    system_prompt = f"""You are Kibo, an AI learning mentor.
{role_ctx}

Your task is to provide a single, punchy, 1-2 sentence fun fact or "did you know" insight about the concept the user is learning.
Do not provide a long explanation. Do not use markdown. Just provide the fun fact.
Make it sound slightly retro, geeky, or encouraging, fitting your persona as a floating pet assistant.

Concept: {request.concept}
Transcript context:
{request.transcript[:3000]}
"""
    
    # We use empty prompt as the system prompt contains everything needed
    response = await generate(user_text="Provide a fun fact.", system_instruction=system_prompt)
    return response.strip()
