"""
Campaign Agent - Creates multi-week video content campaigns.

Plans week-by-week video campaigns with user approval at each stage.
Generates single videos per post using Veo 3.1, auto-generates captions and hashtags.
"""

print("📦 Loading campaign_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_model_for_agent
from prompts.campaign_agent import CAMPAIGN_AGENT_PROMPT
from tools.calendar import (
    get_content_calendar_suggestions,
    get_upcoming_events,
    get_festivals_and_events,
    suggest_best_posting_times,
)
from tools.web_search import search_trending_topics, get_ai_knowledge
from tools.video_gen import generate_video, suggest_video_ideas
from tools.content import write_caption, generate_hashtags
from tools.response_formatter import format_response_for_user
from memory.store import save_to_memory, recall_from_memory, get_brand_context

print(f"📊 Creating CampaignPlannerAgent with model: {get_model_for_agent('campaign_agent')}")

campaign_agent = LlmAgent(
    name="CampaignPlannerAgent",
    model=get_model_for_agent("campaign_agent"),
    instruction=CAMPAIGN_AGENT_PROMPT,
    tools=[
        # Planning tools
        get_content_calendar_suggestions,
        get_upcoming_events,
        get_festivals_and_events,
        suggest_best_posting_times,
        search_trending_topics,
        get_ai_knowledge,
        # Video generation
        generate_video,
        suggest_video_ideas,
        # Caption tools
        write_caption,
        generate_hashtags,
        # Response formatting
        format_response_for_user,
        # Memory
        save_to_memory,
        recall_from_memory,
        get_brand_context,
    ],
    description="Plans multi-week video content campaigns with week-by-week approval. Generates videos with auto-captions and hashtags.",
)

print("✅ CampaignPlannerAgent created successfully!")
