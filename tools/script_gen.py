"""
Script Generation Tools for Marketing Video Agent Factory.

Provides specialized script generation functions for marketing videos:
- Generate video scripts based on strategy and marketing context
- Refine scripts based on feedback
- Create script variations for A/B testing
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


def generate_video_script(
    video_type: str,
    strategy_concept: str,
    brand_name: str,
    target_audience: str,
    marketing_goals: List[str],
    brand_messaging: str,
    products_services: str = "",
    duration_seconds: int = 30,
    tone: str = "professional"
) -> Dict:
    """
    Generate a compelling video script based on marketing strategy.

    Args:
        video_type: Type of video (brand_story, product_launch, explainer, etc.)
        strategy_concept: The selected strategy/concept for the video
        brand_name: Name of the brand
        target_audience: Target audience description
        marketing_goals: List of marketing goals (awareness, conversion, etc.)
        brand_messaging: Key brand messages and value propositions
        products_services: Products/services being featured
        duration_seconds: Target video duration
        tone: Brand tone (professional, playful, etc.)

    Returns:
        Dictionary with script, hook, CTA, and notes
    """
    print(f"📝 Generating video script for {video_type} video")
    print(f"   Brand: {brand_name}, Duration: {duration_seconds}s")

    try:
        client = _get_client()

        # Build prompt based on video type
        prompt_parts = [
            f"Create a compelling {duration_seconds}-second video script for a {video_type} video.",
            "",
            f"BRAND: {brand_name}",
            f"TARGET AUDIENCE: {target_audience}",
            f"MARKETING GOALS: {', '.join(marketing_goals)}",
            f"BRAND MESSAGING: {brand_messaging}",
            "",
            f"STRATEGY CONCEPT: {strategy_concept}",
            "",
        ]

        if products_services:
            prompt_parts.append(f"PRODUCTS/SERVICES: {products_services}")
            prompt_parts.append("")

        prompt_parts.extend([
            "REQUIREMENTS:",
            f"- Tone: {tone}",
            "- Hook in first 3 seconds (grab attention)",
            "- Clear value proposition",
            "- Address target audience pain points",
            "- Strong call-to-action at the end",
            "- Natural, conversational language",
            "- Optimized for {duration_seconds} seconds",
            "",
            "OUTPUT FORMAT:",
            "1. HOOK (first 3 seconds)",
            "2. MAIN CONTENT (body)",
            "3. CTA (call-to-action)",
            "4. VISUAL NOTES (what should appear on screen)",
        ])

        full_prompt = "\n".join(prompt_parts)

        model = os.getenv("SCRIPT_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,  # More creative for scripts
                max_output_tokens=2048,
            )
        )

        script_text = response.text if hasattr(response, 'text') else str(response)

        # Parse script into components
        hook = _extract_section(script_text, "HOOK")
        main_content = _extract_section(script_text, "MAIN CONTENT") or _extract_section(script_text, "BODY")
        cta = _extract_section(script_text, "CTA") or _extract_section(script_text, "CALL-TO-ACTION")
        visual_notes = _extract_section(script_text, "VISUAL NOTES")

        return {
            "status": "success",
            "script": script_text,
            "hook": hook or script_text.split('\n')[0] if script_text else "",
            "main_content": main_content or script_text,
            "cta": cta or "",
            "visual_notes": visual_notes or "",
            "duration_estimate": duration_seconds,
            "word_count": len(script_text.split()),
            "video_type": video_type,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Script generation failed: {str(e)}",
            "script": "",
        }


def refine_script(
    original_script: str,
    feedback: str,
    brand_context: Dict,
    target_audience: str
) -> Dict:
    """
    Refine a script based on feedback.

    Args:
        original_script: The original script text
        feedback: User feedback on what to change
        brand_context: Brand context dictionary
        target_audience: Target audience description

    Returns:
        Dictionary with refined script
    """
    print(f"✏️ Refining script based on feedback")

    try:
        client = _get_client()

        prompt = f"""Refine this video script based on the feedback provided.

ORIGINAL SCRIPT:
{original_script}

FEEDBACK:
{feedback}

BRAND CONTEXT:
- Name: {brand_context.get('name', '')}
- Tone: {brand_context.get('tone', 'professional')}
- Messaging: {brand_context.get('marketing_context', {}).get('brand_messaging', '')}

TARGET AUDIENCE:
{target_audience}

Please refine the script to address the feedback while maintaining brand consistency and appeal to the target audience.
"""

        model = os.getenv("SCRIPT_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
            )
        )

        refined_script = response.text if hasattr(response, 'text') else str(response)

        return {
            "status": "success",
            "script": refined_script,
            "original_script": original_script,
            "changes_made": feedback,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Script refinement failed: {str(e)}",
            "script": original_script,
        }


def generate_script_variations(
    base_script: str,
    brand_context: Dict,
    num_variations: int = 3
) -> Dict:
    """
    Generate multiple script variations for A/B testing.

    Args:
        base_script: The base script
        brand_context: Brand context dictionary
        num_variations: Number of variations to generate (default: 3)

    Returns:
        Dictionary with script variations
    """
    print(f"🔄 Generating {num_variations} script variations")

    try:
        client = _get_client()

        prompt = f"""Generate {num_variations} distinct variations of this video script.
Each variation should:
- Maintain the core message
- Use different hooks and approaches
- Appeal to different aspects of the target audience
- Have unique CTAs

BASE SCRIPT:
{base_script}

BRAND CONTEXT:
- Name: {brand_context.get('name', '')}
- Tone: {brand_context.get('tone', 'professional')}

Format each variation clearly with:
VARIATION 1:
[script]

VARIATION 2:
[script]

etc.
"""

        model = os.getenv("SCRIPT_MODEL", "gemini-2.5-flash")
        
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9,  # More creative for variations
                max_output_tokens=4096,
            )
        )

        variations_text = response.text if hasattr(response, 'text') else str(response)

        # Parse variations
        variations = _parse_variations(variations_text, num_variations)

        return {
            "status": "success",
            "variations": variations,
            "base_script": base_script,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Variation generation failed: {str(e)}",
            "variations": [],
        }


def _extract_section(text: str, section_name: str) -> Optional[str]:
    """Extract a section from script text."""
    import re
    pattern = rf"(?i){section_name}[:\-]?\s*\n(.*?)(?=\n[A-Z]+[:\-]|$)"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None


def _parse_variations(text: str, num_variations: int) -> List[str]:
    """Parse variations from text."""
    import re
    variations = []
    pattern = r"(?i)variation\s+\d+[:\-]?\s*\n(.*?)(?=\nvariation\s+\d+|$)"
    matches = re.finditer(pattern, text, re.DOTALL)
    
    for match in matches:
        variations.append(match.group(1).strip())
    
    # If pattern didn't work, try splitting by numbered sections
    if len(variations) < num_variations:
        parts = re.split(r'\n(?=\d+[.)]\s)', text)
        variations = [p.strip() for p in parts if p.strip()][:num_variations]
    
    return variations[:num_variations]
