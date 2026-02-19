"""
Animation Agent - Transforms static images into animated videos/cinemagraphs.

Uses Veo 3.1 for high-quality video generation with optional audio.
The agent uses Gemini for reasoning and orchestrates the Veo video tools.
"""

print("📦 Loading animation_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_model_for_agent
from prompts.animation_agent import ANIMATION_AGENT_PROMPT
from tools.animation import animate_image, generate_video_from_text
from tools.video_gen import generate_video
from memory.store import save_to_memory, recall_from_memory, get_brand_context

print(f"🎬 Creating AnimationAgent with model: {get_model_for_agent('animation_agent')}")

animation_agent = LlmAgent(
    name="AnimationAgent",
    model=get_model_for_agent("animation_agent"),
    instruction=ANIMATION_AGENT_PROMPT,
    tools=[
        generate_video,
        animate_image,
        generate_video_from_text,
        save_to_memory,
        recall_from_memory,
        get_brand_context,
    ],
    description="Transforms static images into animated videos/cinemagraphs using Veo 3.1 with audio support."
)

print("✅ AnimationAgent created successfully!")
