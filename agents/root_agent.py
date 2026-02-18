"""
Root Agent (Marketing Video Manager) - Orchestrates the marketing video workflow.
"""

print("📦 Loading root_agent.py...")

from google.adk.agents import LlmAgent
from google.genai import types
from config.models import get_orchestrator_model
from prompts.root_agent import get_root_agent_prompt
from memory.store import get_memory_store, get_or_create_project, save_to_memory, recall_from_memory
from tools.marketing_research import research_market_trends, analyze_competitors, get_target_audience_insights
from tools.response_formatter import format_response_for_user

print("✅ Imports completed in root_agent.py")

# Import sub-agents
print("📦 Importing sub-agents...")
from agents.video_strategy_agent import video_strategy_agent
from agents.video_script_agent import video_script_agent
from agents.video_production_agent import video_production_agent
from agents.video_optimization_agent import video_optimization_agent
print("✅ Sub-agents imported")


def get_memory_context() -> str:
    """Get current memory context for the orchestrator."""
    print("🧠 get_memory_context() called")
    try:
        store = get_memory_store()
        # Get recent activity summary
        recent = store.get_recent_content(5)
        if recent:
            return f"Recent generations: {len(recent)} items"
        return "No previous context."
    except Exception:
        return "No previous context."


# Create the root agent with dynamic prompt
print(f"🤖 Creating MarketingVideoManager agent...")
print(f"   Model: {get_orchestrator_model()}")

root_agent = LlmAgent(
    name="MarketingVideoManager",
    model=get_orchestrator_model(),
    instruction=get_root_agent_prompt(get_memory_context()),
    sub_agents=[
        video_strategy_agent,
        video_script_agent,
        video_production_agent,
        video_optimization_agent,
    ],
    tools=[
        get_or_create_project,
        save_to_memory,
        recall_from_memory,
        research_market_trends,
        analyze_competitors,
        get_target_audience_insights,
        format_response_for_user,  # MUST call this before returning any response to user
    ],
    generate_content_config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH"
            ),
        ]
    )
)

print(f"✅ MarketingVideoManager agent created successfully!")
