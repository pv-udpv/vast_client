"""Tests for VastLoggingConfig."""

import pytest

from vast_client.logging import (
    VastLoggingConfig,
    SamplingStrategy,
    get_logging_config,
    set_logging_config,
)


class TestVastLoggingConfig:
    """Test suite for VastLoggingConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = VastLoggingConfig()
        
        assert config.level == "INFO"
        assert config.debug_sample_rate == 0.0
        assert config.sampling_strategy == SamplingStrategy.RANDOM
        assert config.operation_levels == {}
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = VastLoggingConfig(
            level="DEBUG",
            debug_sample_rate=0.5,
            sampling_strategy=SamplingStrategy.DETERMINISTIC,
            operation_levels={"track_event": "INFO", "send_trackable": "DEBUG"},
        )
        
        assert config.level == "DEBUG"
        assert config.debug_sample_rate == 0.5
        assert config.sampling_strategy == SamplingStrategy.DETERMINISTIC
        assert config.operation_levels["track_event"] == "INFO"
    
    def test_should_log_debug_disabled(self):
        """Test debug logging disabled (sample_rate = 0.0)."""
        config = VastLoggingConfig(debug_sample_rate=0.0)
        
        # Should never log debug
        for _ in range(100):
            assert not config.should_log_debug()
    
    def test_should_log_debug_enabled(self):
        """Test debug logging enabled (sample_rate = 1.0)."""
        config = VastLoggingConfig(debug_sample_rate=1.0)
        
        # Should always log debug
        for _ in range(100):
            assert config.should_log_debug()
    
    def test_should_log_debug_random_sampling(self):
        """Test random sampling."""
        config = VastLoggingConfig(
            debug_sample_rate=0.5,
            sampling_strategy=SamplingStrategy.RANDOM,
        )
        
        # Run 1000 times and check roughly 50% are sampled
        samples = [config.should_log_debug() for _ in range(1000)]
        sample_count = sum(samples)
        
        # Should be roughly 500 ± 100 (allow for randomness)
        assert 400 <= sample_count <= 600
    
    def test_should_log_debug_deterministic_sampling(self):
        """Test deterministic sampling with request_id."""
        config = VastLoggingConfig(
            debug_sample_rate=0.5,
            sampling_strategy=SamplingStrategy.DETERMINISTIC,
        )
        
        # Same request_id should always return same result
        request_id = "abc123def456"
        result1 = config.should_log_debug(request_id=request_id)
        result2 = config.should_log_debug(request_id=request_id)
        result3 = config.should_log_debug(request_id=request_id)
        
        assert result1 == result2 == result3
    
    def test_should_log_debug_operation_override(self):
        """Test operation-specific log level override."""
        config = VastLoggingConfig(
            debug_sample_rate=1.0,  # Enable debug globally
            operation_levels={
                "track_event": "INFO",  # Disable debug for this operation
                "send_trackable": "DEBUG",  # Enable debug for this operation
            },
        )
        
        # track_event should not log debug (overridden to INFO)
        assert not config.should_log_debug(operation="track_event")
        
        # send_trackable should log debug
        assert config.should_log_debug(operation="send_trackable")
        
        # Unknown operation should use global setting
        assert config.should_log_debug(operation="unknown_op")
    
    def test_get_effective_level(self):
        """Test getting effective log level for operations."""
        config = VastLoggingConfig(
            level="INFO",
            operation_levels={"debug_op": "DEBUG", "warn_op": "WARNING"},
        )
        
        assert config.get_effective_level("debug_op") == "DEBUG"
        assert config.get_effective_level("warn_op") == "WARNING"
        assert config.get_effective_level("unknown_op") == "INFO"
        assert config.get_effective_level(None) == "INFO"
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "level": "DEBUG",
            "debug_sample_rate": 0.25,
            "sampling_strategy": "deterministic",
            "operation_levels": {"op1": "INFO"},
        }
        
        config = VastLoggingConfig.from_dict(config_dict)
        
        assert config.level == "DEBUG"
        assert config.debug_sample_rate == 0.25
        assert config.sampling_strategy == SamplingStrategy.DETERMINISTIC
        assert config.operation_levels["op1"] == "INFO"
    
    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = VastLoggingConfig(
            level="WARNING",
            debug_sample_rate=0.1,
            sampling_strategy=SamplingStrategy.DETERMINISTIC,
            operation_levels={"op1": "DEBUG"},
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["level"] == "WARNING"
        assert config_dict["debug_sample_rate"] == 0.1
        assert config_dict["sampling_strategy"] == "deterministic"
        assert config_dict["operation_levels"]["op1"] == "DEBUG"
    
    def test_global_config(self):
        """Test global config get/set."""
        # Save original config
        original_config = get_logging_config()
        
        try:
            # Set custom config
            custom_config = VastLoggingConfig(level="DEBUG", debug_sample_rate=0.5)
            set_logging_config(custom_config)
            
            # Should retrieve same config
            retrieved_config = get_logging_config()
            assert retrieved_config.level == "DEBUG"
            assert retrieved_config.debug_sample_rate == 0.5
        finally:
            # Restore original
            set_logging_config(original_config)
    
    def test_sampling_strategy_none(self):
        """Test SamplingStrategy.NONE logs everything."""
        config = VastLoggingConfig(
            debug_sample_rate=0.1,  # Low rate
            sampling_strategy=SamplingStrategy.NONE,
        )
        
        # Should always return True regardless of sample_rate
        for _ in range(100):
            assert config.should_log_debug()
    
    def test_hierarchical_messages_config(self):
        """Test hierarchical messages configuration."""
        config = VastLoggingConfig(enable_hierarchical_messages=True)
        assert config.enable_hierarchical_messages is True
        
        config2 = VastLoggingConfig(enable_hierarchical_messages=False)
        assert config2.enable_hierarchical_messages is False
    
    def test_max_namespace_depth_config(self):
        """Test max namespace depth configuration."""
        config = VastLoggingConfig(max_namespace_depth=5)
        assert config.max_namespace_depth == 5
