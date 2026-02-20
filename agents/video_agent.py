"""
Video Agent - Creates video content using Veo 3.1 and external services.

Handles three types of video generation:
1. Video from Image - Transform user's uploaded images into promotional videos
2. Motion Graphics - Create branded motion graphics from text
3. AI Talking Head - Guide users to external AI presenter services
"""

print("📦 Loading video_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_model_for_agent
from prompts.video_agent import VIDEO_AGENT_PROMPT
from tools.video_gen import (
    generate_video,
    get_video_type_options,
    suggest_video_ideas,
)
from tools.response_formatter import format_response_for_user
from tools.content import write_caption, generate_hashtags
from memory.store import save_to_memory, recall_from_memory, get_brand_context

print(f"🎬 Creating VideoAgent with model: {get_model_for_agent('video_agent')}")

video_agent = LlmAgent(
    name="VideoAgent",
    model=get_model_for_agent("video_agent"),
    instruction=VIDEO_AGENT_PROMPT,
    tools=[
        generate_video,
        suggest_video_ideas,
        get_video_type_options,
        write_caption,
        generate_hashtags,
        format_response_for_user,
        save_to_memory,
        recall_from_memory,
        get_brand_context,
    ],
    description="Creates Reels/TikTok videos: suggests ideas, generates 15-second videos, provides captions and hashtags."
)

print("✅ VideoAgent created successfully!")
