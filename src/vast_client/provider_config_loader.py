"""
Provider Configuration Loader

Loads and processes YAML-based provider configurations,
supporting template variable resolution and context preparation.
"""

import hashlib
import re
import secrets
import uuid
from typing import Any

from .settings import get_settings


def generate_uuid_from_multi_fields(*fields) -> str:
    """
    Generate deterministic UUID from multiple field values.

    Creates a consistent UUID based on the concatenation of field values,
    useful for generating device serials and other identifiers.

    Args:
        *fields: Variable number of field values to combine

    Returns:
        UUID string (hyphenated format)

    Examples:
        >>> generate_uuid_from_multi_fields("GLOBAL", "00:11:22:33:44:55", "DeviceUA/1.0")
        'a1b2c3d4-e5f6-4789-a012-3456789abcde'
    """
    # Concatenate all fields
    combined = "".join(str(field) for field in fields)

    # Generate MD5 hash for consistency
    hash_digest = hashlib.md5(combined.encode()).digest()

    # Create UUID from hash
    return str(uuid.UUID(bytes=hash_digest))


class TemplateResolver:
    """
    Resolves template variables in configuration values.

    Supports:
    - ${variable} - Simple substitution
    - ${path.to.value} - Nested path access
    - ${variable|default} - Default value if missing
    """

    TEMPLATE_PATTERN = re.compile(r"\$\{([^}]+)\}")

    @classmethod
    def resolve(cls, template: str, context: dict[str, Any]) -> str:
        """
        Resolve template string with context values.

        Args:
            template: Template string with ${variable} syntax
            context: Dictionary of available variables

        Returns:
            Resolved string value

        Examples:
            >>> context = {"user": "john", "settings": {"theme": "dark"}}
            >>> TemplateResolver.resolve("${user}", context)
            'john'
            >>> TemplateResolver.resolve("${settings.theme}", context)
            'dark'
            >>> TemplateResolver.resolve("${missing|default}", context)
            'default'
        """

        def replacer(match):
            expr = match.group(1)

            # Check for default value syntax: ${var|default}
            if "|" in expr:
                var_path, default = expr.split("|", 1)
                value = cls._get_nested_value(context, var_path.strip())
                return str(value if value is not None else default)
            else:
                value = cls._get_nested_value(context, expr)
                return str(value if value is not None else f"${{{expr}}}")

        if isinstance(template, str):
            return cls.TEMPLATE_PATTERN.sub(replacer, template)
        return template

    @classmethod
    def resolve_dict(cls, data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively resolve templates in dictionary values.

        Args:
            data: Dictionary with potential template values
            context: Dictionary of available variables

        Returns:
            Dictionary with resolved values
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.resolve(value, context)
            elif isinstance(value, dict):
                result[key] = cls.resolve_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    cls.resolve(item, context)
                    if isinstance(item, str)
                    else cls.resolve_dict(item, context)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    @staticmethod
    def _get_nested_value(data: dict[str, Any], path: str) -> Any:
        """
        Get value from nested dictionary using dot-notation path.

        Args:
            data: Dictionary to traverse
            path: Dot-separated path (e.g., "ext.channel_to.display_name")

        Returns:
            Value at path or None if not found
        """
        keys = path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return None
            else:
                return None

        return current


class IPPoolSelector:
    """Selects IP addresses from configured pools."""

    @staticmethod
    def select_ip(pool_config: list[dict[str, Any]], pool_name: str, fallback: str) -> str:
        """
        Select an IP from the specified pool.

        Args:
            pool_config: List of IP pool configurations
            pool_name: Name of pool to select from
            fallback: Fallback IP if pool not found

        Returns:
            Selected IP address
        """
        for pool in pool_config:
            if pool.get("name") == pool_name:
                ips = pool.get("ips", [])
                if not ips:
                    return fallback

                strategy = pool.get("strategy", "random")
                if strategy == "random":
                    return secrets.choice(ips)
                else:
                    # Other strategies can be added here
                    return ips[0]

        return fallback


class ProviderConfigLoader:
    """
    Loads and processes provider configurations from YAML settings.

    Handles:
    - HTTP client configuration
    - Template variable resolution
    - IP pool selection
    - Context preparation
        - Automatic macro mapping with ad_request base path
    """

    def __init__(self, settings=None):
        """
        Initialize config loader.

        Args:
            settings: Settings instance (defaults to global settings)
        """
        self.settings = settings or get_settings()

    @staticmethod
    def process_macro_mappings(
        macro_mapping: dict[str, str], ad_request: dict[str, Any]
    ) -> dict[str, str]:
        """
        Process macro mappings with automatic ad_request base path resolution.

        Converts simple mappings like "device_serial: DEVICE_SERIAL" to use
        ad_request.device_serial automatically.

        Args:
            macro_mapping: Dictionary mapping parameter names to VAST macro names
            ad_request: Ad request context for value resolution

        Returns:
            Dictionary mapping macro names to resolved values

        Examples:
            >>> macro_mapping = {"device_serial": "DEVICE_SERIAL", "city": "CITY"}
            >>> ad_request = {"device_serial": "ABC123", "city": "New York"}
            >>> process_macro_mappings(macro_mapping, ad_request)
            {"DEVICE_SERIAL": "ABC123", "CITY": "New York"}
        """
        result = {}

        for param_name, macro_name in macro_mapping.items():
            # Check if param_name contains a path (e.g., "ext.channel_to.name")
            if "." in param_name:
                # Use nested path resolution
                value = TemplateResolver._get_nested_value(ad_request, param_name)
            else:
                # Simple parameter - look in ad_request directly
                value = ad_request.get(param_name)

            if value is not None:
                result[macro_name] = str(value)

        return result

    def get_provider_config(self, provider: str) -> dict[str, Any]:
        """
        Get raw provider configuration from settings.

        Args:
            provider: Provider name (e.g., "global", "tiger", "leto")

        Returns:
            Provider configuration dictionary

        Raises:
            ValueError: If provider not found
        """
        providers = getattr(self.settings, "providers", {})
        if provider not in providers:
            raise ValueError(f"Provider '{provider}' not found in configuration")

        return providers[provider]

    def prepare_context(self, provider: str, ad_request: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare context from ad_request using provider's context_preparation rules.

        Args:
            provider: Provider name
            ad_request: Ad request data

        Returns:
            Prepared context dictionary with all variables
        """
        config = self.get_provider_config(provider)
        context_prep = config.get("context_preparation", {})

        # Start with ad_request as base context
        context = {**ad_request}

        # Generate device serial if configured
        if "device_serial" in context_prep:
            serial_config = context_prep["device_serial"]
            if serial_config.get("type") == "uuid_multi_fields":
                fields = serial_config.get("fields", [])
                field_values = []

                for field in fields:
                    if "." in field:
                        # Nested path
                        value = TemplateResolver._get_nested_value(ad_request, field)
                        field_values.append(str(value) if value is not None else "")
                    else:
                        # Direct field or static value
                        field_values.append(ad_request.get(field, field))

                context["device_serial"] = generate_uuid_from_multi_fields(*field_values)

        # Extract channel data if configured
        if "channel_extraction" in context_prep:
            channel_ext = context_prep["channel_extraction"]
            context["channel"] = {}

            for key, path in channel_ext.items():
                value = TemplateResolver._get_nested_value(ad_request, path)
                context["channel"][key] = value

        # Select IP if configured
        if "ip_selection" in context_prep:
            ip_config = context_prep["ip_selection"]
            ip_pools = config.get("ip_pools", [])

            selected_ip = IPPoolSelector.select_ip(
                ip_pools, ip_config.get("pool", ""), ip_config.get("fallback", "127.0.0.1")
            )
            context["selected_ip"] = selected_ip

        return context

    def build_http_client_config(self, provider: str, ad_request: dict[str, Any]) -> dict[str, Any]:
        """
        Build EmbedHttpClient configuration from provider config.

        Args:
            provider: Provider name
            ad_request: Ad request data for context

        Returns:
            Dictionary with base_url, base_params, base_headers, encoding_config
        """
        config = self.get_provider_config(provider)
        http_config = config.get("http_client", {})

        if not http_config:
            raise ValueError(f"Provider '{provider}' missing http_client configuration")

        # Prepare context for template resolution
        context = self.prepare_context(provider, ad_request)

        # Get base URL (no template resolution)
        base_url = http_config.get("base_url", "")

        # Merge static and dynamic params
        base_params = http_config.get("base_params", {}).copy()
        dynamic_params = http_config.get("dynamic_params", {})

        # Handle special JSON params
        for key, value in dynamic_params.items():
            if isinstance(value, dict) and value.get("type") == "json":
                # Keep the JSON value structure
                base_params[key] = value.get("value", {})
            else:
                # Regular template resolution
                resolved = TemplateResolver.resolve(value, context)
                base_params[key] = resolved

        # Merge static and dynamic headers
        base_headers = http_config.get("base_headers", {}).copy()
        dynamic_headers = http_config.get("dynamic_headers", {})

        resolved_headers = TemplateResolver.resolve_dict(dynamic_headers, context)
        base_headers.update(resolved_headers)

        # Get encoding config
        encoding_config = http_config.get("encoding_config", {})

        return {
            "base_url": base_url,
            "base_params": base_params,
            "base_headers": base_headers,
            "encoding_config": encoding_config,
        }


__all__ = [
    "TemplateResolver",
    "IPPoolSelector",
    "ProviderConfigLoader",
]
