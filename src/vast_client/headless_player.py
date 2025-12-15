"""Headless VAST player for simulated playback.

Simulated playback implementation using virtual time via SimulatedTimeProvider.
Implements stochastic interruptions based on provider-specific profiles.
Inherits shared playback logic from BaseVastPlayer.
"""

import random
from typing import TYPE_CHECKING, Any

from .base_player import BaseVastPlayer
from .config import PlaybackSessionConfig
from .log_config import update_playback_progress
from .playback_session import PlaybackEventType
from .time_provider import SimulatedTimeProvider, TimeProvider


if TYPE_CHECKING:
    from .client import VastClient


class HeadlessPlayer(BaseVastPlayer):
    """Simulated VAST ad playback with stochastic interruptions.

    Implements headless/simulated playback using virtual time via
    SimulatedTimeProvider. Supports stochastic interruptions based on
    provider-specific interruption profiles for testing resilience.

    Features:
    - Virtual time advancement (0.5x to 2x speed)
    - Stochastic interruption simulation based on provider profiles
    - Full session event tracking with interruption history
    - Session persistence via PlaybackSession.to_json()/from_json()
    - Return tuple: (ad_data, session) with complete playback history

    Interruption Profiles:
    - global: 15% start, 8% midpoint (heavy testing)
    - tiger: 8% start, 5% midpoint (balanced)
    - leto: 5% start, 3% midpoint (stable)
    - yandex: 10% start, 6% midpoint (moderate)
    - google: 20% start, 12% midpoint (stress testing)
    - custom: 7% start, 4% midpoint (default)

    Example:
        >>> config = PlaybackSessionConfig(
        ...     mode=PlaybackMode.HEADLESS,
        ...     headless_tick_interval_sec=0.1,
        ... )
        >>> player = HeadlessPlayer(client, ad_data, config)
        >>> ad_data_result, session = await player.play()
        >>> print(f"Session: {session.status}, Events: {len(session.events)}")
    """

    def __init__(
        self,
        vast_client: "VastClient",
        ad_data: dict[str, Any],
        config: PlaybackSessionConfig | None = None,
    ):
        """Initialize headless VAST player.

        Args:
            vast_client: VastClient instance
            ad_data: Parsed VAST ad data
            config: PlaybackSessionConfig (optional, uses default if None)
        """
        # Call parent constructor - sets up session, logging, etc.
        super().__init__(vast_client, ad_data, config)

        # Headless specific state
        self.time_provider_instance: SimulatedTimeProvider | None = None
        self.interruption_rules = self.config.interruption_rules or {}
        self.interrupted = False
        self.interruption_reason: str | None = None

        # Extract provider-specific interruption profile
        provider_id = ad_data.get("provider_id", "custom")
        self.provider_id = provider_id

        self.logger.info(
            "Headless player initialized",
            provider_id=provider_id,
            tick_interval=self.config.headless_tick_interval_sec,
        )

    async def _default_time_provider(self) -> TimeProvider:
        """Return SimulatedTimeProvider for virtual time.

        Returns:
            SimulatedTimeProvider with configurable speed
        """
        # Create simulated time provider with default 1x speed
        provider = SimulatedTimeProvider(speed=1.0)
        self.time_provider_instance = provider
        return provider

    async def play(self) -> tuple[dict[str, Any], Any]:
        """Execute simulated ad playback with stochastic interruptions.

        Returns:
            Tuple of (ad_data, session) for testing/debugging purposes
        """
        # Initialize time provider
        await self.setup_time_provider()

        if self.time_provider_instance is None:
            self.logger.error("Time provider initialization failed")
            self.session.error(
                "Time provider initialization failed",
                await self.time_provider.current_time() if self.time_provider else 0,
            )
            return self.ad_data, self.session

        self.is_playing = True

        # Update context for playback start
        update_playback_progress(
            playback_seconds=0,
            progress_quartile=0.0,
            progress_percent=0.0,
            vast_event="playback_start",
        )

        self.logger.info("Headless playback started")

        # Send initial events (impression, start, creativeView)
        await self._send_initial_events()

        if self.creative_duration == 0:
            await self._handle_zero_duration()
            return self.ad_data, self.session

        # Simulated playback loop - iterate with tick intervals
        tick_interval = self.config.headless_tick_interval_sec
        current_time = 0.0

        while current_time < self.creative_duration and self.is_playing:
            # Check for stochastic interruption
            if self._should_interrupt(current_time):
                self.interrupted = True
                await self._handle_interruption(current_time)
                break

            # Track progress at current virtual time
            await self._track_simulated_progress(current_time)

            # Advance virtual time (not awaitable)
            if self.time_provider_instance:
                self.time_provider_instance.set_virtual_time(current_time + tick_interval)
            current_time += tick_interval

        # Handle completion
        if self.is_playing and not self.interrupted:
            playback_seconds = int(self.session.duration())

            update_playback_progress(
                playback_seconds=playback_seconds,
                progress_quartile=100.0,
                progress_percent=100.0,
                vast_event="playback_complete",
            )

            # Send complete event
            await self.vast_client.tracker.track_event("complete")

            # Mark session as completed
            if self.time_provider:
                self.session.complete(await self.time_provider.current_time())

            self.logger.info(
                "Headless playback completed",
                total_duration=self.creative_duration,
                total_events=len(self.session.events),
            )

        self.is_playing = False

        # Return session for test inspection
        return self.ad_data, self.session

    def _should_interrupt(self, current_time: float) -> bool:
        """Determine if playback should be interrupted at current time.

        Uses stochastic decision based on provider-specific interruption rules.
        Each event type (start, firstQuartile, midpoint, thirdQuartile, complete)
        has its own interruption probability.

        Args:
            current_time: Current playback time in seconds

        Returns:
            True if interruption should occur, False otherwise
        """
        if not self.interruption_rules:
            return False

        # Get event type for current progress
        quartile_num, progress_pct = self._calculate_quartile(int(current_time))

        event_type_map = {
            0: "start",
            1: "firstQuartile",
            2: "midpoint",
            3: "thirdQuartile",
            4: "complete",
        }

        event_type = event_type_map.get(quartile_num, "progress")

        # Get interruption probability for this event type
        event_rules = self.interruption_rules.get(event_type, {})
        interruption_rate = event_rules.get("interruption_rate", 0.0)

        # Stochastic decision
        if interruption_rate > 0:
            return random.random() < interruption_rate

        return False

    async def _handle_interruption(self, offset_sec: float):
        """Handle a simulated interruption event.

        Args:
            offset_sec: Playback offset where interruption occurred
        """
        self.is_playing = False
        current_time = (
            await self.time_provider.current_time()
            if self.time_provider
            else 0.0
        )

        playback_seconds = int(self.session.duration())
        quartile_num, quartile_float = self._calculate_quartile(int(offset_sec))
        progress_percent = (
            round((offset_sec / self.creative_duration) * 100, 1)
            if self.creative_duration > 0
            else 0.0
        )

        # Determine interruption reason
        if offset_sec < 0.25 * self.creative_duration:
            reason = "network_error"
        elif offset_sec < 0.75 * self.creative_duration:
            reason = "timeout"
        else:
            reason = "device_error"

        self.interruption_reason = reason

        # Update progress context
        update_playback_progress(
            playback_seconds=playback_seconds,
            progress_quartile=quartile_float,
            progress_percent=progress_percent,
            vast_event="playback_interrupted",
        )

        # Record interruption in session
        self.session.interrupt(reason, offset_sec, current_time)

        # Record interruption event
        self.session.record_event(
            PlaybackEventType.INTERRUPT,
            offset_sec,
            current_time,
            {"reason": reason, "quartile": quartile_num},
        )

        self.logger.warning(
            "Headless playback interrupted",
            reason=reason,
            offset_sec=offset_sec,
            progress_pct=progress_percent,
        )

    async def _track_simulated_progress(self, current_time: float):
        """Track simulated playback progress and quartile events.

        Args:
            current_time: Current simulated playback time in seconds
        """
        if self.creative_duration == 0:
            return

        quartile_num, quartile_float = self._calculate_quartile(int(current_time))
        progress_percent = (
            round((current_time / self.creative_duration) * 100, 1)
            if self.creative_duration > 0
            else 0.0
        )

        # Record progress in session
        self.session.current_offset_sec = current_time

        # Check if quartile achieved
        if self._should_track_quartile(quartile_num):
            current_time_val = (
                await self.time_provider.current_time()
                if self.time_provider
                else 0.0
            )
            await self._record_quartile(quartile_num, current_time_val, current_time)

            # Update progress context
            update_playback_progress(
                playback_seconds=int(self.session.duration()),
                progress_quartile=quartile_float,
                progress_percent=progress_percent,
                vast_event=f"quartile_{quartile_num}",
            )

    async def pause(self):
        """Pause simulated playback.

        Inherited from BaseVastPlayer - common implementation for all players.
        """
        await super().pause()

    async def resume(self):
        """Resume simulated playback.

        Inherited from BaseVastPlayer - common implementation for all players.
        """
        await super().resume()

    async def stop(self):
        """Stop simulated playback.

        Inherited from BaseVastPlayer - common implementation for all players.
        """
        await super().stop()

    # ===== Session Management =====

    def get_session_json(self) -> str:
        """Get session data as JSON string for persistence.

        Returns:
            JSON string representation of PlaybackSession
        """
        return self.session.to_json()

    def get_session_dict(self) -> dict[str, Any]:
        """Get session data as dictionary.

        Returns:
            Dictionary representation of PlaybackSession
        """
        return self.session.to_dict()


__all__ = ["HeadlessPlayer"]
