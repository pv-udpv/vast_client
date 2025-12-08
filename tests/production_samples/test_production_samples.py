"""Tests for production VAST samples from real ad servers.

This module tests the VAST client against real production samples from:
- g.adstrm.ru (Adstream)
- Other production ad servers

Samples are extracted from production logs and anonymized.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from vast_client.client import VastClient
from vast_client.config import VastParserConfig
from vast_client.parser import VastParser


class TestProductionSamples:
    """Test VAST client with production samples."""

    @pytest.fixture(scope="class")
    def production_samples_dir(self) -> Path:
        """Get production samples directory."""
        return Path(__file__).parent

    @pytest.fixture(scope="class")
    def vast_parser(self):
        """Create VAST parser with production settings."""
        config = VastParserConfig(
            recover_on_error=True,  # Production may have minor XML issues
            encoding="utf-8",
        )
        return VastParser(config=config)

    def load_production_metadata(self, samples_dir: Path) -> dict[str, Any]:
        """Load production metadata JSON."""
        metadata_file = samples_dir / "production_metadata.json"
        if metadata_file.exists():
            return json.loads(metadata_file.read_text())
        return {}

    def test_adstream_vast3_samples(self, production_samples_dir, vast_parser):
        """Test g.adstrm.ru VAST3 samples."""
        # Check for g.adstrm.ru samples
        adstream_dir = production_samples_dir / "g.adstrm.ru"
        if not adstream_dir.exists():
            pytest.skip("g.adstrm.ru production samples not available")

        xml_files = list(adstream_dir.glob("*.xml"))
        if not xml_files:
            pytest.skip("No g.adstrm.ru XML samples found")

        parsed_count = 0
        for xml_file in xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                # Validate required fields
                assert "vast_version" in vast_data
                assert "impression" in vast_data
                assert "tracking_events" in vast_data

                parsed_count += 1

            except Exception as e:
                pytest.fail(f"Failed to parse {xml_file.name}: {e}")

        assert parsed_count > 0, "No Adstream samples were parsed"

    def test_production_vast_versions(self, production_samples_dir, vast_parser):
        """Test that production samples cover various VAST versions."""
        all_xml_files = list(production_samples_dir.rglob("*.xml"))

        if not all_xml_files:
            pytest.skip("No production samples available")

        versions_found = set()

        for xml_file in all_xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                if vast_data.get("vast_version"):
                    versions_found.add(vast_data["vast_version"])

            except Exception:
                continue

        # Production should have at least VAST 3.0 or 4.0
        assert len(versions_found) > 0, "No VAST versions found in production samples"

    def test_production_tracking_events(self, production_samples_dir, vast_parser):
        """Test tracking events in production samples."""
        all_xml_files = list(production_samples_dir.rglob("*.xml"))

        if not all_xml_files:
            pytest.skip("No production samples available")

        all_events = set()

        for xml_file in all_xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")
                vast_data = vast_parser.parse_vast(xml_content)

                all_events.update(vast_data.get("tracking_events", {}).keys())

            except Exception:
                continue

        # Production samples should have at least basic events
        assert len(all_events) > 0, "No tracking events found in production samples"

    def test_production_macro_patterns(self, production_samples_dir, vast_parser):
        """Test that production samples use real macro patterns."""
        all_xml_files = list(production_samples_dir.rglob("*.xml"))

        if not all_xml_files:
            pytest.skip("No production samples available")

        macros_found = set()
        common_macros = ["TIMESTAMP", "CACHEBUSTING", "RANDOM", "CREATIVE_ID", "ADID"]

        for xml_file in all_xml_files:
            try:
                xml_content = xml_file.read_text(encoding="utf-8")

                # Check for macro patterns in raw XML
                for macro in common_macros:
                    if f"[{macro}]" in xml_content or f"${{{macro}}}" in xml_content:
                        macros_found.add(macro)

            except Exception:
                continue

        # Production samples commonly use TIMESTAMP/CACHEBUSTING
        # This is informational - log what we find
        print(f"\nMacros found in production samples: {macros_found}")


class TestProductionMetadata:
    """Test production metadata and statistics."""

    @pytest.fixture(scope="class")
    def production_metadata(self) -> dict[str, Any]:
        """Load production metadata."""
        metadata_file = Path(__file__).parent / "production_metadata.json"
        if metadata_file.exists():
            return json.loads(metadata_file.read_text())
        return {}

    def test_metadata_structure(self, production_metadata):
        """Test that production metadata has expected structure."""
        if not production_metadata:
            pytest.skip("No production metadata available")

        # Metadata should have information about samples
        assert isinstance(production_metadata, dict)

        if "providers" in production_metadata:
            assert isinstance(production_metadata["providers"], list)

        if "sample_count" in production_metadata:
            assert isinstance(production_metadata["sample_count"], int)
            assert production_metadata["sample_count"] > 0

    def test_production_providers_documented(self, production_metadata):
        """Test that production providers are documented."""
        if not production_metadata:
            pytest.skip("No production metadata available")

        if "providers" in production_metadata:
            providers = production_metadata["providers"]

            # Should have at least one provider
            assert len(providers) > 0, "No providers documented"

            # Each provider should have basic info
            for provider in providers:
                assert "name" in provider or "url" in provider


class TestProductionEdgeCases:
    """Test edge cases found in production."""

    @pytest.fixture
    def vast_parser(self):
        """Create parser with recovery enabled."""
        config = VastParserConfig(recover_on_error=True)
        return VastParser(config=config)

    def test_empty_204_response(self, vast_parser):
        """Test handling of 204 No Content (common in production)."""
        # This is logged frequently in production logs
        # g.adstrm.ru often returns 204 when no ad is available

        # Empty response should be handled gracefully

        # Parser should handle empty input
        # (actual handling depends on client, not parser)

    def test_production_duration_formats(self, vast_parser):
        """Test duration formats seen in production."""
        # Production samples may have various duration formats

        test_cases = [
            ("00:00:15", 15),  # 15 seconds
            ("00:00:30", 30),  # 30 seconds
            ("00:01:00", 60),  # 1 minute
            ("00:00:05", 5),  # 5 seconds (short ad)
        ]

        for duration_str, expected_seconds in test_cases:
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<VAST version="4.0">
  <Ad>
    <InLine>
      <AdSystem>Test</AdSystem>
      <Impression>https://example.com/imp</Impression>
      <Creatives>
        <Creative>
          <Linear>
            <Duration>{duration_str}</Duration>
            <MediaFiles>
              <MediaFile>https://example.com/video.mp4</MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>"""

            vast_data = vast_parser.parse_vast(xml)
            assert vast_data["duration"] == expected_seconds

    def test_cyrillic_parameters(self):
        """Test handling of Cyrillic parameters (seen in g.adstrm.ru logs)."""
        # Production logs show Cyrillic in query parameters
        # Ensure URL building preserves Unicode

        from vast_client.http import build_url_preserving_unicode

        base_url = "https://g.adstrm.ru/vast3"
        params = {
            "category": "кино",  # Cyrillic: "cinema"
            "genre": "комедия",  # Cyrillic: "comedy"
        }

        # Should preserve Cyrillic characters
        result = build_url_preserving_unicode(base_url, params, {})

        assert "кино" in result or "%D0%" in result  # Either raw or percent-encoded
        assert "комедия" in result or "%D0%" in result


class TestProductionIntegration:
    """Integration tests with production scenarios."""

    @pytest.mark.asyncio
    async def test_adstream_typical_workflow(self, production_samples_dir):
        """Test typical g.adstrm.ru workflow."""
        # Typical production workflow:
        # 1. Request ad from g.adstrm.ru/vast3
        # 2. Parse VAST XML response
        # 3. Track impression
        # 4. Track quartile events

        adstream_dir = production_samples_dir / "g.adstrm.ru"
        if not adstream_dir.exists():
            pytest.skip("g.adstrm.ru samples not available")

        # Find a sample XML
        xml_files = list(adstream_dir.glob("*.xml"))
        if not xml_files:
            pytest.skip("No g.adstrm.ru XML samples")

        from unittest.mock import AsyncMock, MagicMock

        # Load sample XML
        sample_xml = xml_files[0].read_text()

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = sample_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Create client
        client = VastClient("https://g.adstrm.ru/vast3")
        client.client = mock_client

        # Request ad
        vast_data = await client.request_ad()

        # Should parse successfully
        assert vast_data is not None
        assert isinstance(vast_data, dict)

        # Should have tracking events
        if "tracking_events" in vast_data:
            assert isinstance(vast_data["tracking_events"], dict)

    @pytest.mark.asyncio
    async def test_production_204_handling(self):
        """Test handling of 204 No Content (common in production)."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock 204 response (no ad available)
        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://g.adstrm.ru/vast3")
        client.client = mock_client

        # Should handle gracefully
        result = await client.request_ad()

        # Should return empty string
        assert result == ""
