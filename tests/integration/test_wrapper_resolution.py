"""Integration tests for VAST wrapper resolution.

Tests the full wrapper chain resolution workflow according to IAB VAST 4.0 spec:
- Wrapper → Inline resolution
- Multiple wrapper chains (depth 2-5)
- Max depth enforcement (5 wrappers)
- followAdditionalWrappers attribute handling
- Tracking event aggregation
- Error handling (timeout, circular refs, max depth)

References:
- VAST 4.0 Spec: https://www.iab.com/wp-content/uploads/2016/04/VAST4.0_Updated_April_2016.pdf
- IAB VAST Samples: https://github.com/InteractiveAdvertisingBureau/VAST_Samples
"""

import asyncio
from pathlib import Path
from typing import Dict, List
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from lxml import etree

from vast_client.client import VastClient
from vast_client.config import VastParserConfig
from vast_client.parser import VastParser


class VastWrapperError(Exception):
    """Base exception for VAST wrapper errors."""
    pass


class WrapperDepthExceededError(VastWrapperError):
    """Raised when wrapper chain exceeds maximum depth (VAST error 302)."""
    pass


class WrapperTimeoutError(VastWrapperError):
    """Raised when wrapper resolution times out (VAST error 301)."""
    pass


class CircularReferenceError(VastWrapperError):
    """Raised when wrapper chain contains circular references."""
    pass


class VastWrapperResolver:
    """Resolves VAST wrapper chains to final inline ads.
    
    Implements IAB VAST 4.0 wrapper resolution specification:
    - Maximum depth: 5 wrappers
    - Respects followAdditionalWrappers attribute
    - Aggregates tracking events from all wrappers
    - Detects circular references
    - Enforces timeouts
    """
    
    MAX_WRAPPER_DEPTH = 5  # VAST 4.0 specification
    DEFAULT_TIMEOUT = 30.0  # seconds
    
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        parser: VastParser,
        max_depth: int = MAX_WRAPPER_DEPTH,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.http_client = http_client
        self.parser = parser
        self.max_depth = max_depth
        self.timeout = timeout
        
    async def resolve(self, vast_xml: str) -> Dict:
        """Resolve VAST wrapper chain to final inline ad.
        
        Args:
            vast_xml: Initial VAST XML (may be wrapper or inline)
            
        Returns:
            dict: Resolved VAST data with aggregated tracking events
            
        Raises:
            WrapperDepthExceededError: If chain exceeds max depth
            WrapperTimeoutError: If resolution times out
            CircularReferenceError: If circular reference detected
        """
        visited_urls: List[str] = []
        wrapper_chain: List[Dict] = []
        current_xml = vast_xml
        depth = 0
        
        try:
            async with asyncio.timeout(self.timeout):
                while depth < self.max_depth:
                    vast_data = self.parser.parse_vast(current_xml)
                    
                    # Check if this is a wrapper or inline ad
                    if not self._is_wrapper(vast_data):
                        # Inline ad found - aggregate all tracking events
                        return self._aggregate_tracking_events(wrapper_chain, vast_data)
                    
                    # It's a wrapper - check followAdditionalWrappers
                    if not self._should_follow_wrappers(vast_data):
                        raise VastWrapperError("Wrapper has followAdditionalWrappers=0")
                    
                    # Extract next VAST URL
                    vast_uri = self._extract_vast_uri(vast_data)
                    if not vast_uri:
                        raise VastWrapperError("Wrapper missing VASTAdTagURI")
                    
                    # Check for circular reference
                    if vast_uri in visited_urls:
                        raise CircularReferenceError(
                            f"Circular reference detected: {vast_uri}"
                        )
                    
                    visited_urls.append(vast_uri)
                    wrapper_chain.append(vast_data)
                    
                    # Fetch next VAST document
                    response = await self.http_client.get(vast_uri)
                    response.raise_for_status()
                    current_xml = response.text
                    
                    depth += 1
                
                # Max depth exceeded
                raise WrapperDepthExceededError(
                    f"Wrapper chain exceeded maximum depth of {self.max_depth}"
                )
                
        except asyncio.TimeoutError:
            raise WrapperTimeoutError(
                f"Wrapper resolution timed out after {self.timeout}s"
            )
    
    def _is_wrapper(self, vast_data: Dict) -> bool:
        """Check if VAST data represents a wrapper ad."""
        return vast_data.get("ad_type") == "wrapper" or "vast_uri" in vast_data
    
    def _should_follow_wrappers(self, vast_data: Dict) -> bool:
        """Check if followAdditionalWrappers allows continuing."""
        # Default is true if not specified
        return vast_data.get("follow_additional_wrappers", True)
    
    def _extract_vast_uri(self, vast_data: Dict) -> str | None:
        """Extract VASTAdTagURI from wrapper."""
        return vast_data.get("vast_uri")
    
    def _aggregate_tracking_events(self, wrapper_chain: List[Dict], inline_ad: Dict) -> Dict:
        """Aggregate tracking events from all wrappers and inline ad.
        
        VAST spec: Tracking events from wrappers should be fired alongside
        inline ad tracking events.
        """
        aggregated = inline_ad.copy()
        aggregated_events = dict(inline_ad.get("tracking_events", {}))
        
        # Aggregate tracking events from each wrapper (order matters)
        for wrapper in wrapper_chain:
            wrapper_events = wrapper.get("tracking_events", {})
            for event_type, urls in wrapper_events.items():
                if event_type not in aggregated_events:
                    aggregated_events[event_type] = []
                # Convert single URL to list if needed
                if isinstance(urls, str):
                    urls = [urls]
                aggregated_events[event_type].extend(urls)
        
        aggregated["tracking_events"] = aggregated_events
        aggregated["wrapper_count"] = len(wrapper_chain)
        
        return aggregated


class TestVastWrapperResolution:
    """Test VAST wrapper resolution functionality."""
    
    @pytest.fixture
    def parser(self) -> VastParser:
        """Create parser with recovery enabled."""
        config = VastParserConfig(recover_on_error=True)
        return VastParser(config=config)
    
    @pytest.fixture
    def mock_http_client(self) -> AsyncMock:
        """Create mock HTTP client for testing."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client
    
    @pytest.fixture
    def iab_samples_path(self) -> Path:
        """Get path to IAB samples directory."""
        return Path(__file__).parent.parent / "iab_samples" / "VAST 4.0 Samples"
    
    @pytest.fixture
    def wrapper_xml(self, iab_samples_path: Path) -> str:
        """Load IAB wrapper sample."""
        wrapper_file = iab_samples_path / "Wrapper_Tag-test.xml"
        return wrapper_file.read_text()
    
    @pytest.fixture
    def inline_xml(self, iab_samples_path: Path) -> str:
        """Load IAB inline sample."""
        inline_file = iab_samples_path / "Inline_Companion_Tag-test.xml"
        return inline_file.read_text()
    
    @pytest.fixture
    def resolver(self, mock_http_client, parser) -> VastWrapperResolver:
        """Create wrapper resolver with mock client."""
        return VastWrapperResolver(mock_http_client, parser)
    
    @pytest.mark.asyncio
    async def test_simple_wrapper_to_inline(self, resolver, mock_http_client, wrapper_xml, inline_xml):
        """Test basic wrapper → inline resolution."""
        # Mock HTTP response for inline ad
        mock_response = Mock()
        mock_response.text = inline_xml
        mock_response.raise_for_status = Mock()
        mock_http_client.get.return_value = mock_response
        
        # Resolve wrapper
        result = await resolver.resolve(wrapper_xml)
        
        # Verify resolution
        assert result["vast_version"] == "4.0"
        assert result["ad_system"] == "iabtechlab"
        assert result["wrapper_count"] == 1
        assert "tracking_events" in result
        
        # Verify HTTP request was made
        mock_http_client.get.assert_called_once()
        call_url = mock_http_client.get.call_args[0][0]
        assert "Inline_Companion_Tag-test.xml" in call_url
    
    @pytest.mark.asyncio
    async def test_inline_ad_no_resolution(self, resolver, inline_xml):
        """Test that inline ads don't require resolution."""
        result = await resolver.resolve(inline_xml)
        
        assert result["vast_version"] == "4.0"
        assert result.get("wrapper_count", 0) == 0
    
    @pytest.mark.asyncio
    async def test_wrapper_chain_depth_2(self, resolver, mock_http_client, parser):
        """Test wrapper → wrapper → inline chain."""
        # Create wrapper chain
        wrapper1_xml = self._create_wrapper_xml("http://example.com/wrapper2")
        wrapper2_xml = self._create_wrapper_xml("http://example.com/inline")
        inline_xml = self._create_inline_xml()
        
        # Mock HTTP responses
        responses = [wrapper2_xml, inline_xml]
        mock_http_client.get.side_effect = [
            self._mock_response(xml) for xml in responses
        ]
        
        result = await resolver.resolve(wrapper1_xml)
        
        assert result["wrapper_count"] == 2
        assert mock_http_client.get.call_count == 2
    
    @pytest.mark.asyncio
    async def test_max_wrapper_depth_exceeded(self, resolver, mock_http_client):
        """Test that max wrapper depth (5) is enforced."""
        # Create chain of 6 wrappers (exceeds limit)
        wrapper_xml = self._create_wrapper_xml("http://example.com/next")
        
        # Mock always returns another wrapper
        mock_http_client.get.return_value = self._mock_response(wrapper_xml)
        
        with pytest.raises(WrapperDepthExceededError) as exc_info:
            await resolver.resolve(wrapper_xml)
        
        assert "exceeded maximum depth of 5" in str(exc_info.value)
        assert mock_http_client.get.call_count == 5
    
    @pytest.mark.asyncio
    async def test_follow_additional_wrappers_false(self, resolver):
        """Test followAdditionalWrappers=0 stops resolution."""
        wrapper_xml = self._create_wrapper_xml(
            "http://example.com/next",
            follow_additional_wrappers=False
        )
        
        with pytest.raises(VastWrapperError) as exc_info:
            await resolver.resolve(wrapper_xml)
        
        assert "followAdditionalWrappers=0" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_circular_reference_detection(self, resolver, mock_http_client):
        """Test circular reference is detected and raises error."""
        wrapper1_xml = self._create_wrapper_xml("http://example.com/wrapper2")
        wrapper2_xml = self._create_wrapper_xml("http://example.com/wrapper1")  # Circular!
        
        mock_http_client.get.side_effect = [
            self._mock_response(wrapper2_xml),
            self._mock_response(wrapper1_xml),
        ]
        
        with pytest.raises(CircularReferenceError) as exc_info:
            await resolver.resolve(wrapper1_xml)
        
        assert "Circular reference detected" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_wrapper_timeout(self, mock_http_client, parser):
        """Test wrapper resolution timeout."""
        resolver = VastWrapperResolver(mock_http_client, parser, timeout=0.1)
        
        # Mock slow response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(1.0)  # Longer than timeout
            return self._mock_response(self._create_inline_xml())
        
        mock_http_client.get.side_effect = slow_response
        wrapper_xml = self._create_wrapper_xml("http://example.com/slow")
        
        with pytest.raises(WrapperTimeoutError) as exc_info:
            await resolver.resolve(wrapper_xml)
        
        assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_wrapper_missing_vast_uri(self, resolver):
        """Test wrapper without VASTAdTagURI raises error."""
        wrapper_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0">
          <Ad id="123">
            <Wrapper>
              <AdSystem>Test</AdSystem>
              <!-- Missing VASTAdTagURI -->
            </Wrapper>
          </Ad>
        </VAST>"""
        
        with pytest.raises(VastWrapperError) as exc_info:
            await resolver.resolve(wrapper_xml)
        
        assert "missing VASTAdTagURI" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_tracking_event_aggregation(self, resolver, mock_http_client):
        """Test tracking events are aggregated from wrapper + inline."""
        # Wrapper with impression tracking
        wrapper_xml = self._create_wrapper_xml(
            "http://example.com/inline",
            tracking_events={
                "impression": ["http://wrapper.com/impression"],
                "start": ["http://wrapper.com/start"],
            }
        )
        
        # Inline with its own tracking
        inline_xml = self._create_inline_xml(
            tracking_events={
                "start": ["http://inline.com/start"],
                "complete": ["http://inline.com/complete"],
            }
        )
        
        mock_http_client.get.return_value = self._mock_response(inline_xml)
        
        result = await resolver.resolve(wrapper_xml)
        
        # Verify aggregation
        assert "impression" in result["tracking_events"]
        assert "http://wrapper.com/impression" in result["tracking_events"]["impression"]
        
        # Start event should have both wrapper and inline URLs
        assert len(result["tracking_events"]["start"]) == 2
        assert "http://wrapper.com/start" in result["tracking_events"]["start"]
        assert "http://inline.com/start" in result["tracking_events"]["start"]
        
        # Complete only from inline
        assert "http://inline.com/complete" in result["tracking_events"]["complete"]
    
    @pytest.mark.asyncio
    async def test_multiple_impressions_aggregation(self, resolver, mock_http_client):
        """Test impression URLs from wrapper and inline are combined."""
        wrapper_xml = self._create_wrapper_xml(
            "http://example.com/inline",
            impressions=["http://wrapper.com/impression1", "http://wrapper.com/impression2"]
        )
        
        inline_xml = self._create_inline_xml(
            impressions=["http://inline.com/impression"]
        )
        
        mock_http_client.get.return_value = self._mock_response(inline_xml)
        
        result = await resolver.resolve(wrapper_xml)
        
        # Should have 3 total impressions
        assert len(result["impression"]) == 3
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, resolver, mock_http_client):
        """Test HTTP errors during wrapper resolution."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=Mock(status_code=404)
        )
        mock_http_client.get.return_value = mock_response
        
        wrapper_xml = self._create_wrapper_xml("http://example.com/missing")
        
        with pytest.raises(httpx.HTTPStatusError):
            await resolver.resolve(wrapper_xml)
    
    # Helper methods for creating test VAST XML
    
    def _create_wrapper_xml(
        self,
        vast_uri: str,
        follow_additional_wrappers: bool = True,
        tracking_events: Dict[str, List[str]] = None,
        impressions: List[str] = None,
    ) -> str:
        """Create wrapper VAST XML for testing."""
        tracking_events = tracking_events or {}
        impressions = impressions or []
        
        tracking_xml = ""
        for event, urls in tracking_events.items():
            for url in urls:
                tracking_xml += f'<Tracking event="{event}"><![CDATA[{url}]]></Tracking>\n'
        
        impression_xml = ""
        for imp_url in impressions:
            impression_xml += f'<Impression><![CDATA[{imp_url}]]></Impression>\n'
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0">
          <Ad id="wrapper-123">
            <Wrapper followAdditionalWrappers="{1 if follow_additional_wrappers else 0}">
              <AdSystem>Test Wrapper</AdSystem>
              {impression_xml}
              <VASTAdTagURI><![CDATA[{vast_uri}]]></VASTAdTagURI>
              <Creatives>
                <Creative>
                  <Linear>
                    <TrackingEvents>
                      {tracking_xml}
                    </TrackingEvents>
                  </Linear>
                </Creative>
              </Creatives>
            </Wrapper>
          </Ad>
        </VAST>"""
    
    def _create_inline_xml(
        self,
        tracking_events: Dict[str, List[str]] = None,
        impressions: List[str] = None,
    ) -> str:
        """Create inline VAST XML for testing."""
        tracking_events = tracking_events or {"start": ["http://inline.com/start"]}
        impressions = impressions or ["http://inline.com/impression"]
        
        tracking_xml = ""
        for event, urls in tracking_events.items():
            for url in urls:
                tracking_xml += f'<Tracking event="{event}"><![CDATA[{url}]]></Tracking>\n'
        
        impression_xml = ""
        for imp_url in impressions:
            impression_xml += f'<Impression><![CDATA[{imp_url}]]></Impression>\n'
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <VAST version="4.0">
          <Ad id="inline-456">
            <InLine>
              <AdSystem>Test Inline</AdSystem>
              {impression_xml}
              <AdTitle>Test Ad</AdTitle>
              <Creatives>
                <Creative>
                  <Linear>
                    <Duration>00:00:30</Duration>
                    <TrackingEvents>
                      {tracking_xml}
                    </TrackingEvents>
                    <MediaFiles>
                      <MediaFile delivery="progressive" type="video/mp4">
                        <![CDATA[http://example.com/video.mp4]]>
                      </MediaFile>
                    </MediaFiles>
                  </Linear>
                </Creative>
              </Creatives>
            </InLine>
          </Ad>
        </VAST>"""
    
    def _mock_response(self, xml_text: str) -> Mock:
        """Create mock HTTP response with XML text."""
        response = Mock()
        response.text = xml_text
        response.raise_for_status = Mock()
        return response


class TestVastWrapperResolutionWithRealSamples:
    """Test wrapper resolution with actual IAB sample files."""
    
    @pytest.fixture
    def iab_samples_path(self) -> Path:
        """Get path to IAB samples directory."""
        return Path(__file__).parent.parent / "iab_samples" / "VAST 4.0 Samples"
    
    @pytest.mark.asyncio
    async def test_parse_wrapper_extract_vast_uri(self, iab_samples_path):
        """Test parsing wrapper to extract VASTAdTagURI."""
        wrapper_file = iab_samples_path / "Wrapper_Tag-test.xml"
        wrapper_xml = wrapper_file.read_text()
        
        parser = VastParser()
        
        # Parse wrapper - need to enhance parser to extract wrapper-specific fields
        root = etree.fromstring(wrapper_xml.encode())
        
        # Extract VASTAdTagURI
        vast_uri_elem = root.find(".//VASTAdTagURI")
        assert vast_uri_elem is not None
        vast_uri = vast_uri_elem.text.strip()
        
        # Verify it points to the correct inline ad
        assert "Inline_Companion_Tag-test.xml" in vast_uri
        assert "raw.githubusercontent.com" in vast_uri
    
    @pytest.mark.asyncio
    async def test_parse_wrapper_attributes(self, iab_samples_path):
        """Test parsing wrapper attributes (followAdditionalWrappers, etc)."""
        wrapper_file = iab_samples_path / "Wrapper_Tag-test.xml"
        wrapper_xml = wrapper_file.read_text()
        
        root = etree.fromstring(wrapper_xml.encode())
        wrapper_elem = root.find(".//Wrapper")
        
        assert wrapper_elem is not None
        
        # Check attributes
        follow_wrappers = wrapper_elem.get("followAdditionalWrappers")
        allow_multiple = wrapper_elem.get("allowMultipleAds")
        fallback = wrapper_elem.get("fallbackOnNoAd")
        
        assert follow_wrappers == "0"  # This wrapper doesn't follow additional
        assert allow_multiple == "1"
        assert fallback == "0"
    
    def test_wrapper_and_inline_relationship(self, iab_samples_path):
        """Document the relationship between wrapper and inline samples."""
        wrapper_file = iab_samples_path / "Wrapper_Tag-test.xml"
        inline_file = iab_samples_path / "Inline_Companion_Tag-test.xml"
        
        # Both files should exist
        assert wrapper_file.exists(), "Wrapper sample not found"
        assert inline_file.exists(), "Inline sample not found"
        
        # Parse wrapper to verify relationship
        wrapper_xml = wrapper_file.read_text()
        root = etree.fromstring(wrapper_xml.encode())
        vast_uri = root.find(".//VASTAdTagURI").text.strip()
        
        # Should reference the inline companion ad
        assert "Inline_Companion_Tag-test.xml" in vast_uri
        
        # Parse inline ad to verify it's a valid target
        inline_xml = inline_file.read_text()
        inline_root = etree.fromstring(inline_xml.encode())
        inline_ad = inline_root.find(".//InLine")
        
        assert inline_ad is not None, "Target is not an InLine ad"
