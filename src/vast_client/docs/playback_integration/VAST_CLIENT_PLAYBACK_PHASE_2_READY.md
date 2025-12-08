# Phase 2 Implementation Plan - Ready to Start

## Overview
Phase 1 (configuration foundation) is 100% complete. Phase 2 will implement the core player architecture with three parallel tracks. This document guides the Phase 2 implementation.

## Phase 2 Structure
**Estimated Duration**: 31 hours (theoretical) → 14 hours (actual, with parallelization)
**Parallelization Strategy**: TRACK A and TRACK B can execute simultaneously

### TRACK A: Player Architecture (14 hours)
Sequential implementation of time-aware player components.

#### T2.1: TimeProvider Abstraction ✅ ALREADY COMPLETED
- **Status**: DONE (src/ctv_middleware/vast_client/time_provider.py)
- **Components**: RealtimeTimeProvider, SimulatedTimeProvider, AutoDetectTimeProvider
- **Ready for**: VastPlayer and HeadlessPlayer implementation
- **Lines**: 280+ lines, fully tested and documented

#### T2.2: BaseVastPlayer Abstract Class (4 hours)
**Purpose**: Define shared playback interface with Template Method pattern

**Implementation Plan**:
```python
# Location: src/ctv_middleware/vast_client/base_player.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from .time_provider import TimeProvider
from .playback_session import PlaybackSession

class BaseVastPlayer(ABC):
    """Abstract base class for VAST players (real and headless)."""
    
    # Protected methods (shared implementation)
    def __init__(self, vast_client, ad_data, config=None):
        self.vast_client = vast_client
        self.ad_data = ad_data
        self.config = config or PlaybackSessionConfig()
        self.session = None
        self.logger = get_context_logger("vast_player")
    
    def _extract_creative_id(self, ad_data) -> str:
        """Shared implementation from current VastPlayer."""
        
    def _calculate_quartile(self, current_time) -> tuple[int, float]:
        """Shared implementation from current VastPlayer."""
    
    # Abstract methods (implementation-specific)
    @abstractmethod
    async def _default_time_provider(self) -> TimeProvider:
        """Return appropriate TimeProvider for this player."""
    
    @abstractmethod
    async def play(self):
        """Execute playback loop (template method)."""
    
    # Shared concrete methods
    async def pause(self):
        """Pause playback (both player types use same logic)."""
    
    async def resume(self):
        """Resume playback (both player types use same logic)."""
    
    async def stop(self):
        """Stop playback (both player types use same logic)."""
```

**Key Design**:
- Template Method pattern for play() loop
- Shared pause/resume/stop logic
- Abstract method for TimeProvider selection
- All logging and event tracking centralized
- PlaybackSession integration for state tracking

**Files to Create**:
- `src/ctv_middleware/vast_client/base_player.py` (150-200 lines)

**Testing Considerations**:
- Mock TimeProvider for deterministic tests
- Test pause/resume state transitions
- Validate quartile tracking logic
- Verify event recording

#### T2.3: VastPlayer Refactoring (3 hours)
**Purpose**: Update existing VastPlayer to inherit from BaseVastPlayer

**Current Location**: `src/ctv_middleware/vast_client/player.py` (319 lines)
**Changes**:
1. Change inheritance: `class VastPlayer(BaseVastPlayer)`
2. Move shared methods to BaseVastPlayer:
   - `_extract_creative_id()` → BaseVastPlayer
   - `_calculate_quartile()` → BaseVastPlayer
   - `pause()`, `resume()`, `stop()` → BaseVastPlayer
3. Keep VastPlayer-specific:
   - Initialization with RealtimeTimeProvider
   - Main play() loop using real-time logic
   - Quartile tracking with wall-clock time
4. Add PlaybackSession integration:
   - Create session in __init__
   - Record events as they occur
   - Track quartiles in session

**Backward Compatibility**:
- Public API unchanged
- Existing code continues to work
- Internal refactoring only

**Testing**:
- All existing tests should pass with minimal changes
- Verify RealtimeTimeProvider selection
- Test session creation and event recording

#### T2.4: HeadlessPlayer Implementation (4 hours)
**Purpose**: New player for simulated playback with interruptions

**Implementation Plan**:
```python
# Location: src/ctv_middleware/vast_client/headless_player.py

class HeadlessPlayer(BaseVastPlayer):
    """Simulated ad playback with stochastic interruptions."""
    
    async def _default_time_provider(self) -> TimeProvider:
        """Return SimulatedTimeProvider."""
        return SimulatedTimeProvider(speed=1.0)
    
    async def play(self):
        """Execute simulation with interruption support."""
        # 1. Create PlaybackSession
        # 2. Setup SimulatedTimeProvider
        # 3. Send impression/start events
        # 4. Loop through simulation ticks:
        #    - Check for interruption based on rules
        #    - Advance virtual time
        #    - Track quartiles
        #    - Record events
        # 5. Complete or interrupt session
        # 6. Return (ad_data, session) tuple
    
    def _should_interrupt(self, event_type, offset_sec) -> bool:
        """Check if interruption should occur at this point."""
        # Use interruption_rules from config
        # Stochastic decision based on probability
    
    async def _simulate_tick(self):
        """Single simulation step (advance virtual time)."""
        # Advance virtual time by tick interval
        # Check for quartile milestones
        # Generate events
```

**Key Features**:
- Stochastic interruption based on provider-specific rules
- Virtual time advancement independent of wall-clock
- Full event recording for analysis
- Session persistence for replay/debugging
- Returns (ad_data, session) tuple for inspection

**Provider-Specific Behavior**:
- Each provider has unique interruption probabilities
- Global: 15% interruption at start, 8% at midpoint
- Google: 20% at start, 12% at midpoint
- Leto: 5% at start, 3% at midpoint
- (Use values from config.py)

**Testing**:
- Mock interruption decisions
- Verify session events recorded correctly
- Test quartile tracking in virtual time
- Validate provider-specific rules

### TRACK B: Config Module & Integration (5 hours - parallel with TRACK A)
Can execute simultaneously with TRACK A player implementations.

#### T2.5: Create PlaybackSessionConfig Module (1.5 hours)
**Purpose**: Organize playback configuration into dedicated module

**Implementation**:
```python
# Location: src/ctv_middleware/vast_client/playback/config.py

from dataclasses import dataclass
from ..config import PlaybackSessionConfig

@dataclass
class PlaybackConfigResolver:
    """Resolves 4-level configuration hierarchy."""
    
    def resolve(
        self,
        mode: str = None,
        publisher: str = None,
        provider: str = None,
        global_config: PlaybackSessionConfig = None,
        player_override: PlaybackSessionConfig = None,
    ) -> PlaybackSessionConfig:
        """
        Resolve configuration with precedence:
        1. Per-player override (highest)
        2. Publisher override
        3. Provider defaults
        4. Global hardcoded (lowest)
        """
        # Start with global defaults
        config = global_config or PlaybackSessionConfig()
        
        # Apply provider-specific rules
        if provider:
            config = get_provider_config(provider)
        
        # Apply publisher overrides
        if publisher:
            config = apply_publisher_overrides(config, publisher)
        
        # Apply per-player overrides
        if player_override:
            config = merge_configs(config, player_override)
        
        return config
```

**Files to Create**:
- `src/ctv_middleware/vast_client/playback/__init__.py` (empty or with imports)
- `src/ctv_middleware/vast_client/playback/config.py` (80-100 lines)

#### T2.6: Configuration Inheritance System (1.5 hours)
**Purpose**: Implement ConfigResolver for hierarchical configuration

**Key Classes**:
- `ConfigResolver`: Main resolution logic
- `PublisherConfigRegistry`: Publisher-specific overrides
- `ProviderConfigFactory`: Provider default factory

**Methods**:
- `resolve()`: Apply all levels of precedence
- `validate()`: Ensure config consistency
- `apply_overrides()`: Merge configurations safely

#### T2.7: VastClient Integration (1 hour)
**Purpose**: Connect VastClient to playback configuration

**Changes to VastClient**:
```python
# In src/ctv_middleware/vast_client/client.py

class VastClient:
    def __init__(self, ...):
        # Add playback config resolution
        self.playback_config_resolver = ConfigResolver()
    
    def get_playback_config(
        self,
        mode: str = None,
        publisher: str = None,
        **overrides
    ) -> PlaybackSessionConfig:
        """Get resolved playback configuration."""
        return self.playback_config_resolver.resolve(
            mode=mode,
            publisher=publisher,
            provider=self.config.provider,
            global_config=self.config.playback,
            player_override=PlaybackSessionConfig(**overrides) if overrides else None
        )
    
    async def play_ad(
        self,
        ad_data,
        mode: str = "auto",
        publisher: str = None,
        **overrides
    ):
        """Play ad with automatic player selection."""
        config = self.get_playback_config(mode, publisher, **overrides)
        player = PlayerFactory.create(self, ad_data, config)
        return await player.play()
```

### TRACK A/B Convergence: PlayerFactory (2 hours)
**Purpose**: Factory for automatic player creation based on mode

**Location**: `src/ctv_middleware/vast_client/player_factory.py`

```python
class PlayerFactory:
    """Factory for creating appropriate player type."""
    
    @staticmethod
    def create(
        vast_client,
        ad_data,
        config: PlaybackSessionConfig = None
    ) -> BaseVastPlayer:
        """
        Create appropriate player based on mode.
        
        Returns:
            VastPlayer: For REAL mode
            HeadlessPlayer: For HEADLESS mode
            Auto-selected: For AUTO mode
        """
        config = config or PlaybackSessionConfig()
        
        if config.mode == PlaybackMode.HEADLESS:
            return HeadlessPlayer(vast_client, ad_data, config)
        elif config.mode == PlaybackMode.AUTO:
            # Auto-detect from environment
            detected_mode = detect_mode_from_env()
            if detected_mode == "headless":
                return HeadlessPlayer(vast_client, ad_data, config)
            else:
                return VastPlayer(vast_client, ad_data, config)
        else:  # REAL or default
            return VastPlayer(vast_client, ad_data, config)
```

## Implementation Sequence

### Week 1 (15 hours)
- **Days 1-2**: T2.1 ✅ (already done), Start T2.2, T2.5 in parallel
- **Days 3-4**: Complete T2.2, T2.3, T2.6 in parallel
- **Day 5**: Complete T2.4, T2.7, T2.8 convergence

### Critical Dependencies
```
T2.1 (TimeProvider) ✅ DONE
    ↓
T2.2 (BaseVastPlayer) ← Must be first
    ↓
┌─→ T2.3 (VastPlayer) ← Parallel with...
│
└─→ T2.4 (HeadlessPlayer) + T2.5-T2.7 (Config Module)
    ↓
    T2.8 (PlayerFactory) ← Depends on all above
```

## Files to Create/Modify (Phase 2)

### New Files
1. `src/ctv_middleware/vast_client/base_player.py` - BaseVastPlayer abstract class
2. `src/ctv_middleware/vast_client/headless_player.py` - HeadlessPlayer implementation
3. `src/ctv_middleware/vast_client/playback/__init__.py` - Package init
4. `src/ctv_middleware/vast_client/playback/config.py` - ConfigResolver
5. `src/ctv_middleware/vast_client/player_factory.py` - PlayerFactory

### Modified Files
1. `src/ctv_middleware/vast_client/player.py` - Refactor VastPlayer
2. `src/ctv_middleware/vast_client/client.py` - Add playback config methods
3. `src/ctv_middleware/vast_client/__init__.py` - Export new classes

## Testing Strategy (Phase 3)

### Config Tests (50 tests)
- PlaybackSessionConfig creation and defaults
- Configuration precedence (4 levels)
- Provider-specific rules application
- Publisher override application
- ConfigResolver resolution logic

### TimeProvider Tests (30 tests)
- RealtimeTimeProvider timing accuracy
- SimulatedTimeProvider virtual time
- Speed scaling (0.5x, 1.0x, 2.0x, etc.)
- AutoDetectTimeProvider delegation
- Edge cases (zero speed, negative times)

### BaseVastPlayer Tests (50 tests)
- Abstract methods enforcement
- Shared method implementations
- Quartile calculation
- Event recording
- Session integration

### VastPlayer Tests (80 tests)
- Real-time playback loop
- RealtimeTimeProvider usage
- Pause/resume functionality
- Stop and cleanup
- Existing behavior preservation

### HeadlessPlayer Tests (120 tests)
- Simulated playback loop
- Interruption decision logic
- Provider-specific rules
- Virtual time advancement
- Event recording
- Session persistence

### PlayerFactory Tests (30 tests)
- Mode-based player selection
- Auto-detection logic
- Configuration passing
- All provider combinations

### Integration Tests (40 tests)
- Full playback workflow
- Cross-component interactions
- Config → Player flow
- Event propagation

## Success Criteria
- ✅ All 340+ tests pass
- ✅ Backward compatibility maintained
- ✅ No breaking changes to public API
- ✅ Full documentation with examples
- ✅ Zero lint/type errors
- ✅ Performance regression < 5%

## Next: Ready for Implementation
Phase 2 is fully planned and ready to begin. All dependencies from Phase 1 are complete. Execute T2.2 first (BaseVastPlayer), then parallelize T2.3/T2.4 with T2.5-T2.7.
