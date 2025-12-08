"""VAST ad player for real-time playback.

Real-time playback implementation using wall-clock timing via RealtimeTimeProvider.
Inherits shared playback logic from BaseVastPlayer.
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any

from ..events import VastEvents
from .base_player import BaseVastPlayer
from .config import PlaybackSessionConfig
from .time_provider import RealtimeTimeProvider, TimeProvider
from ..log_config import update_playback_progress

if TYPE_CHECKING:
    from .client import VastClient


class VastPlayer(BaseVastPlayer):
    """Real-time VAST ad playback using wall-clock timing.

    Inherits shared playback logic from BaseVastPlayer and implements
    real-time specific behavior using RealtimeTimeProvider for wall-clock
    timing via time.time() and asyncio.sleep().

    Features:
    - Real-time playback with asyncio event loop
    - Wall-clock progress tracking
    - Standard quartile tracking (0%, 25%, 50%, 75%, 100%)
    - Pause/resume/stop control (inherited from BaseVastPlayer)

    Example:
        >>> client = VastClient(url)
        >>> ad_data = await client.request_ad()
        >>> player = VastPlayer(client, ad_data)
        >>> await player.play()  # Real-time playback loop
    """

    def __init__(
        self,
        vast_client: "VastClient",
        ad_data: dict[str, Any],
        config: PlaybackSessionConfig | None = None,
    ):
        """Initialize real-time VAST player.

        Args:
            vast_client: VastClient instance
            ad_data: Parsed VAST ad data
            config: PlaybackSessionConfig (optional, uses default if None)
        """
        # Call parent constructor - sets up session, logging, etc.
        super().__init__(vast_client, ad_data, config)

        # Real-time specific state
        self.playback_start_time: float | None = None
        self.current_quartile = 0  # 0=start, 1=25%, 2=50%, 3=75%, 4=100%
        self.quartile_tracked = {0: False, 1: False, 2: False, 3: False, 4: False}

        self.logger.info(VastEvents.PLAYER_INITIALIZED)

    async def _default_time_provider(self) -> TimeProvider:
        """Return RealtimeTimeProvider for wall-clock timing.

        Returns:
            RealtimeTimeProvider using time.time() and asyncio.sleep()
        """
        return RealtimeTimeProvider()

    async def play(self):
        """Execute real-time ad playback with progress tracking.

        Implements Template Method hook for real-time specific behavior.
        Uses wall-clock timing via asyncio.sleep(1) per iteration.
        Inherits pause/resume/stop from BaseVastPlayer.
        """
        # Initialize time provider
        await self.setup_time_provider()

        if self.time_provider is None:
            self.logger.error("Time provider initialization failed")
            return

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

        # Send initial events (impression, start, creativeView)
        await self._send_initial_events()

        if self.creative_duration == 0:
            await self._handle_zero_duration()
            return

        # Real-time playback loop - one iteration per second
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

        # Handle completion
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
        self.session.complete(await self.time_provider.current_time())

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
        """Pause ad playback.

        Inherited from BaseVastPlayer - common implementation for all players.
        """
        await super().pause()

    async def resume(self):
        """Resume ad playback.

        Inherited from BaseVastPlayer - common implementation for all players.
        """
        await super().resume()

    async def stop(self):
        """Stop ad playback.

        Inherited from BaseVastPlayer - common implementation for all players.
        """
        await super().stop()


__all__ = ["VastPlayer"]
