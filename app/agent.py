"""
Marketing Video Agent Factory - Manager Class

This module provides backward compatibility.
The agents have been refactored into the `agents` package.
"""

# Re-export from the new modular structure
from agents.root_agent import root_agent
from agents.video_strategy_agent import video_strategy_agent
from agents.video_script_agent import video_script_agent
from agents.video_production_agent import video_production_agent
from agents.video_optimization_agent import video_optimization_agent

# Re-export memory functions
from memory.store import (
    save_to_memory,
    recall_from_memory,
    get_or_create_project,
    get_memory_store,
)

__all__ = [
    "root_agent",
    "video_strategy_agent",
    "video_script_agent",
    "video_production_agent",
    "video_optimization_agent",
    "save_to_memory",
    "recall_from_memory",
    "get_or_create_project",
    "get_memory_store",
]
