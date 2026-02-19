"""
Caption Agent - Creates engaging captions and strategic hashtags for video content.
"""

print("📦 Loading caption_agent.py...")

from google.adk.agents import LlmAgent
from config.models import get_model_for_agent
from prompts.caption_agent import CAPTION_AGENT_PROMPT
from tools.content import write_caption, generate_hashtags, improve_caption, create_complete_post
from tools.web_search import search_trending_topics
from memory.store import save_to_memory, recall_from_memory

print(f"📝 Creating CaptionAgent with model: {get_model_for_agent('caption_agent')}")

caption_agent = LlmAgent(
    name="CaptionAgent",
    model=get_model_for_agent("caption_agent"),
    instruction=CAPTION_AGENT_PROMPT,
    tools=[
        write_caption,
        generate_hashtags,
        improve_caption,
        create_complete_post,
        search_trending_topics,
        save_to_memory,
        recall_from_memory,
    ],
    description="Creates scroll-stopping captions and strategic hashtag sets for video content."
)

print("✅ CaptionAgent created successfully!")
