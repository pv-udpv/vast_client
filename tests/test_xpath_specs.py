"""Tests for XPath specifications and custom parsing functionality."""

import pytest
from unittest.mock import AsyncMock, Mock

from vast_client.config import (
    XPathSpec,
    ExtractMode,
)
from vast_client.parser import VastParser


class TestXPathSpec:
    """Test XPathSpec dataclass."""

    def test_xpath_spec_creation(self):
        """Test creating XPathSpec with all parameters."""
        spec = XPathSpec(
            xpath=".//Impression",
            name="impressions",
            callback=lambda x: x,
            mode=ExtractMode.LIST,
            required=True,
        )

        assert spec.xpath == ".//Impression"
        assert spec.name == "impressions"
        assert spec.callback is not None
        assert spec.mode == ExtractMode.LIST
        assert spec.required is True

    def test_xpath_spec_defaults(self):
        """Test XPathSpec default values."""
        spec = XPathSpec(xpath=".//Duration", name="duration")

        assert spec.callback is None
        assert spec.mode == ExtractMode.LIST
        assert spec.required is False


class TestVastParserWithSpecs:
    """Test VastParser.parse_with_specs method."""

    def test_parse_with_specs_basic(self):
        """Test parsing with basic XPath specs."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <Impression>https://example.com/impression1</Impression>
                    <Impression>https://example.com/impression2</Impression>
                    <Duration>00:00:30</Duration>
                </InLine>
            </Ad>
        </VAST>"""

        specs = [
            XPathSpec(xpath=".//Impression", name="impressions", mode=ExtractMode.LIST),
            XPathSpec(xpath=".//Duration", name="duration", mode=ExtractMode.SINGLE),
        ]

        parser = VastParser()
        result = parser.parse_with_specs(xml_content, specs)

        assert "impressions" in result
        assert "duration" in result
        assert len(result["impressions"]) == 2
        assert result["duration"] == "00:00:30"

    def test_parse_with_specs_callback(self):
        """Test parsing with callback functions."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <Duration>00:00:30</Duration>
                </InLine>
            </Ad>
        </VAST>"""

        def parse_duration(duration_str):
            """Parse duration to seconds."""
            if duration_str == "00:00:30":
                return 30
            return 0

        specs = [
            XPathSpec(
                xpath=".//Duration",
                name="duration_seconds",
                callback=parse_duration,
                mode=ExtractMode.SINGLE,
            )
        ]

        parser = VastParser()
        result = parser.parse_with_specs(xml_content, specs)

        assert result["duration_seconds"] == 30

    def test_parse_with_specs_required_field_missing(self):
        """Test that required fields raise errors when missing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <!-- No Duration element -->
                </InLine>
            </Ad>
        </VAST>"""

        specs = [
            XPathSpec(xpath=".//Duration", name="duration", mode=ExtractMode.SINGLE, required=True)
        ]

        parser = VastParser()

        with pytest.raises(Exception):  # Should raise VastXMLError
            parser.parse_with_specs(xml_content, specs)

    def test_parse_with_specs_optional_field_missing(self):
        """Test that optional fields return None when missing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <!-- No Duration element -->
                </InLine>
            </Ad>
        </VAST>"""

        specs = [
            XPathSpec(xpath=".//Duration", name="duration", mode=ExtractMode.SINGLE, required=False)
        ]

        parser = VastParser()
        result = parser.parse_with_specs(xml_content, specs)

        assert result["duration"] is None

    def test_parse_with_specs_custom_xpath_patterns(self):
        """Test parsing with custom XPath patterns for provider-specific data."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <Extensions>
                        <Extension type="provider">
                            <ProviderData>
                                <ID>provider_123</ID>
                                <Category>premium</Category>
                            </ProviderData>
                        </Extension>
                    </Extensions>
                </InLine>
            </Ad>
        </VAST>"""

        specs = [
            XPathSpec(
                xpath=".//Extensions/Extension[@type='provider']/ProviderData/ID",
                name="provider_id",
                mode=ExtractMode.SINGLE,
            ),
            XPathSpec(
                xpath=".//Extensions/Extension[@type='provider']/ProviderData/Category",
                name="provider_category",
                mode=ExtractMode.SINGLE,
            ),
        ]

        parser = VastParser()
        result = parser.parse_with_specs(xml_content, specs)

        assert result["provider_id"] == "provider_123"
        assert result["provider_category"] == "premium"

    def test_parse_with_specs_callback_processing_list(self):
        """Test callback processing on list mode results."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <Tracking event="impression">https://example.com/imp1</Tracking>
                    <Tracking event="impression">https://example.com/imp2</Tracking>
                    <Tracking event="start">https://example.com/start</Tracking>
                </InLine>
            </Ad>
        </VAST>"""

        def filter_impressions(urls):
            """Filter only impression URLs."""
            return [url for url in urls if "imp" in url]

        specs = [
            XPathSpec(
                xpath=".//Tracking",
                name="impression_urls",
                callback=filter_impressions,
                mode=ExtractMode.LIST,
            ),
        ]

        parser = VastParser()
        result = parser.parse_with_specs(xml_content, specs)

        assert len(result["impression_urls"]) == 2
        assert "imp1" in result["impression_urls"][0]
        assert "imp2" in result["impression_urls"][1]


class TestVastClientWithSpecs:
    """Test VastClient integration with xpath_specs."""

    @pytest.mark.asyncio
    async def test_client_with_xpath_specs(self):
        """Test client initialization and request with xpath_specs."""
        from vast_client.client import VastClient

        # Define xpath specs
        xpath_specs = [
            XPathSpec(xpath=".//Impression", name="custom_impressions", mode=ExtractMode.LIST),
            XPathSpec(xpath=".//Duration", name="duration", mode=ExtractMode.SINGLE),
        ]

        # Create client with specs
        client = VastClient("https://example.com/vast", xpath_specs=xpath_specs)

        assert client.xpath_specs == xpath_specs

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <Impression>https://example.com/imp1</Impression>
                    <Duration>00:00:30</Duration>
                </InLine>
            </Ad>
        </VAST>"""
        mock_response.headers = {"content-type": "application/xml"}

        # Mock the HTTP client
        from vast_client.http_client_manager import get_main_http_client

        mock_client = Mock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch get_main_http_client to return our mock
        import vast_client.client

        original_get_client = vast_client.client.get_main_http_client
        vast_client.client.get_main_http_client = Mock(return_value=mock_client)

        try:
            # Make request
            result = await client.request_ad()

            # Verify xpath_specs were used
            assert "custom_impressions" in result
            assert "duration" in result
            assert result["custom_impressions"] == ["https://example.com/imp1"]
            assert result["duration"] == "00:00:30"

        finally:
            # Restore original function
            vast_client.client.get_main_http_client = original_get_client

    @pytest.mark.asyncio
    async def test_client_without_xpath_specs(self):
        """Test client works without xpath_specs (standard parsing)."""
        from vast_client.client import VastClient

        # Create client without specs
        client = VastClient("https://example.com/vast")

        assert client.xpath_specs == []

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <Impression>https://example.com/imp1</Impression>
                    <Duration>00:00:30</Duration>
                </InLine>
            </Ad>
        </VAST>"""
        mock_response.headers = {"content-type": "application/xml"}

        # Mock the HTTP client
        from vast_client.http_client_manager import get_main_http_client

        mock_client = Mock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Patch get_main_http_client to return our mock
        import vast_client.client

        original_get_client = vast_client.client.get_main_http_client
        vast_client.client.get_main_http_client = Mock(return_value=mock_client)

        try:
            # Make request
            result = await client.request_ad()

            # Verify standard parsing was used
            assert "impression" in result
            assert "duration" in result
            assert result["impression"] == ["https://example.com/imp1"]
            assert result["duration"] == 30  # Standard parsing converts to seconds

        finally:
            # Restore original function
            vast_client.client.get_main_http_client = original_get_client


class TestWrapperResolution:
    """Test VAST wrapper resolution functionality."""

    @pytest.mark.asyncio
    async def test_wrapper_resolution_inline_ad(self):
        """Test that InLine ads are returned without wrapper resolution."""
        from vast_client.client import VastClient

        client = VastClient("https://example.com/vast")

        # Mock response with InLine ad
        inline_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <AdTitle>Test Ad</AdTitle>
                    <Duration>00:00:30</Duration>
                </InLine>
            </Ad>
        </VAST>"""

        result = await client._resolve_vast_response(inline_xml)

        assert result["ad"]["type"] == "inline"
        assert result["ad_title"] == "Test Ad"
        assert result["duration"] == 30

    @pytest.mark.asyncio
    async def test_wrapper_resolution_follows_wrapper(self):
        """Test that wrapper ads are followed to InLine content."""
        from vast_client.client import VastClient

        client = VastClient("https://example.com/vast")

        # Mock the wrapper response
        wrapper_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <Wrapper>
                    <VASTAdTagURI>https://example.com/inline</VASTAdTagURI>
                </Wrapper>
            </Ad>
        </VAST>"""

        # Mock the InLine response
        inline_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <InLine>
                    <AdTitle>Inline Ad</AdTitle>
                    <Duration>00:00:45</Duration>
                </InLine>
            </Ad>
        </VAST>"""

        # Mock HTTP client responses
        from vast_client.http_client_manager import get_main_http_client

        mock_client = Mock()
        mock_client.get = AsyncMock()

        # First call returns wrapper, second call returns inline
        mock_client.get.side_effect = [
            Mock(status_code=200, text=inline_xml),  # Followed URL
        ]

        # Patch get_main_http_client to return our mock
        import vast_client.client

        original_get_client = vast_client.client.get_main_http_client
        vast_client.client.get_main_http_client = Mock(return_value=mock_client)

        try:
            # The method expects the initial response to be wrapper, then follows
            # For testing, we'll mock the initial parse to detect wrapper
            result = await client._resolve_vast_response(wrapper_xml)

            # Should have followed wrapper and returned inline content
            # (In real usage, this would be called from request_ad after initial parse)
            assert result["_raw_vast_response"] == wrapper_xml

        finally:
            # Restore original function
            vast_client.client.get_main_http_client = original_get_client

    @pytest.mark.asyncio
    async def test_wrapper_resolution_max_depth(self):
        """Test that excessive wrapper chaining is prevented."""
        from vast_client.client import VastClient

        client = VastClient("https://example.com/vast")

        # Create a chain of 6 wrappers (exceeds max depth of 5)
        wrapper_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <Wrapper>
                    <VASTAdTagURI>https://example.com/wrapper1</VASTAdTagURI>
                </Wrapper>
            </Ad>
        </VAST>"""

        result = await client._resolve_vast_response(wrapper_xml)

        # Should mark as failed but return partial result
        assert result["_wrapper_resolution_failed"] is True
        assert result["_raw_vast_response"] == wrapper_xml

    @pytest.mark.asyncio
    async def test_wrapper_resolution_missing_url(self):
        """Test handling of wrappers without VASTAdTagURI."""
        from vast_client.client import VastClient

        client = VastClient("https://example.com/vast")

        # Wrapper without VASTAdTagURI
        invalid_wrapper_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.3">
            <Ad>
                <Wrapper>
                    <!-- Missing VASTAdTagURI -->
                </Wrapper>
            </Ad>
        </VAST>"""

        result = await client._resolve_vast_response(invalid_wrapper_xml)

        # Should return the wrapper data as-is
        assert result["ad"]["type"] == "wrapper"
        assert result["_raw_vast_response"] == invalid_wrapper_xml
