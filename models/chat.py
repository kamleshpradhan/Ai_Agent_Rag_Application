from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class ChatMessage(BaseModel):
    id: str
    document_id: str
    usermessage: str 
    agentresp: str
    timestamp: datetime