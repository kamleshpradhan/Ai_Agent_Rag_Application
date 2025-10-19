from pydantic import BaseModel, EmailStr
from typing import List, Optional


class Document(BaseModel):
    id: str
    user_id: str
    filename: str
    content_type: str
    summary : int
    upload_date: Optional[str]