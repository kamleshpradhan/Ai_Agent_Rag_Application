from fastapi import FastAPI, APIRouter
from pydantic import BaseModel
from database import connec_db
import uuid
import bcrypt
import jwt 
import datetime
import os
from dotenv import load_dotenv


app = FastAPI();
router = APIRouter()
db = connec_db()
load_dotenv()

class LoginRequest(BaseModel):
    username: str
    password: str

class signupRequest(BaseModel):
    username: str
    email: str
    password: str

@router.post("/login")
async def login(login_request: LoginRequest):
    try:
        user = db.users.find_one({"$or": [
        {"username": login_request.username},
        {"email": login_request.username}
                ]})
        print(login_request.username)
        
        if not user:
            return {"message": "User not found"}
        if bcrypt.checkpw(login_request.password.encode('utf-8'), user['password']):
            paylod = {
                "user_id": user['id'],
                "email": user['email'],
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30) 
            }
            token = jwt.encode(
                paylod, 
                os.getenv("JWT_SECRET_KEY"), 
                algorithm=os.getenv("ALGORITHM")
                )
            return {"token":token,"message": "Login successful"}
        else:
            return {"message": "Invalid credentials"}
    except Exception as ex:
        print(ex)
        return {"message": "An error occurred during login"}

@router.post("/register")
async def register(signup_request: signupRequest):
    try:
        user = db.users.find_one({"email": signup_request.email})
        if user:
            return {"message": "User already exists"}
        
        resp = db.users.insert_one({
            "id": str(uuid.uuid4()),
            "username": signup_request.username,
            "email": signup_request.email,
            "password": bcrypt.hashpw(signup_request.password.encode('utf-8') , bcrypt.gensalt(5))
        })
        if not resp.acknowledged:
            return {"message": "Registration failed"}
        else:
            return {"message": "Registration successful"}
    except Exception as ex:
        print(ex)
        return {"message": "An error occurred during registration"}