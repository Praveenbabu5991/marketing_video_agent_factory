"""
Video Script Agent - Writes compelling scripts for marketing videos.
"""

print("📦 Loading video_script_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_script_model
from prompts.video_script_agent import VIDEO_SCRIPT_AGENT_PROMPT
from tools.script_gen import (
    generate_video_script,
    refine_script,
    generate_script_variations,
)
from tools.response_formatter import format_response_for_user
from memory.store import save_to_memory, recall_from_memory

print(f"✍️ Creating VideoScriptAgent with model: {get_script_model()}")

video_script_agent = LlmAgent(
    name="VideoScriptAgent",
    model=get_script_model(),
    instruction=VIDEO_SCRIPT_AGENT_PROMPT,
    tools=[
        generate_video_script,
        refine_script,
        generate_script_variations,
        format_response_for_user,
        save_to_memory,
        recall_from_memory,
    ],
    description="Writes compelling video scripts based on strategy, ensures brand messaging consistency, and optimizes for engagement."
)

print("✅ VideoScriptAgent created successfully!")
