"""Configuration module for Phone Agent."""

from phone_agent.config.apps import APP_PACKAGES
from phone_agent.config.apps_ios import APP_PACKAGES_IOS
from phone_agent.config.i18n import get_message, get_messages
from phone_agent.config.prompts_en import SYSTEM_PROMPT as SYSTEM_PROMPT_EN
from phone_agent.config.prompts_en import SYSTEM_PROMPT_JSON as SYSTEM_PROMPT_EN_JSON
from phone_agent.config.prompts_zh import SYSTEM_PROMPT as SYSTEM_PROMPT_ZH
from phone_agent.config.prompts_zh import SYSTEM_PROMPT_JSON as SYSTEM_PROMPT_ZH_JSON
from phone_agent.config.timing import (
    TIMING_CONFIG,
    ActionTimingConfig,
    ConnectionTimingConfig,
    DeviceTimingConfig,
    TimingConfig,
    get_timing_config,
    update_timing_config,
)


def get_system_prompt(lang: str = "cn", format: str = "pseudo") -> str:
    """
    Get system prompt by language and output format.

    Args:
        lang: Language code, 'cn' for Chinese, 'en' for English.
        format: Output format, 'pseudo' for Python pseudo-code (AutoPhone),
                'json' for JSON format (generic cloud models).

    Returns:
        System prompt string.
    """
    if format == "json":
        if lang == "en":
            return SYSTEM_PROMPT_EN_JSON
        return SYSTEM_PROMPT_ZH_JSON

    # Default: pseudo format (AutoPhone native)
    if lang == "en":
        return SYSTEM_PROMPT_EN
    return SYSTEM_PROMPT_ZH


# Default to Chinese pseudo-code for backward compatibility
SYSTEM_PROMPT = SYSTEM_PROMPT_ZH

__all__ = [
    "APP_PACKAGES",
    "APP_PACKAGES_IOS",
    "SYSTEM_PROMPT",
    "SYSTEM_PROMPT_ZH",
    "SYSTEM_PROMPT_ZH_JSON",
    "SYSTEM_PROMPT_EN",
    "SYSTEM_PROMPT_EN_JSON",
    "get_system_prompt",
    "get_messages",
    "get_message",
    "TIMING_CONFIG",
    "TimingConfig",
    "ActionTimingConfig",
    "DeviceTimingConfig",
    "ConnectionTimingConfig",
    "get_timing_config",
    "update_timing_config",
]
# -*- coding: utf-8 -*-