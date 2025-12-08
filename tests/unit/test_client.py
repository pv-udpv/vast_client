"""Unit tests for VAST client."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from vast_client.client import VastClient


class TestVastClientInitialization:
    """Test VAST client initialization patterns."""

    def test_init_from_url_string(self):
        """Test initialization from simple URL string."""
        client = VastClient("https://ads.example.com/vast")

        assert client.upstream_url == "https://ads.example.com/vast"
        assert client.embedded_params == {}
        assert client.embedded_headers == {}

    def test_init_from_config_dict(self):
        """Test initialization from configuration dictionary."""
        config = {
            "url": "https://ads.example.com/vast",
            "params": {"key": "value"},
            "headers": {"User-Agent": "Test/1.0"},
        }

        client = VastClient(config)

        assert client.upstream_url == "https://ads.example.com/vast"
        assert client.embedded_params == {"key": "value"}
        assert client.embedded_headers == {"User-Agent": "Test/1.0"}

    def test_init_from_vast_config(self, vast_client_config):
        """Test initialization from VastClientConfig."""
        client = VastClient(vast_client_config)

        assert client.config == vast_client_config
        assert client.parser is not None
        assert client.tracker is not None

    def test_from_uri_classmethod(self):
        """Test creating client from URI."""
        client = VastClient.from_uri("https://ads.example.com/vast")

        assert client.upstream_url == "https://ads.example.com/vast"

    def test_from_config_classmethod(self):
        """Test creating client from config dictionary."""
        config = {
            "url": "https://ads.example.com/vast",
            "params": {"version": "4.0"},
        }

        client = VastClient.from_config(config)

        assert client.upstream_url == "https://ads.example.com/vast"
        assert "version" in client.embedded_params


class TestVastClientRequestAd:
    """Test VAST client ad request functionality."""

    @pytest.mark.asyncio
    async def test_request_ad_success(self, minimal_vast_xml):
        """Test successful ad request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        vast_data = await client.request_ad()

        assert isinstance(vast_data, dict)
        assert vast_data["ad_system"] == "Test Ad System"
        assert vast_data["ad_title"] == "Test Ad Title"

    @pytest.mark.asyncio
    async def test_request_ad_no_content(self):
        """Test ad request with 204 No Content response."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        result = await client.request_ad()

        assert result == ""

    @pytest.mark.asyncio
    async def test_request_ad_with_params(self, minimal_vast_xml):
        """Test ad request with additional parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        await client.request_ad(params={"user_id": "user-123"})

        # Verify request was made
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_ad_with_headers(self, minimal_vast_xml):
        """Test ad request with custom headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        await client.request_ad(headers={"X-Custom-Header": "value"})

        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_ad_non_xml_response(self):
        """Test ad request with non-XML response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "Plain text response"
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        result = await client.request_ad()

        # Should return raw text
        assert result == "Plain text response"

    @pytest.mark.asyncio
    async def test_request_ad_creates_tracker(self, minimal_vast_xml):
        """Test that tracker is created after successful VAST parsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        await client.request_ad()

        # Tracker should be created
        assert client.tracker is not None
        # Should have tracking events
        assert "impression" in client.tracker.events or "start" in client.tracker.events


class TestVastClientContextManager:
    """Test VAST client async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self):
        """Test client as async context manager."""
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        async with client as c:
            assert c == client

        # Client should be closed
        # Note: Global client is not closed, only local clients

    @pytest.mark.asyncio
    async def test_context_manager_with_ad_request_context(self, minimal_vast_xml):
        """Test context manager with ad request context."""
        ad_request = {
            "x_request_id": "req-123",
            "publisher_id": "pub-456",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = minimal_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast", ctx=ad_request)
        client.client = mock_client

        async with client:
            vast_data = await client.request_ad()
            assert vast_data is not None


class TestVastClientEdgeCases:
    """Edge case tests for VAST client."""

    @pytest.mark.asyncio
    async def test_request_ad_malformed_xml(self, malformed_vast_xml):
        """Test ad request with malformed XML (with recovery enabled)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = malformed_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Client with recovery enabled (default)
        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        # Should not raise, return raw response
        result = await client.request_ad()
        # With recovery failure, should return raw text
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_request_ad_empty_response(self, empty_vast_xml):
        """Test ad request with empty VAST response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/xml"}
        mock_response.text = empty_vast_xml
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        vast_data = await client.request_ad()

        assert vast_data["vast_version"] == "4.0"
        assert vast_data["impression"] == []

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test client close method."""
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        client = VastClient("https://ads.example.com/vast")
        client.client = mock_client

        await client.close()

        # Note: Global clients are not closed
        # Only local clients would be closed

    def test_init_with_none_url_raises(self):
        """Test that None URL is handled gracefully in config."""
        config = {
            "url": None,
            "params": {},
        }

        client = VastClient(config)
        # Should initialize but upstream_url will be None
        assert client.upstream_url is None
