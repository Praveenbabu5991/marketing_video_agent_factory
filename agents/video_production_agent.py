"""
Video Production Agent - Generates marketing videos using Veo 3.1.
"""

print("📦 Loading video_production_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_production_model
from prompts.video_production_agent import VIDEO_PRODUCTION_AGENT_PROMPT
from tools.video_gen import (
    generate_animated_product_video,
    generate_motion_graphics_video,
    generate_talking_head_video,
    get_video_type_options,
)
from tools.response_formatter import format_response_for_user
from memory.store import save_to_memory, recall_from_memory

print(f"🎬 Creating VideoProductionAgent with model: {get_production_model()}")

video_production_agent = LlmAgent(
    name="VideoProductionAgent",
    model=get_production_model(),
    instruction=VIDEO_PRODUCTION_AGENT_PROMPT,
    tools=[
        generate_animated_product_video,
        generate_motion_graphics_video,
        generate_talking_head_video,
        get_video_type_options,
        format_response_for_user,
        save_to_memory,
        recall_from_memory,
    ],
    description="Generates marketing videos using Veo 3.1, applies brand visuals, and ensures marketing message clarity."
)

print("✅ VideoProductionAgent created successfully!")
