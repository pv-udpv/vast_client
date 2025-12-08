"""Unit tests for configuration classes."""


from vast_client.config import (
    InterruptionType,
    PlaybackMode,
    PlaybackSessionConfig,
    VastClientConfig,
    VastParserConfig,
    VastTrackerConfig,
)


class TestVastParserConfig:
    """Test VastParserConfig dataclass."""

    def test_default_config(self):
        """Test default parser configuration."""
        config = VastParserConfig()

        assert config.xpath_ad_system == ".//AdSystem"
        assert config.xpath_ad_title == ".//AdTitle"
        assert config.xpath_impression == ".//Impression"
        assert config.recover_on_error is True
        assert config.encoding == "utf-8"

    def test_custom_config(self):
        """Test custom parser configuration."""
        config = VastParserConfig(
            xpath_ad_system=".//Custom/AdSystem",
            recover_on_error=False,
            encoding="iso-8859-1",
        )

        assert config.xpath_ad_system == ".//Custom/AdSystem"
        assert config.recover_on_error is False
        assert config.encoding == "iso-8859-1"

    def test_custom_xpaths(self):
        """Test custom XPath configuration."""
        config = VastParserConfig(
            custom_xpaths={
                "custom_field": ".//CustomField",
                "extra_data": ".//ExtraData",
            }
        )

        assert "custom_field" in config.custom_xpaths
        assert config.custom_xpaths["custom_field"] == ".//CustomField"


class TestVastTrackerConfig:
    """Test VastTrackerConfig dataclass."""

    def test_default_config(self):
        """Test default tracker configuration."""
        config = VastTrackerConfig()

        assert config.timeout == 5.0
        assert "[{macro}]" in config.macro_formats
        assert "${{{macro}}}" in config.macro_formats

    def test_custom_config(self):
        """Test custom tracker configuration."""
        config = VastTrackerConfig(
            timeout=10.0,
            macro_formats=["[{macro}]"],
            static_macros={"PUBLISHER_ID": "pub-123"},
        )

        assert config.timeout == 10.0
        assert config.macro_formats == ["[{macro}]"]
        assert config.static_macros["PUBLISHER_ID"] == "pub-123"

    def test_macro_mapping(self):
        """Test macro mapping configuration."""
        config = VastTrackerConfig(
            macro_mapping={
                "publisher_id": "PUBLISHER_ID",
                "device_id": "DEVICE_ID",
            }
        )

        assert "publisher_id" in config.macro_mapping
        assert config.macro_mapping["publisher_id"] == "PUBLISHER_ID"


class TestPlaybackSessionConfig:
    """Test PlaybackSessionConfig dataclass."""

    def test_default_config(self):
        """Test default playback session configuration."""
        config = PlaybackSessionConfig()

        assert config.mode == PlaybackMode.AUTO
        assert config.enable_auto_quartiles is True
        assert config.max_session_duration_sec == 0  # Unlimited

    def test_real_mode_config(self):
        """Test real-time playback configuration."""
        config = PlaybackSessionConfig(
            mode=PlaybackMode.REAL,
        )

        assert config.mode == PlaybackMode.REAL

    def test_headless_mode_config(self):
        """Test headless playback configuration."""
        config = PlaybackSessionConfig(
            mode=PlaybackMode.HEADLESS,
            headless_tick_interval_sec=0.05,
        )

        assert config.mode == PlaybackMode.HEADLESS
        assert config.headless_tick_interval_sec == 0.05

    def test_interruption_rules(self):
        """Test interruption rules configuration."""
        config = PlaybackSessionConfig(
            interruption_rules={
                "start": {"probability": 0.1, "min_offset_sec": 0, "max_offset_sec": 2},
            }
        )

        assert "start" in config.interruption_rules
        assert config.interruption_rules["start"]["probability"] == 0.1


class TestVastClientConfig:
    """Test VastClientConfig dataclass."""

    def test_default_config(self):
        """Test default client configuration."""
        config = VastClientConfig(
            provider="test_provider",
            publisher="test_publisher",
        )

        assert config.provider == "test_provider"
        assert config.publisher == "test_publisher"
        assert config.enable_tracking is True
        assert config.enable_parsing is True

    def test_custom_config(
        self,
        parser_config,
        tracker_config,
        session_config,
    ):
        """Test custom client configuration."""
        config = VastClientConfig(
            provider="custom_provider",
            publisher="custom_publisher",
            enable_tracking=False,
            enable_parsing=True,
            parser=parser_config,
            tracker=tracker_config,
            session=session_config,
        )

        assert config.provider == "custom_provider"
        assert config.enable_tracking is False
        assert config.parser == parser_config
        assert config.tracker == tracker_config
        assert config.session == session_config


class TestPlaybackMode:
    """Test PlaybackMode enum."""

    def test_enum_values(self):
        """Test PlaybackMode enum values."""
        assert PlaybackMode.REAL == "real"
        assert PlaybackMode.HEADLESS == "headless"
        assert PlaybackMode.AUTO == "auto"

    def test_enum_membership(self):
        """Test PlaybackMode enum membership."""
        assert PlaybackMode.REAL in PlaybackMode
        assert PlaybackMode.HEADLESS in PlaybackMode
        assert PlaybackMode.AUTO in PlaybackMode


class TestInterruptionType:
    """Test InterruptionType enum."""

    def test_enum_values(self):
        """Test InterruptionType enum values."""
        assert InterruptionType.NONE == "none"
        assert InterruptionType.PAUSE == "pause"
        assert InterruptionType.STOP == "stop"
        assert InterruptionType.ERROR == "error"
        assert InterruptionType.TIMEOUT == "timeout"
        assert InterruptionType.EXCEEDED_LIMIT == "exceeded_limit"

    def test_enum_membership(self):
        """Test InterruptionType enum membership."""
        assert InterruptionType.PAUSE in InterruptionType
        assert InterruptionType.ERROR in InterruptionType
