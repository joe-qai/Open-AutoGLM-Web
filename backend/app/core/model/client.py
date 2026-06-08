"""Model client for AI inference using OpenAI-compatible API."""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from openai import OpenAI

try:
    import anthropic
except ImportError:
    anthropic = None

from app.core.config.i18n import get_message

# Marker strings for JSON format (used in both streaming and parsing)
# Using standard XML-style tags that all cloud models recognize and follow reliably
JSON_ANSWER_OPEN = "<json_answer>"
JSON_ANSWER_CLOSE = "</json_answer>"
JSON_THINK_OPEN = "<json_think>"
JSON_THINK_CLOSE = "</json_think>"


@dataclass
class ModelConfig:
    """Configuration for the AI model."""

    base_url: str = "http://localhost:8000/v1"
    api_key: str = "EMPTY"
    model_name: str = "AutoPhone-phone-9b"
    provider: str = "openai"  # 'openai' or 'anthropic'
    max_tokens: int = 3000
    temperature: float = 0.0
    top_p: float = 0.85
    frequency_penalty: float = 0.2
    extra_body: dict[str, Any] = field(default_factory=dict)
    lang: str = "cn"  # Language for UI messages: 'cn' or 'en'


@dataclass
class ModelResponse:
    """Response from the AI model."""

    thinking: str
    action: str
    raw_content: str
    # Performance metrics
    time_to_first_token: float | None = None  # Time to first token (seconds)
    time_to_thinking_end: float | None = None  # Time to thinking end (seconds)
    total_time: float | None = None  # Total inference time (seconds)


class ModelClient:
    """
    Client for interacting with OpenAI-compatible vision-language models.

    Args:
        config: Model configuration.
    """

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        if self.config.provider == "anthropic":
            if anthropic is None:
                raise ImportError("Anthropic module not installed. Install with: pip install anthropic")
            self.client = anthropic.Anthropic(
                api_key=self.config.api_key,
                base_url=self.config.base_url if self.config.base_url else None
            )
        else:
            # Configure OpenAI client with proper timeout and SSL settings
            from httpx import Timeout
            timeout = Timeout(connect=30.0, read=120.0, write=60.0, pool=5.0)
            self.client = OpenAI(
                base_url=self.config.base_url, 
                api_key=self.config.api_key,
                timeout=timeout,
            )

    def request(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """
        Send a request to the model.

        Args:
            messages: List of message dictionaries in OpenAI format.

        Returns:
            ModelResponse containing thinking and action.

        Raises:
            ValueError: If the response cannot be parsed.
        """
        if self.config.provider == "anthropic":
            return self._request_anthropic(messages)
        else:
            return self._request_openai(messages)

    def _request_anthropic(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """Anthropic request logic."""
        start_time = time.time()
        time_to_first_token = None
        time_to_thinking_end = None

        # Convert messages to Anthropic format
        system_prompt = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                role = msg["role"]
                content = []
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item["type"] == "text":
                            content.append({"type": "text", "text": item["text"]})
                        elif item["type"] == "image_url":
                            # Extract base64 from data URL
                            url = item["image_url"]["url"]
                            base64_data = url.split(",", 1)[1]
                            content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_data
                                }
                            })
                else:
                    content = msg["content"]
                anthropic_messages.append({"role": role, "content": content})

        stream = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system_prompt,
            messages=anthropic_messages,
            stream=True,
        )

        raw_content = ""
        buffer = ""
        in_action_phase = False
        first_token_received = False
        pseudo_markers = ["finish(message=", "do(action="]
        xml_answer_open = "<answer>"
        all_markers = pseudo_markers + [JSON_ANSWER_OPEN, xml_answer_open]

        for event in stream:
            if event.type == "content_block_delta":
                content = event.delta.text
                raw_content += content

                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                if in_action_phase:
                    continue

                buffer += content

                # Reuse same parsing logic as OpenAI for markers
                if JSON_ANSWER_OPEN in buffer:
                    thinking_part = buffer.split(JSON_ANSWER_OPEN, 1)[0]
                    for tag in [JSON_THINK_OPEN, JSON_THINK_CLOSE]:
                        thinking_part = thinking_part.replace(tag, "")
                    thinking_part = thinking_part.strip()
                    if thinking_part:
                        print(thinking_part, end="", flush=True)
                    print()
                    in_action_phase = True
                    if time_to_thinking_end is None:
                        time_to_thinking_end = time.time() - start_time
                    continue

                marker_found = False
                for marker in pseudo_markers:
                    if marker in buffer:
                        thinking_part = buffer.split(marker, 1)[0]
                        print(thinking_part, end="", flush=True)
                        print()
                        in_action_phase = True
                        marker_found = True
                        if time_to_thinking_end is None:
                            time_to_thinking_end = time.time() - start_time
                        break

                if not marker_found and xml_answer_open in buffer:
                    thinking_part = buffer.split(xml_answer_open, 1)[0]
                    for tag in [JSON_THINK_OPEN, JSON_THINK_CLOSE]:
                        thinking_part = thinking_part.replace(tag, "")
                    thinking_part = thinking_part.strip()
                    if thinking_part:
                        print(thinking_part, end="", flush=True)
                    print()
                    in_action_phase = True
                    marker_found = True
                    if time_to_thinking_end is None:
                        time_to_thinking_end = time.time() - start_time

                if marker_found:
                    continue

                is_potential_marker = False
                for marker in all_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_potential_marker = True
                            break
                    if is_potential_marker:
                        break

                if not is_potential_marker:
                    print(buffer, end="", flush=True)
                    buffer = ""

        total_time = time.time() - start_time
        thinking, action = self._parse_response(raw_content)

        # Print performance metrics (reuse message helper if needed)
        lang = self.config.lang
        print()
        print("=" * 50)
        print(f"⏱️  {get_message('performance_metrics', lang)}:")
        print("-" * 50)
        if time_to_first_token is not None:
            print(f"{get_message('time_to_first_token', lang)}: {time_to_first_token:.3f}s")
        if time_to_thinking_end is not None:
            print(f"{get_message('time_to_thinking_end', lang)}:        {time_to_thinking_end:.3f}s")
        print(f"{get_message('total_inference_time', lang)}:          {total_time:.3f}s")
        print("=" * 50)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _request_openai(self, messages: list[dict[str, Any]]) -> ModelResponse:
        """Original OpenAI request logic."""
        # Start timing
        start_time = time.time()
        time_to_first_token = None
        time_to_thinking_end = None

        stream = self.client.chat.completions.create(
            messages=messages,
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            frequency_penalty=self.config.frequency_penalty,
            extra_body=self.config.extra_body,
            stream=True,
        )

        raw_content = ""
        buffer = ""  # Buffer to hold content that might be part of a marker

        # Markers for pseudo-code format (AutoPhone native)
        pseudo_markers = ["finish(message=", "do(action="]
        # XML markers (legacy format)
        xml_answer_open = "<answer>"

        in_action_phase = False  # Track if we've entered the action phase
        first_token_received = False

        # All markers to check for prefix matching
        all_markers = pseudo_markers + [JSON_ANSWER_OPEN, xml_answer_open]

        for chunk in stream:
            if len(chunk.choices) == 0:
                continue
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                raw_content += content

                # Record time to first token
                if not first_token_received:
                    time_to_first_token = time.time() - start_time
                    first_token_received = True

                if in_action_phase:
                    # Already in action phase, just accumulate content without printing
                    continue

                buffer += content

                # Check for JSON format markers first
                if JSON_ANSWER_OPEN in buffer:
                    # JSON format detected
                    thinking_part = buffer.split(JSON_ANSWER_OPEN, 1)[0]
                    # Strip think/close tags from thinking if present
                    for tag in [JSON_THINK_OPEN, JSON_THINK_CLOSE]:
                        thinking_part = thinking_part.replace(tag, "")
                    thinking_part = thinking_part.strip()
                    if thinking_part:
                        print(thinking_part, end="", flush=True)
                    print()  # Print newline after thinking is complete
                    in_action_phase = True

                    if time_to_thinking_end is None:
                        time_to_thinking_end = time.time() - start_time

                    continue

                # Check for pseudo-code format markers
                marker_found = False
                for marker in pseudo_markers:
                    if marker in buffer:
                        thinking_part = buffer.split(marker, 1)[0]
                        print(thinking_part, end="", flush=True)
                        print()  # Print newline after thinking is complete
                        in_action_phase = True
                        marker_found = True

                        if time_to_thinking_end is None:
                            time_to_thinking_end = time.time() - start_time

                        break

                # Check for XML format markers (legacy)
                if not marker_found and xml_answer_open in buffer:
                    thinking_part = buffer.split(xml_answer_open, 1)[0]
                    # Remove any JSON think tags if present
                    for tag in [JSON_THINK_OPEN, JSON_THINK_CLOSE]:
                        thinking_part = thinking_part.replace(tag, "")
                    thinking_part = thinking_part.strip()
                    if thinking_part:
                        print(thinking_part, end="", flush=True)
                    print()
                    in_action_phase = True
                    marker_found = True

                    if time_to_thinking_end is None:
                        time_to_thinking_end = time.time() - start_time

                if marker_found:
                    continue  # Continue to collect remaining content

                # Check if buffer ends with a prefix of any marker
                # If so, don't print yet (wait for more content)
                is_potential_marker = False
                for marker in all_markers:
                    for i in range(1, len(marker)):
                        if buffer.endswith(marker[:i]):
                            is_potential_marker = True
                            break
                    if is_potential_marker:
                        break

                if not is_potential_marker:
                    # Safe to print the buffer
                    print(buffer, end="", flush=True)
                    buffer = ""

        # Calculate total time
        total_time = time.time() - start_time

        # Parse thinking and action from response
        thinking, action = self._parse_response(raw_content)

        # Print performance metrics
        lang = self.config.lang
        print()
        print("=" * 50)
        print(f"⏱️  {get_message('performance_metrics', lang)}:")
        print("-" * 50)
        if time_to_first_token is not None:
            print(
                f"{get_message('time_to_first_token', lang)}: {time_to_first_token:.3f}s"
            )
        if time_to_thinking_end is not None:
            print(
                f"{get_message('time_to_thinking_end', lang)}:        {time_to_thinking_end:.3f}s"
            )
        print(
            f"{get_message('total_inference_time', lang)}:          {total_time:.3f}s"
        )
        print("=" * 50)

        return ModelResponse(
            thinking=thinking,
            action=action,
            raw_content=raw_content,
            time_to_first_token=time_to_first_token,
            time_to_thinking_end=time_to_thinking_end,
            total_time=total_time,
        )

    def _parse_response(self, content: str) -> tuple[str, str]:
        """
        Parse the model response into thinking and action parts.

        Supports three formats:
        1. JSON format (generic cloud models): uses Bengali numeral markers
        2. Pseudo-code format (AutoPhone native): do(action=...) or finish(message=...)
        3. Legacy XML format: <answer>...</answer>

        Auto-detects format based on marker presence.

        Args:
            content: Raw response content.

        Returns:
            Tuple of (thinking, action).
        """
        # Rule 1: JSON format markers
        if JSON_ANSWER_OPEN in content:
            # Extract thinking part
            thinking = content
            if JSON_THINK_OPEN in content:
                think_start = content.find(JSON_THINK_OPEN) + len(JSON_THINK_OPEN)
                think_end = content.find(JSON_THINK_CLOSE)
                if think_end != -1:
                    thinking = content[think_start:think_end].strip()
                else:
                    thinking = content[think_start:].split(JSON_ANSWER_OPEN, 1)[0].strip()
            else:
                # No think tags - everything before answer tag is thinking
                thinking = content.split(JSON_ANSWER_OPEN, 1)[0].strip()

            # Extract action part
            action_start = content.find(JSON_ANSWER_OPEN) + len(JSON_ANSWER_OPEN)
            if JSON_ANSWER_CLOSE in content[action_start:]:
                action_end = content.find(JSON_ANSWER_CLOSE, action_start)
                action = content[action_start:action_end].strip()
            else:
                action = content[action_start:].strip()

            return thinking, action

        # Rule 2: Pseudo-code format - finish(message=
        if "finish(message=" in content:
            parts = content.split("finish(message=", 1)
            thinking = parts[0].strip()
            action = "finish(message=" + parts[1]
            return thinking, action

        # Rule 3: Pseudo-code format - do(action=
        if "do(action=" in content:
            parts = content.split("do(action=", 1)
            thinking = parts[0].strip()
            action = "do(action=" + parts[1]
            return thinking, action

        # Rule 4: Legacy XML tag parsing
        if "<answer>" in content:
            parts = content.split("<answer>", 1)
            thinking = parts[0].strip()
            # Remove Bengali thinking tags if present
            for tag in [JSON_THINK_OPEN, JSON_THINK_CLOSE]:
                thinking = thinking.replace(tag, "")
            action = parts[1].replace("</answer>", "").strip()
            return thinking, action

        # Rule 5: Try to extract JSON object from raw content (fallback for models
        # that don't use markers but output JSON directly)
        json_match = re.search(r'\{[^{}]*"action"\s*:\s*"[^"]+"[^{}]*\}', content)
        if json_match:
            action = json_match.group(0)
            thinking = content[:json_match.start()].strip()
            # Clean thinking tags if present
            for tag in [JSON_THINK_OPEN, JSON_THINK_CLOSE]:
                thinking = thinking.replace(tag, "")
            return thinking.strip(), action

        # Rule 6: No markers found, return content as action
        return "", content


class MessageBuilder:
    """Helper class for building conversation messages."""

    @staticmethod
    def create_system_message(content: str) -> dict[str, Any]:
        """Create a system message."""
        return {"role": "system", "content": content}

    @staticmethod
    def create_user_message(
        text: str, image_base64: str | None = None
    ) -> dict[str, Any]:
        """
        Create a user message with optional image.

        Args:
            text: Text content.
            image_base64: Optional base64-encoded image.

        Returns:
            Message dictionary.
        """
        content = []

        if image_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                }
            )

        content.append({"type": "text", "text": text})

        return {"role": "user", "content": content}

    @staticmethod
    def create_assistant_message(content: str) -> dict[str, Any]:
        """Create an assistant message."""
        return {"role": "assistant", "content": content}

    @staticmethod
    def remove_images_from_message(message: dict[str, Any]) -> dict[str, Any]:
        """
        Remove image content from a message to save context space.

        Args:
            message: Message dictionary.

        Returns:
            Message with images removed.
        """
        if isinstance(message.get("content"), list):
            message["content"] = [
                item for item in message["content"] if item.get("type") == "text"
            ]
        return message

    @staticmethod
    def build_screen_info(current_app: str, **extra_info) -> str:
        """
        Build screen info string for the model.

        Args:
            current_app: Current app name.
            **extra_info: Additional info to include.

        Returns:
            JSON string with screen info.
        """
        info = {"current_app": current_app, **extra_info}
        return json.dumps(info, ensure_ascii=False)
# -*- coding: utf-8 -*-