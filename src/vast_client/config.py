"""
VAST Client Configuration Module

Provides configuration classes for all VAST client components,
enabling provider-specific customization and publisher overrides.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal

from .settings import get_settings
from .context import TrackingContext


class ExtractMode(str, Enum):
    """XPath extraction mode enumeration."""

    SINGLE = "single"  # Extract first match only
    LIST = "list"  # Extract all matches as list


class PlaybackMode(str, Enum):
    """Playback mode enumeration."""

    REAL = "real"  # Real-time playback (wall-clock)
    HEADLESS = "headless"  # Simulated playback (virtual time)
    AUTO = "auto"  # Auto-detect from settings


class InterruptionType(str, Enum):
    """Playback interruption reason enumeration."""

    NONE = "none"
    PAUSE = "pause"
    STOP = "stop"
    ERROR = "error"
    TIMEOUT = "timeout"
    EXCEEDED_LIMIT = "exceeded_limit"


@dataclass
class VastParserConfig:
    """Configuration for VAST XML parsing."""

    # Standard XPath selectors
    xpath_ad_system: str = ".//AdSystem"
    xpath_ad_title: str = ".//AdTitle"
    xpath_impression: str = ".//Impression"
    xpath_error: str = ".//Error"
    xpath_creative: str = ".//Creative"
    xpath_media_files: str = ".//MediaFile"
    xpath_tracking_events: str = ".//Tracking"
    xpath_duration: str = ".//Duration"
    xpath_extensions: str = ".//Extensions/Extension"

    # Custom XPath for provider-specific fields
    custom_xpaths: dict[str, str] = field(default_factory=dict)

    # Parsing options
    strict_xml: bool = False
    recover_on_error: bool = True
    encoding: str = "utf-8"

    # Publisher-specific overrides
    publisher_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaybackSessionConfig:
    """
    Configuration for VAST ad playback sessions.

    Controls playback behavior, including mode selection (real vs. simulated),
    interruption handling, and session persistence. Supports provider-specific
    and publisher-specific overrides through hierarchical configuration.

    Attributes:
        mode: Playback mode - 'real' (wall-clock), 'headless' (simulated), or 'auto' (auto-detect)
        interruption_rules: Provider-specific interruption probabilities and timing rules
        max_session_duration_sec: Maximum playback duration in seconds (0 = unlimited)
        enable_auto_quartiles: Automatically track quartile events at 25/50/75 percent
        quartile_offset_tolerance_sec: Tolerance for quartile detection (seconds)
        headless_tick_interval_sec: Simulation tick interval for headless playback (seconds)
        enable_session_persistence: Store playback sessions for recovery (feature-gated)
        emit_playback_events: Emit structured playback event logs
        log_tracking_urls: Log tracking URLs before sending

    Examples:
        Basic real-time playback:
        >>> config = PlaybackSessionConfig(mode=PlaybackMode.REAL)

        Headless with custom interruption rules:
        >>> config = PlaybackSessionConfig(
        ...     mode=PlaybackMode.HEADLESS,
        ...     interruption_rules={
        ...         'start': {'probability': 0.1, 'min_offset_sec': 0, 'max_offset_sec': 2},
        ...         'midpoint': {'probability': 0.05, 'min_offset_sec': -5, 'max_offset_sec': 5}
        ...     }
        ... )

        Production configuration with session persistence:
        >>> config = PlaybackSessionConfig(
        ...     mode=PlaybackMode.AUTO,
        ...     max_session_duration_sec=300,
        ...     enable_session_persistence=True,
        ...     enable_auto_quartiles=True
        ... )
    """

    # Playback mode selection
    mode: PlaybackMode = PlaybackMode.REAL

    # Interruption rules (provider-specific)
    # Structure: {event_type: {'probability': float, 'min_offset_sec': int, 'max_offset_sec': int}}
    interruption_rules: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "start": {"probability": 0.0, "min_offset_sec": 0, "max_offset_sec": 2},
            "firstQuartile": {"probability": 0.0, "min_offset_sec": -2, "max_offset_sec": 2},
            "midpoint": {"probability": 0.0, "min_offset_sec": -2, "max_offset_sec": 2},
            "thirdQuartile": {"probability": 0.0, "min_offset_sec": -2, "max_offset_sec": 2},
            "complete": {"probability": 0.0, "min_offset_sec": -5, "max_offset_sec": 0},
        }
    )

    # Session duration limits
    max_session_duration_sec: int = 0  # 0 = unlimited

    # Quartile tracking options
    enable_auto_quartiles: bool = True
    quartile_offset_tolerance_sec: float = 1.0

    # Headless playback options
    headless_tick_interval_sec: float = 0.1  # Simulation granularity

    # Session persistence
    enable_session_persistence: bool = False

    # Logging and observability
    emit_playback_events: bool = True
    log_tracking_urls: bool = False


@dataclass
class VastTrackerConfig:
    """
    Configuration for VAST tracking with context injection support.

    This class provides comprehensive configuration for VAST tracking operations,
    including context injection parameters for different deployment environments.

    Examples:
        Development Configuration:
        >>> dev_config = VastTrackerConfig(
        ...     context_timeout=30.0,      # Longer timeouts for debugging
        ...     context_max_retries=5,     # More retries for unstable networks
        ...     context_retry_delay=2.0,   # Longer delays between retries
        ...     default_capabilities=[
        ...         'macros', 'state', 'logging_contextual',
        ...         'http_send_contextual', 'metrics_contextual'
        ...     ]
        ... )
        >>> dev_context = dev_config.build_context(
        ...     logger=create_dev_logger(level="DEBUG"),
        ...     http_client=httpx.AsyncClient(timeout=30.0),
        ...     metrics=development_metrics_client
        ... )

        Production Configuration:
        >>> prod_config = VastTrackerConfig(
        ...     context_timeout=5.0,       # Fast timeouts for production
        ...     context_max_retries=3,     # Conservative retry policy
        ...     context_retry_delay=0.5,   # Quick retry cycles
        ...     default_capabilities=[
        ...         'macros', 'state', 'logging_contextual', 'http_send_contextual'
        ...     ]
        ... )
        >>> prod_context = prod_config.build_context(
        ...     logger=create_prod_logger(level="INFO"),
        ...     http_client=httpx.AsyncClient(
        ...         timeout=5.0,
        ...         limits=httpx.Limits(max_connections=100)
        ...     ),
        ...     metrics=production_metrics_client
        ... )

        Testing Configuration:
        >>> test_config = VastTrackerConfig(
        ...     context_timeout=1.0,       # Fast tests
        ...     context_max_retries=1,     # No retries in tests
        ...     context_retry_delay=0.1,   # Minimal delays
        ...     default_capabilities=['macros', 'state']  # Minimal capabilities
        ... )
        >>> test_context = test_config.build_context(
        ...     logger=create_test_logger(),
        ...     http_client=MockAsyncClient(),  # Mock HTTP client
        ...     metrics=MockMetricsClient()     # Mock metrics
        ... )
    """

    # Macro formats (order matters - more specific first)
    macro_formats: list[str] = field(default_factory=lambda: ["[{macro}]", "${{{macro}}}"])

    # Static macros (provider-specific)
    static_macros: dict[str, str] = field(default_factory=dict)

    # Mapping from EmbedHttpClient params to VAST macros
    macro_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "ab_uid": "DEVICE_SERIAL",
            "ad_place": "PLACEMENT_TYPE",
            "media_title": "CHANNEL_NAME",
            "media_tag": "CHANNEL_CATEGORY",
        }
    )

    # Tracking options
    timeout: float = 5.0
    retry_on_error: bool = False
    max_retries: int = 0

    # Context injection configuration
    context_timeout: float = 5.0
    """Timeout for HTTP requests in context injection (seconds)."""

    context_max_retries: int = 3
    """Maximum number of retries for failed operations."""

    context_retry_delay: float = 1.0
    """Base delay between retries (seconds). Uses exponential backoff."""

    default_capabilities: list[str] = field(
        default_factory=lambda: ["macros", "state", "logging_contextual", "http_send_contextual"]
    )
    """
    Default capabilities to apply to trackables.
    
    Available capabilities:
    - 'macros': Macro replacement functionality
    - 'state': State management (StateMixin)
    - 'logging_contextual': Context-injected logging
    - 'http_send_contextual': Context-injected HTTP client
    - 'metrics_contextual': Context-injected metrics client
    - 'retry_logic_contextual': Context-injected retry logic
    """

    # Publisher-specific overrides
    publisher_overrides: dict[str, Any] = field(default_factory=dict)

    def build_context(
        self, logger: Any = None, http_client: Any = None, metrics: Any = None
    ) -> TrackingContext:
        """
        Build TrackingContext from configuration values.

        Args:
            logger: Structured logger instance (e.g., structlog.BoundLogger)
            http_client: HTTP client instance (e.g., httpx.AsyncClient)
            metrics: Metrics client instance

        Returns:
            TrackingContext: Configured context instance

        Examples:
            Basic context creation:
            >>> config = VastTrackerConfig()
            >>> context = config.build_context()

            Development context with all dependencies:
            >>> dev_config = VastTrackerConfig(
            ...     context_timeout=30.0,
            ...     context_max_retries=5
            ... )
            >>> context = dev_config.build_context(
            ...     logger=dev_logger,
            ...     http_client=httpx.AsyncClient(timeout=30.0),
            ...     metrics=dev_metrics
            ... )

            Production context with optimized settings:
            >>> prod_config = VastTrackerConfig(
            ...     context_timeout=5.0,
            ...     context_max_retries=3,
            ...     context_retry_delay=0.5
            ... )
            >>> context = prod_config.build_context(
            ...     logger=prod_logger,
            ...     http_client=production_http_client,
            ...     metrics=prod_metrics
            ... )
        """
        return TrackingContext(
            logger=logger,
            http_client=http_client,
            metrics_client=metrics,
            timeout=self.context_timeout,
            max_retries=self.context_max_retries,
            retry_delay=self.context_retry_delay,
        )

    def get_capability_decorators(self) -> list[Callable]:
        """
        Get list of decorator functions based on default_capabilities.

        Returns:
            List of decorator functions to apply to trackables

        Examples:
            >>> config = VastTrackerConfig(default_capabilities=['macros', 'logging_contextual'])
            >>> decorators = config.get_capability_decorators()
            >>> # Apply decorators to a trackable class
            >>> for decorator in decorators:
            ...     MyTrackable = decorator(MyTrackable)
        """
        from .capabilities import (
            with_macros,
            with_state,
            with_logging_contextual,
            with_http_send_contextual,
            with_metrics_contextual,
            with_retry_logic_contextual,
        )

        capability_map = {
            "macros": with_macros,
            "state": with_state,
            "logging_contextual": with_logging_contextual,
            "http_send_contextual": with_http_send_contextual,
            "metrics_contextual": with_metrics_contextual,
            "retry_logic_contextual": with_retry_logic_contextual,
        }

        return [capability_map[cap] for cap in self.default_capabilities if cap in capability_map]


@dataclass
class XPathSpec:
    """XPath specification with callback processing for multi-chain parsing.

    Defines how to extract data from VAST XML using XPath expressions,
    with support for callback functions to process the extracted data.

    Attributes:
        xpath: XPath expression to match elements
        name: Field name in the result dictionary
        callback: Function to process extracted data
        mode: Extraction mode - 'single' (first match) or 'list' (all matches)
        required: Whether this extraction is required (fail if not found)

    Examples:
        Basic extraction with processing:
        >>> spec = XPathSpec(
        ...     xpath=".//Impression",
        ...     name="impressions",
        ...     callback=lambda urls: [url.strip() for url in urls if url],
        ...     mode=ExtractMode.LIST
        ... )

        Single value extraction with validation:
        >>> spec = XPathSpec(
        ...     xpath=".//Duration",
        ...     name="duration_seconds",
        ...     callback=lambda d: int(float(d)) if d else None,
        ...     mode=ExtractMode.SINGLE,
        ...     required=True
        ... )
    """

    xpath: str
    name: str
    callback: Callable[[Any], Any] | None = None
    mode: ExtractMode = ExtractMode.LIST
    required: bool = False


@dataclass
class VastClientConfig:
    """Complete VAST client configuration."""

    # Provider identification
    provider: str = "generic"  # "global", "tiger", "leto", etc.
    publisher: str | None = None  # Publisher ID for custom logic

    # Component configurations
    parser: VastParserConfig = field(default_factory=VastParserConfig)
    tracker: VastTrackerConfig = field(default_factory=VastTrackerConfig)
    playback: PlaybackSessionConfig = field(default_factory=PlaybackSessionConfig)

    # Global options
    enable_tracking: bool = True
    enable_parsing: bool = True

    # SSL/TLS verification
    ssl_verify: bool | str = True  # True (verify), False (disable), or path to CA bundle

    # Provider-specific settings
    provider_settings: dict[str, Any] = field(default_factory=dict)


def get_default_vast_config(provider: str = "generic") -> VastClientConfig:
    """
    Get default VAST configuration for a provider.

    .. deprecated:: 2.0
        This function is deprecated in favor of YAML-based provider configurations.
        Use :class:`ProviderConfigLoader` from :mod:`provider_config_loader` instead.

        Migration example::

            # Old approach
            config = get_default_vast_config("global")

            # New approach
            from .provider_config_loader import ProviderConfigLoader
            from .provider_factory import build_provider_client

            loader = ProviderConfigLoader()
            client = await build_provider_client("global", ad_request)

    Includes provider-specific tracking macros, parser settings, and
    playback interruption rules for headless mode simulation.

    Warning:
        This function contains hardcoded provider logic and will be removed
        in a future version. New providers should be defined in YAML configuration
        files (settings/config.yaml) instead of adding more if/elif branches here.
    """
    import warnings

    warnings.warn(
        "get_default_vast_config() is deprecated and will be removed in v3.0. "
        "Use YAML-based provider configurations instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    config = VastClientConfig(provider=provider)

    if provider == "global":
        # AdStream Global specific config
        config.tracker.macro_mapping.update(
            {
                "city": "CITY",
                "city_code": "CITY_CODE",
            }
        )
        config.parser.custom_xpaths.update(
            {
                "city_info": ".//Extensions/Extension[@type='city']/Name",
            }
        )
        config.tracker.static_macros.update(
            {
                "AD_SERVER": "AdStream Global",
            }
        )
        # Global provider has higher interruption probability
        config.playback.interruption_rules.update(
            {
                "start": {"probability": 0.15, "min_offset_sec": 0, "max_offset_sec": 3},
                "firstQuartile": {"probability": 0.05, "min_offset_sec": -2, "max_offset_sec": 2},
                "midpoint": {"probability": 0.08, "min_offset_sec": -3, "max_offset_sec": 3},
                "thirdQuartile": {"probability": 0.05, "min_offset_sec": -2, "max_offset_sec": 2},
                "complete": {"probability": 0.02, "min_offset_sec": -5, "max_offset_sec": 0},
            }
        )

    elif provider == "tiger":
        # AdStream Tiger specific config
        config.tracker.macro_mapping.update(
            {
                "city_name": "CITY",
                "city_code": "CITY_CODE",
            }
        )
        config.tracker.static_macros.update(
            {
                "AD_SERVER": "AdStream Tiger",
            }
        )
        # Tiger has moderate interruption probability
        config.playback.interruption_rules.update(
            {
                "start": {"probability": 0.08, "min_offset_sec": 0, "max_offset_sec": 2},
                "firstQuartile": {"probability": 0.03, "min_offset_sec": -1, "max_offset_sec": 1},
                "midpoint": {"probability": 0.05, "min_offset_sec": -2, "max_offset_sec": 2},
                "thirdQuartile": {"probability": 0.03, "min_offset_sec": -1, "max_offset_sec": 1},
                "complete": {"probability": 0.01, "min_offset_sec": -5, "max_offset_sec": 0},
            }
        )

    elif provider == "leto":
        # Leto specific config
        config.tracker.macro_formats = ["%%{macro}%%", "[{macro}]"]  # Different format priority
        config.tracker.macro_mapping.update(
            {
                "wl": "WL",
                "pad_id": "PAD_ID",
                "block_id": "BLOCK_ID",
            }
        )
        config.tracker.static_macros.update(
            {
                "AD_SERVER": "Leto",
            }
        )
        # Leto has low interruption probability
        config.playback.interruption_rules.update(
            {
                "start": {"probability": 0.05, "min_offset_sec": 0, "max_offset_sec": 2},
                "firstQuartile": {"probability": 0.02, "min_offset_sec": -1, "max_offset_sec": 1},
                "midpoint": {"probability": 0.03, "min_offset_sec": -1, "max_offset_sec": 1},
                "thirdQuartile": {"probability": 0.02, "min_offset_sec": -1, "max_offset_sec": 1},
                "complete": {"probability": 0.01, "min_offset_sec": -5, "max_offset_sec": 0},
            }
        )

    elif provider == "yandex":
        # Yandex Direct specific config
        config.tracker.macro_formats = ["{macro}", "[{macro}]"]
        config.tracker.macro_mapping.update(
            {
                "yandex_uid": "YANDEX_UID",
                "campaign_id": "CAMPAIGN_ID",
                "banner_id": "BANNER_ID",
            }
        )
        config.tracker.static_macros.update(
            {
                "AD_SERVER": "Yandex Direct",
            }
        )
        # Yandex has moderate interruption probability
        config.playback.interruption_rules.update(
            {
                "start": {"probability": 0.10, "min_offset_sec": 0, "max_offset_sec": 2},
                "firstQuartile": {"probability": 0.04, "min_offset_sec": -1, "max_offset_sec": 1},
                "midpoint": {"probability": 0.06, "min_offset_sec": -2, "max_offset_sec": 2},
                "thirdQuartile": {"probability": 0.04, "min_offset_sec": -1, "max_offset_sec": 1},
                "complete": {"probability": 0.02, "min_offset_sec": -5, "max_offset_sec": 0},
            }
        )

    elif provider == "google":
        # Google AdSense/AdExchange specific config
        config.tracker.macro_formats = ["%%{macro}%%", "[{macro}]"]
        config.tracker.macro_mapping.update(
            {
                "google_gid": "GOOGLE_GID",
                "google_cust_params": "GOOGLE_CUST_PARAMS",
            }
        )
        config.tracker.static_macros.update(
            {
                "AD_SERVER": "Google AdSense",
            }
        )
        # Google has high interruption probability
        config.playback.interruption_rules.update(
            {
                "start": {"probability": 0.20, "min_offset_sec": 0, "max_offset_sec": 3},
                "firstQuartile": {"probability": 0.08, "min_offset_sec": -2, "max_offset_sec": 2},
                "midpoint": {"probability": 0.12, "min_offset_sec": -3, "max_offset_sec": 3},
                "thirdQuartile": {"probability": 0.08, "min_offset_sec": -2, "max_offset_sec": 2},
                "complete": {"probability": 0.03, "min_offset_sec": -5, "max_offset_sec": 0},
            }
        )

    elif provider == "custom":
        # Generic custom provider config
        config.tracker.macro_formats = ["[{macro}]", "${{{macro}}}", "{{{macro}}}"]
        config.tracker.static_macros.update(
            {
                "AD_SERVER": "Custom Provider",
            }
        )
        # Custom has moderate-low interruption probability
        config.playback.interruption_rules.update(
            {
                "start": {"probability": 0.07, "min_offset_sec": 0, "max_offset_sec": 2},
                "firstQuartile": {"probability": 0.03, "min_offset_sec": -1, "max_offset_sec": 1},
                "midpoint": {"probability": 0.04, "min_offset_sec": -1, "max_offset_sec": 1},
                "thirdQuartile": {"probability": 0.03, "min_offset_sec": -1, "max_offset_sec": 1},
                "complete": {"probability": 0.01, "min_offset_sec": -5, "max_offset_sec": 0},
            }
        )

    return config


def get_vast_config_with_publisher_overrides(
    provider: str = "generic",
    publisher: str | None = None,
    publisher_overrides: dict[str, Any] | None = None,
) -> VastClientConfig:
    """Get VAST configuration with publisher-specific overrides."""
    config = get_default_vast_config(provider)
    config.publisher = publisher

    if publisher_overrides:
        # Apply parser overrides
        if "parser" in publisher_overrides:
            parser_overrides = publisher_overrides["parser"]
            for key, value in parser_overrides.items():
                if hasattr(config.parser, key):
                    setattr(config.parser, key, value)

        # Apply tracker overrides
        if "tracker" in publisher_overrides:
            tracker_overrides = publisher_overrides["tracker"]
            for key, value in tracker_overrides.items():
                if hasattr(config.tracker, key):
                    setattr(config.tracker, key, value)

        # Apply global overrides
        for key, value in publisher_overrides.items():
            if key not in ["parser", "tracker"] and hasattr(config, key):
                setattr(config, key, value)

    return config


def create_provider_config_factory(provider: str) -> Callable[..., VastClientConfig]:
    """
    Create a factory function for a specific provider configuration.

    .. deprecated:: 2.0
        This function is deprecated. Use YAML-based provider configurations instead.
        See :func:`get_default_vast_config` for migration instructions.
    """
    import warnings

    warnings.warn(
        f"create_provider_config_factory() is deprecated. "
        f"Define provider '{provider}' in YAML configuration instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    def factory(publisher: str | None = None, **overrides) -> VastClientConfig:
        return get_vast_config_with_publisher_overrides(
            provider=provider,
            publisher=publisher,
            publisher_overrides=overrides,
        )

    return factory


# Provider-specific factory functions
# DEPRECATED: These will be removed in v3.0
# Use YAML-based provider configurations instead
global_config = create_provider_config_factory("global")
tiger_config = create_provider_config_factory("tiger")
leto_config = create_provider_config_factory("leto")
yandex_config = create_provider_config_factory("yandex")
google_config = create_provider_config_factory("google")
custom_config = create_provider_config_factory("custom")


def get_vast_config_from_settings() -> VastClientConfig:
    """Get VAST configuration from main settings."""
    main_settings = get_settings()

    # Use main config values where applicable
    return VastClientConfig(
        enable_tracking=main_settings.vast_client.enable_tracking,
        # Other settings can be added as needed
    )


__all__ = [
    "ExtractMode",
    "PlaybackMode",
    "InterruptionType",
    "VastParserConfig",
    "PlaybackSessionConfig",
    "VastTrackerConfig",
    "XPathSpec",
    "VastClientConfig",
    "get_default_vast_config",
    "get_vast_config_with_publisher_overrides",
    "create_provider_config_factory",
    "global_config",
    "tiger_config",
    "leto_config",
    "yandex_config",
    "google_config",
    "custom_config",
    "get_vast_config_from_settings",
]
