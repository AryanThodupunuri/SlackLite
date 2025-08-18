from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import jwt
import bcrypt
import uuid
import os
import json
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from pathlib import Path
import aiofiles
import mimetypes

# Environment setup
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="SlackLite API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "slack-lite-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Security
security = HTTPBearer()

# Database setup
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.slacklite

# File upload setup
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    is_online: bool = False
    avatar_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Channel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    created_by: str
    members: List[str] = []
    is_public: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    sender_id: str
    sender_username: str
    channel_id: Optional[str] = None
    recipient_id: Optional[str] = None
    message_type: str = "text"  # text, file, image
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    reactions: Dict[str, List[str]] = {}  # emoji -> [user_ids]
    edited_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MessageCreate(BaseModel):
    content: str
    channel_id: Optional[str] = None
    recipient_id: Optional[str] = None

class MessageEdit(BaseModel):
    content: str

class ReactionAdd(BaseModel):
    emoji: str

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_channels: Dict[str, List[str]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, username: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # Update user online status
        await db.users.update_one(
            {"id": user_id}, 
            {"$set": {"is_online": True}}
        )
        
        # Notify all users about online status
        await self.broadcast_user_status(user_id, username, True)
        
    async def disconnect(self, user_id: str, username: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
        # Update user offline status
        await db.users.update_one(
            {"id": user_id}, 
            {"$set": {"is_online": False}}
        )
        
        # Notify all users about offline status
        await self.broadcast_user_status(user_id, username, False)
        
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(json.dumps(message))
            
    async def broadcast_to_channel(self, message: dict, channel_id: str):
        # Get channel members
        channel = await db.channels.find_one({"id": channel_id})
        if channel:
            for member_id in channel.get("members", []):
                if member_id in self.active_connections:
                    await self.active_connections[member_id].send_text(json.dumps(message))
                    
    async def broadcast_user_status(self, user_id: str, username: str, is_online: bool):
        status_message = {
            "type": "user_status",
            "user_id": user_id,
            "username": username,
            "is_online": is_online,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all connected users
        for connection in self.active_connections.values():
            try:
                await connection.send_text(json.dumps(status_message))
            except:
                pass  # Connection might be closed

manager = ConnectionManager()

# Authentication helpers
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# API Routes

@app.post("/api/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({
        "$or": [{"username": user_data.username}, {"email": user_data.email}]
    })
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user = User(username=user_data.username, email=user_data.email)
    
    # Store in database
    user_doc = user.dict()
    user_doc["password_hash"] = hashed_password
    await db.users.insert_one(user_doc)
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.post("/api/auth/login")
async def login(login_data: UserLogin):
    # Find user
    user_doc = await db.users.find_one({"username": login_data.username})
    if not user_doc or not verify_password(login_data.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    user = User(**user_doc)
    access_token = create_access_token(data={"sub": user.id})
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.get("/api/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.get("/api/users", response_model=List[User])
async def get_users(current_user: User = Depends(get_current_user)):
    users = await db.users.find({}, {"password_hash": 0}).to_list(length=None)
    return [User(**user) for user in users]

# Channel endpoints
@app.post("/api/channels", response_model=Channel)
async def create_channel(channel_data: ChannelCreate, current_user: User = Depends(get_current_user)):
    # Check if channel name exists
    existing_channel = await db.channels.find_one({"name": channel_data.name})
    if existing_channel:
        raise HTTPException(status_code=400, detail="Channel name already exists")
    
    channel = Channel(
        name=channel_data.name,
        description=channel_data.description,
        created_by=current_user.id,
        members=[current_user.id],
        is_public=channel_data.is_public
    )
    
    await db.channels.insert_one(channel.dict())
    return channel

@app.get("/api/channels", response_model=List[Channel])
async def get_channels(current_user: User = Depends(get_current_user)):
    # Get public channels and private channels where user is a member
    channels = await db.channels.find({
        "$or": [
            {"is_public": True},
            {"members": current_user.id}
        ]
    }).to_list(length=None)
    return [Channel(**channel) for channel in channels]

@app.post("/api/channels/{channel_id}/join")
async def join_channel(channel_id: str, current_user: User = Depends(get_current_user)):
    channel = await db.channels.find_one({"id": channel_id})
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if not channel["is_public"]:
        raise HTTPException(status_code=403, detail="Cannot join private channel")
    
    # Add user to channel members
    await db.channels.update_one(
        {"id": channel_id},
        {"$addToSet": {"members": current_user.id}}
    )
    
    return {"message": "Joined channel successfully"}

@app.post("/api/channels/{channel_id}/leave")
async def leave_channel(channel_id: str, current_user: User = Depends(get_current_user)):
    await db.channels.update_one(
        {"id": channel_id},
        {"$pull": {"members": current_user.id}}
    )
    
    return {"message": "Left channel successfully"}

# Message endpoints
@app.post("/api/messages", response_model=Message)
async def send_message(message_data: MessageCreate, current_user: User = Depends(get_current_user)):
    message = Message(
        content=message_data.content,
        sender_id=current_user.id,
        sender_username=current_user.username,
        channel_id=message_data.channel_id,
        recipient_id=message_data.recipient_id
    )
    
    await db.messages.insert_one(message.dict())
    
    # Broadcast message via WebSocket
    message_dict = message.dict()
    message_dict["type"] = "new_message"
    
    if message.channel_id:
        await manager.broadcast_to_channel(message_dict, message.channel_id)
    elif message.recipient_id:
        await manager.send_personal_message(message_dict, message.recipient_id)
        await manager.send_personal_message(message_dict, current_user.id)
    
    return message

@app.get("/api/messages/channel/{channel_id}")
async def get_channel_messages(channel_id: str, skip: int = 0, limit: int = 50, current_user: User = Depends(get_current_user)):
    # Check if user is member of channel
    channel = await db.channels.find_one({"id": channel_id})
    if not channel or current_user.id not in channel.get("members", []):
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    messages = await db.messages.find({"channel_id": channel_id}).sort("created_at", -1).skip(skip).limit(limit).to_list(length=None)
    return [Message(**msg) for msg in reversed(messages)]

@app.get("/api/messages/direct/{user_id}")
async def get_direct_messages(user_id: str, skip: int = 0, limit: int = 50, current_user: User = Depends(get_current_user)):
    messages = await db.messages.find({
        "$or": [
            {"sender_id": current_user.id, "recipient_id": user_id},
            {"sender_id": user_id, "recipient_id": current_user.id}
        ]
    }).sort("created_at", -1).skip(skip).limit(limit).to_list(length=None)
    return [Message(**msg) for msg in reversed(messages)]

@app.put("/api/messages/{message_id}", response_model=Message)
async def edit_message(message_id: str, edit_data: MessageEdit, current_user: User = Depends(get_current_user)):
    message = await db.messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message["sender_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Can only edit your own messages")
    
    # Update message
    await db.messages.update_one(
        {"id": message_id},
        {"$set": {"content": edit_data.content, "edited_at": datetime.utcnow()}}
    )
    
    updated_message = await db.messages.find_one({"id": message_id})
    message_obj = Message(**updated_message)
    
    # Broadcast edit via WebSocket
    edit_message_dict = message_obj.dict()
    edit_message_dict["type"] = "message_edited"
    
    if message_obj.channel_id:
        await manager.broadcast_to_channel(edit_message_dict, message_obj.channel_id)
    elif message_obj.recipient_id:
        await manager.send_personal_message(edit_message_dict, message_obj.recipient_id)
        await manager.send_personal_message(edit_message_dict, current_user.id)
    
    return message_obj

@app.post("/api/messages/{message_id}/reactions")
async def add_reaction(message_id: str, reaction_data: ReactionAdd, current_user: User = Depends(get_current_user)):
    message = await db.messages.find_one({"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Add reaction
    emoji = reaction_data.emoji
    reactions = message.get("reactions", {})
    
    if emoji not in reactions:
        reactions[emoji] = []
    
    if current_user.id not in reactions[emoji]:
        reactions[emoji].append(current_user.id)
    
    await db.messages.update_one(
        {"id": message_id},
        {"$set": {"reactions": reactions}}
    )
    
    # Broadcast reaction via WebSocket
    reaction_message = {
        "type": "reaction_added",
        "message_id": message_id,
        "emoji": emoji,
        "user_id": current_user.id,
        "reactions": reactions
    }
    
    if message.get("channel_id"):
        await manager.broadcast_to_channel(reaction_message, message["channel_id"])
    elif message.get("recipient_id"):
        await manager.send_personal_message(reaction_message, message["recipient_id"])
        await manager.send_personal_message(reaction_message, message["sender_id"])
    
    return {"message": "Reaction added successfully"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # Generate unique filename
    file_extension = Path(file.filename).suffix
    unique_filename = f"{str(uuid.uuid4())}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Determine file type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    file_type = "image" if mime_type and mime_type.startswith("image/") else "file"
    
    file_url = f"/uploads/{unique_filename}"
    
    return {
        "file_url": file_url,
        "file_name": file.filename,
        "file_type": file_type,
        "size": len(content)
    }

# WebSocket endpoint
@app.websocket("/api/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        # Verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        
        user = await db.users.find_one({"id": user_id})
        if not user:
            await websocket.close(code=1008)
            return
            
        await manager.connect(websocket, user_id, user["username"])
        
        try:
            while True:
                data = await websocket.receive_text()
                # Handle incoming WebSocket messages if needed
                
        except WebSocketDisconnect:
            await manager.disconnect(user_id, user["username"])
            
    except jwt.PyJWTError:
        await websocket.close(code=1008)

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)