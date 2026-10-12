"""Configuration module for AI Job Hunter."""

from config.profile import CANDIDATE_PROFILE, get_candidate_context
from config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "CANDIDATE_PROFILE", "get_candidate_context"]
