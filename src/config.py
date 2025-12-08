"""
Settings Management Module

Provides pydantic-based configuration management with:
- YAML configuration file loading
- Environment variable overrides
- Template variable substitution (${var|default})
- Ad request context integration
- Multi-environment support (dev, prod, test)
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TemplateEngine:
    """Template engine for variable substitution in configuration values."""
    
    # Pattern: ${variable} or ${variable|default}
    VARIABLE_PATTERN = re.compile(r'\$\{([^}|]+)(?:\|([^}]+))?\}')
    
    @classmethod
    def substitute(cls, value: str, context: dict[str, Any]) -> str:
        """
        Substitute template variables in a string.
        
        Args:
            value: String with template variables (e.g., "${ad_request.user_agent|default}")
            context: Context dictionary with ad_request and other variables
            
        Returns:
            String with variables substituted
            
        Examples:
            >>> context = {'ad_request': {'user_agent': 'Mozilla/5.0'}}
            >>> TemplateEngine.substitute('${ad_request.user_agent}', context)
            'Mozilla/5.0'
            >>> TemplateEngine.substitute('${ad_request.missing|default}', context)
            'default'
        """
        if not isinstance(value, str):
            return value
        
        def replacer(match):
            var_path = match.group(1).strip()
            default = match.group(2).strip() if match.group(2) else ""
            
            # Navigate nested path (e.g., "ad_request.device_serial")
            parts = var_path.split('.')
            current = context
            
            try:
                for part in parts:
                    current = current[part]
                return str(current) if current is not None else default
            except (KeyError, TypeError):
                return default
        
        return cls.VARIABLE_PATTERN.sub(replacer, value)
    
    @classmethod
    def substitute_dict(cls, data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Recursively substitute variables in dictionary values."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.substitute(value, context)
            elif isinstance(value, dict):
                result[key] = cls.substitute_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    cls.substitute(v, context) if isinstance(v, str)
                    else cls.substitute_dict(v, context) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            else:
                result[key] = value
        return result


class VastClientSettings(BaseSettings):
    """VAST Client configuration settings."""
    
    model_config = SettingsConfigDict(extra='allow')
    
    enable_tracking: bool = True
    enable_parsing: bool = True
    default_provider: str = "generic"
    default_publisher: str | None = None
    
    parser: dict[str, Any] = Field(default_factory=dict)
    tracker: dict[str, Any] = Field(default_factory=dict)
    playback: dict[str, Any] = Field(default_factory=dict)


class HttpSettings(BaseSettings):
    """HTTP client configuration settings."""
    
    model_config = SettingsConfigDict(extra='allow')
    
    timeout: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0
    
    default_headers: dict[str, str] = Field(default_factory=dict)
    context_headers: dict[str, str] = Field(default_factory=dict)
    base_params: dict[str, Any] = Field(default_factory=dict)
    context_params: dict[str, Any] = Field(default_factory=dict)
    
    follow_redirects: bool = True
    verify_ssl: bool = True
    
    encoding: dict[str, Any] = Field(default_factory=dict)


class Settings(BaseSettings):
    """
    Main application settings with multi-environment support.
    
    Configuration hierarchy (lowest to highest precedence):
    1. settings/config.yaml (base)
    2. settings/config.{environment}.yaml (environment-specific)
    3. Environment variables (VAST_*)
    
    Examples:
        Load settings:
        >>> settings = get_settings()
        >>> print(settings.environment)
        'development'
        
        With ad_request context:
        >>> settings = get_settings()
        >>> context_settings = settings.with_context(ad_request={'user_agent': 'Mozilla/5.0'})
        >>> print(context_settings.http.default_headers['User-Agent'])
        'Mozilla/5.0'
    """
    
    model_config = SettingsConfigDict(
        env_prefix='VAST_',
        env_nested_delimiter='__',
        case_sensitive=False,
        extra='allow',
    )
    
    environment: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"
    
    vast_client: dict[str, Any] = Field(default_factory=dict)
    http: dict[str, Any] = Field(default_factory=dict)
    
    logging: dict[str, Any] = Field(default_factory=dict)
    providers: dict[str, Any] = Field(default_factory=dict)
    templates: dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def load_from_yaml(cls, config_path: Path | None = None) -> "Settings":
        """
        Load settings from YAML configuration file.
        
        Args:
            config_path: Path to config file (default: settings/config.yaml)
            
        Returns:
            Settings instance
        """
        if config_path is None:
            # Default to settings/config.yaml in project root
            # config.py is in /src/config.py, so parent.parent gives project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "settings" / "config.yaml"
        
        if not config_path.exists():
            # Return default settings if config doesn't exist
            return cls()
        
        # Load base configuration
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}
        
        # Load environment-specific overrides
        env = os.getenv('VAST_ENVIRONMENT', config_data.get('environment', 'development'))
        env_config_path = config_path.parent / f"config.{env}.yaml"
        
        if env_config_path.exists():
            with open(env_config_path) as f:
                env_config = yaml.safe_load(f) or {}
                # Deep merge environment config
                config_data = cls._deep_merge(config_data, env_config)
        
        # Create settings instance from merged config
        return cls(**config_data)
    
    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Settings._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def with_context(self, ad_request: dict[str, Any] | None = None, **kwargs) -> "Settings":
        """
        Create a new Settings instance with template variables substituted.
        
        Args:
            ad_request: Ad request context dictionary
            **kwargs: Additional context variables
            
        Returns:
            New Settings instance with substituted values
            
        Examples:
            >>> settings = get_settings()
            >>> ad_request = {
            ...     'user_agent': 'Mozilla/5.0',
            ...     'device_serial': 'ABC123'
            ... }
            >>> context_settings = settings.with_context(ad_request=ad_request)
        """
        context = {
            'ad_request': ad_request or {},
            **kwargs
        }
        
        # Convert to dict, substitute variables, and create new instance
        config_dict = self.model_dump()
        substituted = TemplateEngine.substitute_dict(config_dict, context)
        
        return Settings(**substituted)
    
    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get provider-specific configuration."""
        return self.providers.get(provider, {})


@lru_cache
def get_settings(config_path: Path | None = None) -> Settings:
    """
    Get cached settings instance.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Settings instance
        
    Examples:
        >>> settings = get_settings()
        >>> print(settings.vast_client.enable_tracking)
        True
    """
    return Settings.load_from_yaml(config_path)


def reload_settings() -> Settings:
    """Reload settings by clearing cache."""
    get_settings.cache_clear()
    return get_settings()


__all__ = [
    'Settings',
    'VastClientSettings',
    'HttpSettings',
    'TemplateEngine',
    'get_settings',
    'reload_settings',
]
