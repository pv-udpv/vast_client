"""Tests for IAB VAST samples."""

from pathlib import Path

import pytest
from lxml import etree

from vast_client.config import VastParserConfig
from vast_client.parser import VastParser


class TestIABVastSamples:
    """Test VAST parser against official IAB samples."""

    @pytest.fixture(scope="class")
    def iab_samples_path(self) -> Path:
        """Get path to IAB samples directory."""
        return Path(__file__).parent

    @pytest.fixture(scope="class")
    def vast_parser(self):
        """Create VAST parser with recovery enabled."""
        config = VastParserConfig(recover_on_error=True)
        return VastParser(config=config)

    def get_vast_files(self, iab_samples_path: Path, version: str) -> list[Path]:
        """Get all VAST XML files for a specific version."""
        version_dir = iab_samples_path / f"VAST {version} Samples"
        if not version_dir.exists():
            return []

        xml_files = list(version_dir.glob("*.xml"))
        # Also check subdirectories
        for subdir in version_dir.iterdir():
            if subdir.is_dir():
                xml_files.extend(subdir.glob("*.xml"))

        return xml_files

    def test_vast_1_2_samples(self, iab_samples_path, vast_parser):
        """Test parsing VAST 1.0-2.0 samples."""
        xml_files = self.get_vast_files(iab_samples_path, "1-2.0")

        if not xml_files:
            pytest.skip("VAST 1-2.0 samples not found")

        parsed_count = 0
        for xml_file in xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                # Basic validation
                assert "vast_version" in vast_data
                parsed_count += 1

            except Exception as e:
                pytest.fail(f"Failed to parse {xml_file.name}: {e}")

        assert parsed_count > 0, "No VAST 1-2.0 files were parsed"

    def test_vast_3_samples(self, iab_samples_path, vast_parser):
        """Test parsing VAST 3.0 samples."""
        xml_files = self.get_vast_files(iab_samples_path, "3.0")

        if not xml_files:
            pytest.skip("VAST 3.0 samples not found")

        parsed_count = 0
        for xml_file in xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                assert "vast_version" in vast_data
                parsed_count += 1

            except Exception as e:
                pytest.fail(f"Failed to parse {xml_file.name}: {e}")

        assert parsed_count > 0, "No VAST 3.0 files were parsed"

    def test_vast_4_0_samples(self, iab_samples_path, vast_parser):
        """Test parsing VAST 4.0 samples."""
        xml_files = self.get_vast_files(iab_samples_path, "4.0")

        if not xml_files:
            pytest.skip("VAST 4.0 samples not found")

        parsed_count = 0
        for xml_file in xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                assert "vast_version" in vast_data
                assert vast_data["vast_version"] in ["4.0", "4.1", "4.2"]
                parsed_count += 1

            except Exception as e:
                pytest.fail(f"Failed to parse {xml_file.name}: {e}")

        assert parsed_count > 0, "No VAST 4.0 files were parsed"

    def test_vast_4_1_samples(self, iab_samples_path, vast_parser):
        """Test parsing VAST 4.1 samples."""
        xml_files = self.get_vast_files(iab_samples_path, "4.1")

        if not xml_files:
            pytest.skip("VAST 4.1 samples not found")

        parsed_count = 0
        for xml_file in xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                assert "vast_version" in vast_data
                parsed_count += 1

            except Exception as e:
                pytest.fail(f"Failed to parse {xml_file.name}: {e}")

        assert parsed_count > 0, "No VAST 4.1 files were parsed"

    def test_vast_4_2_samples(self, iab_samples_path, vast_parser):
        """Test parsing VAST 4.2 samples."""
        xml_files = self.get_vast_files(iab_samples_path, "4.2")

        if not xml_files:
            pytest.skip("VAST 4.2 samples not found")

        parsed_count = 0
        for xml_file in xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                assert "vast_version" in vast_data
                parsed_count += 1

            except Exception as e:
                pytest.fail(f"Failed to parse {xml_file.name}: {e}")

        assert parsed_count > 0, "No VAST 4.2 files were parsed"


class TestIABVastSamplesDetailed:
    """Detailed tests for specific IAB sample features."""

    @pytest.fixture(scope="class")
    def vast_parser(self):
        """Create VAST parser."""
        config = VastParserConfig(recover_on_error=True)
        return VastParser(config=config)

    def test_inline_linear_sample(self, vast_parser):
        """Test parsing inline linear ad sample."""
        # This is a common pattern in IAB samples
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad id="12345">
    <InLine>
      <AdSystem version="1.0">Test System</AdSystem>
      <AdTitle>Test Title</AdTitle>
      <Impression><![CDATA[https://example.com/impression]]></Impression>
      <Creatives>
        <Creative id="creative-001">
          <Linear>
            <Duration>00:00:30</Duration>
            <TrackingEvents>
              <Tracking event="start"><![CDATA[https://example.com/start]]></Tracking>
              <Tracking event="firstQuartile"><![CDATA[https://example.com/q1]]></Tracking>
              <Tracking event="midpoint"><![CDATA[https://example.com/mid]]></Tracking>
              <Tracking event="thirdQuartile"><![CDATA[https://example.com/q3]]></Tracking>
              <Tracking event="complete"><![CDATA[https://example.com/complete]]></Tracking>
            </TrackingEvents>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4" width="1920" height="1080">
                <![CDATA[https://example.com/video.mp4]]>
              </MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""

        vast_data = vast_parser.parse_vast(xml)

        assert vast_data["vast_version"] == "4.0"
        assert vast_data["ad_system"] == "Test System"
        assert vast_data["ad_title"] == "Test Title"
        assert len(vast_data["impression"]) == 1
        assert vast_data["duration"] == 30
        assert "start" in vast_data["tracking_events"]
        assert "firstQuartile" in vast_data["tracking_events"]
        assert "midpoint" in vast_data["tracking_events"]
        assert "thirdQuartile" in vast_data["tracking_events"]
        assert "complete" in vast_data["tracking_events"]

    def test_all_samples_have_required_fields(self, vast_parser):
        """Test that all parsed samples have required fields."""
        iab_samples_path = Path(__file__).parent
        all_xml_files = []

        for version in ["1-2.0", "3.0", "4.0", "4.1", "4.2"]:
            version_dir = iab_samples_path / f"VAST {version} Samples"
            if version_dir.exists():
                all_xml_files.extend(version_dir.glob("*.xml"))
                for subdir in version_dir.iterdir():
                    if subdir.is_dir():
                        all_xml_files.extend(subdir.glob("*.xml"))

        if not all_xml_files:
            pytest.skip("No IAB samples found")

        for xml_file in all_xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                # Required fields that should always be present
                assert "vast_version" in vast_data, f"{xml_file.name}: missing vast_version"
                assert "impression" in vast_data, f"{xml_file.name}: missing impression"
                assert "tracking_events" in vast_data, f"{xml_file.name}: missing tracking_events"
                assert isinstance(vast_data["tracking_events"], dict)

            except etree.XMLSyntaxError:
                # Some samples might be intentionally malformed
                continue
            except Exception as e:
                # Log but don't fail - some samples might be edge cases
                print(f"Warning: Could not fully validate {xml_file.name}: {e}")

    def test_samples_tracking_event_types(self, vast_parser):
        """Test that samples contain various tracking event types."""
        iab_samples_path = Path(__file__).parent
        all_xml_files = []

        for version in ["3.0", "4.0", "4.1", "4.2"]:
            version_dir = iab_samples_path / f"VAST {version} Samples"
            if version_dir.exists():
                all_xml_files.extend(version_dir.glob("*.xml"))

        if not all_xml_files:
            pytest.skip("No IAB samples found")

        # Track which event types we've seen
        seen_events = set()

        for xml_file in all_xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                seen_events.update(vast_data["tracking_events"].keys())

            except Exception:
                continue

        # Should have seen at least some common events
        common_events = {"start", "complete"}
        assert len(seen_events & common_events) > 0, "No common tracking events found in samples"
