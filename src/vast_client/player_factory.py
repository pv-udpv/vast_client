"""
Player Factory for VAST Client

Provides factory functions for creating appropriate VAST player instances
based on playback mode, environment detection, and configuration.

Supports three playback modes:
- REAL: Real-time playback with wall-clock time progression
- HEADLESS: Simulated playback with virtual time for testing
- AUTO: Automatic detection based on environment (CI, testing, production)
"""

import os
from typing import TYPE_CHECKING

from .base_player import BaseVastPlayer
from .config import PlaybackMode, PlaybackSessionConfig
from .headless_player import HeadlessPlayer
from .player import VastPlayer


if TYPE_CHECKING:
    from .client import VastClient


class PlayerFactory:
    """
    Factory for creating appropriate VAST player instances.

    The factory supports three modes of operation:
    1. Explicit mode selection (REAL or HEADLESS)
    2. Automatic mode detection (AUTO)
    3. Environment-based defaults

    Examples:
        Create real-time player explicitly:
        >>> factory = PlayerFactory()
        >>> config = PlaybackSessionConfig(mode=PlaybackMode.REAL)
        >>> player = factory.create(
        ...     vast_client=client,
        ...     creative_id="creative-123",
        ...     ad_data=vast_response,
        ...     config=config
        ... )
        >>> isinstance(player, VastPlayer)
        True

        Create headless player for testing:
        >>> factory = PlayerFactory()
        >>> config = PlaybackSessionConfig(mode=PlaybackMode.HEADLESS)
        >>> player = factory.create(
        ...     vast_client=client,
        ...     creative_id="creative-123",
        ...     ad_data=vast_response,
        ...     config=config
        ... )
        >>> isinstance(player, HeadlessPlayer)
        True

        Auto-detect from environment:
        >>> factory = PlayerFactory()
        >>> config = PlaybackSessionConfig(mode=PlaybackMode.AUTO)
        >>> player = factory.create(
        ...     vast_client=client,
        ...     creative_id="creative-123",
        ...     ad_data=vast_response,
        ...     config=config
        ... )
        >>> # Returns HeadlessPlayer in CI/test environments
        >>> # Returns VastPlayer in production environments
    """

    @staticmethod
    def create(
        vast_client: "VastClient",
        creative_id: str,
        ad_data: dict,
        config: PlaybackSessionConfig | None = None,
    ) -> BaseVastPlayer:
        """
        Create appropriate player instance based on configuration.

        Args:
            vast_client: VastClient instance for tracking
            creative_id: Unique creative identifier
            ad_data: VAST ad data dictionary
            config: Playback configuration (defaults to REAL mode if None)

        Returns:
            BaseVastPlayer: Either VastPlayer or HeadlessPlayer instance

        Mode Resolution:
            - If config.mode == REAL: Always returns VastPlayer
            - If config.mode == HEADLESS: Always returns HeadlessPlayer
            - If config.mode == AUTO: Returns HeadlessPlayer if:
                * CI environment detected (CI=true, GITHUB_ACTIONS=true, etc.)
                * Testing environment (PYTEST_CURRENT_TEST set)
                * Headless environment (DISPLAY not set on Linux)
              Otherwise returns VastPlayer

        Examples:
            Real-time production playback:
            >>> player = PlayerFactory.create(
            ...     vast_client=client,
            ...     creative_id="creative-123",
            ...     ad_data=vast_response,
            ...     config=PlaybackSessionConfig(mode=PlaybackMode.REAL)
            ... )

            Headless testing:
            >>> player = PlayerFactory.create(
            ...     vast_client=client,
            ...     creative_id="creative-123",
            ...     ad_data=vast_response,
            ...     config=PlaybackSessionConfig(mode=PlaybackMode.HEADLESS)
            ... )

            Auto-detection:
            >>> player = PlayerFactory.create(
            ...     vast_client=client,
            ...     creative_id="creative-123",
            ...     ad_data=vast_response,
            ...     config=PlaybackSessionConfig(mode=PlaybackMode.AUTO)
            ... )
        """
        # Default to REAL mode if no config provided
        if config is None:
            config = PlaybackSessionConfig(mode=PlaybackMode.REAL)

        # Determine effective mode
        mode = config.mode
        if mode == PlaybackMode.AUTO:
            mode = PlayerFactory._detect_mode_from_environment()

        # Create appropriate player
        if mode == PlaybackMode.HEADLESS:
            return HeadlessPlayer(
                vast_client=vast_client,
                creative_id=creative_id,
                ad_data=ad_data,
                config=config,
            )
        else:  # REAL or any other mode defaults to VastPlayer
            return VastPlayer(
                vast_client=vast_client,
                creative_id=creative_id,
                ad_data=ad_data,
                config=config,
            )

    @staticmethod
    def create_real(
        vast_client: "VastClient",
        creative_id: str,
        ad_data: dict,
        config: PlaybackSessionConfig | None = None,
    ) -> VastPlayer:
        """
        Create a real-time VastPlayer instance explicitly.

        Args:
            vast_client: VastClient instance for tracking
            creative_id: Unique creative identifier
            ad_data: VAST ad data dictionary
            config: Playback configuration (mode will be set to REAL)

        Returns:
            VastPlayer: Real-time player instance

        Examples:
            >>> player = PlayerFactory.create_real(
            ...     vast_client=client,
            ...     creative_id="creative-123",
            ...     ad_data=vast_response
            ... )
            >>> await player.setup_time_provider()
            >>> await player.play()
        """
        if config is None:
            config = PlaybackSessionConfig(mode=PlaybackMode.REAL)
        else:
            # Ensure mode is REAL
            config.mode = PlaybackMode.REAL

        return VastPlayer(
            vast_client=vast_client,
            creative_id=creative_id,
            ad_data=ad_data,
            config=config,
        )

    @staticmethod
    def create_headless(
        vast_client: "VastClient",
        creative_id: str,
        ad_data: dict,
        config: PlaybackSessionConfig | None = None,
    ) -> HeadlessPlayer:
        """
        Create a HeadlessPlayer instance explicitly for testing/simulation.

        Args:
            vast_client: VastClient instance for tracking
            creative_id: Unique creative identifier
            ad_data: VAST ad data dictionary
            config: Playback configuration (mode will be set to HEADLESS)

        Returns:
            HeadlessPlayer: Simulated player instance

        Examples:
            >>> player = PlayerFactory.create_headless(
            ...     vast_client=client,
            ...     creative_id="creative-123",
            ...     ad_data=vast_response,
            ...     config=PlaybackSessionConfig(
            ...         interruption_rules={
            ...             'start': {'probability': 0.1}
            ...         }
            ...     )
            ... )
            >>> await player.setup_time_provider()
            >>> ad_data, session = await player.play()
            >>> print(session.was_interrupted)
        """
        if config is None:
            config = PlaybackSessionConfig(mode=PlaybackMode.HEADLESS)
        else:
            # Ensure mode is HEADLESS
            config.mode = PlaybackMode.HEADLESS

        return HeadlessPlayer(
            vast_client=vast_client,
            creative_id=creative_id,
            ad_data=ad_data,
            config=config,
        )

    @staticmethod
    def _detect_mode_from_environment() -> PlaybackMode:
        """
        Detect appropriate playback mode from environment variables.

        Detection Logic:
            Returns HEADLESS if any of the following are true:
            1. CI environment detected:
               - CI=true
               - GITHUB_ACTIONS=true
               - GITLAB_CI=true
               - JENKINS_URL is set
               - TRAVIS=true
               - CIRCLECI=true
            2. Testing environment:
               - PYTEST_CURRENT_TEST is set
               - TESTING=true
               - TEST_MODE=true
            3. Headless environment (Linux only):
               - DISPLAY is not set

            Returns REAL for all other cases (production default)

        Returns:
            PlaybackMode: Either HEADLESS or REAL

        Examples:
            >>> # In CI environment
            >>> os.environ['CI'] = 'true'
            >>> PlayerFactory._detect_mode_from_environment()
            <PlaybackMode.HEADLESS: 'headless'>

            >>> # In production
            >>> os.environ.clear()
            >>> PlayerFactory._detect_mode_from_environment()
            <PlaybackMode.REAL: 'real'>
        """
        # Check for CI environment
        ci_indicators = [
            "CI",                # Generic CI flag
            "GITHUB_ACTIONS",    # GitHub Actions
            "GITLAB_CI",         # GitLab CI
            "JENKINS_URL",       # Jenkins
            "TRAVIS",            # Travis CI
            "CIRCLECI",          # CircleCI
        ]

        for indicator in ci_indicators:
            if os.getenv(indicator):
                return PlaybackMode.HEADLESS

        # Check for testing environment
        test_indicators = [
            "PYTEST_CURRENT_TEST",  # pytest running
            "TESTING",              # Generic test flag
            "TEST_MODE",            # Alternative test flag
        ]

        for indicator in test_indicators:
            if os.getenv(indicator):
                return PlaybackMode.HEADLESS

        # Check for headless environment (Linux only)
        # DISPLAY not set usually indicates headless server
        if os.name == "posix" and not os.getenv("DISPLAY"):
            return PlaybackMode.HEADLESS

        # Default to real-time for production
        return PlaybackMode.REAL

    @staticmethod
    def is_headless_environment() -> bool:
        """
        Check if current environment is headless (useful for conditional logic).

        Returns:
            bool: True if headless environment detected, False otherwise

        Examples:
            >>> if PlayerFactory.is_headless_environment():
            ...     print("Running in CI or headless environment")
            ... else:
            ...     print("Running in production with display")
        """
        return PlayerFactory._detect_mode_from_environment() == PlaybackMode.HEADLESS


# Convenience factory functions
def create_player(
    vast_client: "VastClient",
    creative_id: str,
    ad_data: dict,
    config: PlaybackSessionConfig | None = None,
) -> BaseVastPlayer:
    """
    Convenience function for creating VAST players.

    Delegates to PlayerFactory.create().

    Args:
        vast_client: VastClient instance for tracking
        creative_id: Unique creative identifier
        ad_data: VAST ad data dictionary
        config: Playback configuration

    Returns:
        BaseVastPlayer: Appropriate player instance

    Examples:
        >>> player = create_player(client, "creative-123", vast_response)
        >>> await player.setup_time_provider()
        >>> await player.play()
    """
    return PlayerFactory.create(vast_client, creative_id, ad_data, config)


def create_real_player(
    vast_client: "VastClient",
    creative_id: str,
    ad_data: dict,
    config: PlaybackSessionConfig | None = None,
) -> VastPlayer:
    """
    Convenience function for creating real-time VAST players.

    Delegates to PlayerFactory.create_real().

    Args:
        vast_client: VastClient instance for tracking
        creative_id: Unique creative identifier
        ad_data: VAST ad data dictionary
        config: Playback configuration

    Returns:
        VastPlayer: Real-time player instance

    Examples:
        >>> player = create_real_player(client, "creative-123", vast_response)
        >>> await player.setup_time_provider()
        >>> await player.play()
    """
    return PlayerFactory.create_real(vast_client, creative_id, ad_data, config)


def create_headless_player(
    vast_client: "VastClient",
    creative_id: str,
    ad_data: dict,
    config: PlaybackSessionConfig | None = None,
) -> HeadlessPlayer:
    """
    Convenience function for creating headless VAST players for testing.

    Delegates to PlayerFactory.create_headless().

    Args:
        vast_client: VastClient instance for tracking
        creative_id: Unique creative identifier
        ad_data: VAST ad data dictionary
        config: Playback configuration

    Returns:
        HeadlessPlayer: Simulated player instance

    Examples:
        >>> player = create_headless_player(client, "creative-123", vast_response)
        >>> await player.setup_time_provider()
        >>> ad_data, session = await player.play()
        >>> print(session.was_interrupted)
    """
    return PlayerFactory.create_headless(vast_client, creative_id, ad_data, config)


__all__ = [
    "PlayerFactory",
    "create_player",
    "create_real_player",
    "create_headless_player",
]
