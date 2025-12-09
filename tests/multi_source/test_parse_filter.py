"""Tests for VAST parse filter."""

import pytest

from vast_client.multi_source import VastParseFilter, MediaType


class TestVastParseFilter:
    """Test VastParseFilter functionality."""

    def test_default_filter(self):
        """Test default parse filter."""
        filter = VastParseFilter()

        assert filter.media_types == [MediaType.ALL]
        assert filter.min_duration is None
        assert filter.max_duration is None
        assert filter.accept_wrappers is True

    def test_video_only_filter(self):
        """Test video-only filter."""
        filter = VastParseFilter(media_types=[MediaType.VIDEO])

        assert MediaType.VIDEO in filter.media_types
        assert MediaType.AUDIO not in filter.media_types

    def test_duration_filter(self):
        """Test filter with duration constraints."""
        filter = VastParseFilter(min_duration=15, max_duration=30)

        assert filter.min_duration == 15
        assert filter.max_duration == 30

    def test_matches_duration_valid(self):
        """Test filter matches valid duration."""
        filter = VastParseFilter(min_duration=10, max_duration=60)
        vast_data = {"duration": 30}

        assert filter.matches(vast_data) is True

    def test_matches_duration_too_short(self):
        """Test filter rejects too short duration."""
        filter = VastParseFilter(min_duration=20, max_duration=60)
        vast_data = {"duration": 10}

        assert filter.matches(vast_data) is False

    def test_matches_duration_too_long(self):
        """Test filter rejects too long duration."""
        filter = VastParseFilter(min_duration=10, max_duration=30)
        vast_data = {"duration": 45}

        assert filter.matches(vast_data) is False

    def test_matches_media_type_video(self):
        """Test filter matches video media type."""
        filter = VastParseFilter(media_types=[MediaType.VIDEO])
        vast_data = {
            "media_files": [{"type": "video/mp4"}],
        }

        assert filter.matches(vast_data) is True

    def test_matches_media_type_audio_rejected(self):
        """Test filter rejects audio when only video allowed."""
        filter = VastParseFilter(media_types=[MediaType.VIDEO])
        vast_data = {
            "media_files": [{"type": "audio/mp3"}],
        }

        assert filter.matches(vast_data) is False

    def test_matches_media_type_all(self):
        """Test filter with ALL media type."""
        filter = VastParseFilter(media_types=[MediaType.ALL])
        vast_data = {
            "media_files": [{"type": "video/mp4"}],
        }

        assert filter.matches(vast_data) is True

    def test_matches_no_media_files(self):
        """Test filter with no media files."""
        filter = VastParseFilter(media_types=[MediaType.VIDEO])
        vast_data = {"media_files": []}

        assert filter.matches(vast_data) is False

    def test_matches_bitrate_valid(self):
        """Test filter matches valid bitrate."""
        filter = VastParseFilter(min_bitrate=1000, max_bitrate=5000)
        vast_data = {
            "media_files": [{"bitrate": "2000"}],
        }

        assert filter.matches(vast_data) is True

    def test_matches_bitrate_too_low(self):
        """Test filter rejects low bitrate."""
        filter = VastParseFilter(min_bitrate=2000)
        vast_data = {
            "media_files": [{"bitrate": "1000"}],
        }

        assert filter.matches(vast_data) is False

    def test_matches_dimensions_valid(self):
        """Test filter matches valid dimensions."""
        filter = VastParseFilter(required_dimensions=(1920, 1080))
        vast_data = {
            "media_files": [{"width": "1920", "height": "1080"}],
        }

        assert filter.matches(vast_data) is True

    def test_matches_dimensions_invalid(self):
        """Test filter rejects invalid dimensions."""
        filter = VastParseFilter(required_dimensions=(1920, 1080))
        vast_data = {
            "media_files": [{"width": "1280", "height": "720"}],
        }

        assert filter.matches(vast_data) is False

    def test_matches_complex_filter(self):
        """Test complex filter with multiple criteria."""
        filter = VastParseFilter(
            media_types=[MediaType.VIDEO],
            min_duration=15,
            max_duration=30,
            min_bitrate=1000,
        )

        valid_data = {
            "duration": 20,
            "media_files": [{"type": "video/mp4", "bitrate": "2000"}],
        }

        invalid_data = {
            "duration": 10,  # Too short
            "media_files": [{"type": "video/mp4", "bitrate": "2000"}],
        }

        assert filter.matches(valid_data) is True
        assert filter.matches(invalid_data) is False
