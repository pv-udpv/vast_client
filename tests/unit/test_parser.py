"""Unit tests for VAST parser."""

import pytest
from lxml import etree

from vast_client.config import VastParserConfig
from vast_client.parser import VastParser


class TestVastParser:
    """Test suite for VastParser class."""

    def test_parser_initialization(self, parser_config):
        """Test parser initialization with config."""
        parser = VastParser(config=parser_config)
        assert parser.config == parser_config
        assert parser.logger is not None

    def test_parser_initialization_without_config(self):
        """Test parser initialization without config (uses defaults)."""
        parser = VastParser()
        assert parser.config is not None
        assert isinstance(parser.config, VastParserConfig)

    def test_parse_minimal_vast(self, vast_parser, minimal_vast_xml):
        """Test parsing minimal valid VAST XML."""
        vast_data = vast_parser.parse_vast(minimal_vast_xml)

        assert vast_data["vast_version"] == "4.0"
        assert vast_data["ad_system"] == "Test Ad System"
        assert vast_data["ad_title"] == "Test Ad Title"
        assert len(vast_data["impression"]) == 1
        assert vast_data["media_url"] == "https://media.example.com/video.mp4"
        assert vast_data["duration"] == 15

    def test_parse_vast_with_quartiles(self, vast_parser, vast_with_quartiles_xml):
        """Test parsing VAST XML with quartile events."""
        vast_data = vast_parser.parse_vast(vast_with_quartiles_xml)

        assert "start" in vast_data["tracking_events"]
        assert "firstQuartile" in vast_data["tracking_events"]
        assert "midpoint" in vast_data["tracking_events"]
        assert "thirdQuartile" in vast_data["tracking_events"]
        assert "complete" in vast_data["tracking_events"]
        assert vast_data["duration"] == 30

    def test_parse_vast_with_macros(self, vast_parser, vast_with_macros_xml):
        """Test parsing VAST XML with macro placeholders."""
        vast_data = vast_parser.parse_vast(vast_with_macros_xml)

        # Macros should be preserved in tracking URLs
        impression_url = vast_data["impression"][0]
        assert "[TIMESTAMP]" in impression_url
        assert "[RANDOM]" in impression_url

        start_url = vast_data["tracking_events"]["start"][0]
        assert "[CREATIVE_ID]" in start_url or "${TIMESTAMP}" in start_url

    def test_parse_vast_with_error_urls(self, vast_parser, vast_with_error_xml):
        """Test parsing VAST XML with error tracking URLs."""
        vast_data = vast_parser.parse_vast(vast_with_error_xml)

        assert len(vast_data["error"]) == 1
        assert "[ERRORCODE]" in vast_data["error"][0]
        assert vast_data["duration"] == 10

    def test_parse_empty_vast(self, vast_parser, empty_vast_xml):
        """Test parsing empty VAST response (no ads)."""
        vast_data = vast_parser.parse_vast(empty_vast_xml)

        assert vast_data["vast_version"] == "4.0"
        assert vast_data["ad_system"] is None
        assert vast_data["ad_title"] is None
        assert vast_data["impression"] == []

    def test_parse_malformed_vast_with_recovery(self):
        """Test parsing malformed VAST with recovery enabled."""
        config = VastParserConfig(recover_on_error=True)
        parser = VastParser(config=config)

        malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad id="test">
    <InLine>
      <AdSystem>Test</AdSystem>
      <!-- Missing closing tag - parser should recover -->
      <AdTitle>Test Ad
    </InLine>
  </Ad>
</VAST>"""

        # With recovery, should not raise exception
        vast_data = parser.parse_vast(malformed_xml)
        assert vast_data is not None

    def test_parse_malformed_vast_without_recovery(self):
        """Test parsing malformed VAST without recovery (should raise)."""
        config = VastParserConfig(recover_on_error=False)
        parser = VastParser(config=config)

        malformed_xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test
    </InLine>
</VAST>"""

        # Without recovery, should raise XMLSyntaxError
        with pytest.raises(etree.XMLSyntaxError):
            parser.parse_vast(malformed_xml)

    def test_parse_duration_formats(self, vast_parser):
        """Test parsing different duration formats."""
        xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad><InLine><AdSystem>Test</AdSystem><Creatives><Creative><Linear>
    <Duration>{duration}</Duration>
    <MediaFiles><MediaFile delivery="progressive" type="video/mp4">https://example.com/video.mp4</MediaFile></MediaFiles>
  </Linear></Creative></Creatives></InLine></Ad>
</VAST>"""

        # Test HH:MM:SS format
        vast_data = vast_parser.parse_vast(xml_template.format(duration="00:01:30"))
        assert vast_data["duration"] == 90

        # Test with hours
        vast_data = vast_parser.parse_vast(xml_template.format(duration="01:30:00"))
        assert vast_data["duration"] == 5400

    def test_parse_media_files(self, vast_parser, minimal_vast_xml):
        """Test parsing media files with attributes."""
        vast_data = vast_parser.parse_vast(minimal_vast_xml)

        assert len(vast_data["media_files"]) == 1
        media_file = vast_data["media_files"][0]

        assert media_file["url"] == "https://media.example.com/video.mp4"
        assert media_file["delivery"] == "progressive"
        assert media_file["type"] == "video/mp4"
        assert media_file["width"] == "1280"
        assert media_file["height"] == "720"

    def test_parse_creative_ids(self, vast_parser, minimal_vast_xml):
        """Test parsing creative IDs."""
        vast_data = vast_parser.parse_vast(minimal_vast_xml)

        assert vast_data["creative"]["id"] == "creative-001"
        assert vast_data["creative"]["ad_id"] == "ad-001"

    def test_parse_extensions(self, vast_parser):
        """Test parsing VAST extensions."""
        xml_with_extensions = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <Extensions>
        <Extension type="CustomTracking">
          <CustomData>value123</CustomData>
        </Extension>
      </Extensions>
      <Impression>https://example.com/imp</Impression>
      <Creatives><Creative><Linear>
        <Duration>00:00:10</Duration>
        <MediaFiles><MediaFile>https://example.com/video.mp4</MediaFile></MediaFiles>
      </Linear></Creative></Creatives>
    </InLine>
  </Ad>
</VAST>"""

        vast_data = vast_parser.parse_vast(xml_with_extensions)
        assert "extensions" in vast_data
        assert len(vast_data["extensions"]) > 0

    def test_custom_xpath_config(self):
        """Test parser with custom XPath configuration."""
        config = VastParserConfig(
            custom_xpaths={
                "custom_field": ".//CustomField",
            }
        )
        parser = VastParser(config=config)

        xml_with_custom = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <CustomField>custom_value</CustomField>
      <Impression>https://example.com/imp</Impression>
      <Creatives><Creative><Linear>
        <Duration>00:00:10</Duration>
        <MediaFiles><MediaFile>https://example.com/video.mp4</MediaFile></MediaFiles>
      </Linear></Creative></Creatives>
    </InLine>
  </Ad>
</VAST>"""

        vast_data = parser.parse_vast(xml_with_custom)
        assert "custom_field" in vast_data["extensions"]
        assert "custom_value" in vast_data["extensions"]["custom_field"]

    def test_from_config_classmethod(self):
        """Test creating parser from config dictionary."""
        config_dict = {
            "recover_on_error": True,
            "encoding": "utf-8",
            "strict_xml": False,
        }

        parser = VastParser.from_config(config_dict)
        assert parser.config.recover_on_error is True
        assert parser.config.encoding == "utf-8"
        assert parser.config.strict_xml is False


class TestVastParserEdgeCases:
    """Edge case tests for VAST parser."""

    def test_parse_multiple_impressions(self, vast_parser):
        """Test parsing VAST with multiple impression URLs."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <Impression>https://tracking1.example.com/imp</Impression>
      <Impression>https://tracking2.example.com/imp</Impression>
      <Impression>https://tracking3.example.com/imp</Impression>
      <Creatives><Creative><Linear>
        <Duration>00:00:10</Duration>
        <MediaFiles><MediaFile>https://example.com/video.mp4</MediaFile></MediaFiles>
      </Linear></Creative></Creatives>
    </InLine>
  </Ad>
</VAST>"""

        vast_data = vast_parser.parse_vast(xml)
        assert len(vast_data["impression"]) == 3

    def test_parse_multiple_tracking_events(self, vast_parser):
        """Test parsing multiple tracking events of same type."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <Impression>https://example.com/imp</Impression>
      <Creatives><Creative><Linear>
        <Duration>00:00:10</Duration>
        <MediaFiles><MediaFile>https://example.com/video.mp4</MediaFile></MediaFiles>
        <TrackingEvents>
          <Tracking event="start">https://tracking1.example.com/start</Tracking>
          <Tracking event="complete">https://tracking1.example.com/complete</Tracking>
        </TrackingEvents>
      </Linear></Creative></Creatives>
    </InLine>
  </Ad>
</VAST>"""

        vast_data = vast_parser.parse_vast(xml)
        assert "start" in vast_data["tracking_events"]
        assert "complete" in vast_data["tracking_events"]

    def test_parse_vast_with_cdata_sections(self, vast_parser):
        """Test parsing URLs within CDATA sections."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <Impression><![CDATA[https://example.com/imp?param=<>&"]]></Impression>
      <Creatives><Creative><Linear>
        <Duration>00:00:10</Duration>
        <MediaFiles><MediaFile><![CDATA[https://example.com/video.mp4]]></MediaFile></MediaFiles>
      </Linear></Creative></Creatives>
    </InLine>
  </Ad>
</VAST>"""

        vast_data = vast_parser.parse_vast(xml)
        # CDATA should preserve special characters
        assert "param=<>&" in vast_data["impression"][0]

    def test_parse_vast_different_versions(self, vast_parser):
        """Test parsing different VAST versions."""
        for version in ["1.0", "2.0", "3.0", "4.0", "4.1", "4.2"]:
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<VAST version="{version}">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <Impression>https://example.com/imp</Impression>
      <Creatives><Creative><Linear>
        <Duration>00:00:10</Duration>
        <MediaFiles><MediaFile>https://example.com/video.mp4</MediaFile></MediaFiles>
      </Linear></Creative></Creatives>
    </InLine>
  </Ad>
</VAST>"""

            vast_data = vast_parser.parse_vast(xml)
            assert vast_data["vast_version"] == version
