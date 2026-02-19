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
        "agent": "Marketing Video Agent Factory",
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

        # Also save structured brand context to MemoryStore for tool retrieval
        store = get_memory_store()
        mem_session = store.get_or_create_session(session_id, request.user_id)

        for att in request.attachments:
            if att.get("type") == "logo":
                logo_path = att.get('full_path', att.get('path', ''))
                attachment_context += f"\n📷 LOGO_PATH: {logo_path}"
                mem_session.brand.logo_path = logo_path
                if att.get("colors"):
                    colors_data = att["colors"]
                    dominant = colors_data.get('dominant', '')
                    palette = colors_data.get('palette', [])
                    attachment_context += f"\n🎨 BRAND_COLORS: {dominant}"
                    if palette:
                        attachment_context += f", {','.join(palette)}"
                    all_colors = [dominant] + palette if dominant else palette
                    mem_session.brand.colors = [c for c in all_colors if c]
            elif att.get("type") == "company_overview":
                content = att.get('content', '')
                attachment_context += f"\n📋 COMPANY_OVERVIEW: {content}"
                mem_session.brand.marketing_context.company_overview = content
                if not mem_session.brand.overview:
                    mem_session.brand.overview = content
            elif att.get("type") == "target_audience":
                content = att.get('content', '')
                attachment_context += f"\n👥 TARGET_AUDIENCE: {content}"
                mem_session.brand.marketing_context.target_audience = content
            elif att.get("type") == "products_services":
                content = att.get('content', '')
                attachment_context += f"\n🛍️ PRODUCTS_SERVICES: {content}"
                mem_session.brand.marketing_context.products_services = content
            elif att.get("type") == "marketing_goals":
                goals = att.get('goals', [])
                attachment_context += f"\n🎯 MARKETING_GOALS: {','.join(goals)}"
                mem_session.brand.marketing_context.marketing_goals = goals
            elif att.get("type") == "brand_messaging":
                content = att.get('content', '')
                attachment_context += f"\n💬 BRAND_MESSAGING: {content}"
                mem_session.brand.marketing_context.brand_messaging = content
            elif att.get("type") == "user_images":
                user_imgs = att.get("images", [])
                if user_imgs:
                    attachment_context += "\n📸 USER_IMAGES_FOR_VIDEO:"
                    from memory.state import UserUploadedImage
                    for img in user_imgs:
                        intent = img.get("usage_intent", "auto")
                        path = img.get("path", img.get("full_path", ""))
                        attachment_context += f"\n  - [{intent.upper()}] {path}"
                        mem_session.brand.user_images.append(
                            UserUploadedImage(
                                id=img.get("id", ""),
                                filename=img.get("filename", ""),
                                path=path,
                                url=img.get("url", ""),
                                uploaded_at=img.get("uploaded_at", ""),
                                usage_intent=intent,
                                extracted_colors=img.get("extracted_colors", []),
                                dimensions=tuple(img.get("dimensions", ())),
                            )
                        )
                    all_paths = [img.get("path", img.get("full_path", "")) for img in user_imgs if img.get("path") or img.get("full_path")]
                    attachment_context += f"\n  USER_IMAGES_PATHS: {','.join(all_paths)}"

        # Parse brand name, industry, tone from message text
        # Message formats vary:
        #   "Company: TechNova. Industry: SaaS." (period-separated)
        #   "- Company: SocialBunkr\n- Industry: Travel" (newline-separated)
        #   "[...Industry: Travel & Hospitality, Tone: creative, ...]" (comma-separated in brackets)
        import re as _re_brand
        brand_match = _re_brand.search(r"Company:\s*([^.,\n\]]+)", sanitized_message)
        if brand_match and not mem_session.brand.name:
            mem_session.brand.name = brand_match.group(1).strip()
        industry_match = _re_brand.search(r"Industry:\s*([^.,\n\]]+(?:\s*&\s*[^.,\n\]]+)?)", sanitized_message)
        if industry_match and not mem_session.brand.industry:
            mem_session.brand.industry = industry_match.group(1).strip()
        tone_match = _re_brand.search(r"(?:Style|Tone):\s*(\w+)", sanitized_message, _re_brand.IGNORECASE)
        if tone_match:
            mem_session.brand.tone = tone_match.group(1).strip().lower()

        store.update_session(mem_session)

        message_text = message_text + attachment_context
    
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=message_text)]
    )

    async def generate():
        yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

        # Log the user message for debugging
        import sys
        print(f"\n📨 User Message: {sanitized_message[:200]}...", flush=True)
        sys.stdout.flush()
        
        # Check if this is a brand setup completion message
        brand_setup_keywords = ["set up my brand", "brand setup", "I've set up", "setup complete", 
                               "brand configured", "Logo:", "Colors:", "Style:"]
        is_brand_setup = any(keyword.lower() in sanitized_message.lower() for keyword in brand_setup_keywords)
        
        if is_brand_setup:
            print("✅ Detected brand setup completion - checking for video type guidance", flush=True)
            sys.stdout.flush()
        
        # Extract brand details for response
        brand_name = ""
        industry = ""
        colors = ""
        style = ""
        
        if is_brand_setup:
            # Try to extract brand info from message
            import re
            brand_match = re.search(r"brand:\s*([^.(]+)", sanitized_message, re.IGNORECASE)
            if brand_match:
                brand_name = brand_match.group(1).strip()
            
            industry_match = re.search(r"\(([^)]+)\)", sanitized_message)
            if industry_match:
                industry = industry_match.group(1).strip()
            
            color_match = re.search(r"Colors?:\s*(#[0-9A-Fa-f]+)", sanitized_message)
            if color_match:
                colors = color_match.group(1)
            
            style_match = re.search(r"Style:\s*(\w+)", sanitized_message, re.IGNORECASE)
            if style_match:
                style = style_match.group(1).strip()
        
        collected_response = ""
        has_format_response = False
        
        try:
            async for event in runner.run_async(
                user_id=request.user_id,
                session_id=session_id,
                new_message=user_message
            ):
                # Log event author for debugging
                author = getattr(event, 'author', None) or getattr(event, 'agent_name', 'unknown')
                print(f"📡 Event from: {author} | has_content={bool(event.content)}", flush=True)
                sys.stdout.flush()

                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Handle text parts
                        if hasattr(part, 'text') and part.text:
                            text_content = part.text
                            
                            # CRITICAL FIX: Extract JSON from tool result wrapper {'result': '...'}
                            # ADK wraps tool outputs as: {'result': '{"text":"...","has_choices":...}'}
                            # ast.literal_eval fails on \\'ve patterns, so use regex extraction
                            extracted_json = None
                            
                            stripped_tc = text_content.strip()
                            is_wrapper = (
                                stripped_tc.startswith("{'result':") or 
                                stripped_tc.startswith('{"result":')
                            )
                            
                            print(f"📝 Part text [{len(stripped_tc)} chars] starts='{stripped_tc[:40]}...' is_wrapper={is_wrapper}", flush=True)
                            sys.stdout.flush()
                            
                            if is_wrapper and 'has_choices' in stripped_tc:
                                try:
                                    if stripped_tc.startswith("{'result':"):
                                        # Regex: extract content between {'result': ' and final '}
                                        import re as _re
                                        wrapper_m = _re.match(r"^\{'result':\s*'(.*)'\}\s*$", stripped_tc, _re.DOTALL)
                                        if wrapper_m:
                                            inner_raw = wrapper_m.group(1)
                                            # Unescape Python string escapes: \\' → ', \\\\ → \\
                                            inner_str = inner_raw.replace("\\'", "'")
                                            inner_str = inner_str.replace("\\\\", "\\")
                                            # Now inner_str should be valid JSON (with \uXXXX escapes)
                                            try:
                                                inner_json = json.loads(inner_str)
                                                if isinstance(inner_json, dict) and 'has_choices' in inner_json:
                                                    has_format_response = True
                                                    extracted_json = json.dumps(inner_json, ensure_ascii=False)
                                                    print("✅ Extracted JSON via regex from wrapper", flush=True)
                                                    sys.stdout.flush()
                                            except json.JSONDecodeError as je:
                                                print(f"⚠️ JSON parse failed after unescape: {je}", flush=True)
                                    elif stripped_tc.startswith('{"result":'):
                                        # JSON wrapper: {"result": "..."}
                                        outer = json.loads(stripped_tc)
                                        result_val = outer.get('result', '')
                                        if isinstance(result_val, str):
                                            inner_json = json.loads(result_val)
                                        else:
                                            inner_json = result_val
                                        if isinstance(inner_json, dict) and 'has_choices' in inner_json:
                                            has_format_response = True
                                            extracted_json = json.dumps(inner_json, ensure_ascii=False)
                                            print("✅ Extracted JSON from JSON wrapper", flush=True)
                                            sys.stdout.flush()
                                except Exception as e:
                                    print(f"⚠️ Wrapper extraction failed: {e}", flush=True)
                                    sys.stdout.flush()
                                
                                # Always skip wrapper text (never show raw wrapper to user)
                                if extracted_json:
                                    yield f"data: {json.dumps({'type': 'text', 'content': extracted_json})}\n\n"
                                    collected_response += extracted_json
                                else:
                                    print("⚠️  Skipping unparseable wrapper chunk", flush=True)
                                    sys.stdout.flush()
                                continue
                            
                            # Check if this looks like JSON (format_response_for_user output)
                            is_structured_json = False
                            try:
                                parsed = json.loads(text_content.strip())
                                if isinstance(parsed, dict) and 'has_choices' in parsed:
                                    has_format_response = True
                                    is_structured_json = True
                                    print("✅ Found format_response_for_user JSON in text part", flush=True)
                                    sys.stdout.flush()
                            except:
                                pass
                            
                            # Only skip text that is clearly a raw JSON echo of structured content
                            # (not all plain text - sub-agent responses must pass through)
                            if has_format_response and not is_structured_json:
                                stripped = text_content.strip()
                                # Skip ONLY if text is a JSON object echo containing choices
                                if stripped.startswith('{') and ('"has_choices"' in stripped or '"choices"' in stripped):
                                    print(f"⏭️  Skipping JSON echo [{len(stripped)} chars]", flush=True)
                                    sys.stdout.flush()
                                    continue
                                # Allow all other text through (sub-agent responses, follow-up text)
                            
                            collected_response += text_content
                            yield f"data: {json.dumps({'type': 'text', 'content': text_content})}\n\n"
                        
                        # Handle function call results (format_response_for_user returns JSON)
                        if hasattr(part, 'function_call') and part.function_call:
                            func_name = part.function_call.name if hasattr(part.function_call, 'name') else ""
                            print(f"🔧 Function call: {func_name}", flush=True)
                            sys.stdout.flush()
                            if 'format_response' in func_name.lower():
                                has_format_response = True
                            # Send progress notification for long-running video generation
                            if any(vg in func_name for vg in ['generate_video', 'generate_animated_product_video', 'generate_motion_graphics_video', 'animate_image', 'generate_video_from_text']):
                                yield f"data: {json.dumps({'type': 'status', 'message': '🎬 Generating your video... This may take 2-5 minutes. Please wait.'})}\n\n"
                        
                        # Handle function response (result of function call)
                        if hasattr(part, 'function_response') and part.function_response:
                            func_name = part.function_response.name if hasattr(part.function_response, 'name') else ""
                            response_text = ""
                            resp_obj = None
                            if hasattr(part.function_response, 'response'):
                                resp_obj = part.function_response.response
                                # ADK may return response as dict with 'result' key
                                if isinstance(resp_obj, dict) and 'result' in resp_obj:
                                    response_text = resp_obj['result']
                                    print(f"📦 Extracted 'result' from function_response dict", flush=True)
                                else:
                                    response_text = str(resp_obj)
                            elif hasattr(part.function_response, 'text'):
                                response_text = part.function_response.text

                            # Send dedicated video_generated event for video tools
                            video_tools = ['generate_video', 'generate_animated_product_video', 'generate_motion_graphics_video', 'animate_image', 'generate_video_from_text']
                            if func_name in video_tools:
                                try:
                                    video_result = None
                                    if isinstance(resp_obj, dict) and 'result' in resp_obj:
                                        vr = resp_obj['result']
                                        video_result = json.loads(vr) if isinstance(vr, str) else vr
                                    elif isinstance(resp_obj, dict):
                                        video_result = resp_obj
                                    elif isinstance(response_text, str):
                                        video_result = json.loads(response_text)

                                    if isinstance(video_result, dict) and video_result.get('status') == 'success' and video_result.get('url'):
                                        video_event = {
                                            'type': 'video_generated',
                                            'url': video_result['url'],
                                            'filename': video_result.get('filename', ''),
                                            'video_path': video_result.get('video_path', ''),
                                            'video_type': video_result.get('type', ''),
                                        }
                                        yield f"data: {json.dumps(video_event)}\n\n"
                                        print(f"🎬 Sent video_generated event: {video_result['url']}", flush=True)
                                        sys.stdout.flush()
                                except Exception as ve:
                                    print(f"⚠️ Could not parse video result: {ve}", flush=True)
                            
                            if response_text and ('format_response' in func_name.lower() or '"has_choices"' in response_text):
                                has_format_response = True
                                print(f"✅ Function {func_name} returned structured response", flush=True)
                                
                                # Extract inner JSON if wrapped in {'result': '...'}
                                clean_text = response_text
                                stripped_rt = response_text.strip()
                                if stripped_rt.startswith("{'result':") and 'has_choices' in stripped_rt:
                                    import re as _re
                                    wrapper_m = _re.match(r"^\{'result':\s*'(.*)'\}\s*$", stripped_rt, _re.DOTALL)
                                    if wrapper_m:
                                        inner_raw = wrapper_m.group(1)
                                        inner_str = inner_raw.replace("\\'", "'").replace("\\\\", "\\")
                                        try:
                                            inner_json = json.loads(inner_str)
                                            if isinstance(inner_json, dict) and 'has_choices' in inner_json:
                                                clean_text = json.dumps(inner_json, ensure_ascii=False)
                                                print("✅ Cleaned wrapper from function_response", flush=True)
                                        except json.JSONDecodeError:
                                            pass
                                elif stripped_rt.startswith('{"result":') and 'has_choices' in stripped_rt:
                                    try:
                                        outer = json.loads(stripped_rt)
                                        rv = outer.get('result', '')
                                        inner_json = json.loads(rv) if isinstance(rv, str) else rv
                                        if isinstance(inner_json, dict) and 'has_choices' in inner_json:
                                            clean_text = json.dumps(inner_json, ensure_ascii=False)
                                            print("✅ Cleaned JSON wrapper from function_response", flush=True)
                                    except (json.JSONDecodeError, TypeError):
                                        pass
                                
                                # Validate clean_text is parseable JSON with choices
                                try:
                                    test_parsed = json.loads(clean_text)
                                    if isinstance(test_parsed, dict) and 'has_choices' in test_parsed:
                                        collected_response += clean_text
                                        yield f"data: {json.dumps({'type': 'text', 'content': clean_text})}\n\n"
                                        print(f"✅ Sent clean structured response [{len(clean_text)} chars]", flush=True)
                                    else:
                                        collected_response += clean_text
                                        yield f"data: {json.dumps({'type': 'text', 'content': clean_text})}\n\n"
                                except (json.JSONDecodeError, TypeError):
                                    collected_response += clean_text
                                    yield f"data: {json.dumps({'type': 'text', 'content': clean_text})}\n\n"
                                
                                sys.stdout.flush()
            
            # =================================================================
            # POST-PROCESSING: Inject interactive buttons when agent fails
            # to call format_response_for_user at critical workflow steps
            # =================================================================
            
            if not has_format_response:
                import re
                from tools.response_formatter import format_response_for_user
                
                injected = False
                
                # ---------------------------------------------------------
                # SCENARIO 1: Brand setup detected → inject video types
                # ---------------------------------------------------------
                if is_brand_setup:
                    print("⚠️  Brand setup detected but no interactive buttons", flush=True)
                    sys.stdout.flush()
                    
                    color_desc = f"vibrant {colors}" if colors else "brand colors"
                    resp_text = f"Perfect! I see you've set up {brand_name or 'your brand'}"
                    if industry:
                        resp_text += f" ({industry})"
                    resp_text += f" with your {color_desc} branding"
                    if style:
                        resp_text += f" and {style} style"
                    resp_text += ". Great foundation! 🎨\n\nNow, let's create an amazing marketing video! I can help you create **9 different types of marketing videos**:\n\n**Marketing-Specific Types:**\n📖 Brand Story - Tell your mission and values\n🚀 Product Launch - Announce new products\n💡 Explainer - Show how services work\n⭐ Testimonial - Share customer stories\n📚 Educational - Tips and insights\n🎯 Promotional - Deals and campaigns\n\n**Creative Types:**\n📦 Animated Product - Showcase products\n✨ Motion Graphics - Eye-catching animations\n🎙️ AI Talking Head - AI presenter videos\n\n**Which type would you like to create?**"
                    
                    fc = '[{"id": "brand_story", "label": "Brand Story", "value": "brand story", "icon": "📖"}, {"id": "product_launch", "label": "Product Launch", "value": "product launch", "icon": "🚀"}, {"id": "explainer", "label": "Explainer", "value": "explainer", "icon": "💡"}, {"id": "testimonial", "label": "Testimonial", "value": "testimonial", "icon": "⭐"}, {"id": "educational", "label": "Educational", "value": "educational", "icon": "📚"}, {"id": "promotional", "label": "Promotional", "value": "promotional", "icon": "🎯"}, {"id": "animated_product", "label": "Animated Product", "value": "animated product", "icon": "📦"}, {"id": "motion_graphics", "label": "Motion Graphics", "value": "motion graphics", "icon": "✨"}, {"id": "talking_head", "label": "AI Talking Head", "value": "talking head", "icon": "🎙️"}]'
                    
                    formatted = format_response_for_user(
                        response_text=resp_text, force_choices=fc,
                        choice_type="menu", allow_free_input=True,
                        input_hint="Or describe what you'd like to create"
                    )
                    yield f"data: {json.dumps({'type': 'text', 'content': formatted})}\n\n"
                    print("✅ Injected video type options", flush=True)
                    sys.stdout.flush()
                    injected = True
                
                # ---------------------------------------------------------
                # SCENARIO 2: Concepts/ideas were presented → inject
                # numbered selection buttons (1, 2, 3)
                # ---------------------------------------------------------
                if not injected:
                    resp_lower = collected_response.lower()
                    has_concepts = (
                        ("video concepts" in resp_lower or "video concept" in resp_lower or
                         "here are" in resp_lower or "strategic video" in resp_lower) and
                        (re.search(r'\b1\.\s+', collected_response) is not None) and
                        (re.search(r'\b2\.\s+', collected_response) is not None)
                    )
                    
                    if has_concepts:
                        print("⚠️  Concepts presented but no selection buttons", flush=True)
                        sys.stdout.flush()
                        
                        # Extract concept titles from numbered items
                        concept_titles = []
                        for m in re.finditer(r'(?:^|\n)\s*(\d+)\.\s+(.+?)(?:\n|$)', collected_response):
                            num = m.group(1)
                            title = m.group(2).strip()
                            # Clean up: remove "**" markdown bold markers
                            title = title.replace("**", "").strip()
                            # Truncate long titles
                            if len(title) > 60:
                                title = title[:57] + "..."
                            concept_titles.append((num, title))
                        
                        if len(concept_titles) >= 2:
                            choices = []
                            for num, title in concept_titles[:5]:
                                emoji_map = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣"}
                                choices.append({
                                    "id": f"idea_{num}",
                                    "label": f"Idea {num}: {title}",
                                    "value": num,
                                    "icon": emoji_map.get(num, "🔢")
                                })
                            
                            fc = json.dumps(choices)
                            formatted = format_response_for_user(
                                response_text=collected_response + "\n\n**Which idea do you like?** Pick one below!",
                                force_choices=fc,
                                choice_type="single_select",
                                allow_free_input=True,
                                input_hint="Or describe your own concept"
                            )
                            yield f"data: {json.dumps({'type': 'text', 'content': formatted})}\n\n"
                            print(f"✅ Injected {len(choices)} concept selection buttons", flush=True)
                            sys.stdout.flush()
                            injected = True
                
                # ---------------------------------------------------------
                # SCENARIO 3: User selected an idea and concept was
                # developed → inject Yes/No confirmation buttons
                # ---------------------------------------------------------
                if not injected:
                    user_lower = sanitized_message.lower().strip()
                    is_idea_selection = bool(re.match(
                        r'^(go with|option|idea|concept|choose|select|pick|i like|let\'?s go with|number)?\s*'
                        r'(option|idea|concept|number)?\s*#?\s*[1-5]\b',
                        user_lower
                    )) or user_lower in ("1", "2", "3", "4", "5", "yes")
                    
                    resp_lower = collected_response.lower()
                    has_concept_details = (
                        ("hook" in resp_lower or "script" in resp_lower or
                         "key message" in resp_lower or "duration" in resp_lower or
                         "concept" in resp_lower) and
                        len(collected_response) > 100
                    )
                    
                    if is_idea_selection and has_concept_details:
                        print("⚠️  Concept developed but no confirmation buttons", flush=True)
                        sys.stdout.flush()
                        
                        formatted = format_response_for_user(
                            response_text=collected_response + "\n\n**Ready to generate this video?**",
                            force_choices='[{"id": "yes", "label": "Yes, generate!", "value": "yes generate", "icon": "✅"}, {"id": "refine", "label": "Refine the concept", "value": "refine concept", "icon": "✏️"}, {"id": "different", "label": "Pick a different idea", "value": "show ideas again", "icon": "🔄"}]',
                            choice_type="confirmation",
                            allow_free_input=True,
                            input_hint="Or tell me what to change"
                        )
                        yield f"data: {json.dumps({'type': 'text', 'content': formatted})}\n\n"
                        print("✅ Injected confirmation buttons", flush=True)
                        sys.stdout.flush()
                        injected = True
                
                # ---------------------------------------------------------
                # SCENARIO 4: Response ends with a question but no
                # interactive options → inject contextual buttons
                # ---------------------------------------------------------
                if not injected:
                    resp_stripped = collected_response.strip()
                    ends_with_question = resp_stripped.endswith("?") or "which" in resp_stripped[-200:].lower() or "would you like" in resp_stripped[-200:].lower()
                    
                    if ends_with_question and len(resp_stripped) > 50:
                        # Check for video type sub-options (e.g. "Which style would you like?")
                        resp_lower = resp_stripped.lower()
                        
                        if any(vt in resp_lower for vt in ["motion graphics", "brand story", "product launch", "explainer", "testimonial", "educational", "promotional", "animated product", "talking head"]):
                            # Try to extract options from the response text
                            options = []
                            # Look for emoji + text patterns
                            for m in re.finditer(r'([\U0001F300-\U0001FAD6\u2600-\u27BF\u2702-\u27B0])\s+(.+?)(?:\n|$)', collected_response):
                                emoji = m.group(1)
                                text = m.group(2).strip().replace("**", "")
                                if len(text) < 80 and text and not text.startswith("Video Concepts"):
                                    options.append({"id": text.lower().replace(" ", "_")[:30], "label": text[:50], "value": text[:50], "icon": emoji})
                            
                            if len(options) >= 2:
                                # Add a "Suggest ideas" option
                                options.append({"id": "suggest", "label": "Suggest ideas for me", "value": "suggest ideas", "icon": "💡"})
                                
                                fc = json.dumps(options[:8])
                                formatted = format_response_for_user(
                                    response_text=resp_stripped,
                                    force_choices=fc,
                                    choice_type="menu",
                                    allow_free_input=True,
                                    input_hint="Or describe what you want"
                                )
                                yield f"data: {json.dumps({'type': 'text', 'content': formatted})}\n\n"
                                print(f"✅ Injected {len(options)} contextual options", flush=True)
                                sys.stdout.flush()
                                injected = True
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Error in chat stream: {e}")
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


# =============================================================================
# URL Scraping
# =============================================================================

class UrlScrapeRequest(BaseModel):
    username: str
    limit: int = 6
    url_type: str = "auto"

    @field_validator('limit')
    @classmethod
    def limit_range(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError('Limit must be between 1 and 20')
        return v


@app.post("/scrape-instagram")
async def scrape_url_images(request: UrlScrapeRequest):
    """
    Scrape images and brand info from various sources for style reference.

    NOTE: Instagram scraping is limited due to API restrictions.
    For best results, upload reference images manually.
    """
    import httpx
    import re
    from urllib.parse import urlparse
    from tools.web_scraper import scrape_brand_from_url

    url_or_username = request.username.strip()

    # Extract brand info from URL
    brand_info = scrape_brand_from_url(url_or_username)

    # Detect URL type
    url_type = request.url_type
    if url_type == "auto":
        if "instagram.com" in url_or_username or url_or_username.startswith("@"):
            url_type = "instagram"
        elif "pinterest.com" in url_or_username:
            url_type = "pinterest"
        else:
            url_type = "website"

    # Create identifier for folder
    if url_type == "instagram":
        # Extract username from URL
        identifier = url_or_username.lstrip("@").split("/")[-1].split("?")[0] or "instagram"
    else:
        try:
            parsed = urlparse(url_or_username if url_or_username.startswith("http") else f"https://{url_or_username}")
            identifier = parsed.netloc.replace(".", "_") or "website"
        except Exception:
            identifier = "scraped"

    # Sanitize identifier
    identifier = re.sub(r'[^\w\-]', '_', identifier)

    # Create folder for scraped images
    scraped_dir = UPLOAD_DIR / "scraped" / identifier
    scraped_dir.mkdir(parents=True, exist_ok=True)

    images = []

    # For Instagram, return a helpful message since scraping is restricted
    if url_type == "instagram":
        return {
            "success": True,
            "identifier": identifier,
            "url_type": "instagram",
            "images": [],
            "brand_info": brand_info,
            "message": f"Instagram images require manual upload, but we've noted @{identifier} as your brand reference. Upload images from their profile as Reference Images."
        }

    # For websites, try to scrape images
    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
        follow_redirects=True,
        timeout=15.0
    ) as client:
        try:
            target_url = url_or_username if url_or_username.startswith("http") else f"https://{url_or_username}"
            response = await client.get(target_url)

            if response.status_code == 200:
                html = response.text

                # Extract image URLs
                img_patterns = [
                    r'<img[^>]+src=["\']([^"\']+)["\']',
                    r'<meta[^>]+property="og:image"[^>]+content=["\']([^"\']+)["\']',
                ]

                found_urls = set()
                for pattern in img_patterns:
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for match in matches:
                        if match.startswith("//"):
                            match = "https:" + match
                        elif match.startswith("/"):
                            parsed = urlparse(target_url)
                            match = f"{parsed.scheme}://{parsed.netloc}{match}"
                        elif not match.startswith("http"):
                            continue

                        if any(ext in match.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            if not any(skip in match.lower() for skip in ['icon', 'favicon', '1x1', 'pixel']):
                                found_urls.add(match)

                # Download images
                for i, img_url in enumerate(list(found_urls)[:request.limit]):
                    try:
                        img_response = await client.get(img_url, timeout=10.0)
                        if img_response.status_code == 200 and len(img_response.content) > 10000:
                            ext = ".jpg"
                            for e in ['.png', '.webp']:
                                if e in img_url.lower():
                                    ext = e
                                    break

                            filename = f"web_{identifier}_{i}{ext}"
                            filepath = scraped_dir / filename

                            with open(filepath, "wb") as f:
                                f.write(img_response.content)

                            images.append({
                                "url": f"/uploads/scraped/{identifier}/{filename}",
                                "full_path": str(filepath),
                                "source": url_type
                            })
                    except Exception:
                        continue

        except Exception:
            return {
                "success": False,
                "identifier": identifier,
                "url_type": url_type,
                "images": [],
                "message": "Could not fetch images from this URL. Please upload reference images manually."
            }

    if images:
        return {
            "success": True,
            "identifier": identifier,
            "url_type": url_type,
            "images": images,
            "brand_info": brand_info,
            "message": f"Successfully scraped {len(images)} images and brand info for style reference"
        }

    return {
        "success": True if brand_info.get("status") == "success" else False,
        "identifier": identifier,
        "url_type": url_type,
        "images": [],
        "brand_info": brand_info,
        "message": "Extracted brand info. No images found - please upload reference images manually."
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
