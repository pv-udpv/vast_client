"""VAST client custom exception hierarchy.

Provides specific exception types for various error scenarios in VAST parsing,
tracking, and HTTP operations. This enables consistent error handling and
more informative error logging throughout the codebase.

Exception Hierarchy:
    VastException (base)
    ├── VastParseError
    │   ├── VastXMLError
    │   ├── VastElementError
    │   └── VastExtensionError
    ├── VastTrackingError
    │   ├── VastTrackingURLError
    │   └── VastTrackingNetworkError
    ├── VastConfigError
    │   ├── VastConfigValidationError
    │   └── VastConfigNotFoundError
    └── VastHTTPError
        ├── VastHTTPTimeoutError
        └── VastHTTPSSLError
"""

from typing import Optional


class VastException(Exception):
    """Base exception for all VAST client errors.

    All VAST-specific exceptions inherit from this class to allow
    catching all VAST errors with a single except clause.
    """

    def __init__(self, message: str, context: Optional[dict] = None):
        """Initialize VAST exception.

        Args:
            message: Error message
            context: Optional context dictionary for debugging
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return string representation with context."""
        if self.context:
            context_str = "; ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


# Parsing Errors

class VastParseError(VastException):
    """Base exception for VAST parsing errors.

    Raised when there are issues parsing VAST XML or extracted data.
    """

    pass


class VastXMLError(VastParseError):
    """Raised when XML parsing fails.

    This includes malformed XML, encoding issues, and XML syntax errors.

    Attributes:
        xml_preview: First 200 characters of XML that failed to parse
        parser_error: The underlying lxml parser error
    """

    def __init__(
        self,
        message: str,
        xml_preview: Optional[str] = None,
        parser_error: Optional[Exception] = None,
        context: Optional[dict] = None,
    ):
        """Initialize XML error.

        Args:
            message: Error message
            xml_preview: Preview of problematic XML
            parser_error: The underlying parser exception
            context: Additional context
        """
        if context is None:
            context = {}
        if xml_preview:
            context["xml_preview"] = xml_preview[:200]
        super().__init__(message, context)
        self.xml_preview = xml_preview
        self.parser_error = parser_error


class VastElementError(VastParseError):
    """Raised when extracting or processing XML elements fails.

    This includes issues converting elements to dictionaries,
    accessing element attributes, or processing element hierarchies.

    Attributes:
        element_tag: XML tag of problematic element
        operation: The operation that failed (e.g., 'to_dict', 'attribute_access')
    """

    def __init__(
        self,
        message: str,
        element_tag: Optional[str] = None,
        operation: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize element error.

        Args:
            message: Error message
            element_tag: XML tag of problematic element
            operation: The operation that failed
            context: Additional context
        """
        if context is None:
            context = {}
        if element_tag:
            context["element_tag"] = element_tag
        if operation:
            context["operation"] = operation
        super().__init__(message, context)
        self.element_tag = element_tag
        self.operation = operation


class VastExtensionError(VastParseError):
    """Raised when parsing VAST extensions fails.

    Attributes:
        extension_type: Type of extension that failed to parse
        field_name: Custom field name if applicable
    """

    def __init__(
        self,
        message: str,
        extension_type: Optional[str] = None,
        field_name: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize extension error.

        Args:
            message: Error message
            extension_type: Type of extension
            field_name: Custom field name
            context: Additional context
        """
        if context is None:
            context = {}
        if extension_type:
            context["extension_type"] = extension_type
        if field_name:
            context["field_name"] = field_name
        super().__init__(message, context)
        self.extension_type = extension_type
        self.field_name = field_name


class VastDurationError(VastParseError):
    """Raised when parsing duration fails.

    Attributes:
        duration_text: The duration string that failed to parse
    """

    def __init__(
        self,
        message: str,
        duration_text: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize duration error.

        Args:
            message: Error message
            duration_text: The duration string that failed
            context: Additional context
        """
        if context is None:
            context = {}
        if duration_text:
            context["duration_text"] = duration_text
        super().__init__(message, context)
        self.duration_text = duration_text


# Tracking Errors

class VastTrackingError(VastException):
    """Base exception for VAST tracking errors.

    Raised when there are issues with VAST tracking operations.
    """

    pass


class VastTrackingURLError(VastTrackingError):
    """Raised when tracking URL is invalid or malformed.

    Attributes:
        url: The problematic tracking URL
        url_type: Type of URL (impression, tracking, click, etc.)
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        url_type: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize tracking URL error.

        Args:
            message: Error message
            url: The problematic URL (may be redacted)
            url_type: Type of URL
            context: Additional context
        """
        if context is None:
            context = {}
        if url:
            context["url"] = url[:100]  # Redact long URLs
        if url_type:
            context["url_type"] = url_type
        super().__init__(message, context)
        self.url = url
        self.url_type = url_type


class VastTrackingNetworkError(VastTrackingError):
    """Raised when tracking request fails due to network issues.

    Attributes:
        http_status: HTTP status code if available
        network_error: The underlying network exception
    """

    def __init__(
        self,
        message: str,
        http_status: Optional[int] = None,
        network_error: Optional[Exception] = None,
        context: Optional[dict] = None,
    ):
        """Initialize tracking network error.

        Args:
            message: Error message
            http_status: HTTP status code
            network_error: The underlying exception
            context: Additional context
        """
        if context is None:
            context = {}
        if http_status:
            context["http_status"] = http_status
        super().__init__(message, context)
        self.http_status = http_status
        self.network_error = network_error


# Configuration Errors

class VastConfigError(VastException):
    """Base exception for VAST configuration errors.

    Raised when there are issues with VAST client configuration.
    """

    pass


class VastConfigValidationError(VastConfigError):
    """Raised when configuration validation fails.

    Attributes:
        config_key: Configuration key that failed validation
        config_value: The invalid configuration value
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize config validation error.

        Args:
            message: Error message
            config_key: The config key
            config_value: The config value (may be redacted)
            context: Additional context
        """
        if context is None:
            context = {}
        if config_key:
            context["config_key"] = config_key
        if config_value:
            context["config_value"] = str(config_value)[:100]
        super().__init__(message, context)
        self.config_key = config_key
        self.config_value = config_value


class VastConfigNotFoundError(VastConfigError):
    """Raised when required configuration is not found.

    Attributes:
        config_key: The missing configuration key
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize config not found error.

        Args:
            message: Error message
            config_key: The missing configuration key
            context: Additional context
        """
        if context is None:
            context = {}
        if config_key:
            context["config_key"] = config_key
        super().__init__(message, context)
        self.config_key = config_key


# HTTP Errors

class VastHTTPError(VastException):
    """Base exception for VAST HTTP operation errors.

    Raised when HTTP operations fail (VAST requests, tracking, etc.).
    """

    pass


class VastHTTPTimeoutError(VastHTTPError):
    """Raised when HTTP request times out.

    Attributes:
        timeout: Configured timeout in seconds
        operation: The operation that timed out
    """

    def __init__(
        self,
        message: str,
        timeout: Optional[float] = None,
        operation: Optional[str] = None,
        context: Optional[dict] = None,
    ):
        """Initialize HTTP timeout error.

        Args:
            message: Error message
            timeout: Configured timeout value
            operation: The operation that timed out
            context: Additional context
        """
        if context is None:
            context = {}
        if timeout:
            context["timeout"] = timeout
        if operation:
            context["operation"] = operation
        super().__init__(message, context)
        self.timeout = timeout
        self.operation = operation


class VastHTTPSSLError(VastHTTPError):
    """Raised when SSL/TLS verification fails.

    Attributes:
        url: URL that failed SSL verification
        ssl_error: The underlying SSL exception
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        ssl_error: Optional[Exception] = None,
        context: Optional[dict] = None,
    ):
        """Initialize SSL error.

        Args:
            message: Error message
            url: URL that failed verification
            ssl_error: The underlying exception
            context: Additional context
        """
        if context is None:
            context = {}
        if url:
            context["url"] = url[:100]
        super().__init__(message, context)
        self.url = url
        self.ssl_error = ssl_error


__all__ = [
    "VastException",
    "VastParseError",
    "VastXMLError",
    "VastElementError",
    "VastExtensionError",
    "VastDurationError",
    "VastTrackingError",
    "VastTrackingURLError",
    "VastTrackingNetworkError",
    "VastConfigError",
    "VastConfigValidationError",
    "VastConfigNotFoundError",
    "VastHTTPError",
    "VastHTTPTimeoutError",
    "VastHTTPSSLError",
]
