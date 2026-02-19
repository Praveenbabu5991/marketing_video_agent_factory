"""Prompts package for Marketing Video Agent Factory."""

from prompts.root_agent import ROOT_AGENT_PROMPT, get_root_agent_prompt
from prompts.video_agent import VIDEO_AGENT_PROMPT, get_video_agent_prompt
from prompts.animation_agent import ANIMATION_AGENT_PROMPT
from prompts.caption_agent import CAPTION_AGENT_PROMPT

__all__ = [
    "ROOT_AGENT_PROMPT",
    "get_root_agent_prompt",
    "VIDEO_AGENT_PROMPT",
    "get_video_agent_prompt",
    "ANIMATION_AGENT_PROMPT",
    "CAPTION_AGENT_PROMPT",
]
