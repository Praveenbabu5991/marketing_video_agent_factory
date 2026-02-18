"""
Video Strategy Agent - Analyzes marketing context and suggests video concepts.
"""

print("📦 Loading video_strategy_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_strategy_model
from prompts.video_strategy_agent import VIDEO_STRATEGY_AGENT_PROMPT
from tools.marketing_research import (
    research_market_trends,
    analyze_competitors,
    get_target_audience_insights,
    suggest_marketing_strategies,
)
from tools.response_formatter import format_response_for_user
from memory.store import save_to_memory, recall_from_memory

print(f"🎯 Creating VideoStrategyAgent with model: {get_strategy_model()}")

video_strategy_agent = LlmAgent(
    name="VideoStrategyAgent",
    model=get_strategy_model(),
    instruction=VIDEO_STRATEGY_AGENT_PROMPT,
    tools=[
        research_market_trends,
        analyze_competitors,
        get_target_audience_insights,
        suggest_marketing_strategies,
        format_response_for_user,
        save_to_memory,
        recall_from_memory,
    ],
    description="Analyzes marketing goals, researches trends, and suggests video concepts aligned with marketing objectives."
)

print("✅ VideoStrategyAgent created successfully!")
