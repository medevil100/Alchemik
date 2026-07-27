"""
ComposerEngine configuration.

Defines the time window, limits, and merge rules for the
ETAP 7.3 Composite Events scaling engine.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class ComposerConfig:
    """
    Configuration for the ComposerEngine.

    Attributes:
        time_window_seconds: Maximum time span (in seconds) within which
            events for the same instrument are considered related and can
            be merged into a Composite Event.  Default: 60 seconds.
        max_composite_events: Maximum number of component events allowed
            in a single Composite Event.  Groups larger than this limit
            are split deterministically into multiple Composite Events.
            Default: 10.
        default_event_type: The event_type value assigned to every
            Composite Event created by the engine.
        default_event_family: The event_family used when component events
            belong to different families (the engine uses this as a
            fallback).
    """

    time_window_seconds: int = 60
    max_composite_events: int = 10
    default_event_type: str = "COMPOSITE_MULTI_EVENT"
    default_event_family: str = "SYSTEM"


# Module-level singleton — configuration values used by ComposerEngine.
_composer_config = ComposerConfig()


def get_composer_config() -> ComposerConfig:
    """Return the current ComposerEngine configuration."""
    return _composer_config


def set_composer_config(config: ComposerConfig) -> None:
    """
    Replace the active ComposerEngine configuration.

    Intended mainly for testing; the engine uses ``get_composer_config()``
    internally.
    """
    global _composer_config
    _composer_config = config