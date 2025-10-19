from pydantic import BaseModel, EmailStr
from typing import List, Optional


class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    password: str