"""
Marketing Video Agent Factory - FastAPI Server

Provides a secure web interface for marketing video generation with:
- Enhanced brand setup with marketing context
- File upload with validation
- Streaming chat responses
- Session management with persistence
- Rate limiting
"""

import os
import uuid
import json
import time
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from PIL import Image
import io

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load environment
load_dotenv()

# Import configuration
from config.settings import (
    HOST, PORT, DEBUG, ALLOWED_ORIGINS,
    UPLOAD_DIR, GENERATED_DIR, STATIC_DIR, TEMPLATES_DIR,
    MAX_UPLOAD_SIZE_BYTES, ALLOWED_IMAGE_TYPES, MAX_IMAGE_DIMENSION,
    RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW,
    SESSION_TIMEOUT_HOURS,
)

# Import the root agent
from agents.root_agent import root_agent

# Import tools for direct use
from tools.image_utils import extract_brand_colors

# Import memory store
from memory.store import get_memory_store


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""
    
    EXCLUDED_PATHS = ['/static/', '/generated/', '/uploads/', '/favicon.ico', '/health']
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        window_start = current_time - 60
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]
        
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please wait a moment and try again."}
            )
        
        self.requests[client_ip].append(current_time)
        return await call_next(request)


# =============================================================================
# Initialize FastAPI
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup and shutdown events."""
    try:
        store = get_memory_store()
        deleted = store.cleanup_old_sessions(SESSION_TIMEOUT_HOURS)
        if deleted > 0:
            print(f"🧹 Cleaned up {deleted} old sessions")
    except Exception as e:
        print(f"⚠️ Session cleanup error: {e}")
    
    yield
    
    print("👋 Marketing Video Agent Factory shutting down...")


app = FastAPI(
    title="Marketing Video Agent Factory",
    description="Multi-agent marketing video generation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=RATE_LIMIT_REQUESTS)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

# Static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/generated", StaticFiles(directory=str(GENERATED_DIR)), name="generated")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ADK components
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="marketing_video_agent",
    session_service=session_service,
)


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "default_user"
    session_id: Optional[str] = None
    attachments: Optional[list[dict]] = None
    last_generated_video: Optional[str] = None
    
    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 10000:
            raise ValueError('Message too long (max 10000 characters)')
        return v.strip()


class MarketingContextRequest(BaseModel):
    """Request model for marketing context."""
    session_id: str
    company_overview: str
    target_audience: str
    products_services: str
    marketing_goals: list[str]
    brand_messaging: str
    competitive_positioning: Optional[str] = ""
    key_differentiators: Optional[list[str]] = []


# =============================================================================
# File Validation Helpers
# =============================================================================

def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: PNG, JPEG, GIF, WebP"
        )
    
    ext = Path(file.filename).suffix.lower()
    if ext not in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}:
        raise HTTPException(status_code=400, detail="Invalid file extension")


async def validate_image_content(content: bytes) -> None:
    """Validate image content and dimensions."""
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB"
        )
    
    try:
        image = Image.open(io.BytesIO(content))
        width, height = image.size
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            raise HTTPException(
                status_code=400,
                detail=f"Image too large. Maximum dimension: {MAX_IMAGE_DIMENSION}px"
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file")


# =============================================================================
# Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "agent": "Marketing Video Manager",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    """Upload a logo file and extract brand colors."""
    validate_image_file(file)
    content = await file.read()
    await validate_image_content(content)
    
    ext = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / unique_filename
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    colors = extract_brand_colors(str(filepath))
    
    return {
        "success": True,
        "filename": unique_filename,
        "path": f"/uploads/{unique_filename}",
        "full_path": str(filepath),
        "colors": colors
    }


@app.post("/upload-reference")
async def upload_reference(file: UploadFile = File(...)):
    """Upload a reference image for style inspiration."""
    validate_image_file(file)
    content = await file.read()
    await validate_image_content(content)
    
    ext = Path(file.filename).suffix.lower()
    unique_filename = f"ref_{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / unique_filename
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    return {
        "success": True,
        "filename": unique_filename,
        "path": f"/uploads/{unique_filename}",
        "full_path": str(filepath)
    }


USER_IMAGE_INTENTS = [
    "background", "product_focus", "team_people",
    "style_reference", "logo_badge", "auto",
]


@app.post("/upload-user-image")
async def upload_user_image(
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
    usage_intent: str = Form(default="auto"),
):
    """Upload images user wants included in videos."""
    validate_image_file(file)
    content = await file.read()
    await validate_image_content(content)
    
    if usage_intent not in USER_IMAGE_INTENTS:
        usage_intent = "auto"
    
    image_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix.lower()
    filename = f"img_{image_id}{ext}"
    
    if session_id:
        user_images_dir = UPLOAD_DIR / "user_images" / session_id
    else:
        user_images_dir = UPLOAD_DIR / "user_images" / "default"
    
    user_images_dir.mkdir(parents=True, exist_ok=True)
    filepath = user_images_dir / filename
    
    with open(filepath, "wb") as f:
        f.write(content)
    
    colors = extract_brand_colors(str(filepath))
    
    with Image.open(filepath) as img:
        dimensions = img.size
    
    if session_id:
        url = f"/uploads/user_images/{session_id}/{filename}"
    else:
        url = f"/uploads/user_images/default/{filename}"
    
    return {
        "success": True,
        "image": {
            "id": image_id,
            "filename": file.filename,
            "path": str(filepath),
            "url": url,
            "uploaded_at": datetime.now().isoformat(),
            "usage_intent": usage_intent,
            "extracted_colors": colors.get("palette", []),
            "dimensions": dimensions,
        },
    }


@app.post("/upload-marketing-context")
async def upload_marketing_context(request: MarketingContextRequest):
    """Upload marketing context (company overview, target audience, etc.)."""
    # Store marketing context in session
    store = get_memory_store()
    session = store.get_or_create_session(request.session_id, "default_user")
    
    # Update brand context with marketing information
    if not session.brand.marketing_context:
        from memory.state import MarketingContext
    
    session.brand.marketing_context.company_overview = request.company_overview
    session.brand.marketing_context.target_audience = request.target_audience
    session.brand.marketing_context.products_services = request.products_services
    session.brand.marketing_context.marketing_goals = request.marketing_goals
    session.brand.marketing_context.brand_messaging = request.brand_messaging
    session.brand.marketing_context.competitive_positioning = request.competitive_positioning
    session.brand.marketing_context.key_differentiators = request.key_differentiators
    
    store.update_session(session)
    
    return {
        "success": True,
        "message": "Marketing context saved successfully",
        "session_id": request.session_id,
    }


def sanitize_unicode(text: str) -> str:
    """Remove invalid Unicode characters."""
    if not text:
        return text
    import re
    cleaned = re.sub(r'[\ud800-\udfff]', '', text)
    try:
        cleaned = cleaned.encode('utf-8', errors='replace').decode('utf-8')
    except UnicodeError:
        cleaned = ''.join(c for c in text if ord(c) < 0x10000 or (ord(c) >= 0x10000 and ord(c) <= 0x10FFFF))
    return cleaned


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response using Server-Sent Events."""
    sanitized_message = sanitize_unicode(request.message)
    
    session_id = request.session_id or str(uuid.uuid4())
    
    session = await session_service.get_session(
        app_name="marketing_video_agent",
        user_id=request.user_id,
        session_id=session_id
    )
    
    if not session:
        session = await session_service.create_session(
            app_name="marketing_video_agent",
            user_id=request.user_id,
            session_id=session_id
        )
    
    # Build message with marketing context
    message_text = sanitized_message
    
    if request.last_generated_video:
        message_text = f"{message_text}\n\n[LAST GENERATED VIDEO: {request.last_generated_video}]"
    
    if request.attachments:
        attachment_context = "\n\n[MARKETING CONTEXT PROVIDED:]"
        for att in request.attachments:
            if att.get("type") == "logo":
                attachment_context += f"\n📷 LOGO_PATH: {att.get('full_path', att.get('path'))}"
                if att.get("colors"):
                    colors = att["colors"]
                    attachment_context += f"\n🎨 BRAND_COLORS: {colors.get('dominant')}"
                    if colors.get('palette'):
                        attachment_context += f", {','.join(colors.get('palette', []))}"
            elif att.get("type") == "company_overview":
                attachment_context += f"\n📋 COMPANY_OVERVIEW: {att.get('content', '')}"
            elif att.get("type") == "target_audience":
                attachment_context += f"\n👥 TARGET_AUDIENCE: {att.get('content', '')}"
            elif att.get("type") == "products_services":
                attachment_context += f"\n🛍️ PRODUCTS_SERVICES: {att.get('content', '')}"
            elif att.get("type") == "marketing_goals":
                attachment_context += f"\n🎯 MARKETING_GOALS: {','.join(att.get('goals', []))}"
            elif att.get("type") == "brand_messaging":
                attachment_context += f"\n💬 BRAND_MESSAGING: {att.get('content', '')}"
            elif att.get("type") == "user_images":
                user_imgs = att.get("images", [])
                if user_imgs:
                    attachment_context += "\n📸 USER_IMAGES_FOR_VIDEO:"
                    for img in user_imgs:
                        intent = img.get("usage_intent", "auto")
                        path = img.get("path", img.get("full_path", ""))
                        attachment_context += f"\n  - [{intent.upper()}] {path}"
                    all_paths = [img.get("path", img.get("full_path", "")) for img in user_imgs if img.get("path") or img.get("full_path")]
                    attachment_context += f"\n  USER_IMAGES_PATHS: {','.join(all_paths)}"
        message_text = message_text + attachment_context
    
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )
    
    async def generate():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
        
        try:
            async for event in runner.run_async(
                user_id=request.user_id,
                session_id=session_id,
                new_message=user_message
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            yield f"data: {json.dumps({'type': 'text', 'content': part.text})}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred. Please try again.'})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/sessions")
async def create_session(user_id: str = "default_user"):
    """Create a new chat session."""
    session_id = str(uuid.uuid4())
    await session_service.create_session(
        app_name="marketing_video_agent",
        user_id=user_id,
        session_id=session_id
    )
    return {"session_id": session_id, "user_id": user_id}


@app.get("/generated-videos")
async def list_generated_videos(limit: int = 20, offset: int = 0):
    """List generated videos with pagination."""
    videos = []
    for pattern in ['*.mp4', '*.mov', '*.avi']:
        for video_path in GENERATED_DIR.glob(pattern):
            videos.append({
                "filename": video_path.name,
                "url": f"/generated/{video_path.name}",
                "created": video_path.stat().st_mtime,
                "type": "video"
            })
    
    videos.sort(key=lambda x: x["created"], reverse=True)
    total = len(videos)
    videos = videos[offset:offset + limit]
    
    return {
        "videos": videos,
        "total": total,
        "limit": limit,
        "offset": offset,
        "hasMore": offset + limit < total
    }


@app.get("/preset-paths")
async def get_preset_paths():
    """Get full filesystem paths for preset logos and reference images."""
    presets_dir = STATIC_DIR / "presets"
    presets = {}
    
    preset_config = {
        "socialbunkr": {
            "logo": "socialbunkr-logo.jpeg",
            "refs_folder": "socialbunkr-refs"
        },
        "hylancer": {
            "logo": "hylancer-logo.jpeg",
            "refs_folder": "hylancer-refs"
        },
        "technova": {
            "logo": None,
            "refs_folder": None
        }
    }
    
    for preset_id, config in preset_config.items():
        preset_data = {}
        
        if config["logo"]:
            logo_path = presets_dir / config["logo"]
            if logo_path.exists():
                preset_data["logo_url"] = f"/static/presets/{config['logo']}"
                preset_data["logo_full_path"] = str(logo_path)
        
        if config["refs_folder"]:
            refs_folder = presets_dir / config["refs_folder"]
            if refs_folder.exists() and refs_folder.is_dir():
                ref_files = []
                for ext in ['*.png', '*.jpg', '*.jpeg', '*.webp']:
                    ref_files.extend(refs_folder.glob(ext))
                
                if ref_files:
                    preset_data["reference_images"] = []
                    for ref_file in sorted(ref_files)[:8]:
                        preset_data["reference_images"].append({
                            "url": f"/static/presets/{config['refs_folder']}/{ref_file.name}",
                            "full_path": str(ref_file)
                        })
        
        if preset_data:
            presets[preset_id] = preset_data
    
    return {"presets": presets}


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print(f"\n🎬 Marketing Video Agent Factory starting...")
    print(f"📍 Custom UI: http://localhost:{PORT}")
    print(f"📍 API Docs: http://localhost:{PORT}/docs")
    print(f"\n💡 Tip: Run 'adk web' for ADK's built-in UI\n")
    
    uvicorn.run(
        "app.fast_api_app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG
    )
