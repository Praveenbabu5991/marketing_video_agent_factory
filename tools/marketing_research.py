"""
Marketing Research Tools for Marketing Video Agent Factory.

Provides market research and analysis functions:
- Research market trends
- Analyze competitors
- Get target audience insights
- Suggest marketing strategies
"""

import os
from typing import Optional, Dict, List
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


def _get_client():
    """Get Gemini client with validation."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key not configured. Please set GOOGLE_API_KEY in your environment.")
    return genai.Client(api_key=api_key)


def research_market_trends(
    industry: str,
    topic: str = "",
    timeframe: str = "current"
) -> Dict:
    """
    Research current market trends for an industry.

    Args:
        industry: Industry or niche
        topic: Specific topic to research (optional)
        timeframe: Timeframe for trends (current, 6 months, 1 year)

    Returns:
        Dictionary with trends, insights, and recommendations
    """
    print(f"🔍 Researching market trends for {industry}")

    try:
        client = _get_client()

        prompt = f"""Research current market trends for the {industry} industry.

{"Focus on: " + topic if topic else ""}
Timeframe: {timeframe}

Provide:
1. Top 3-5 current trends
2. Emerging opportunities
3. Consumer behavior shifts
4. Video content trends in this industry
5. Best practices for marketing videos

Format as structured insights with actionable recommendations.
"""

        model = os.getenv("STRATEGY_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        trends_text = response.text if hasattr(response, 'text') else str(response)

        return {
            "status": "success",
            "industry": industry,
            "topic": topic,
            "timeframe": timeframe,
            "trends": trends_text,
            "insights": _extract_insights(trends_text),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Market research failed: {str(e)}",
            "trends": "",
        }


def analyze_competitors(
    brand_name: str,
    industry: str,
    competitors: Optional[List[str]] = None
) -> Dict:
    """
    Analyze competitors' video marketing strategies.

    Args:
        brand_name: Name of the brand
        industry: Industry or niche
        competitors: List of competitor names (optional)

    Returns:
        Dictionary with competitor analysis and recommendations
    """
    print(f"🔍 Analyzing competitors for {brand_name}")

    try:
        client = _get_client()

        competitors_str = ", ".join(competitors) if competitors else "top competitors in the industry"
        
        prompt = f"""Analyze video marketing strategies of competitors in the {industry} industry.

BRAND: {brand_name}
COMPETITORS: {competitors_str}

Provide:
1. Common video types used by competitors
2. Messaging themes and approaches
3. Visual styles and branding
4. Content gaps and opportunities
5. Recommendations for differentiation

Focus on actionable insights for creating unique marketing videos.
"""

        model = os.getenv("STRATEGY_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        analysis_text = response.text if hasattr(response, 'text') else str(response)

        return {
            "status": "success",
            "brand_name": brand_name,
            "industry": industry,
            "competitors": competitors or [],
            "analysis": analysis_text,
            "recommendations": _extract_recommendations(analysis_text),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Competitor analysis failed: {str(e)}",
            "analysis": "",
        }


def get_target_audience_insights(
    target_audience: str,
    industry: str,
    products_services: str = ""
) -> Dict:
    """
    Get insights about target audience preferences and behaviors.

    Args:
        target_audience: Target audience description
        industry: Industry or niche
        products_services: Products/services being marketed

    Returns:
        Dictionary with audience insights and video preferences
    """
    print(f"👥 Getting target audience insights")

    try:
        client = _get_client()

        prompt = f"""Provide insights about this target audience for video marketing:

TARGET AUDIENCE: {target_audience}
INDUSTRY: {industry}
{"PRODUCTS/SERVICES: " + products_services if products_services else ""}

Provide:
1. Demographics and psychographics
2. Pain points and desires
3. Preferred video content types
4. Best platforms for reaching them
5. Video length preferences
6. Messaging that resonates
7. Visual style preferences

Format as actionable insights for creating effective marketing videos.
"""

        model = os.getenv("STRATEGY_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        insights_text = response.text if hasattr(response, 'text') else str(response)

        return {
            "status": "success",
            "target_audience": target_audience,
            "insights": insights_text,
            "video_preferences": _extract_video_preferences(insights_text),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Audience insights failed: {str(e)}",
            "insights": "",
        }


def suggest_marketing_strategies(
    brand_name: str,
    marketing_goals: List[str],
    target_audience: str,
    industry: str
) -> Dict:
    """
    Suggest marketing video strategies based on goals and context.

    Args:
        brand_name: Name of the brand
        marketing_goals: List of marketing goals
        target_audience: Target audience description
        industry: Industry or niche

    Returns:
        Dictionary with suggested strategies and video concepts
    """
    print(f"💡 Suggesting marketing strategies for {brand_name}")

    try:
        client = _get_client()

        prompt = f"""Suggest marketing video strategies for:

BRAND: {brand_name}
MARKETING GOALS: {', '.join(marketing_goals)}
TARGET AUDIENCE: {target_audience}
INDUSTRY: {industry}

Provide:
1. 3-5 video strategy concepts aligned with goals
2. Recommended video types for each goal
3. Key messaging themes
4. Content pillars
5. Distribution strategy recommendations

Format as actionable strategies with specific video concepts.
"""

        model = os.getenv("STRATEGY_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,  # More creative for strategies
                max_output_tokens=2048,
            )
        )

        strategies_text = response.text if hasattr(response, 'text') else str(response)

        return {
            "status": "success",
            "brand_name": brand_name,
            "marketing_goals": marketing_goals,
            "strategies": strategies_text,
            "video_concepts": _extract_video_concepts(strategies_text),
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Strategy suggestion failed: {str(e)}",
            "strategies": "",
        }


def _extract_insights(text: str) -> List[str]:
    """Extract key insights from text."""
    import re
    # Look for numbered or bulleted insights
    insights = re.findall(r'(?:^|\n)[\d•\-\*]\s*([^\n]+)', text)
    return insights[:10] if insights else [text[:200]]


def _extract_recommendations(text: str) -> List[str]:
    """Extract recommendations from text."""
    import re
    # Look for recommendation patterns
    recommendations = re.findall(r'(?:recommend|suggest|should|consider)[:\-]?\s*([^\n]+)', text, re.IGNORECASE)
    return recommendations[:10] if recommendations else []


def _extract_video_preferences(text: str) -> Dict:
    """Extract video preferences from insights."""
    import re
    preferences = {
        "length": "",
        "platforms": [],
        "styles": [],
    }
    
    # Extract length mentions
    length_match = re.search(r'(\d+)[\s\-]*(?:second|minute|sec|min)', text, re.IGNORECASE)
    if length_match:
        preferences["length"] = length_match.group(0)
    
    # Extract platform mentions
    platforms = ["YouTube", "Instagram", "TikTok", "LinkedIn", "Facebook"]
    for platform in platforms:
        if platform.lower() in text.lower():
            preferences["platforms"].append(platform)
    
    return preferences


def _extract_video_concepts(text: str) -> List[str]:
    """Extract video concepts from strategies."""
    import re
    # Look for concept patterns
    concepts = re.findall(r'(?:concept|idea|video|strategy)[:\-]?\s*([^\n]+)', text, re.IGNORECASE)
    return concepts[:10] if concepts else []
