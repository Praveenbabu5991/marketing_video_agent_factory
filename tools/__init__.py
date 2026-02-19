"""Tools package for Marketing Video Agent Factory."""

from tools.video_gen import (
    generate_animated_product_video,
    generate_motion_graphics_video,
    generate_talking_head_video,
    get_video_type_options,
    suggest_video_ideas,
)
from tools.animation import animate_image, generate_video_from_text
from tools.content import write_caption, generate_hashtags, improve_caption, create_complete_post
from tools.response_formatter import format_response_for_user
from tools.web_search import get_ai_knowledge, search_trending_topics, get_competitor_insights
from tools.web_scraper import scrape_brand_from_url
