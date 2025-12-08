"""
Base VAST Player

Abstract base class defining the playback interface for both real-time and
simulated (headless) ad playback. Implements Template Method pattern with
shared logic and abstract methods for implementation-specific behavior.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from .log_config import (
    get_context_logger,
    set_playback_context,
    update_playback_progress,
)
from .config import PlaybackSessionConfig
from .playback_session import (
    PlaybackSession,
    PlaybackEventType,
)
from .time_provider import TimeProvider

if TYPE_CHECKING:
    from .client import VastClient


class BaseVastPlayer(ABC):
    """
    Abstract base class for VAST ad players (real-time and headless).
    
    Defines the unified playback interface using Template Method pattern.
    Subclasses (VastPlayer, HeadlessPlayer) implement playback-specific behavior
    while sharing common logic for progress tracking, event recording, and
    session management.
    
    Architecture:
        - Template Method: play() method delegates to subclass-specific logic
        - Shared Methods: pause(), resume(), stop() work for all player types
        - Abstract Methods: _default_time_provider() for player-specific time source
        - State Management: PlaybackSession tracks all playback events
        - Lifecycle: _extract_creative_id(), _calculate_quartile() shared
    
    Usage:
        Real-time player (VastPlayer):
        >>> player = VastPlayer(vast_client, ad_data)
        >>> await player.play()  # Uses RealtimeTimeProvider
        
        Headless player (HeadlessPlayer):
        >>> config = PlaybackSessionConfig(mode=PlaybackMode.HEADLESS)
        >>> player = HeadlessPlayer(vast_client, ad_data, config)
        >>> ad_data, session = await player.play()  # Returns session with events
    """

    def __init__(
        self,
        vast_client: "VastClient",
        ad_data: dict[str, Any],
        config: PlaybackSessionConfig | None = None,
    ):
        """
        Initialize base player.

        Args:
            vast_client: VastClient instance for tracking
            ad_data: Parsed VAST ad data
            config: PlaybackSessionConfig (uses default if None)
        """
        self.vast_client = vast_client
        self.ad_data = ad_data
        self.config = config or PlaybackSessionConfig()

        # Extract creative context
        self.creative_id = self._extract_creative_id(ad_data)
        self.creative_duration = ad_data.get("duration", 0)

        # Initialize session
        self.session = PlaybackSession(
            ad_id=self.creative_id,
            duration_sec=self.creative_duration,
            metadata={"ad_data": ad_data},
        )

        # Time provider (set in subclass via setup_time_provider)
        self.time_provider: TimeProvider | None = None

        # Playback state
        self.is_playing = False
        self._pause_start_time: float | None = None

        # Use contextual logger
        self.logger = get_context_logger("vast_player")

        # Set playback context
        set_playback_context(
            creative_id=self.creative_id,
            creative_duration=self.creative_duration,
            playback_seconds=0,
            progress_quartile=0.0,
            progress_percent=0.0,
            vast_event="player_initialized",
        )

        self.logger.info(
            "Player initialized",
            player_type=self.__class__.__name__,
            creative_id=self.creative_id,
            duration=self.creative_duration,
        )

    # ===== Abstract Methods =====
    # Subclasses must implement these

    @abstractmethod
    async def _default_time_provider(self) -> TimeProvider:
        """
        Return the appropriate TimeProvider for this player.

        Subclasses select between RealtimeTimeProvider (wall-clock)
        or SimulatedTimeProvider (virtual time).

        Returns:
            TimeProvider: Real or simulated time provider
        """
        pass

    @abstractmethod
    async def play(self):
        """
        Execute main playback loop.

        Subclasses implement their specific playback logic:
        - VastPlayer: Real-time playback with wall-clock timing
        - HeadlessPlayer: Simulated playback with virtual time and interruptions

        This is the Template Method hook for playback-specific behavior.
        """
        pass

    # ===== Async Setup Method =====

    async def setup_time_provider(self):
        """
        Initialize time provider asynchronously.

        Must be called by subclasses after __init__ to set up the time provider.

        Example:
            class VastPlayer(BaseVastPlayer):
                async def __init__(self, vast_client, ad_data, config=None):
                    super().__init__(vast_client, ad_data, config)
                    await self.setup_time_provider()
        """
        if self.time_provider is None:
            self.time_provider = await self._default_time_provider()
            self.logger.debug(
                "Time provider initialized",
                provider_type=self.time_provider.__class__.__name__,
                provider_mode=self.time_provider.get_mode(),
            )

    # ===== Shared Methods =====
    # These work for all player types

    def _extract_creative_id(self, ad_data: dict[str, Any]) -> str:
        """
        Extract creative ID from various sources in ad_data.

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
        """
        Calculate current quartile and return number and percentage.

        Quartiles:
        - 0: Start (0%)
        - 1: First quartile (25%)
        - 2: Midpoint (50%)
        - 3: Third quartile (75%)
        - 4: Complete (100%)

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

    async def pause(self):
        """
        Pause ad playback.

        Common implementation for all player types.
        Records pause event and stops playback loop.
        """
        if not self.is_playing or self.time_provider is None:
            return

        self.is_playing = False
        self._pause_start_time = await self.time_provider.current_time()

        # Calculate current progress
        playback_seconds = int(self.session.duration())
        quartile_num, quartile_float = self._calculate_quartile(
            int(self.session.current_offset_sec)
        )
        progress_percent = (
            round(
                (self.session.current_offset_sec / self.creative_duration) * 100, 1
            )
            if self.creative_duration > 0
            else 0.0
        )

        # Update context
        update_playback_progress(
            playback_seconds=playback_seconds,
            progress_quartile=quartile_float,
            progress_percent=progress_percent,
            vast_event="playback_pause",
        )

        # Record event
        self.session.record_event(
            PlaybackEventType.PAUSE,
            self.session.current_offset_sec,
            await self.time_provider.current_time(),
        )

        await self.vast_client.tracker.track_event("pause")
        self.logger.info("Playback paused")

    async def resume(self):
        """
        Resume ad playback.

        Common implementation for all player types.
        Accounts for pause duration and resumes playback loop.
        """
        if self.is_playing or self.time_provider is None:
            return

        self.is_playing = True

        # Update start time accounting for pause duration
        if (
            hasattr(self, "_pause_start_time")
            and self._pause_start_time is not None
            and self.session.start_time is not None
        ):
            pause_duration = (
                await self.time_provider.current_time()
            ) - self._pause_start_time
            self.session.start_time += pause_duration
            self._pause_start_time = None

        # Calculate current progress
        playback_seconds = int(self.session.duration())
        quartile_num, quartile_float = self._calculate_quartile(
            int(self.session.current_offset_sec)
        )
        progress_percent = (
            round(
                (self.session.current_offset_sec / self.creative_duration) * 100, 1
            )
            if self.creative_duration > 0
            else 0.0
        )

        # Update context
        update_playback_progress(
            playback_seconds=playback_seconds,
            progress_quartile=quartile_float,
            progress_percent=progress_percent,
            vast_event="playback_resume",
        )

        # Record event
        self.session.record_event(
            PlaybackEventType.RESUME,
            self.session.current_offset_sec,
            await self.time_provider.current_time(),
        )

        await self.vast_client.tracker.track_event("resume")
        self.logger.info("Playback resumed")

    async def stop(self):
        """
        Stop ad playback.

        Common implementation for all player types.
        Records stop event and cleanly terminates playback.
        """
        if not self.is_playing or self.time_provider is None:
            return

        self.is_playing = False

        # Calculate final progress
        playback_seconds = int(self.session.duration())
        quartile_num, quartile_float = self._calculate_quartile(
            int(self.session.current_offset_sec)
        )
        progress_percent = (
            round(
                (self.session.current_offset_sec / self.creative_duration) * 100, 1
            )
            if self.creative_duration > 0
            else 0.0
        )

        # Update context
        update_playback_progress(
            playback_seconds=playback_seconds,
            progress_quartile=quartile_float,
            progress_percent=progress_percent,
            vast_event="playback_stop",
        )

        # Record event
        self.session.record_event(
            PlaybackEventType.STOP,
            self.session.current_offset_sec,
            await self.time_provider.current_time(),
        )

        # Mark session as closed (interrupted/stopped)
        self.session.interrupt(
            "stop",
            self.session.current_offset_sec,
            await self.time_provider.current_time(),
        )

        await self.vast_client.tracker.track_event("close")
        self.logger.info("Playback stopped")

    # ===== Protected Helper Methods =====

    async def _send_initial_events(self):
        """
        Send initial tracking events (impression, start, creativeView).

        Called at beginning of playback for both real and simulated players.
        """
        if self.time_provider is None:
            return

        await self.vast_client.tracker.track_event("impression")
        await self.vast_client.tracker.track_event("start")
        await self.vast_client.tracker.track_event("creativeView")

        # Record session start
        self.session.start(await self.time_provider.current_time())

        # Record initial events in session
        self.session.record_event(
            PlaybackEventType.START,
            0.0,
            await self.time_provider.current_time(),
        )

    async def _handle_zero_duration(self):
        """
        Handle case where ad duration is zero or not specified.

        Logs error and returns early without playback.
        """
        if self.time_provider is None:
            return

        update_playback_progress(
            playback_seconds=0,
            progress_quartile=0.0,
            progress_percent=0.0,
            vast_event="playback_error",
        )

        self.session.error("Zero duration", await self.time_provider.current_time())

        self.logger.error(
            "Ad duration not specified, skipping playback",
            error_reason="zero_duration",
        )
        self.is_playing = False

    def _should_track_quartile(self, quartile_num: int) -> bool:
        """
        Check if a quartile should be tracked.

        Args:
            quartile_num: Quartile number (0-4)

        Returns:
            True if quartile hasn't been tracked yet
        """
        return self.session.should_track_quartile(quartile_num)

    async def _record_quartile(
        self, quartile_num: int, current_time: float, _offset_sec: float
    ):
        """
        Record quartile achievement.

        Args:
            quartile_num: Quartile number (0-4)
            current_time: Current timestamp
            _offset_sec: Current playback offset (unused, for future use)
        """
        self.session.mark_quartile_tracked(quartile_num, current_time)

        quartile_names = {
            0: "start",
            1: "firstQuartile",
            2: "midpoint",
            3: "thirdQuartile",
            4: "complete",
        }

        event_name = quartile_names.get(quartile_num, "unknown")
        # Don't re-track start/complete and avoid duplicate tracking
        if (
            event_name not in ("start", "complete")
            and event_name not in self.vast_client.tracker.tracked_events
        ):
            await self.vast_client.tracker.track_event(event_name)

        # Update context
        quartile_percent = {0: 0.0, 1: 25.0, 2: 50.0, 3: 75.0, 4: 100.0}.get(
            quartile_num, 0.0
        )

        update_playback_progress(
            playback_seconds=int(self.session.duration()),
            progress_quartile=quartile_percent,
            progress_percent=quartile_percent,
            vast_event=f"quartile_{quartile_num}",
        )

        self.logger.info(
            f"Quartile reached: {quartile_percent}%",
            quartile_name=event_name,
            quartile_num=quartile_num,
        )


__all__ = ["BaseVastPlayer"]
