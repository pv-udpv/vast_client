"""Settings management for VAST client.

Provides a minimal settings interface compatible with the parent config module.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any


class Settings:
    """Minimal settings class for VAST client standalone mode."""
    
    def __init__(self, **kwargs):
        """Initialize settings with keyword arguments."""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """Get provider-specific configuration.
        
        Args:
            provider: Provider name
            
        Returns:
            Provider configuration dict
        """
        providers = getattr(self, 'providers', {})
        return providers.get(provider, {})
    
    def with_context(self, ad_request: dict[str, Any] | None = None, **kwargs) -> "Settings":
        """Create settings instance with context substitution.
        
        Args:
            ad_request: Ad request context
            **kwargs: Additional context
            
        Returns:
            Settings instance (self in minimal implementation)
        """
        return self


@lru_cache
def get_settings(config_path: Path | None = None) -> Settings:
    """Get cached settings instance.
    
    Args:
        config_path: Optional config file path
        
    Returns:
        Settings instance
    """
    # Try to import from parent config if available
    try:
        # Check if we're in a larger package with parent config
        import sys
        from pathlib import Path
        
        # Add parent src to path if not already there
        src_parent = Path(__file__).parent.parent.parent
        if str(src_parent) not in sys.path:
            sys.path.insert(0, str(src_parent))
        
        # Try to import parent config
        try:
            from config import get_settings as parent_get_settings
            return parent_get_settings(config_path)
        except ImportError:
            pass
    except Exception:
        pass
    
    # Fallback to minimal settings
    return Settings(
        vast_client={'enable_tracking': True, 'enable_parsing': True},
        http={'timeout': 30.0, 'max_retries': 3},
        providers={}
    )


__all__ = ["Settings", "get_settings"]
