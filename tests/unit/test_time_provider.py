"""Unit tests for time providers."""

import asyncio

import pytest

from vast_client.config import PlaybackMode
from vast_client.time_provider import (
    RealtimeTimeProvider,
    SimulatedTimeProvider,
    TimeProvider,
    create_time_provider,
)


class TestRealtimeTimeProvider:
    """Test RealtimeTimeProvider (wall-clock time)."""

    def test_creation(self):
        """Test creating realtime time provider."""
        provider = RealtimeTimeProvider()
        assert provider is not None

    def test_now_returns_time(self):
        """Test that now() returns current time."""
        provider = RealtimeTimeProvider()
        t1 = provider.now()
        t2 = provider.now()

        assert isinstance(t1, float)
        assert isinstance(t2, float)
        assert t2 >= t1  # Time should not go backwards

    @pytest.mark.asyncio
    async def test_sleep(self):
        """Test async sleep with realtime provider."""
        provider = RealtimeTimeProvider()

        start = provider.now()
        await provider.sleep(0.1)  # Sleep for 100ms
        end = provider.now()

        elapsed = end - start
        assert elapsed >= 0.1  # Should have slept at least 100ms
        assert elapsed < 0.2  # But not too much longer


class TestSimulatedTimeProvider:
    """Test SimulatedTimeProvider (virtual time)."""

    def test_creation(self):
        """Test creating simulated time provider."""
        provider = SimulatedTimeProvider()
        assert provider is not None
        assert provider.speed_multiplier == 1.0

    def test_creation_with_speed(self):
        """Test creating with custom speed multiplier."""
        provider = SimulatedTimeProvider(speed_multiplier=2.0)
        assert provider.speed_multiplier == 2.0

    def test_now_returns_virtual_time(self):
        """Test that now() returns virtual time."""
        provider = SimulatedTimeProvider()

        t1 = provider.now()
        provider.advance(1.0)  # Advance by 1 second
        t2 = provider.now()

        assert t2 == t1 + 1.0

    def test_advance(self):
        """Test advancing virtual time."""
        provider = SimulatedTimeProvider()

        initial = provider.now()

        provider.advance(5.0)
        assert provider.now() == initial + 5.0

        provider.advance(3.5)
        assert provider.now() == initial + 8.5

    def test_reset(self):
        """Test resetting virtual time."""
        provider = SimulatedTimeProvider()

        provider.advance(10.0)
        assert provider.now() == 10.0

        provider.reset()
        assert provider.now() == 0.0

    @pytest.mark.asyncio
    async def test_sleep_advances_time(self):
        """Test that sleep advances virtual time."""
        provider = SimulatedTimeProvider()

        start = provider.now()
        await provider.sleep(2.5)
        end = provider.now()

        assert end == start + 2.5

    @pytest.mark.asyncio
    async def test_sleep_with_speed_multiplier(self):
        """Test sleep with speed multiplier."""
        provider = SimulatedTimeProvider(speed_multiplier=10.0)

        start = provider.now()
        await provider.sleep(10.0)  # 10 virtual seconds
        end = provider.now()

        # Virtual time should advance by 10 seconds
        assert end == start + 10.0
        # But real time should be ~1 second (10 / 10x speed)

    def test_set_speed_multiplier(self):
        """Test changing speed multiplier."""
        provider = SimulatedTimeProvider()

        provider.set_speed_multiplier(5.0)
        assert provider.speed_multiplier == 5.0

        provider.set_speed_multiplier(0.5)
        assert provider.speed_multiplier == 0.5

    @pytest.mark.asyncio
    async def test_concurrent_sleep(self):
        """Test multiple concurrent sleep operations."""
        provider = SimulatedTimeProvider()

        async def sleep_task(duration: float) -> float:
            start = provider.now()
            await provider.sleep(duration)
            return provider.now() - start

        # Run multiple sleep tasks concurrently
        results = await asyncio.gather(
            sleep_task(1.0),
            sleep_task(2.0),
            sleep_task(3.0),
        )

        # All should have advanced by their requested durations
        assert results[0] == pytest.approx(1.0, abs=0.01)
        assert results[1] == pytest.approx(2.0, abs=0.01)
        assert results[2] == pytest.approx(3.0, abs=0.01)


class TestCreateTimeProvider:
    """Test create_time_provider factory function."""

    def test_create_realtime_provider(self):
        """Test creating realtime provider."""
        provider = create_time_provider(PlaybackMode.REAL)
        assert isinstance(provider, RealtimeTimeProvider)

    def test_create_headless_provider(self):
        """Test creating simulated provider for headless mode."""
        provider = create_time_provider(PlaybackMode.HEADLESS)
        assert isinstance(provider, SimulatedTimeProvider)

    def test_create_auto_provider_default(self):
        """Test creating provider in auto mode (should default to realtime)."""
        provider = create_time_provider(PlaybackMode.AUTO)
        # Auto mode defaults to realtime unless settings say otherwise
        assert isinstance(provider, RealtimeTimeProvider | SimulatedTimeProvider)

    def test_create_with_speed_multiplier(self):
        """Test creating simulated provider with speed multiplier."""
        provider = create_time_provider(PlaybackMode.HEADLESS, speed_multiplier=5.0)
        assert isinstance(provider, SimulatedTimeProvider)
        assert provider.speed_multiplier == 5.0


class TestTimeProviderProtocol:
    """Test TimeProvider protocol compliance."""

    def test_realtime_implements_protocol(self):
        """Test that RealtimeTimeProvider implements TimeProvider protocol."""
        provider = RealtimeTimeProvider()

        # Should have required methods
        assert hasattr(provider, "now")
        assert hasattr(provider, "sleep")
        assert callable(provider.now)
        assert callable(provider.sleep)

    def test_simulated_implements_protocol(self):
        """Test that SimulatedTimeProvider implements TimeProvider protocol."""
        provider = SimulatedTimeProvider()

        # Should have required methods
        assert hasattr(provider, "now")
        assert hasattr(provider, "sleep")
        assert callable(provider.now)
        assert callable(provider.sleep)

    @pytest.mark.asyncio
    async def test_protocol_interchangeable(self):
        """Test that both providers can be used interchangeably."""

        async def use_time_provider(provider: TimeProvider) -> float:
            """Function that uses TimeProvider protocol."""
            start = provider.now()
            await provider.sleep(0.1)
            end = provider.now()
            return end - start

        # Both should work with the same function
        realtime_result = await use_time_provider(RealtimeTimeProvider())
        simulated_result = await use_time_provider(SimulatedTimeProvider())

        assert realtime_result >= 0.1
        assert simulated_result == 0.1


class TestSimulatedTimeProviderEdgeCases:
    """Edge case tests for SimulatedTimeProvider."""

    def test_advance_negative_raises(self):
        """Test that advancing by negative value raises error."""
        provider = SimulatedTimeProvider()

        with pytest.raises(ValueError):
            provider.advance(-1.0)

    def test_zero_speed_multiplier_raises(self):
        """Test that zero speed multiplier raises error."""
        with pytest.raises(ValueError):
            SimulatedTimeProvider(speed_multiplier=0.0)

    def test_negative_speed_multiplier_raises(self):
        """Test that negative speed multiplier raises error."""
        with pytest.raises(ValueError):
            SimulatedTimeProvider(speed_multiplier=-1.0)

    @pytest.mark.asyncio
    async def test_very_small_sleep(self):
        """Test sleep with very small duration."""
        provider = SimulatedTimeProvider()

        start = provider.now()
        await provider.sleep(0.001)  # 1ms
        end = provider.now()

        assert end == start + 0.001

    @pytest.mark.asyncio
    async def test_zero_sleep(self):
        """Test sleep with zero duration."""
        provider = SimulatedTimeProvider()

        start = provider.now()
        await provider.sleep(0.0)
        end = provider.now()

        assert end == start
