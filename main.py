from fastapi import FastAPI,Request, UploadFile, File, HTTPException, status, BackgroundTasks, WebSocket, WebSocketDisconnect,WebSocketException
import json
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from datetime import datetime
from langchain_core.messages import HumanMessage,SystemMessage, AIMessage
from dotenv import load_dotenv
import inspect
from vectorizer import AsyncDocumentVectorizer, get_chroma_collections
import uuid
import os
import asyncio
import shutil
from database import connec_db
from router.auth import router
import jwt 


app = FastAPI()

# logging for debugging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("app")

# allow local testing from other origins if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

load_dotenv()  # Load environment variables from .env file
openai_api_key = os.getenv("OPENAI_API_KEY")

# Simple in-memory stores (replace with DB for production)
documents: Dict[str, Dict[str, Any]] = {}
chats: Dict[str, List[Dict[str, Any]]] = {}


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size: int


class ChatMessageIn(BaseModel):
    role: str  # e.g., 'user' or 'assistant'
    text: str


app.include_router(router, prefix="/auth", tags=["authentication"])


@app.get("/")
async def read_root():
    return {"Hello": "World"}


def _validate_file(file: UploadFile) -> None:
    # Basic validation: allow common doc types
    allowed = ["text/plain", "application/pdf"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Unsupported file type: {file.content_type}")


document_status = {}
vectorizer = AsyncDocumentVectorizer(openai_api_key=openai_api_key, persist_directory="./chroma_db")


async def convert_to_vector(file_path: str, filename: str, document_id: str):
    """Background vectorization function"""
    try:
        # Update status
        # ensure the document_status entry exists (upload should create it, but be defensive)
        document_status.setdefault(document_id, {})
        document_status[document_id]["status"] = "processing"

        # Vectorize document — the vectorizer API may be sync or async; handle both
        maybe_result = vectorizer.vectorize_document_async(
            file_path=file_path,
            collection_name="default",
            document_id=document_id
        )

        if inspect.isawaitable(maybe_result):
            result = await maybe_result
        else:
            result = maybe_result
        
        # Update final status
        if result["success"]:
            document_status[document_id]["status"] = "completed"
            document_status[document_id]["metadata"] = result
        else:
            document_status[document_id]["status"] = "failed"
            document_status[document_id]["error"] = result["error"]
            
    except Exception as e:
        document_status[document_id]["status"] = "failed"
        document_status[document_id]["error"] = str(e)


def validate_token(request: Request):
    try:
        db = connec_db()
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

        token = parts[1]

        decoded_token = {}
        try:
            decoded_token = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

        user = db.users.find_one({"id": decoded_token["user_id"]})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return decoded_token
        
    except HTTPException:
        raise  HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed")
        



@app.post("/api/documents/upload", response_model=DocumentOut)
async def upload_document(request: Request ,file: UploadFile = File(...), 
                          background_tasks: BackgroundTasks = BackgroundTasks()):
    _validate_file(file)

    doc_id = str(uuid.uuid4())
    filename = f"{doc_id}_{os.path.basename(file.filename)}"
    dest_path = os.path.join(UPLOAD_DIR, filename)
    db = connec_db()
    decoded_token = validate_token(request)

    try:
        with open(dest_path, "wb") as out_f:
            shutil.copyfileobj(file.file, out_f)
    finally:
        file.file.close()

    size = os.path.getsize(dest_path)

    # initialize document status before scheduling the background task
    document_status[doc_id] = {"status": "pending", "path": dest_path}

    background_tasks.add_task(
        convert_to_vector,
        str(dest_path),
        filename,
        doc_id,
    )


    documents[doc_id] = {
        "id": doc_id,
        "filename": filename,
        "original_name": file.filename,
        "content_type": file.content_type,
        "size": size,
        "path": dest_path,
    }

    # initialize chat history for this doc
    chats[doc_id] = []

    try:
        db.user_documents.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": decoded_token["user_id"],
            "filename": filename.split("_",1)[1],
            "upload_date": datetime.now(),
            "document_id": doc_id
        })
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return DocumentOut(id=doc_id, filename=file.filename, content_type=file.content_type, size=size)



@app.get("/api/documents")
async def list_documents(request: Request):
    decoded_token = validate_token(request)
    db = connec_db()
    try:
        user_docs_cursor = db.user_documents.find({"user_id": decoded_token["user_id"]}, {"_id": 0})
        try:
            user_docs = list(user_docs_cursor)
        except Exception:
            try:
                user_docs = user_docs_cursor.to_list(length=None)
            except Exception:
                user_docs = []
        return user_docs
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
   


@app.delete("/api/documents/{doc_id}")
async def delete_document(request: Request, doc_id: str):
   try:
       db = connec_db()
       decoded_token = validate_token(request);
       if not decoded_token:
           raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
       resp = db.user_documents.delete_one({"document_id": doc_id, "user_id": decoded_token["user_id"]})
       if resp.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
       files = os.scandir(UPLOAD_DIR)
       for f in files:
           if f.name.startswith(doc_id+"_"):
               os.remove(f.path)
               break
       return {"detail": "Document deleted successfully"}
   except Exception as e:
       print("Some exception occured")





@app.post("/api/chat/{doc_id}")
async def post_chat(request: Request ,doc_id: str, msg: ChatMessageIn):
    try:
        db = connec_db()
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

        token = parts[1]

        decoded_token = {}
        try:
            decoded_token = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

        user = db.users.find_one({"id": decoded_token["user_id"]})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        client = ChatOpenAI(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            max_tokens=500,
            temperature=0.1
        )
        
        documents_lst = os.scandir(UPLOAD_DIR)
        document_ids = [d.name.split("_")[0] for d in documents_lst]
        if doc_id not in document_ids:  # Use your existing documents dict
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        

        doc_data = get_chroma_collections("default",doc_id)
        print(doc_data)  # Use the function from previous examples
        
        if not doc_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document content not found")
        
        
        user_message = msg.text  
        
        prompt_context = f"""Based on the following document chunks, answer the user's question.
                    Document Chunks:{doc_data["full_content"]}
                    Question: {user_message}
                    Answer based on document context:"""
        
        response = client.invoke([
            SystemMessage(content="You are a helpful AI assistant that answers questions based on provided document context."),
            HumanMessage(content=prompt_context)
        ])
        
        ai_response = response.content 
        
        # Store chat history
        if doc_id not in chats:
            chats[doc_id] = []
        
        chats[doc_id].append({
            "user_message": user_message,
            "ai_response": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        
        try:
            db.chat_history.insert_one({
                "doc_id": doc_id,
                "user_id": decoded_token["user_id"],  # Add user_id if available
                "user_message": user_message,
                "ai_response": ai_response,
                "timestamp": datetime.now()
            })
        except Exception as e:
            print(f"❌ Error saving chat history to DB: {str(e)}")
        return {"response": ai_response}
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))






@app.get("/api/chat/{doc_id}")
def get_chat_history(doc_id: str, request: Request):
    db = connec_db()
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

        token = parts[1]

        decoded_token = {}
        try:
            decoded_token = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

        user = db.users.find_one({"id": decoded_token["user_id"]})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        

        query = {"doc_id": doc_id, "user_id": decoded_token.get("user_id")}
        cursor = db.chat_history.find(query, {"_id": 0})
        try:
            messages = list(cursor)
        except Exception:
            try:
                messages = cursor.to_list(length=None)
            except Exception:
                messages = []

        return {"doc_id": doc_id, "messages": messages}
        
    except Exception as e:
        print(f"❌ Error retrieving chat history from DB: {str(e)}")
        return {"doc_id": doc_id, "messages": []}



@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    conversation_history = []
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message.strip():
                continue
            
            # Send typing indicator
            await websocket.send_text(json.dumps({
                "type": "typing",
                "status": "AI is thinking..."
            }))
            
            # Initialize non-streaming client for cleaner responses
            client = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=os.getenv("OPENAI_API_KEY"),
                max_tokens=500,
                streaming=False,  # Turn off streaming for cleaner responses
                temperature=0.7
            )
            
            # Build messages with proper history
            messages = [
                SystemMessage(content="You are a helpful assistant. Provide clear, accurate responses.")
            ]
            
            # Add recent conversation context
            for msg in conversation_history[-10:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            messages.append(HumanMessage(content=user_message))
            
            try:
                # Get complete response
                response = await client.ainvoke(messages)
                full_response = response.content
                
                # Simulate typing effect by sending chunks
                words = full_response.split()
                current_text = ""
                
                for word in words:
                    current_text += word + " "
                    await websocket.send_text(json.dumps({
                        "type": "stream",
                        "content": word + " ",
                        "full_content": current_text.strip()
                    }))
                    await asyncio.sleep(0.05)  # Typing effect
                
                # Add to history
                conversation_history.append({"role": "user", "content": user_message})
                conversation_history.append({"role": "assistant", "content": full_response})
                
                # Send completion
                await websocket.send_text(json.dumps({
                    "type": "complete",
                    "full_response": full_response
                }))
                
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error: {str(e)}"
                }))
            
    except WebSocketDisconnect:
        print("Client disconnected")
