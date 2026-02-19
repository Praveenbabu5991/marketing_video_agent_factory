"""
Response Formatter Tool

Parses agent responses and extracts structured choices for the frontend UI.
"""

import re
import json
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class ChoiceType(Enum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    CONFIRMATION = "confirmation"
    MENU = "menu"


@dataclass
class Choice:
    id: str
    label: str
    value: str
    icon: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FormattedResponse:
    text: str
    has_choices: bool = False
    choice_type: str = "single_select"
    choices: list = field(default_factory=list)
    allow_free_input: bool = True
    input_placeholder: str = "Type your response..."
    input_hint: str = ""

    def to_dict(self) -> dict:
        return {
            "text": self.text, "has_choices": self.has_choices,
            "choice_type": self.choice_type,
            "choices": [c.to_dict() if isinstance(c, Choice) else c for c in self.choices],
            "allow_free_input": self.allow_free_input,
            "input_placeholder": self.input_placeholder, "input_hint": self.input_hint
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def format_response_for_user(
    response_text: str, force_choices: Optional[str] = None,
    choice_type: str = "single_select", allow_free_input: bool = True,
    input_placeholder: str = "Type your response...", input_hint: str = ""
) -> str:
    """
    Format the orchestrator's response for the frontend.

    Args:
        response_text: The full response text from the orchestrator
        force_choices: Optional JSON string of choices to force display
        choice_type: Type of choice UI
        allow_free_input: Whether to show free text input
        input_placeholder: Placeholder text for input
        input_hint: Hint text above input

    Returns:
        JSON string with structured response
    """
    if force_choices:
        try:
            choices_list = json.loads(force_choices)
            choices = [
                Choice(
                    id=c.get("id", f"option_{i}"), label=c.get("label", ""),
                    value=c.get("value", c.get("label", "")),
                    icon=c.get("icon", ""), description=c.get("description", "")
                )
                for i, c in enumerate(choices_list)
            ]
            clean_text = _remove_choice_patterns(response_text)
            result = FormattedResponse(
                text=clean_text, has_choices=True, choice_type=choice_type,
                choices=choices, allow_free_input=allow_free_input,
                input_placeholder=input_placeholder,
                input_hint=input_hint if input_hint else ("Or type your own response" if allow_free_input else "")
            )
            return result.to_json()
        except json.JSONDecodeError:
            pass

    choices = _extract_choices_from_text(response_text)

    if choices:
        clean_text = _remove_choice_patterns(response_text)
        detected_type = _detect_choice_type(choices, response_text)
        result = FormattedResponse(
            text=clean_text, has_choices=True, choice_type=detected_type,
            choices=choices, allow_free_input=allow_free_input,
            input_placeholder=input_placeholder,
            input_hint=input_hint if input_hint else ("Or type your own response" if allow_free_input else "")
        )
    else:
        result = FormattedResponse(
            text=response_text, has_choices=False, choices=[],
            allow_free_input=allow_free_input,
            input_placeholder=input_placeholder, input_hint=input_hint
        )

    return result.to_json()


def _extract_choices_from_text(text: str) -> list:
    """Extract choice options from response text."""
    choices = []
    seen_labels = set()

    # Numbered options
    numbered_pattern = r'^\s*(\d+)[.)\]]\s*\*?\*?([^*\n-]+)\*?\*?\s*(?:[-–—:]\s*([^\n]+))?'
    for match in re.finditer(numbered_pattern, text, re.MULTILINE):
        label = match.group(2).strip()
        description = match.group(3).strip() if match.group(3) else ""
        if any(skip in label.lower() for skip in ['step', 'first', 'then', 'next', 'finally']):
            continue
        if label.lower() not in seen_labels and len(label) < 50:
            seen_labels.add(label.lower())
            choices.append(Choice(id=_to_id(label), label=label, value=label.lower(), icon=_get_icon_for_label(label), description=description))

    if len(choices) >= 2:
        return choices[:8]

    # Bullet options
    bullet_pattern = r'^\s*[-•*]\s*\*?\*?([^*\n-]+)\*?\*?\s*(?:[-–—:]\s*([^\n]+))?'
    for match in re.finditer(bullet_pattern, text, re.MULTILINE):
        label = match.group(1).strip()
        description = match.group(2).strip() if match.group(2) else ""
        if len(label) > 50 or label.count(' ') > 6:
            continue
        if label.lower() not in seen_labels:
            seen_labels.add(label.lower())
            choices.append(Choice(id=_to_id(label), label=label, value=label.lower(), icon=_get_icon_for_label(label), description=description))

    if 2 <= len(choices) <= 8:
        return choices
    return []


def _remove_choice_patterns(text: str) -> str:
    """Remove choice option patterns from text."""
    text = re.sub(r'\n\s*\d+[.)\]]\s*\*?\*?[^*\n]+\*?\*?(?:\s*[-–—:][^\n]+)?(?=\n|$)', '', text)
    text = re.sub(r'\n\s*[-•*]\s*\*?\*?[^*\n]{1,50}\*?\*?(?:\s*[-–—:][^\n]+)?(?=\n|$)', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _detect_choice_type(choices: list, text: str) -> str:
    labels_lower = [c.label.lower() for c in choices]
    if any(word in ' '.join(labels_lower) for word in {'yes', 'no', 'approve', 'reject', 'confirm', 'cancel', 'skip'}):
        return "confirmation"
    if any(word in ' '.join(labels_lower) for word in {'video', 'animation', 'create', 'generate'}):
        return "menu"
    return "single_select"


def _to_id(label: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', label.lower())
    return re.sub(r'\s+', '_', clean.strip())[:30]


def _get_icon_for_label(label: str) -> str:
    label_lower = label.lower()
    icon_map = {
        'yes': '✅', 'approve': '✅', 'no': '❌', 'cancel': '❌', 'skip': '⏭️',
        'edit': '✏️', 'video': '🎬', 'animate': '🎬', 'animation': '🎬',
        'generate': '✨', 'create': '✨', 'download': '⬇️',
        'idea': '💡', 'suggest': '💡', 'done': '🎉', 'new': '🆕',
    }
    for keyword, icon in icon_map.items():
        if keyword in label_lower:
            return icon
    return ''


__all__ = ['format_response_for_user', 'FormattedResponse', 'Choice', 'ChoiceType']
