"""
Time Provider Abstraction

Provides pluggable time source for both real-time and simulated playback modes.
Enables unified playback loop code with different time behaviors.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

from .log_config import get_context_logger


class TimeProvider(ABC):
    """
    Abstract base class for time providers.
    
    Enables different time behaviors (real vs. simulated) while maintaining
    a unified playback interface. Subclasses must implement time retrieval
    and sleep operations.
    """
    
    @abstractmethod
    async def current_time(self) -> float:
        """Get current time (implementation-dependent).
        
        Returns:
            Current time as float (Unix timestamp for real, virtual time for simulated)
        """
        pass
    
    @abstractmethod
    async def sleep(self, seconds: float) -> None:
        """Sleep for specified duration.
        
        Args:
            seconds: Duration to sleep (wall-clock for real, virtual for simulated)
        """
        pass
    
    @abstractmethod
    def elapsed_time(self, start_time: float) -> float:
        """Calculate elapsed time since start_time.
        
        Args:
            start_time: Reference time from earlier current_time() call
            
        Returns:
            Elapsed time in seconds
        """
        pass
    
    @abstractmethod
    def get_mode(self) -> str:
        """Get time provider mode identifier."""
        pass


class RealtimeTimeProvider(TimeProvider):
    """
    Real-time time provider using wall-clock time.
    
    Uses time.time() for current time and asyncio.sleep() for delays.
    Suitable for production playback where timing follows actual elapsed time.
    
    Examples:
        >>> provider = RealtimeTimeProvider()
        >>> start = await provider.current_time()
        >>> await provider.sleep(1.0)  # Sleep 1 real second
        >>> elapsed = provider.elapsed_time(start)
        >>> assert 0.95 < elapsed < 1.1  # Allow for scheduling variance
    """
    
    def __init__(self):
        """Initialize real-time provider."""
        self.logger = get_context_logger("realtime_time_provider")
        self.logger.info("Real-time time provider initialized")
    
    async def current_time(self) -> float:
        """Get current wall-clock time.
        
        Returns:
            Unix timestamp (seconds since epoch)
        """
        return time.time()
    
    async def sleep(self, seconds: float) -> None:
        """Sleep for specified wall-clock duration.
        
        Args:
            seconds: Duration to sleep in seconds
        """
        await asyncio.sleep(seconds)
    
    def elapsed_time(self, start_time: float) -> float:
        """Calculate real wall-clock elapsed time.
        
        Args:
            start_time: Reference Unix timestamp
            
        Returns:
            Elapsed time in seconds
        """
        return time.time() - start_time
    
    def get_mode(self) -> str:
        """Get provider mode."""
        return "realtime"


class SimulatedTimeProvider(TimeProvider):
    """
    Simulated time provider for headless playback.
    
    Maintains virtual time independent of wall-clock time. Advances virtual time
    based on simulation steps. Useful for testing, replay, and speed-scaled playback.
    
    Features:
        - Virtual time tracking independent of wall-clock
        - Speed scaling (1.0 = normal, 0.5 = half speed, 2.0 = double speed)
        - Precise control over playback timing
        - Suitable for deterministic testing and analysis
    
    Examples:
        Normal speed simulation (1x):
        >>> provider = SimulatedTimeProvider(speed=1.0)
        >>> start = await provider.current_time()
        >>> await provider.sleep(1.0)  # Advance virtual time 1 second
        >>> elapsed = provider.elapsed_time(start)
        >>> assert elapsed == 1.0
        
        Half-speed simulation (0.5x):
        >>> provider = SimulatedTimeProvider(speed=0.5)
        >>> start = await provider.current_time()
        >>> await provider.sleep(1.0)  # Virtual time advances only 0.5 seconds
        >>> elapsed = provider.elapsed_time(start)
        >>> assert elapsed == 0.5
        
        Double-speed simulation (2x):
        >>> provider = SimulatedTimeProvider(speed=2.0)
        >>> start = await provider.current_time()
        >>> await provider.sleep(1.0)  # Virtual time advances 2 seconds
        >>> elapsed = provider.elapsed_time(start)
        >>> assert elapsed == 2.0
    """
    
    def __init__(self, speed: float = 1.0, initial_time: float = 0.0):
        """
        Initialize simulated time provider.
        
        Args:
            speed: Speed multiplier for virtual time (1.0 = normal)
            initial_time: Starting virtual time (default: 0.0)
            
        Raises:
            ValueError: If speed <= 0
        """
        if speed <= 0:
            raise ValueError(f"Speed must be positive, got {speed}")
        
        self.speed = speed
        self.virtual_time = initial_time
        self.logger = get_context_logger("simulated_time_provider")
        self.logger.info(
            "Simulated time provider initialized",
            speed=self.speed,
            initial_time=self.virtual_time
        )
    
    async def current_time(self) -> float:
        """Get current virtual time.
        
        Returns:
            Current virtual time (not wall-clock)
        """
        return self.virtual_time
    
    async def sleep(self, seconds: float) -> None:
        """Advance virtual time (no actual sleep).
        
        Args:
            seconds: Virtual duration to advance (will be scaled by speed)
        """
        # Advance virtual time by seconds * speed
        advance = seconds * self.speed
        self.virtual_time += advance
        # Yield control to allow event loop to process other tasks
        await asyncio.sleep(0)
    
    def elapsed_time(self, start_time: float) -> float:
        """Calculate elapsed virtual time.
        
        Args:
            start_time: Reference virtual time from earlier current_time() call
            
        Returns:
            Elapsed virtual time in seconds
        """
        return self.virtual_time - start_time
    
    def get_mode(self) -> str:
        """Get provider mode."""
        return "simulated"
    
    def set_virtual_time(self, virtual_time: float) -> None:
        """Set virtual time directly (for state recovery).
        
        Args:
            virtual_time: New virtual time value
        """
        self.virtual_time = virtual_time
        self.logger.info("Virtual time set", virtual_time=virtual_time)
    
    def set_speed(self, speed: float) -> None:
        """Change simulation speed.
        
        Args:
            speed: New speed multiplier
            
        Raises:
            ValueError: If speed <= 0
        """
        if speed <= 0:
            raise ValueError(f"Speed must be positive, got {speed}")
        self.speed = speed
        self.logger.info("Simulation speed changed", speed=speed)


class AutoDetectTimeProvider(TimeProvider):
    """
    Time provider that auto-detects between real and simulated based on environment.
    
    Useful when the playback mode is determined at runtime. Delegates to
    appropriate provider based on configuration.
    """
    
    def __init__(self, playback_mode: str = "real", **provider_kwargs):
        """
        Initialize auto-detect provider.
        
        Args:
            playback_mode: 'real', 'simulated', or 'auto'
            **provider_kwargs: Additional kwargs passed to provider
        """
        self.logger = get_context_logger("auto_detect_time_provider")
        
        # For now, always use the specified mode (could add env detection later)
        if playback_mode == "simulated":
            self.provider: TimeProvider = SimulatedTimeProvider(**provider_kwargs)
        else:  # real or auto defaults to realtime
            self.provider = RealtimeTimeProvider()
        
        self.logger.info(
            "Auto-detect time provider initialized",
            selected_provider=self.provider.get_mode(),
            playback_mode=playback_mode
        )
    
    async def current_time(self) -> float:
        """Get current time from underlying provider."""
        return await self.provider.current_time()
    
    async def sleep(self, seconds: float) -> None:
        """Sleep using underlying provider."""
        await self.provider.sleep(seconds)
    
    def elapsed_time(self, start_time: float) -> float:
        """Calculate elapsed time using underlying provider."""
        return self.provider.elapsed_time(start_time)
    
    def get_mode(self) -> str:
        """Get underlying provider mode."""
        return self.provider.get_mode()


def create_time_provider(mode: str = "real", **kwargs) -> TimeProvider:
    """
    Factory function to create appropriate time provider.
    
    Args:
        mode: 'real', 'simulated', or 'auto'
        **kwargs: Additional arguments passed to provider
        
    Returns:
        Configured TimeProvider instance
        
    Examples:
        Real-time provider:
        >>> provider = create_time_provider("real")
        
        Simulated provider with custom speed:
        >>> provider = create_time_provider("simulated", speed=0.5)
        
        Auto-detect provider:
        >>> provider = create_time_provider("auto")
    """
    if mode == "simulated":
        return SimulatedTimeProvider(**kwargs)
    elif mode == "auto":
        return AutoDetectTimeProvider(playback_mode="auto", **kwargs)
    else:  # default to real
        return RealtimeTimeProvider()


__all__ = [
    "TimeProvider",
    "RealtimeTimeProvider",
    "SimulatedTimeProvider",
    "AutoDetectTimeProvider",
    "create_time_provider",
]
