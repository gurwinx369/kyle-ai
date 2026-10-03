from pydantic import BaseModel
from typing import Optional

class FunFactRequest(BaseModel):
    concept: str
    transcript: str
    user_profession: Optional[str] = "student"

class FunFactResponse(BaseModel):
    fun_fact: str
