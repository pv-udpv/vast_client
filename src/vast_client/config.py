"""
VAST Client Configuration Module

Provides configuration classes for all VAST client components,
enabling provider-specific customization and publisher overrides.
"""

from dataclasses import dataclass, field
from typing import Any, Callable

from ..config import get_settings
from .context import TrackingContext


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
    macro_mapping: dict[str, str] = field(default_factory=lambda: {
        "ab_uid": "DEVICE_SERIAL",
        "ad_place": "PLACEMENT_TYPE",
        "media_title": "CHANNEL_NAME",
        "media_tag": "CHANNEL_CATEGORY",
    })

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
    
    default_capabilities: list[str] = field(default_factory=lambda: [
        'macros', 'state', 'logging_contextual', 'http_send_contextual'
    ])
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
        self, 
        logger: Any = None,
        http_client: Any = None,
        metrics: Any = None
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
            retry_delay=self.context_retry_delay
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
            with_macros, with_state, with_logging_contextual,
            with_http_send_contextual, with_metrics_contextual,
            with_retry_logic_contextual
        )
        
        capability_map = {
            'macros': with_macros,
            'state': with_state,
            'logging_contextual': with_logging_contextual,
            'http_send_contextual': with_http_send_contextual,
            'metrics_contextual': with_metrics_contextual,
            'retry_logic_contextual': with_retry_logic_contextual,
        }
        
        return [
            capability_map[cap] for cap in self.default_capabilities 
            if cap in capability_map
        ]


@dataclass
class VastClientConfig:
    """Complete VAST client configuration."""

    # Provider identification
    provider: str = "generic"  # "global", "tiger", "leto", etc.
    publisher: str | None = None  # Publisher ID for custom logic

    # Component configurations
    parser: VastParserConfig = field(default_factory=VastParserConfig)
    tracker: VastTrackerConfig = field(default_factory=VastTrackerConfig)

    # Global options
    enable_tracking: bool = True
    enable_parsing: bool = True

    # Provider-specific settings
    provider_settings: dict[str, Any] = field(default_factory=dict)


def get_default_vast_config(provider: str = "generic") -> VastClientConfig:
    """Get default VAST configuration for a provider."""
    config = VastClientConfig(provider=provider)

    if provider == "global":
        # AdStream Global specific config
        config.tracker.macro_mapping.update({
            "city": "CITY",
            "city_code": "CITY_CODE",
        })
        config.parser.custom_xpaths.update({
            "city_info": ".//Extensions/Extension[@type='city']/Name",
        })
        config.tracker.static_macros.update({
            "AD_SERVER": "AdStream Global",
        })

    elif provider == "tiger":
        # AdStream Tiger specific config
        config.tracker.macro_mapping.update({
            "city_name": "CITY",
            "city_code": "CITY_CODE",
        })
        config.tracker.static_macros.update({
            "AD_SERVER": "AdStream Tiger",
        })

    elif provider == "leto":
        # Leto specific config
        config.tracker.macro_formats = ["%%{macro}%%", "[{macro}]"]  # Different format priority
        config.tracker.macro_mapping.update({
            "wl": "WL",
            "pad_id": "PAD_ID",
            "block_id": "BLOCK_ID",
        })
        config.tracker.static_macros.update({
            "AD_SERVER": "Leto",
        })

    elif provider == "yandex":
        # Yandex Direct specific config
        config.tracker.macro_formats = ["{macro}", "[{macro}]"]
        config.tracker.macro_mapping.update({
            "yandex_uid": "YANDEX_UID",
            "campaign_id": "CAMPAIGN_ID",
            "banner_id": "BANNER_ID",
        })
        config.tracker.static_macros.update({
            "AD_SERVER": "Yandex Direct",
        })

    elif provider == "google":
        # Google AdSense/AdExchange specific config
        config.tracker.macro_formats = ["%%{macro}%%", "[{macro}]"]
        config.tracker.macro_mapping.update({
            "google_gid": "GOOGLE_GID",
            "google_cust_params": "GOOGLE_CUST_PARAMS",
        })
        config.tracker.static_macros.update({
            "AD_SERVER": "Google AdSense",
        })

    elif provider == "custom":
        # Generic custom provider config
        config.tracker.macro_formats = ["[{macro}]", "${{{macro}}}", "{{{macro}}}"]
        config.tracker.static_macros.update({
            "AD_SERVER": "Custom Provider",
        })

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
    """Create a factory function for a specific provider configuration."""
    def factory(publisher: str | None = None, **overrides) -> VastClientConfig:
        return get_vast_config_with_publisher_overrides(
            provider=provider,
            publisher=publisher,
            publisher_overrides=overrides,
        )
    return factory

# Provider-specific factory functions
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
    "VastParserConfig",
    "VastTrackerConfig",
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
