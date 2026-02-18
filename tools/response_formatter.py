"""
Response Formatter Tool

This tool is called by the orchestrator before returning any response to the user.
It parses the response and extracts:
1. Text content (message to display)
2. Choices (structured options for user selection)

The frontend uses this structured output to render:
- Text message
- Interactive choice buttons (if choices exist)
- Free text input fallback (if no choices or user wants custom input)
"""

import re
import json
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class ChoiceType(Enum):
    """Type of choice for UI rendering hints"""
    SINGLE_SELECT = "single_select"  # Radio buttons / chips - select one
    MULTI_SELECT = "multi_select"    # Checkboxes - select multiple
    CONFIRMATION = "confirmation"     # Yes/No/Cancel type
    MENU = "menu"                     # Main menu options


@dataclass
class Choice:
    """A single choice option"""
    id: str                          # Unique identifier (e.g., "option_1", "yes", "single_post")
    label: str                       # Display text (e.g., "Single Post", "Yes, proceed")
    value: str                       # Value to send back (e.g., "single_post", "yes")
    icon: str = ""                   # Optional emoji icon
    description: str = ""            # Optional description/subtitle

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FormattedResponse:
    """Structured response for the frontend"""
    text: str                        # Main message text (markdown supported)
    has_choices: bool = False        # Whether choices are present
    choice_type: str = "single_select"  # Type of choice UI to render
    choices: list = field(default_factory=list)  # List of Choice objects
    allow_free_input: bool = True    # Whether to show free text input
    input_placeholder: str = "Type your response..."  # Placeholder for free input
    input_hint: str = ""             # Hint text above input (e.g., "Or describe what you want")

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "has_choices": self.has_choices,
            "choice_type": self.choice_type,
            "choices": [c.to_dict() if isinstance(c, Choice) else c for c in self.choices],
            "allow_free_input": self.allow_free_input,
            "input_placeholder": self.input_placeholder,
            "input_hint": self.input_hint
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def format_response_for_user(
    response_text: str,
    force_choices: Optional[str] = None,
    choice_type: str = "single_select",
    allow_free_input: bool = True,
    input_placeholder: str = "Type your response...",
    input_hint: str = ""
) -> str:
    """
    Format the orchestrator's response for the frontend.

    This tool MUST be called by the orchestrator before returning any response.
    It parses the response text and extracts choices if present.

    Args:
        response_text: The full response text from the orchestrator
        force_choices: Optional JSON string of choices to force display
                      Format: '[{"id": "opt1", "label": "Option 1", "value": "option1", "icon": "📸", "description": "..."}]'
        choice_type: Type of choice UI - "single_select", "multi_select", "confirmation", "menu"
        allow_free_input: Whether to show free text input below choices
        input_placeholder: Placeholder text for the input field
        input_hint: Hint text shown above input (e.g., "Or type your own idea")

    Returns:
        JSON string with structured response
    """
    # If force_choices is provided, use those directly
    if force_choices:
        try:
            choices_list = json.loads(force_choices)
            choices = [
                Choice(
                    id=c.get("id", f"option_{i}"),
                    label=c.get("label", ""),
                    value=c.get("value", c.get("label", "")),
                    icon=c.get("icon", ""),
                    description=c.get("description", "")
                )
                for i, c in enumerate(choices_list)
            ]

            # Clean the response text (remove choice patterns if they exist)
            clean_text = _remove_choice_patterns(response_text)

            result = FormattedResponse(
                text=clean_text,
                has_choices=True,
                choice_type=choice_type,
                choices=choices,
                allow_free_input=allow_free_input,
                input_placeholder=input_placeholder,
                input_hint=input_hint if input_hint else ("Or type your own response" if allow_free_input else "")
            )

            return result.to_json()

        except json.JSONDecodeError:
            pass  # Fall through to auto-detection

    # Auto-detect choices from the response text
    choices = _extract_choices_from_text(response_text)

    if choices:
        # Clean the response text
        clean_text = _remove_choice_patterns(response_text)

        # Detect choice type from context
        detected_type = _detect_choice_type(choices, response_text)

        result = FormattedResponse(
            text=clean_text,
            has_choices=True,
            choice_type=detected_type,
            choices=choices,
            allow_free_input=allow_free_input,
            input_placeholder=input_placeholder,
            input_hint=input_hint if input_hint else ("Or type your own response" if allow_free_input else "")
        )
    else:
        # No choices detected - just text response
        result = FormattedResponse(
            text=response_text,
            has_choices=False,
            choice_type="single_select",
            choices=[],
            allow_free_input=allow_free_input,
            input_placeholder=input_placeholder,
            input_hint=input_hint
        )

    return result.to_json()


def _extract_choices_from_text(text: str) -> list:
    """Extract choice options from response text using multiple patterns."""
    choices = []
    seen_labels = set()

    # Common emoji set for matching
    emoji_set = r'[📸📅🖼️✨🎬✏️🔄✅❌👍👎🎯💡📝🚀💼📊🎨📱💰🔥⭐🌟💫🎉🎊👋🤝💪🙌👏🎁💝💖💕❤️🧡💛💚💙💜🖤🤍🤎🌹💌🏠🏢🛒🎵🎶🍕🍔☕️🌮🥗🏃‍♂️🧘‍♀️💼👔👗🎮📚✈️🏖️🎄🎃🐰🐣🦃🎅]'

    # Pattern 1: Emoji menu format - **💝 Label** - description
    emoji_menu_pattern = rf'\*\*({emoji_set})\s*([^*]+?)\*\*\s*[-–—:]\s*([^\n]+)'
    for match in re.finditer(emoji_menu_pattern, text):
        icon = match.group(1).strip()
        label = match.group(2).strip()
        description = match.group(3).strip()

        norm_label = label.lower().strip()
        if norm_label not in seen_labels and len(label) > 0:
            seen_labels.add(norm_label)
            choices.append(Choice(
                id=_to_id(label),
                label=label,
                value=label.lower(),
                icon=icon,
                description=description
            ))

    if len(choices) >= 2:
        return choices[:8]

    # Pattern 2: Numbered options
    numbered_pattern = r'^\s*(\d+)[.)\]]\s*\*?\*?([^*\n-]+)\*?\*?\s*(?:[-–—:]\s*([^\n]+))?'
    for match in re.finditer(numbered_pattern, text, re.MULTILINE):
        label = match.group(2).strip()
        description = match.group(3).strip() if match.group(3) else ""

        if any(skip in label.lower() for skip in ['step', 'first', 'then', 'next', 'finally']):
            continue

        if label.lower() not in seen_labels and len(label) < 50:
            seen_labels.add(label.lower())
            icon = _get_icon_for_label(label)
            choices.append(Choice(
                id=_to_id(label),
                label=label,
                value=label.lower(),
                icon=icon,
                description=description
            ))

    if len(choices) >= 2:
        return choices[:8]

    return []


def _remove_choice_patterns(text: str) -> str:
    """Remove choice option patterns from text, leaving clean message."""
    text = re.sub(r'\n\s*\*\*[📸📅🖼️✨🎬✏️🔄✅❌👍👎🎯💡📝🚀💼📊🎨📱💰🔥⭐🌟💫✨🎉🎊👋🤝💪🙌👏🎁💝💖💕❤️🧡💛💚💙💜🖤🤍🤎]+\s*[^*]+\*\*\s*[-–—:][^\n]+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()
    return text


def _detect_choice_type(choices: list, text: str) -> str:
    """Detect the type of choices based on content."""
    labels_lower = [c.label.lower() for c in choices]

    confirmation_words = {'yes', 'no', 'approve', 'reject', 'confirm', 'cancel', 'skip', 'proceed'}
    if any(word in ' '.join(labels_lower) for word in confirmation_words):
        return "confirmation"

    menu_words = {'post', 'campaign', 'image', 'video', 'carousel', 'blog', 'create', 'generate'}
    if any(word in ' '.join(labels_lower) for word in menu_words):
        return "menu"

    return "single_select"


def _to_id(label: str) -> str:
    """Convert label to a valid ID."""
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', label.lower())
    return re.sub(r'\s+', '_', clean.strip())[:30]


def _get_icon_for_label(label: str) -> str:
    """Get an appropriate icon based on the label text."""
    label_lower = label.lower()

    icon_map = {
        'yes': '✅', 'approve': '✅', 'confirm': '✅', 'proceed': '✅',
        'no': '❌', 'reject': '❌', 'cancel': '❌',
        'skip': '⏭️', 'edit': '✏️',
        'video': '🎬', 'reel': '🎬', 'animate': '🎬',
        'generate': '✨', 'create': '✨',
        'idea': '💡', 'suggest': '💡',
        'done': '🎉', 'finish': '🎉',
    }

    for keyword, icon in icon_map.items():
        if keyword in label_lower:
            return icon

    return ''


__all__ = ['format_response_for_user', 'FormattedResponse', 'Choice', 'ChoiceType']
