from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime


class UserDocument(BaseModel):
    id: str
    user_id: str
    filename: str
    content: str
    summary: str
    upload_date: datetime