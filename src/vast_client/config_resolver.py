"""
Configuration Resolution System for VAST Client

Implements a 4-level hierarchical configuration resolution system:
1. Global defaults (lowest precedence)
2. Provider-specific configuration
3. Publisher-specific overrides
4. Per-player instance overrides (highest precedence)

This module provides the ConfigResolver class which intelligently merges
configurations from different levels, ensuring type safety and validation.
"""

from dataclasses import replace
from typing import Any

from .config import (
    PlaybackSessionConfig,
    VastClientConfig,
    VastTrackerConfig,
    VastParserConfig,
    get_default_vast_config,
)


class ConfigResolver:
    """
    Resolves VAST client configuration through 4-level hierarchy.
    
    Resolution Order (lowest to highest precedence):
    1. Global hardcoded defaults
    2. Provider-specific defaults
    3. Publisher-specific overrides
    4. Per-player instance overrides
    
    Examples:
        Basic resolution with provider:
        >>> resolver = ConfigResolver()
        >>> config = resolver.resolve(provider="tiger")
        >>> print(config.playback.interruption_rules['start']['probability'])
        0.08  # Tiger-specific 8% start interruption rate
        
        Resolution with publisher override:
        >>> resolver = ConfigResolver()
        >>> publisher_overrides = {
        ...     "playback": {"max_session_duration_sec": 180}
        ... }
        >>> config = resolver.resolve(
        ...     provider="global",
        ...     publisher="premium_network",
        ...     publisher_overrides=publisher_overrides
        ... )
        >>> print(config.playback.max_session_duration_sec)
        180  # Publisher-specific override applied
        
        Resolution with per-player override:
        >>> resolver = ConfigResolver()
        >>> player_override = PlaybackSessionConfig(
        ...     enable_auto_quartiles=False,
        ...     log_tracking_urls=True
        ... )
        >>> config = resolver.resolve(
        ...     provider="leto",
        ...     playback_override=player_override
        ... )
        >>> print(config.playback.enable_auto_quartiles)
        False  # Player override takes precedence
    """
    
    def __init__(self):
        """Initialize the configuration resolver."""
        self._cache: dict[tuple, VastClientConfig] = {}
    
    def resolve(
        self,
        provider: str = "generic",
        publisher: str | None = None,
        publisher_overrides: dict[str, Any] | None = None,
        playback_override: PlaybackSessionConfig | None = None,
        tracker_override: VastTrackerConfig | None = None,
        parser_override: VastParserConfig | None = None,
    ) -> VastClientConfig:
        """
        Resolve configuration with 4-level hierarchy.
        
        Args:
            provider: Provider name (global, tiger, leto, yandex, google, custom)
            publisher: Publisher identifier for publisher-specific overrides
            publisher_overrides: Dictionary of publisher-specific configuration overrides
            playback_override: Per-player playback configuration override
            tracker_override: Per-player tracker configuration override
            parser_override: Per-player parser configuration override
        
        Returns:
            VastClientConfig: Fully resolved configuration
            
        Resolution Process:
            1. Start with provider defaults (get_default_vast_config)
            2. Apply publisher overrides if provided
            3. Apply per-player component overrides (playback, tracker, parser)
            4. Validate final configuration
        """
        # Create cache key for memoization
        cache_key = (
            provider,
            publisher,
            tuple(sorted(publisher_overrides.items())) if publisher_overrides else None,
            id(playback_override),  # Use object id for overrides
            id(tracker_override),
            id(parser_override),
        )
        
        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Level 1 & 2: Get provider-specific defaults
        config = get_default_vast_config(provider)
        
        # Level 3: Apply publisher overrides
        if publisher:
            config.publisher = publisher
        
        if publisher_overrides:
            config = self._apply_publisher_overrides(config, publisher_overrides)
        
        # Level 4: Apply per-player overrides (highest precedence)
        if playback_override:
            config = self._apply_playback_override(config, playback_override)
        
        if tracker_override:
            config = self._apply_tracker_override(config, tracker_override)
        
        if parser_override:
            config = self._apply_parser_override(config, parser_override)
        
        # Validate final configuration
        self._validate_config(config)
        
        # Cache and return
        self._cache[cache_key] = config
        return config
    
    def _apply_publisher_overrides(
        self,
        config: VastClientConfig,
        overrides: dict[str, Any]
    ) -> VastClientConfig:
        """
        Apply publisher-specific configuration overrides.
        
        Args:
            config: Base configuration
            overrides: Dictionary of publisher overrides
        
        Returns:
            VastClientConfig: Configuration with publisher overrides applied
        """
        # Apply parser overrides
        if "parser" in overrides:
            parser_overrides = overrides["parser"]
            parser_fields = {}
            for key, value in parser_overrides.items():
                if hasattr(config.parser, key):
                    parser_fields[key] = value
            if parser_fields:
                config.parser = replace(config.parser, **parser_fields)
        
        # Apply tracker overrides
        if "tracker" in overrides:
            tracker_overrides = overrides["tracker"]
            tracker_fields = {}
            for key, value in tracker_overrides.items():
                if hasattr(config.tracker, key):
                    tracker_fields[key] = value
            if tracker_fields:
                config.tracker = replace(config.tracker, **tracker_fields)
        
        # Apply playback overrides
        if "playback" in overrides:
            playback_overrides = overrides["playback"]
            playback_fields = {}
            for key, value in playback_overrides.items():
                if hasattr(config.playback, key):
                    playback_fields[key] = value
            if playback_fields:
                config.playback = replace(config.playback, **playback_fields)
        
        # Apply global config overrides
        global_fields = {}
        for key, value in overrides.items():
            if key not in ["parser", "tracker", "playback"] and hasattr(config, key):
                global_fields[key] = value
        if global_fields:
            config = replace(config, **global_fields)
        
        return config
    
    def _apply_playback_override(
        self,
        config: VastClientConfig,
        override: PlaybackSessionConfig
    ) -> VastClientConfig:
        """
        Apply per-player playback configuration override.
        
        Args:
            config: Base configuration
            override: Playback configuration override
        
        Returns:
            VastClientConfig: Configuration with playback override applied
        """
        # Merge playback configs (override takes precedence for non-default values)
        merged_playback = self._merge_playback_configs(config.playback, override)
        return replace(config, playback=merged_playback)
    
    def _apply_tracker_override(
        self,
        config: VastClientConfig,
        override: VastTrackerConfig
    ) -> VastClientConfig:
        """
        Apply per-player tracker configuration override.
        
        Args:
            config: Base configuration
            override: Tracker configuration override
        
        Returns:
            VastClientConfig: Configuration with tracker override applied
        """
        # Replace entire tracker config (simpler approach for tracker)
        return replace(config, tracker=override)
    
    def _apply_parser_override(
        self,
        config: VastClientConfig,
        override: VastParserConfig
    ) -> VastClientConfig:
        """
        Apply per-player parser configuration override.
        
        Args:
            config: Base configuration
            override: Parser configuration override
        
        Returns:
            VastClientConfig: Configuration with parser override applied
        """
        # Replace entire parser config
        return replace(config, parser=override)
    
    def _merge_playback_configs(
        self,
        base: PlaybackSessionConfig,
        override: PlaybackSessionConfig
    ) -> PlaybackSessionConfig:
        """
        Intelligently merge two playback configurations.
        
        The override config takes precedence for all non-default values.
        Special handling for interruption_rules to deep merge.
        
        Args:
            base: Base playback configuration
            override: Override playback configuration
        
        Returns:
            PlaybackSessionConfig: Merged configuration
        """
        # Start with base config fields
        merged_fields = {}
        default_config = PlaybackSessionConfig()
        
        # For each field in override, use override value if it differs from default
        for field_name in [f.name for f in PlaybackSessionConfig.__dataclass_fields__.values()]:
            override_value = getattr(override, field_name)
            default_value = getattr(default_config, field_name)
            base_value = getattr(base, field_name)
            
            # Special handling for interruption_rules (deep merge)
            if field_name == "interruption_rules":
                merged_fields[field_name] = self._merge_interruption_rules(
                    base_value, override_value, default_value
                )
            # Use override if it's not the default value
            elif override_value != default_value:
                merged_fields[field_name] = override_value
            else:
                merged_fields[field_name] = base_value
        
        return PlaybackSessionConfig(**merged_fields)
    
    def _merge_interruption_rules(
        self,
        base: dict[str, dict[str, Any]],
        override: dict[str, dict[str, Any]],
        default: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """
        Deep merge interruption rules dictionaries.
        
        Args:
            base: Base interruption rules
            override: Override interruption rules
            default: Default interruption rules
        
        Returns:
            dict: Merged interruption rules
        """
        merged = base.copy()
        
        # For each event type in override
        for event_type, override_rules in override.items():
            default_rules = default.get(event_type, {})
            
            # Only merge if override differs from default
            if override_rules != default_rules:
                if event_type in merged:
                    # Deep merge individual fields
                    merged[event_type] = {**merged[event_type], **override_rules}
                else:
                    # Add new event type
                    merged[event_type] = override_rules
        
        return merged
    
    def _validate_config(self, config: VastClientConfig) -> None:
        """
        Validate final resolved configuration.
        
        Args:
            config: Configuration to validate
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate playback configuration
        playback = config.playback
        
        # Validate session duration
        if playback.max_session_duration_sec < 0:
            raise ValueError(
                f"max_session_duration_sec must be >= 0, got {playback.max_session_duration_sec}"
            )
        
        # Validate interruption rules
        for event_type, rules in playback.interruption_rules.items():
            if "probability" in rules:
                prob = rules["probability"]
                if not 0.0 <= prob <= 1.0:
                    raise ValueError(
                        f"Interruption probability for '{event_type}' must be between 0.0 and 1.0, "
                        f"got {prob}"
                    )
        
        # Validate headless tick interval
        if playback.headless_tick_interval_sec <= 0:
            raise ValueError(
                f"headless_tick_interval_sec must be > 0, got {playback.headless_tick_interval_sec}"
            )
        
        # Validate quartile tolerance
        if playback.quartile_offset_tolerance_sec < 0:
            raise ValueError(
                f"quartile_offset_tolerance_sec must be >= 0, "
                f"got {playback.quartile_offset_tolerance_sec}"
            )
    
    def clear_cache(self) -> None:
        """Clear the configuration cache."""
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """Get the current cache size."""
        return len(self._cache)


__all__ = ["ConfigResolver"]
