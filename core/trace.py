import uuid
from typing import Optional
from fastapi import Header


def get_trace_id(x_conversation_id: Optional[str] = Header(default=None)) -> str:
    """Turn 1: client sends no header -> a new trace_id is minted and returned
    in the response body.

    Turn 2+: client echoes that same value back via the X-Conversation-ID
    header.
    """
    return x_conversation_id or str(uuid.uuid4())
