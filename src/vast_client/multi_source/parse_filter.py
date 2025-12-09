"""
VAST Parse Filter

Filtering logic for selective VAST parsing based on media types, duration,
and other criteria.
"""

from dataclasses import dataclass, field
from typing import Any

from .fetch_config import MediaType


@dataclass
class VastParseFilter:
    """
    Filter for selective VAST parsing.

    Allows filtering of VAST responses based on various criteria such as
    media type, duration, bitrate, and dimensions.

    Attributes:
        media_types: List of acceptable media types (video, audio, all)
        min_duration: Minimum acceptable ad duration in seconds (None = no min)
        max_duration: Maximum acceptable ad duration in seconds (None = no max)
        min_bitrate: Minimum bitrate in kbps (None = no min)
        max_bitrate: Maximum bitrate in kbps (None = no max)
        required_dimensions: Required video dimensions as (width, height) tuple
        accept_wrappers: Whether to accept VAST wrapper ads
        max_wrapper_depth: Maximum wrapper chain depth to follow

    Examples:
        Video-only filter with duration constraints:
        >>> filter = VastParseFilter(
        ...     media_types=[MediaType.VIDEO],
        ...     min_duration=15,
        ...     max_duration=30
        ... )

        High-quality video filter:
        >>> filter = VastParseFilter(
        ...     media_types=[MediaType.VIDEO],
        ...     min_bitrate=2000,
        ...     required_dimensions=(1920, 1080)
        ... )
    """

    media_types: list[MediaType] = field(default_factory=lambda: [MediaType.ALL])
    min_duration: int | None = None
    max_duration: int | None = None
    min_bitrate: int | None = None
    max_bitrate: int | None = None
    required_dimensions: tuple[int, int] | None = None
    accept_wrappers: bool = True
    max_wrapper_depth: int = 5

    def matches(self, vast_data: dict[str, Any]) -> bool:
        """
        Check if parsed VAST data matches filter criteria.

        Args:
            vast_data: Parsed VAST data dictionary

        Returns:
            bool: True if data matches all filter criteria, False otherwise
        """
        # Check duration
        if self.min_duration is not None or self.max_duration is not None:
            duration = vast_data.get("duration", 0)
            if self.min_duration is not None and duration < self.min_duration:
                return False
            if self.max_duration is not None and duration > self.max_duration:
                return False

        # Check media type
        if MediaType.ALL not in self.media_types:
            media_files = vast_data.get("media_files", [])
            if not media_files:
                return False

            # Check if any media file matches the allowed types
            media_type_match = False
            for media_file in media_files:
                file_type = media_file.get("type", "")
                if MediaType.VIDEO in self.media_types and file_type.startswith("video/"):
                    media_type_match = True
                    break
                if MediaType.AUDIO in self.media_types and file_type.startswith("audio/"):
                    media_type_match = True
                    break

            if not media_type_match:
                return False

        # Check bitrate (if specified and available in media files)
        if self.min_bitrate is not None or self.max_bitrate is not None:
            media_files = vast_data.get("media_files", [])
            if media_files:
                # Check first media file's bitrate
                bitrate = media_files[0].get("bitrate")
                if bitrate is not None:
                    try:
                        bitrate_int = int(bitrate)
                        if self.min_bitrate is not None and bitrate_int < self.min_bitrate:
                            return False
                        if self.max_bitrate is not None and bitrate_int > self.max_bitrate:
                            return False
                    except (ValueError, TypeError):
                        # Skip validation if bitrate is not a valid integer
                        pass

        # Check dimensions (if specified and available)
        if self.required_dimensions is not None:
            media_files = vast_data.get("media_files", [])
            if media_files:
                width = media_files[0].get("width")
                height = media_files[0].get("height")
                if width is not None and height is not None:
                    try:
                        width_int = int(width)
                        height_int = int(height)
                        required_width, required_height = self.required_dimensions
                        if width_int != required_width or height_int != required_height:
                            return False
                    except (ValueError, TypeError):
                        # Skip validation if dimensions are not valid integers
                        pass

        return True


__all__ = ["VastParseFilter"]
