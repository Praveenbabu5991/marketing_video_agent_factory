"""Tools package for Marketing Video Agent Factory."""

from tools.video_gen import (
    generate_animated_product_video,
    generate_motion_graphics_video,
    generate_talking_head_video,
    get_video_type_options,
    suggest_video_ideas,
)
from tools.script_gen import (
    generate_video_script,
    refine_script,
    generate_script_variations,
)
from tools.marketing_research import (
    research_market_trends,
    analyze_competitors,
    get_target_audience_insights,
    suggest_marketing_strategies,
)
from tools.response_formatter import format_response_for_user

__all__ = [
    # Video generation
    "generate_animated_product_video",
    "generate_motion_graphics_video",
    "generate_talking_head_video",
    "get_video_type_options",
    "suggest_video_ideas",
    # Script generation
    "generate_video_script",
    "refine_script",
    "generate_script_variations",
    # Marketing research
    "research_market_trends",
    "analyze_competitors",
    "get_target_audience_insights",
    "suggest_marketing_strategies",
    # Response formatting
    "format_response_for_user",
]
