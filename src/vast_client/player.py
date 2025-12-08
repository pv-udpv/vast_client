"""VAST ad player for handling playback and progress tracking."""

import asyncio
import time
from typing import TYPE_CHECKING, Any

from ..events import VastEvents
from ..log_config import (
    get_context_logger,
    set_playback_context,
    update_playback_progress,
)

if TYPE_CHECKING:
    from .client import VastClient


class VastPlayer:
    """Handles VAST ad playback and progress tracking."""

    def __init__(self, vast_client: "VastClient", ad_data: dict[str, Any]):
        """Initialize VAST player.

        Args:
            vast_client: VastClient instance
            ad_data: Parsed VAST ad data
        """
        self.vast_client = vast_client
        self.ad_data = ad_data
        self.is_playing = False

        # Extract creative context
        self.creative_id = self._extract_creative_id(ad_data)
        self.creative_duration = ad_data.get("duration", 0)

        # Progress tracking
        self.playback_start_time = None
        self.current_quartile = 0  # 0=start, 1=25%, 2=50%, 3=75%, 4=100%
        self.quartile_tracked = {0: False, 1: False, 2: False, 3: False, 4: False}

        # Use contextual logger
        self.logger = get_context_logger("vast_player")

        # Set playback context
        set_playback_context(
            creative_id=self.creative_id,
            creative_duration=self.creative_duration,
            playback_seconds=0,
            progress_quartile=0.0,
            progress_percent=0.0,
            vast_event="player_init",
        )

        self.logger.info(VastEvents.PLAYER_INITIALIZED)

    def _extract_creative_id(self, ad_data: dict[str, Any]) -> str:
        """Extract creative ID from various sources in ad_data.

        Args:
            ad_data: Parsed VAST ad data

        Returns:
            Creative ID or 'unknown' if not found
        """
        creative = ad_data.get("creative", {})
        if isinstance(creative, dict):
            return creative.get("id") or creative.get("ad_id") or "unknown"
        return "unknown"

    def _calculate_quartile(self, current_time: int) -> tuple[int, float]:
        """Calculate current quartile and return number and percentage.

        Args:
            current_time: Current playback time in seconds

        Returns:
            Tuple of (quartile_number, percentage)
        """
        if self.creative_duration <= 0:
            return 0, 0.0

        progress = current_time / self.creative_duration
        if progress >= 1.0:
            return 4, 100.0
        elif progress >= 0.75:
            return 3, 75.0
        elif progress >= 0.5:
            return 2, 50.0
        elif progress >= 0.25:
            return 1, 25.0
        else:
            return 0, round(progress * 100, 1)

    async def play(self):
        """Start ad playback with progress tracking."""
        self.is_playing = True
        self.playback_start_time = time.time()

        # Update context for playback start
        update_playback_progress(
            playback_seconds=0,
            progress_quartile=0.0,
            progress_percent=0.0,
            vast_event="playback_start",
        )

        self.logger.info(VastEvents.PLAYBACK_STARTED)

        await self.vast_client.tracker.track_event("impression")
        await self.vast_client.tracker.track_event("start")
        await self.vast_client.tracker.track_event("creativeView")

        if self.creative_duration == 0:
            update_playback_progress(
                playback_seconds=0,
                progress_quartile=0.0,
                progress_percent=0.0,
                vast_event="playback_error",
            )
            self.logger.error(
                "Ad duration is not specified, skipping playback",
                error_reason="zero_duration",
            )
            self.is_playing = False
            return

        for i in range(self.creative_duration):
            if not self.is_playing:
                playback_seconds = (
                    int(time.time() - self.playback_start_time)
                    if self.playback_start_time
                    else i
                )
                quartile_num, quartile_float = self._calculate_quartile(i)
                progress_percent = round((i / self.creative_duration) * 100, 1)

                update_playback_progress(
                    playback_seconds=playback_seconds,
                    progress_quartile=quartile_float,
                    progress_percent=progress_percent,
                    vast_event="playback_interrupted",
                )

                self.logger.warning("Playback interrupted", interrupted_at_second=i)
                break

            await asyncio.sleep(1)
            await self._track_progress(i + 1)

        if self.is_playing:
            playback_seconds = (
                int(time.time() - self.playback_start_time)
                if self.playback_start_time
                else self.creative_duration
            )
            update_playback_progress(
                playback_seconds=playback_seconds,
                progress_quartile=100.0,
                progress_percent=100.0,
                vast_event="playback_complete",
            )

            await self.vast_client.tracker.track_event("complete")
            self.logger.info(
                "Ad playback completed", total_duration=self.creative_duration
            )
        self.is_playing = False

    async def _track_progress(self, current_time: int):
        """Track playback progress and handle quartile events.

        Args:
            current_time: Current playback time in seconds
        """
        if self.creative_duration == 0:
            return

        # Calculate real playback time and progress
        playback_seconds = (
            int(time.time() - self.playback_start_time)
            if self.playback_start_time
            else current_time
        )
        quartile_num, quartile_float = self._calculate_quartile(current_time)
        progress_percent = round((current_time / self.creative_duration) * 100, 1)

        # Update context without logging every second
        update_playback_progress(
            playback_seconds=playback_seconds,
            progress_quartile=quartile_float,
            progress_percent=progress_percent,
            vast_event="progress_update",
        )

        # Track quartiles and log only their achievement
        if (
            quartile_num > self.current_quartile
            and not self.quartile_tracked[quartile_num]
        ):
            self.current_quartile = quartile_num
            self.quartile_tracked[quartile_num] = True

            # Log only quartile achievement
            quartile_names = {1: "firstQuartile", 2: "midpoint", 3: "thirdQuartile"}
            if quartile_num in quartile_names:
                event_name = quartile_names[quartile_num]

                # Update context for quartile
                update_playback_progress(
                    playback_seconds=playback_seconds,
                    progress_quartile=quartile_float,
                    progress_percent=progress_percent,
                    vast_event=f"quartile_{quartile_num}",
                )

                self.logger.info(
                    f"Quartile reached: {quartile_float}%",
                    quartile_name=event_name,
                    quartile_reached=True,
                )

                # Send tracking event
                if event_name not in self.vast_client.tracker.tracked_events:
                    await self.vast_client.tracker.track_event(event_name)

    async def pause(self):
        """Pause ad playback."""
        if self.is_playing:
            self.is_playing = False
            self._pause_start_time = time.time()  # Remember when paused

            playback_seconds = (
                int(time.time() - self.playback_start_time)
                if self.playback_start_time
                else 0
            )
            quartile_num, quartile_float = self._calculate_quartile(playback_seconds)
            progress_percent = (
                round((playback_seconds / self.creative_duration) * 100, 1)
                if self.creative_duration > 0
                else 0.0
            )

            update_playback_progress(
                playback_seconds=playback_seconds,
                progress_quartile=quartile_float,
                progress_percent=progress_percent,
                vast_event="playback_pause",
            )

            await self.vast_client.tracker.track_event("pause")
            self.logger.info("Ad playback paused")

    async def resume(self):
        """Resume ad playback."""
        if not self.is_playing:
            self.is_playing = True

            # Update start time accounting for pause duration
            if (
                hasattr(self, "_pause_start_time")
                and self._pause_start_time
                and self.playback_start_time is not None
            ):
                pause_duration = time.time() - self._pause_start_time
                self.playback_start_time += pause_duration
                self._pause_start_time = None

            playback_seconds = (
                int(time.time() - self.playback_start_time)
                if self.playback_start_time
                else 0
            )
            quartile_num, quartile_float = self._calculate_quartile(playback_seconds)
            progress_percent = (
                round((playback_seconds / self.creative_duration) * 100, 1)
                if self.creative_duration > 0
                else 0.0
            )

            update_playback_progress(
                playback_seconds=playback_seconds,
                progress_quartile=quartile_float,
                progress_percent=progress_percent,
                vast_event="playback_resume",
            )

            await self.vast_client.tracker.track_event("resume")
            self.logger.info("Ad playback resumed")

    async def stop(self):
        """Stop ad playback."""
        if self.is_playing:
            self.is_playing = False
            playback_seconds = (
                int(time.time() - self.playback_start_time)
                if self.playback_start_time
                else 0
            )
            quartile_num, quartile_float = self._calculate_quartile(playback_seconds)
            progress_percent = (
                round((playback_seconds / self.creative_duration) * 100, 1)
                if self.creative_duration > 0
                else 0.0
            )

            update_playback_progress(
                playback_seconds=playback_seconds,
                progress_quartile=quartile_float,
                progress_percent=progress_percent,
                vast_event="playback_stop",
            )

            await self.vast_client.tracker.track_event("close")
            self.logger.info("Ad playback stopped", stopped_early=True)


__all__ = ["VastPlayer"]
