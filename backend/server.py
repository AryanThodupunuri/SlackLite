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
    # Ephemeral messaging settings
    ttl_enabled: bool = False
    ttl_seconds: int = 3600  # Default 1 hour
    ttl_options: List[int] = [300, 900, 1800, 3600, 21600, 86400]  # 5min, 15min, 30min, 1h, 6h, 24h
    # Domain specialization
    domain_type: str = "general"  # general, sports, study, agile
    domain_config: Dict[str, Any] = {}

class ChannelCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = True
    ttl_enabled: bool = False
    ttl_seconds: int = 3600
    domain_type: str = "general"
    domain_config: Dict[str, Any] = {}

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    sender_id: str
    sender_username: str
    channel_id: Optional[str] = None
    recipient_id: Optional[str] = None
    message_type: str = "text"  # text, file, image, system, ephemeral
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    reactions: Dict[str, List[str]] = {}  # emoji -> [user_ids]
    edited_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Ephemeral messaging
    is_ephemeral: bool = False
    expires_at: Optional[datetime] = None
    ttl_seconds: Optional[int] = None
    # Domain-specific data
    domain_data: Dict[str, Any] = {}

class MessageCreate(BaseModel):
    content: str
    channel_id: Optional[str] = None
    recipient_id: Optional[str] = None

class MessageEdit(BaseModel):
    content: str

class ReactionAdd(BaseModel):
    emoji: str

# Domain-specific models

# Sports Team Models
class PlayerStats(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str
    player_name: str
    channel_id: str
    games_played: int = 0
    points: int = 0
    assists: int = 0
    rebounds: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class GameSchedule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    date: datetime
    opponent: str
    location: str
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled
    score_home: Optional[int] = None
    score_away: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Study Group Models
class Flashcard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    created_by: str
    question: str
    answer: str
    difficulty: int = 1  # 1-5 scale
    subject: str
    tags: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StudyMaterial(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    uploaded_by: str
    title: str
    file_url: str
    file_type: str
    subject: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Agile/DevOps Models
class JiraIntegration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    jira_url: str
    project_key: str
    username: str
    api_token: str  # Encrypted
    webhook_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GitHubIntegration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    repo_owner: str
    repo_name: str
    access_token: str  # Encrypted
    webhook_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SprintInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    channel_id: str
    sprint_name: str
    start_date: datetime
    end_date: datetime
    story_points_planned: int = 0
    story_points_completed: int = 0
    velocity: float = 0.0
    status: str = "active"  # planning, active, completed
    created_at: datetime = Field(default_factory=datetime.utcnow)

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

# Ephemeral messaging helper functions
async def setup_message_ttl():
    """Setup TTL index for ephemeral messages"""
    try:
        # Create TTL index on expires_at field
        await db.messages.create_index("expires_at", expireAfterSeconds=0)
        print("✅ TTL index created for ephemeral messages")
    except Exception as e:
        print(f"⚠️ TTL index setup warning: {e}")

async def calculate_expiry_time(channel_id: str) -> Optional[datetime]:
    """Calculate message expiry time based on channel settings"""
    channel = await db.channels.find_one({"id": channel_id})
    if channel and channel.get("ttl_enabled", False):
        ttl_seconds = channel.get("ttl_seconds", 3600)
        return datetime.utcnow() + timedelta(seconds=ttl_seconds)
    return None

async def cleanup_expired_messages():
    """Background job to clean up expired messages and notify clients"""
    while True:
        try:
            # Find messages that are about to expire (within 10 seconds)
            expiring_soon = await db.messages.find({
                "expires_at": {
                    "$gte": datetime.utcnow(),
                    "$lte": datetime.utcnow() + timedelta(seconds=10)
                },
                "is_ephemeral": True
            }).to_list(length=None)
            
            # Notify clients about expiring messages
            for message in expiring_soon:
                expiry_notification = {
                    "type": "message_expiring",
                    "message_id": message["id"],
                    "channel_id": message.get("channel_id"),
                    "expires_at": message["expires_at"].isoformat()
                }
                
                if message.get("channel_id"):
                    await manager.broadcast_to_channel(expiry_notification, message["channel_id"])
                elif message.get("recipient_id"):
                    await manager.send_personal_message(expiry_notification, message["recipient_id"])
                    await manager.send_personal_message(expiry_notification, message["sender_id"])
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            print(f"❌ Cleanup job error: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# Start background cleanup task
@app.on_event("startup")
async def startup_event():
    await setup_message_ttl()
    # Start background cleanup task
    asyncio.create_task(cleanup_expired_messages())

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

@app.put("/api/channels/{channel_id}/settings")
async def update_channel_settings(
    channel_id: str, 
    ttl_enabled: bool = False,
    ttl_seconds: int = 3600,
    domain_type: str = "general",
    domain_config: Dict[str, Any] = {},
    current_user: User = Depends(get_current_user)
):
    # Check if user is channel creator or admin
    channel = await db.channels.find_one({"id": channel_id})
    if not channel or channel["created_by"] != current_user.id:
        raise HTTPException(status_code=403, detail="Only channel creator can modify settings")
    
    update_data = {
        "ttl_enabled": ttl_enabled,
        "ttl_seconds": ttl_seconds,
        "domain_type": domain_type,
        "domain_config": domain_config
    }
    
    await db.channels.update_one({"id": channel_id}, {"$set": update_data})
    
    # Notify channel members about settings change
    settings_update = {
        "type": "channel_settings_updated",
        "channel_id": channel_id,
        "ttl_enabled": ttl_enabled,
        "ttl_seconds": ttl_seconds,
        "domain_type": domain_type,
        "updated_by": current_user.username
    }
    
    await manager.broadcast_to_channel(settings_update, channel_id)
    
    return {"message": "Channel settings updated successfully"}

# Sports Team Endpoints
@app.post("/api/sports/stats", response_model=PlayerStats)
async def create_player_stats(
    channel_id: str,
    player_name: str,
    games_played: int = 0,
    points: int = 0,
    assists: int = 0,
    rebounds: int = 0,
    current_user: User = Depends(get_current_user)
):
    # Verify channel is sports type
    channel = await db.channels.find_one({"id": channel_id, "domain_type": "sports"})
    if not channel:
        raise HTTPException(status_code=404, detail="Sports channel not found")
    
    stats = PlayerStats(
        player_id=current_user.id,
        player_name=player_name,
        channel_id=channel_id,
        games_played=games_played,
        points=points,
        assists=assists,
        rebounds=rebounds
    )
    
    await db.player_stats.insert_one(stats.dict())
    
    # Broadcast stats update
    stats_update = {
        "type": "player_stats_updated",
        "channel_id": channel_id,
        "player_name": player_name,
        "stats": stats.dict()
    }
    await manager.broadcast_to_channel(stats_update, channel_id)
    
    return stats

@app.get("/api/sports/stats/{channel_id}")
async def get_team_stats(channel_id: str, current_user: User = Depends(get_current_user)):
    stats = await db.player_stats.find({"channel_id": channel_id}).to_list(length=None)
    return [PlayerStats(**stat) for stat in stats]

@app.post("/api/sports/schedule", response_model=GameSchedule)
async def create_game_schedule(
    channel_id: str,
    date: datetime,
    opponent: str,
    location: str,
    current_user: User = Depends(get_current_user)
):
    game = GameSchedule(
        channel_id=channel_id,
        date=date,
        opponent=opponent,
        location=location
    )
    
    await db.game_schedule.insert_one(game.dict())
    
    # Send system message about new game
    system_message = Message(
        content=f"🏀 New game scheduled: vs {opponent} on {date.strftime('%Y-%m-%d %H:%M')} at {location}",
        sender_id="system",
        sender_username="GameBot",
        channel_id=channel_id,
        message_type="system"
    )
    
    await db.messages.insert_one(system_message.dict())
    
    game_announcement = system_message.dict()
    game_announcement["type"] = "new_message"
    await manager.broadcast_to_channel(game_announcement, channel_id)
    
    return game

@app.get("/api/sports/schedule/{channel_id}")
async def get_team_schedule(channel_id: str, current_user: User = Depends(get_current_user)):
    games = await db.game_schedule.find({"channel_id": channel_id}).sort("date", 1).to_list(length=None)
    return [GameSchedule(**game) for game in games]

# Study Group Endpoints
@app.post("/api/study/flashcards", response_model=Flashcard)
async def create_flashcard(
    channel_id: str,
    question: str,
    answer: str,
    difficulty: int = 1,
    subject: str = "",
    tags: List[str] = [],
    current_user: User = Depends(get_current_user)
):
    flashcard = Flashcard(
        channel_id=channel_id,
        created_by=current_user.id,
        question=question,
        answer=answer,
        difficulty=difficulty,
        subject=subject,
        tags=tags
    )
    
    await db.flashcards.insert_one(flashcard.dict())
    
    # Send system message about new flashcard
    system_message = Message(
        content=f"📚 New flashcard added: {subject} (Difficulty: {difficulty}/5)",
        sender_id="system",
        sender_username="StudyBot",
        channel_id=channel_id,
        message_type="system"
    )
    
    await db.messages.insert_one(system_message.dict())
    
    flashcard_announcement = system_message.dict()
    flashcard_announcement["type"] = "new_message"
    await manager.broadcast_to_channel(flashcard_announcement, channel_id)
    
    return flashcard

@app.get("/api/study/flashcards/{channel_id}")
async def get_flashcards(channel_id: str, subject: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {"channel_id": channel_id}
    if subject:
        query["subject"] = subject
    
    flashcards = await db.flashcards.find(query).to_list(length=None)
    return [Flashcard(**card) for card in flashcards]

@app.post("/api/study/materials", response_model=StudyMaterial)
async def upload_study_material(
    channel_id: str,
    title: str,
    file_url: str,
    file_type: str,
    subject: str,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    material = StudyMaterial(
        channel_id=channel_id,
        uploaded_by=current_user.id,
        title=title,
        file_url=file_url,
        file_type=file_type,
        subject=subject,
        description=description
    )
    
    await db.study_materials.insert_one(material.dict())
    
    # Send system message about new material
    system_message = Message(
        content=f"📄 New study material: {title} ({subject})",
        sender_id="system",
        sender_username="StudyBot",
        channel_id=channel_id,
        message_type="system"
    )
    
    await db.messages.insert_one(system_message.dict())
    
    material_announcement = system_message.dict()
    material_announcement["type"] = "new_message"
    await manager.broadcast_to_channel(material_announcement, channel_id)
    
    return material

@app.get("/api/study/materials/{channel_id}")
async def get_study_materials(channel_id: str, current_user: User = Depends(get_current_user)):
    materials = await db.study_materials.find({"channel_id": channel_id}).to_list(length=None)
    return [StudyMaterial(**material) for material in materials]

# Agile/DevOps Endpoints
@app.post("/api/agile/jira-webhook")
async def jira_webhook(request: dict):
    """Handle Jira webhook notifications"""
    try:
        event_type = request.get("webhookEvent")
        issue = request.get("issue", {})
        
        if event_type == "jira:issue_updated":
            issue_key = issue.get("key")
            summary = issue.get("fields", {}).get("summary")
            status = issue.get("fields", {}).get("status", {}).get("name")
            
            # Find channels with Jira integration
            integrations = await db.jira_integrations.find({}).to_list(length=None)
            
            for integration in integrations:
                channel_id = integration["channel_id"]
                
                # Send system message about Jira update
                system_message = Message(
                    content=f"🔄 Jira Update: {issue_key} - {summary} → Status: {status}",
                    sender_id="system",
                    sender_username="JiraBot",
                    channel_id=channel_id,
                    message_type="system",
                    domain_data={
                        "jira_issue_key": issue_key,
                        "jira_status": status,
                        "jira_summary": summary
                    }
                )
                
                await db.messages.insert_one(system_message.dict())
                
                jira_update = system_message.dict()
                jira_update["type"] = "new_message"
                await manager.broadcast_to_channel(jira_update, channel_id)
        
        return {"status": "processed"}
    except Exception as e:
        print(f"❌ Jira webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/agile/github-webhook")
async def github_webhook(request: dict):
    """Handle GitHub webhook notifications"""
    try:
        action = request.get("action")
        
        if "pull_request" in request:
            pr = request["pull_request"]
            pr_number = pr.get("number")
            title = pr.get("title")
            user = pr.get("user", {}).get("login")
            
            # Find channels with GitHub integration
            integrations = await db.github_integrations.find({}).to_list(length=None)
            
            for integration in integrations:
                channel_id = integration["channel_id"]
                repo_name = integration["repo_name"]
                
                if action == "opened":
                    content = f"🔀 New PR #{pr_number} opened by {user}: {title}"
                elif action == "closed":
                    content = f"✅ PR #{pr_number} closed: {title}"
                elif action == "merged":
                    content = f"🎉 PR #{pr_number} merged: {title}"
                else:
                    continue
                
                # Send system message about GitHub activity
                system_message = Message(
                    content=content,
                    sender_id="system",
                    sender_username="GitHubBot",
                    channel_id=channel_id,
                    message_type="system",
                    domain_data={
                        "github_pr_number": pr_number,
                        "github_action": action,
                        "github_repo": repo_name
                    }
                )
                
                await db.messages.insert_one(system_message.dict())
                
                github_update = system_message.dict()
                github_update["type"] = "new_message"
                await manager.broadcast_to_channel(github_update, channel_id)
        
        return {"status": "processed"}
    except Exception as e:
        print(f"❌ GitHub webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/agile/sprint", response_model=SprintInfo)
async def create_sprint(
    channel_id: str,
    sprint_name: str,
    start_date: datetime,
    end_date: datetime,
    story_points_planned: int = 0,
    current_user: User = Depends(get_current_user)
):
    sprint = SprintInfo(
        channel_id=channel_id,
        sprint_name=sprint_name,
        start_date=start_date,
        end_date=end_date,
        story_points_planned=story_points_planned
    )
    
    await db.sprint_info.insert_one(sprint.dict())
    
    # Send system message about new sprint
    system_message = Message(
        content=f"🚀 New sprint created: {sprint_name} ({story_points_planned} points planned)",
        sender_id="system",
        sender_username="SprintBot",
        channel_id=channel_id,
        message_type="system"
    )
    
    await db.messages.insert_one(system_message.dict())
    
    sprint_announcement = system_message.dict()
    sprint_announcement["type"] = "new_message"
    await manager.broadcast_to_channel(sprint_announcement, channel_id)
    
    return sprint

@app.get("/api/agile/sprint/{channel_id}")
async def get_active_sprint(channel_id: str, current_user: User = Depends(get_current_user)):
    sprint = await db.sprint_info.find_one({"channel_id": channel_id, "status": "active"})
    if sprint:
        return SprintInfo(**sprint)
    return None

# Message endpoints
@app.post("/api/messages", response_model=Message)
async def send_message(message_data: MessageCreate, current_user: User = Depends(get_current_user)):
    # Check if message should be ephemeral
    expires_at = None
    is_ephemeral = False
    ttl_seconds = None
    
    if message_data.channel_id:
        expires_at = await calculate_expiry_time(message_data.channel_id)
        if expires_at:
            is_ephemeral = True
            channel = await db.channels.find_one({"id": message_data.channel_id})
            ttl_seconds = channel.get("ttl_seconds", 3600)
    
    message = Message(
        content=message_data.content,
        sender_id=current_user.id,
        sender_username=current_user.username,
        channel_id=message_data.channel_id,
        recipient_id=message_data.recipient_id,
        is_ephemeral=is_ephemeral,
        expires_at=expires_at,
        ttl_seconds=ttl_seconds
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