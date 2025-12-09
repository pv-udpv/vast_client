"""Logging configuration with sampling and operation-level control."""

import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SamplingStrategy(str, Enum):
    """Sampling strategy for debug logs."""

    RANDOM = "random"
    """Random sampling based on sample_rate probability"""

    DETERMINISTIC = "deterministic"
    """Deterministic sampling based on hash of request_id"""

    NONE = "none"
    """No sampling - log everything"""


@dataclass
class VastLoggingConfig:
    """Configuration for VAST client logging.

    Controls log levels, sampling, and operation-specific verbosity.

    Example:
        ```python
        config = VastLoggingConfig(
            level="INFO",
            debug_sample_rate=0.1,  # 10% of debug logs
            sampling_strategy=SamplingStrategy.DETERMINISTIC,
            operation_levels={
                "track_event": "INFO",      # Always log
                "send_trackable": "DEBUG",  # Only if sampled
                "apply_macros": "DEBUG",    # Only if sampled
            }
        )
        ```
    """

    # Global log level
    level: str = "INFO"

    # Debug sampling configuration
    debug_sample_rate: float = 0.0
    """Rate for sampling debug logs (0.0 = none, 1.0 = all)"""

    sampling_strategy: SamplingStrategy = SamplingStrategy.RANDOM
    """Strategy for sampling debug logs"""

    # Operation-specific log levels
    operation_levels: dict[str, str] = field(default_factory=dict)
    """Per-operation log level overrides"""

    # Advanced configuration
    enable_hierarchical_messages: bool = True
    """Enable hierarchical indentation in log messages"""

    max_namespace_depth: int = 3
    """Maximum depth for nested namespace grouping"""

    def should_log_debug(self, operation: str | None = None, request_id: str | None = None) -> bool:
        """Determine if a debug log should be emitted.

        Args:
            operation: Operation name (e.g., "track_event", "send_trackable")
            request_id: Request ID for deterministic sampling

        Returns:
            True if debug log should be emitted, False otherwise
        """
        # Check operation-specific level first
        if operation and operation in self.operation_levels:
            op_level = self.operation_levels[operation]
            if op_level == "DEBUG":
                # Proceed to sampling logic
                pass
            elif op_level == "INFO":
                # Don't log debug for this operation
                return False
            # Otherwise continue with sampling

        # Apply sampling if configured
        if self.debug_sample_rate <= 0.0:
            return False
        elif self.debug_sample_rate >= 1.0:
            return True

        # Apply sampling strategy
        if self.sampling_strategy == SamplingStrategy.NONE:
            return True
        elif self.sampling_strategy == SamplingStrategy.RANDOM:
            return random.random() < self.debug_sample_rate
        elif self.sampling_strategy == SamplingStrategy.DETERMINISTIC:
            if request_id:
                # Hash request_id to get deterministic sampling
                hash_value = int(hashlib.md5(request_id.encode()).hexdigest()[:8], 16)
                threshold = int(self.debug_sample_rate * 0xFFFFFFFF)
                return hash_value < threshold
            else:
                # Fall back to random if no request_id
                return random.random() < self.debug_sample_rate

        return False

    def get_effective_level(self, operation: str | None = None) -> str:
        """Get effective log level for an operation.

        Args:
            operation: Operation name

        Returns:
            Effective log level (e.g., "INFO", "DEBUG")
        """
        if operation and operation in self.operation_levels:
            return self.operation_levels[operation]
        return self.level

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "VastLoggingConfig":
        """Create configuration from dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            VastLoggingConfig instance
        """
        # Convert sampling_strategy string to enum
        if "sampling_strategy" in config_dict:
            strategy = config_dict["sampling_strategy"]
            if isinstance(strategy, str):
                config_dict["sampling_strategy"] = SamplingStrategy(strategy)

        return cls(**config_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        return {
            "level": self.level,
            "debug_sample_rate": self.debug_sample_rate,
            "sampling_strategy": self.sampling_strategy.value,
            "operation_levels": self.operation_levels.copy(),
            "enable_hierarchical_messages": self.enable_hierarchical_messages,
            "max_namespace_depth": self.max_namespace_depth,
        }


# Global default configuration
_default_config = VastLoggingConfig()


def get_logging_config() -> VastLoggingConfig:
    """Get global logging configuration.

    Returns:
        Current global VastLoggingConfig
    """
    return _default_config


def set_logging_config(config: VastLoggingConfig) -> None:
    """Set global logging configuration.

    Args:
        config: VastLoggingConfig to set as global
    """
    global _default_config
    _default_config = config


__all__ = [
    "SamplingStrategy",
    "VastLoggingConfig",
    "get_logging_config",
    "set_logging_config",
]
