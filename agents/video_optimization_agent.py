"""
Video Optimization Agent - Optimizes videos for different platforms and adds enhancements.
"""

print("📦 Loading video_optimization_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_optimization_model
from prompts.video_optimization_agent import VIDEO_OPTIMIZATION_AGENT_PROMPT
from tools.response_formatter import format_response_for_user
from memory.store import save_to_memory, recall_from_memory

print(f"⚡ Creating VideoOptimizationAgent with model: {get_optimization_model()}")

video_optimization_agent = LlmAgent(
    name="VideoOptimizationAgent",
    model=get_optimization_model(),
    instruction=VIDEO_OPTIMIZATION_AGENT_PROMPT,
    tools=[
        format_response_for_user,
        save_to_memory,
        recall_from_memory,
    ],
    description="Optimizes videos for different platforms, suggests improvements, and creates platform-specific versions."
)

print("✅ VideoOptimizationAgent created successfully!")
