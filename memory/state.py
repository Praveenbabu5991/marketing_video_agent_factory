"""
Workflow State Management for Marketing Video Agent Factory.
Provides explicit state tracking for marketing video generation workflow.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
import json


class WorkflowState(Enum):
    """Explicit workflow states for marketing video generation."""
    START = "start"
    BRAND_SETUP = "brand_setup"
    MARKETING_CONTEXT_SETUP = "marketing_context_setup"
    BRAND_COMPLETE = "brand_complete"
    
    # Video type selection
    VIDEO_TYPE_SELECTION = "video_type_selection"
    
    # Strategy flow
    VIDEO_STRATEGY_SELECTION = "video_strategy_selection"
    STRATEGY_IDEAS_SHOWN = "strategy_ideas_shown"
    STRATEGY_SELECTED = "strategy_selected"
    
    # Script development flow
    SCRIPT_DEVELOPMENT = "script_development"
    SCRIPT_PRESENTED = "script_presented"
    SCRIPT_APPROVED = "script_approved"
    
    # Video production flow
    VIDEO_PRODUCTION = "video_production"
    VIDEO_GENERATING = "video_generating"
    VIDEO_GENERATED = "video_generated"
    
    # Optimization flow
    VIDEO_OPTIMIZATION = "video_optimization"
    OPTIMIZATION_COMPLETE = "optimization_complete"
    
    # Common
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class UserUploadedImage:
    """
    Single user-uploaded image for videos.
    
    Usage intent options:
    - "background" - Use as background image
    - "product_focus" - Show product prominently in foreground
    - "team_people" - Include people/team in composition
    - "style_reference" - Use for style inspiration only (not in final video)
    - "logo_badge" - Include as logo/badge overlay
    - "auto" - Let AI decide best placement
    """
    id: str = ""
    filename: str = ""
    path: str = ""
    url: str = ""
    uploaded_at: str = ""
    usage_intent: str = "auto"
    extracted_colors: list = field(default_factory=list)
    dimensions: tuple = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "path": self.path,
            "url": self.url,
            "uploaded_at": self.uploaded_at,
            "usage_intent": self.usage_intent,
            "extracted_colors": self.extracted_colors,
            "dimensions": self.dimensions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserUploadedImage":
        return cls(
            id=data.get("id", ""),
            filename=data.get("filename", ""),
            path=data.get("path", ""),
            url=data.get("url", ""),
            uploaded_at=data.get("uploaded_at", ""),
            usage_intent=data.get("usage_intent", "auto"),
            extracted_colors=data.get("extracted_colors", []),
            dimensions=tuple(data.get("dimensions", ())),
        )


@dataclass
class MarketingContext:
    """Marketing-specific context for video generation."""
    company_overview: str = ""
    target_audience: str = ""
    products_services: str = ""
    marketing_goals: list = field(default_factory=list)  # ["awareness", "conversion", "engagement", etc.]
    brand_messaging: str = ""
    competitive_positioning: str = ""
    key_differentiators: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "company_overview": self.company_overview,
            "target_audience": self.target_audience,
            "products_services": self.products_services,
            "marketing_goals": self.marketing_goals,
            "brand_messaging": self.brand_messaging,
            "competitive_positioning": self.competitive_positioning,
            "key_differentiators": self.key_differentiators,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MarketingContext":
        return cls(
            company_overview=data.get("company_overview", ""),
            target_audience=data.get("target_audience", ""),
            products_services=data.get("products_services", ""),
            marketing_goals=data.get("marketing_goals", []),
            brand_messaging=data.get("brand_messaging", ""),
            competitive_positioning=data.get("competitive_positioning", ""),
            key_differentiators=data.get("key_differentiators", []),
        )
    
    def is_complete(self) -> bool:
        """Check if basic marketing context is set."""
        return bool(self.company_overview and self.target_audience)


@dataclass
class BrandContext:
    """Brand information for the session."""
    name: str = ""
    industry: str = ""
    overview: str = ""
    tone: str = "professional"
    logo_path: Optional[str] = None
    colors: list = field(default_factory=list)
    reference_images: list = field(default_factory=list)
    user_images: list = field(default_factory=list)  # List of UserUploadedImage dicts
    marketing_context: MarketingContext = field(default_factory=MarketingContext)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "industry": self.industry,
            "overview": self.overview,
            "tone": self.tone,
            "logo_path": self.logo_path,
            "colors": self.colors,
            "reference_images": self.reference_images,
            "user_images": [
                img.to_dict() if isinstance(img, UserUploadedImage) else img
                for img in self.user_images
            ],
            "marketing_context": self.marketing_context.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrandContext":
        user_images_data = data.get("user_images", [])
        user_images = [
            UserUploadedImage.from_dict(img) if isinstance(img, dict) else img
            for img in user_images_data
        ]
        marketing_context_data = data.get("marketing_context", {})
        marketing_context = MarketingContext.from_dict(marketing_context_data) if marketing_context_data else MarketingContext()
        
        return cls(
            name=data.get("name", ""),
            industry=data.get("industry", ""),
            overview=data.get("overview", ""),
            tone=data.get("tone", "professional"),
            logo_path=data.get("logo_path"),
            colors=data.get("colors", []),
            reference_images=data.get("reference_images", []),
            user_images=user_images,
            marketing_context=marketing_context,
        )

    def is_complete(self) -> bool:
        """Check if basic brand info is set."""
        return bool(self.name)

    def get_images_for_generation(self) -> list:
        """Get images intended for use in video generation (not style reference)."""
        return [
            img for img in self.user_images
            if isinstance(img, UserUploadedImage) and img.usage_intent != "style_reference"
        ]

    def get_style_reference_images(self) -> list:
        """Get images for style reference only."""
        style_refs = [
            img for img in self.user_images
            if isinstance(img, UserUploadedImage) and img.usage_intent == "style_reference"
        ]
        return style_refs + [{"path": p} for p in self.reference_images]


@dataclass
class VideoContext:
    """Context for current video being created."""
    video_type: Optional[str] = None  # "brand_story", "product_launch", "explainer", etc.
    selected_strategy: Optional[dict] = None
    script: Optional[str] = None
    script_notes: Optional[str] = None
    video_path: Optional[str] = None
    video_metadata: Optional[dict] = None
    optimization_notes: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "video_type": self.video_type,
            "selected_strategy": self.selected_strategy,
            "script": self.script,
            "script_notes": self.script_notes,
            "video_path": self.video_path,
            "video_metadata": self.video_metadata,
            "optimization_notes": self.optimization_notes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "VideoContext":
        return cls(**data)
    
    def reset(self):
        """Reset for new video."""
        self.video_type = None
        self.selected_strategy = None
        self.script = None
        self.script_notes = None
        self.video_path = None
        self.video_metadata = None
        self.optimization_notes = None


@dataclass
class SessionState:
    """Complete session state."""
    session_id: str
    user_id: str
    workflow_state: WorkflowState = WorkflowState.START
    brand: BrandContext = field(default_factory=BrandContext)
    video: VideoContext = field(default_factory=VideoContext)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "workflow_state": self.workflow_state.value,
            "brand": self.brand.to_dict(),
            "video": self.video.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            workflow_state=WorkflowState(data["workflow_state"]),
            brand=BrandContext.from_dict(data.get("brand", {})),
            video=VideoContext.from_dict(data.get("video", {})),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )
    
    def transition(self, new_state: WorkflowState) -> None:
        """Transition to a new workflow state."""
        self.workflow_state = new_state
        self.updated_at = datetime.now()
    
    def get_context_summary(self) -> str:
        """Get a summary for the agent."""
        parts = [f"State: {self.workflow_state.value}"]
        
        if self.brand.name:
            parts.append(f"Brand: {self.brand.name}")
        if self.video.video_type:
            parts.append(f"Video Type: {self.video.video_type}")
        if self.video.video_path:
            parts.append(f"Video: {self.video.video_path}")
        
        return " | ".join(parts)


class StateTransitions:
    """Valid state transitions for the workflow."""

    VALID_TRANSITIONS = {
        WorkflowState.START: [WorkflowState.BRAND_SETUP],
        WorkflowState.BRAND_SETUP: [WorkflowState.MARKETING_CONTEXT_SETUP, WorkflowState.BRAND_COMPLETE],
        WorkflowState.MARKETING_CONTEXT_SETUP: [WorkflowState.BRAND_COMPLETE],
        WorkflowState.BRAND_COMPLETE: [WorkflowState.VIDEO_TYPE_SELECTION],
        
        # Video type selection
        WorkflowState.VIDEO_TYPE_SELECTION: [WorkflowState.VIDEO_STRATEGY_SELECTION],
        
        # Strategy flow
        WorkflowState.VIDEO_STRATEGY_SELECTION: [WorkflowState.STRATEGY_IDEAS_SHOWN],
        WorkflowState.STRATEGY_IDEAS_SHOWN: [WorkflowState.STRATEGY_SELECTED],
        WorkflowState.STRATEGY_SELECTED: [WorkflowState.SCRIPT_DEVELOPMENT],
        
        # Script development flow
        WorkflowState.SCRIPT_DEVELOPMENT: [WorkflowState.SCRIPT_PRESENTED],
        WorkflowState.SCRIPT_PRESENTED: [WorkflowState.SCRIPT_APPROVED, WorkflowState.SCRIPT_DEVELOPMENT],
        WorkflowState.SCRIPT_APPROVED: [WorkflowState.VIDEO_PRODUCTION],
        
        # Video production flow
        WorkflowState.VIDEO_PRODUCTION: [WorkflowState.VIDEO_GENERATING],
        WorkflowState.VIDEO_GENERATING: [WorkflowState.VIDEO_GENERATED],
        WorkflowState.VIDEO_GENERATED: [WorkflowState.VIDEO_OPTIMIZATION, WorkflowState.COMPLETE],
        
        # Optimization flow
        WorkflowState.VIDEO_OPTIMIZATION: [WorkflowState.OPTIMIZATION_COMPLETE],
        WorkflowState.OPTIMIZATION_COMPLETE: [WorkflowState.COMPLETE, WorkflowState.VIDEO_TYPE_SELECTION],
        
        WorkflowState.COMPLETE: [WorkflowState.VIDEO_TYPE_SELECTION],
        WorkflowState.ERROR: [WorkflowState.START, WorkflowState.VIDEO_TYPE_SELECTION],
    }
    
    @classmethod
    def is_valid_transition(cls, from_state: WorkflowState, to_state: WorkflowState) -> bool:
        """Check if a state transition is valid."""
        valid_next = cls.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_next
    
    @classmethod
    def get_valid_next_states(cls, current_state: WorkflowState) -> list:
        """Get valid next states from current state."""
        return cls.VALID_TRANSITIONS.get(current_state, [])
