# VAST Client Headless Playback Integration Plan

## Executive Summary

Integrate dual playback modes (real-time + headless simulated) into the VAST Client package to support both production playback and testing/simulation scenarios. This involves a 5-layer architecture redesign with TimeProvider abstraction, configuration hierarchy extension, and comprehensive testing infrastructure.

**Estimated Effort**: 60-65 hours (50-55 hours actual via parallelization)
**Timeline**: 3-4 dev-weeks
**Team Capacity**: 1-2 developers with parallel track execution

---

## Phase Overview

### Phase 1: Configuration Foundation (15 hours - Sequential)
Establish configuration layer prerequisites for playback system.

- **T1.1** (4h): Add PlaybackSessionConfig dataclass to config.py
- **T1.2** (3h): Integrate into VastTrackerConfig hierarchy
- **T1.3** (2h): Update provider-specific factory functions (6 providers)
- **T1.4** (6h): Write 50+ configuration unit tests

**Dependencies**: None - can start immediately
**Blockers**: None
**Deliverable**: Extensible configuration system ready for playback modes

---

### Phase 2: Player Architecture (31 hours → 14 hours with parallelization)

#### TRACK A: Core Player Implementation (14 hours - Can execute in parallel with TRACK B)
- **T2.1** (3h): TimeProvider abstraction (RealtimeTimeProvider + SimulatedTimeProvider)
- **T2.2** (4h): BaseVastPlayer abstract base class with Template Method pattern
- **T2.3** (3h): VastPlayer refactor (inherit from BaseVastPlayer)
- **T2.4** (4h): HeadlessPlayer implementation (simulated playback with stochastic interruptions)

**Dependencies**: T1.4 complete (config system ready)
**Blockers**: None - tests can use mock configs
**Deliverable**: Unified player hierarchy with dual playback modes

#### TRACK B: Configuration Integration (5 hours - Can execute in parallel with TRACK A)
- **T2.5** (2h): Create vast_client/playback/config.py module
- **T2.6** (2h): ConfigResolver with 4-level precedence logic
- **T2.7** (1h): VastClient.get_playback_config() method

**Dependencies**: T1.2 complete (VastTrackerConfig.playback field)
**Blockers**: None - independent implementation
**Deliverable**: Configuration resolution system with precedence rules

#### Convergence: Integration (2 hours - Start after TRACK A/B complete)
- **T2.8** (2h): PlayerFactory integration, auto-mode detection, initialization patterns

**Dependencies**: T2.1-T2.7 complete
**Critical Path**: Cannot start until both tracks complete
**Deliverable**: Ready for Phase 3 testing

---

### Phase 3: Testing Suite (44 hours → 10-12 hours with parallelization)

- **T3.1-T3.6** (220+ unit tests): Component-level tests for all new classes
- **T3.7** (40 integration tests): Cross-component playback scenarios
- **T3.8** (30 e2e tests): Full workflow validation

**Test Coverage Target**: 95%+ core, 80%+ overall
**Dependencies**: Phase 2 complete
**Deliverable**: Comprehensive test suite (320+ tests total)

---

### Phase 4: Documentation (24 hours → 6 hours with parallelization)

- **T4.1**: Update ARCHITECTURE.md with playback layers
- **T4.2**: Update README.md with configuration reference
- **T4.3**: Create PLAYBACK_GUIDE.md comprehensive guide
- **T4.4**: Create examples/ directory (3 scenarios)
- **T4.5**: Validate all examples
- **T4.6**: API reference documentation

**Dependencies**: Phase 2-3 complete
**Deliverable**: Complete documentation suite

---

## Architecture Design

### 5-Layer System

```
Layer 1: Public API & Facade
├─ VastClient (orchestrator)
├─ VastParser (XML handling)
├─ VastTracker (event tracking)
└─ VastPlayer (playback controller)

Layer 2: Configuration & Context
├─ VastParserConfig
├─ VastTrackerConfig + PlaybackSessionConfig
├─ TrackingContext (DI container)
└─ ConfigResolver (4-level precedence)

Layer 3: Core Protocol & Domain
├─ Trackable protocol
├─ PlaybackSession (state management)
├─ PlaybackSessionState (serializable state)
└─ TimeProvider abstraction

Layer 4: Capability System
├─ @with_macros (macro substitution)
├─ @with_state (tracking state)
├─ @with_playback_state (playback state)
└─ @with_interruption (interruption handling)

Layer 5: HTTP & Networking
├─ EmbedHttpClient
├─ Connection pooling
└─ Timeout management
```

### Key Components to Implement

#### TimeProvider (New Abstraction)
```python
class TimeProvider(ABC):
    """Base class for pluggable time sources"""
    @abstractmethod
    def time(self) -> float: ...
    
    @abstractmethod
    async def sleep(self, seconds: float) -> None: ...

class RealtimeTimeProvider(TimeProvider):
    """Wall-clock time using asyncio.sleep()"""
    
class SimulatedTimeProvider(TimeProvider):
    """Virtual time with speed scaling (useful for testing)"""
    def __init__(self, speed: float = 1.0): ...
```

#### BaseVastPlayer (New Abstract Base)
```python
class BaseVastPlayer(ABC):
    """Abstract base for playback implementations"""
    
    @abstractmethod
    def _default_time_provider(self) -> TimeProvider: ...
    
    # Template Method pattern
    async def play(self) -> None:
        """Unified playback loop"""
        
    def pause(self) -> None: ...
    async def resume(self) -> None: ...
    def stop(self) -> None: ...
```

#### VastPlayer (Refactored Existing)
```python
class VastPlayer(BaseVastPlayer):
    """Real-time playback with wall-clock tracking"""
    
    def _default_time_provider(self) -> TimeProvider:
        return RealtimeTimeProvider()
```

#### HeadlessPlayer (New)
```python
class HeadlessPlayer(BaseVastPlayer):
    """Simulated playback with virtual time and stochastic interruptions"""
    
    def _default_time_provider(self) -> TimeProvider:
        return SimulatedTimeProvider(speed=config.playback.speed)
    
    async def play(self) -> PlaybackSession:
        """Returns session instead of void"""
```

#### PlaybackSessionConfig (New Configuration)
```python
@dataclass
class PlaybackSessionConfig:
    """Configuration for playback behavior"""
    mode: Literal['real', 'headless', 'auto'] = 'auto'
    
    # Interruption rules by provider
    interruption_rules: dict[str, InterruptionRule] = field(
        default_factory=lambda: {...}
    )
    
    # Playback options
    max_session_duration_sec: float = 300.0
    enable_auto_quartiles: bool = True
    quartile_offset_tolerance_sec: float = 0.5
    headless_tick_interval_sec: float = 0.1
    headless_playback_speed: float = 1.0
    
    # State management
    enable_session_persistence: bool = False
    emit_playback_events: bool = True
    log_tracking_urls: bool = False
```

#### PlaybackSession (New Domain Object)
```python
@dataclass
class PlaybackSession:
    """Captures playback state and history"""
    session_id: str
    duration_sec: float
    config: PlaybackSessionConfig
    
    status: PlaybackStatus  # pending|running|completed|closed|error
    current_offset_sec: float = 0.0
    start_time: float | None = None
    end_time: float | None = None
    
    events: list[PlaybackEvent] = field(default_factory=list)
    quartiles_tracked: set[int] = field(default_factory=set)
    interruption_scheduled: InterruptionReason | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Methods for state transitions
    def start(self) -> None: ...
    def advance(self, offset_sec: float) -> None: ...
    def close(self) -> None: ...
    def complete(self) -> None: ...
    def error(self, reason: str) -> None: ...
    def record_event(self, event: PlaybackEvent) -> None: ...
    def should_track_quartile(self, quartile: int) -> bool: ...
    def to_dict(self) -> dict: ...
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlaybackSession': ...
```

#### ConfigResolver (New Builder)
```python
class ConfigResolver:
    """Resolves playback configuration with 4-level precedence"""
    
    @staticmethod
    def resolve(
        mode: str | None = None,
        publisher: str | None = None,
        provider: str | None = None,
        global_config: PlaybackSessionConfig | None = None
    ) -> PlaybackSessionConfig:
        """
        Precedence order (highest to lowest):
        1. Per-player override (mode parameter)
        2. Publisher context
        3. Provider defaults (global, tiger, leto, yandex, google, custom)
        4. Global hardcoded defaults
        """
```

#### PlayerFactory (New Factory)
```python
class PlayerFactory:
    """Creates appropriate player instance"""
    
    @staticmethod
    def create(
        vast_client: VastClient,
        ad_data: dict,
        mode: str | None = None,
        config: PlaybackSessionConfig | None = None
    ) -> VastPlayer | HeadlessPlayer:
        """
        Auto-detects mode from config or environment
        Handles all initialization patterns
        """
```

---

## Configuration Hierarchy

### 4-Level Precedence System

```
Per-Player Override (Highest Priority)
    ↓ (overrides everything below)
Publisher Context
    ↓ (overrides provider + global)
Provider Defaults (global/tiger/leto/yandex/google/custom)
    ↓ (overrides global)
Global Hardcoded Defaults (Lowest Priority)
```

### Provider-Specific Interruption Rules

```python
{
    'global': {
        'start': {'probability': 0.05, 'min_offset_sec': 0, 'max_offset_sec': 1},
        'midpoint': {'probability': 0.10, 'min_offset_sec': 5, 'max_offset_sec': 15},
        'complete': {'probability': 0.15, 'min_offset_sec': 20, 'max_offset_sec': 25}
    },
    'tiger': {
        'start': {'probability': 0.02, 'min_offset_sec': 0, 'max_offset_sec': 0.5},
        # ... (very reliable, low interruption)
    },
    'leto': {
        'start': {'probability': 0.20, 'min_offset_sec': 0, 'max_offset_sec': 3},
        # ... (moderate reliability)
    },
    'yandex': {
        'start': {'probability': 0.25, 'min_offset_sec': 0, 'max_offset_sec': 5},
        # ... (lower reliability)
    },
    'google': {
        'start': {'probability': 0.08, 'min_offset_sec': 0, 'max_offset_sec': 1},
        # ... (high reliability)
    },
    'custom': {
        'start': {'probability': 0.15, 'min_offset_sec': 0, 'max_offset_sec': 3},
        # ... (configurable)
    }
}
```

---

## Task Dependency Graph

```
Phase 1 (Sequential - 15 hours)
│
├─ T1.1: PlaybackSessionConfig → T1.2
├─ T1.2: VastTrackerConfig.playback → T1.3
├─ T1.3: Provider factories → T1.4
└─ T1.4: Config tests → Gate to Phase 2

Phase 2 (Parallel - 31 hours → 14 hours actual)
│
├─ TRACK A (14 hours parallel with TRACK B)
│  ├─ T2.1: TimeProvider abstraction
│  ├─ T2.2: BaseVastPlayer (depends on T2.1)
│  ├─ T2.3: VastPlayer refactor (depends on T2.2)
│  └─ T2.4: HeadlessPlayer (depends on T2.2)
│
├─ TRACK B (5 hours parallel with TRACK A)
│  ├─ T2.5: playback/config.py module
│  ├─ T2.6: ConfigResolver (depends on T2.5)
│  └─ T2.7: VastClient integration (depends on T2.6)
│
└─ T2.8: PlayerFactory (depends on TRACK A + TRACK B complete)

Phase 3 & 4 (Parallel - 68 hours → 16-18 hours actual)
│
├─ T3.1-T3.8: Testing suite (44 hours → 10-12 hours)
└─ T4.1-T4.6: Documentation (24 hours → 6 hours)
```

---

## Testing Strategy

### Test Suite Breakdown

| Category | Count | Scope |
|----------|-------|-------|
| Config Tests | 50 | PlaybackSessionConfig, VastTrackerConfig, ConfigResolver |
| TimeProvider Tests | 30 | RealtimeTimeProvider, SimulatedTimeProvider, time progression |
| BaseVastPlayer Tests | 40 | Abstract methods, template method pattern, state transitions |
| VastPlayer Tests | 60 | Real-time playback, quartile tracking, tracking integration |
| HeadlessPlayer Tests | 50 | Simulated playback, interruptions, session recording |
| PlaybackSession Tests | 35 | State management, serialization, event recording |
| PlayerFactory Tests | 15 | Mode detection, initialization patterns, config resolution |
| Unit Subtotal | **250+** | Core functionality |
| Integration Tests | 40 | Cross-component workflows, config precedence, state persistence |
| E2E Tests | 30 | Full VAST workflows (real + headless), tracking validation |
| **Total** | **320+** | Complete coverage |

### Test Patterns

```python
# Config precedence test example
def test_playback_config_precedence_per_player_overrides_provider():
    """Verify per-player override takes precedence over provider"""
    resolver = ConfigResolver()
    config = resolver.resolve(
        mode='headless',  # per-player override
        provider='tiger',  # provider default
        global_config=DEFAULT_CONFIG
    )
    assert config.mode == 'headless'
    assert config.interruption_rules == get_provider_rules('tiger')

# Real vs headless comparison test
@pytest.mark.asyncio
async def test_real_and_headless_produce_same_event_sequence():
    """Verify both playback modes generate identical tracking events"""
    ad_data = create_test_ad(duration=30)
    
    # Real playback (mock time)
    real_player = VastPlayer(mock_client, ad_data)
    real_events = await real_player.play()
    
    # Headless playback
    headless_player = HeadlessPlayer(mock_client, ad_data, mode='fast')
    session = await headless_player.play()
    headless_events = [e.event_type for e in session.events]
    
    # Both should track quartiles
    assert 'start' in real_events
    assert 'midpoint' in real_events
    assert 'complete' in real_events
    assert 'start' in headless_events
    assert 'midpoint' in headless_events
    assert 'complete' in headless_events
```

---

## Code Examples

### Example 1: Real-Time Playback (Existing Pattern, Refactored)

```python
from vast_client import VastClient, VastPlayer

async def play_ad_realtime():
    client = VastClient("https://ads.example.com/vast")
    ad_data = await client.request_ad()
    
    # Existing code still works (backward compatible)
    player = VastPlayer(client, ad_data)
    await player.play()
    
    print(f"Playback complete: {player.playback_seconds}s")
```

### Example 2: Headless Simulation (New Pattern)

```python
from vast_client import VastClient
from vast_client.playback import PlayerFactory

async def simulate_ad_playback():
    client = VastClient("https://ads.example.com/vast")
    ad_data = await client.request_ad()
    
    # Create headless player with custom config
    player = PlayerFactory.create(
        client, 
        ad_data,
        mode='headless',
        config=PlaybackSessionConfig(
            mode='headless',
            headless_playback_speed=2.0,  # 2x speed
            enable_session_persistence=True
        )
    )
    
    # Returns session instead of void
    session = await player.play()
    
    # Session captures all events and state
    print(f"Session ID: {session.session_id}")
    print(f"Duration: {session.duration_sec}s")
    print(f"Events recorded: {len(session.events)}")
    print(f"Quartiles: {session.quartiles_tracked}")
    
    # Session can be serialized for analysis
    import json
    session_dict = session.to_dict()
    # json.dump(session_dict, open("session.json", "w"))
```

### Example 3: Configuration Precedence

```python
from vast_client.playback import ConfigResolver, PlaybackSessionConfig

# Global defaults
global_config = PlaybackSessionConfig(
    mode='auto',
    headless_playback_speed=1.0
)

# Resolve with precedence
config = ConfigResolver.resolve(
    mode='headless',           # Per-player: HIGHEST
    publisher='my_publisher',  # Publisher context
    provider='tiger',          # Provider defaults
    global_config=global_config  # Global: LOWEST
)

# Result: mode='headless' (from mode parameter)
# Interruption rules: from provider 'tiger'
# All other settings: from global_config or provider defaults
```

---

## Parallelization Strategy

### Team Execution (2 developers)

**Developer A (TimeProvider + BaseVastPlayer)**
- T2.1: TimeProvider implementation (3h)
- T2.2: BaseVastPlayer abstract class (4h)
- T2.3: VastPlayer refactor (3h)
- T2.4: HeadlessPlayer implementation (4h)
- **Subtotal: 14 hours**

**Developer B (Configuration System)**
- T2.5: playback/config.py module (2h)
- T2.6: ConfigResolver builder (2h)
- T2.7: VastClient integration (1h)
- **Subtotal: 5 hours**

**Then (Convergence)**
- Both: T2.8 PlayerFactory integration (2h)

**Time Savings**: 31h sequential → 14h actual = 17 hours saved (55% efficiency gain)

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Quartile tracking assumes continuous time | Medium | TimeProvider abstraction handles both; cross-validation tests |
| Real/headless event sequence divergence | Medium | Integration tests verify identical event ordering |
| Configuration precedence complexity | Medium | 25+ precedence tests validate all scenarios |
| Session persistence overhead | Low | Feature-gated via environment variable |
| Breaking changes to VastPlayer API | Medium | Inherit from BaseVastPlayer; public interface unchanged |
| Interruption stochasticity in tests | Low | Use seeded random, record event sequences |
| Performance regression from abstraction layers | Low | Benchmark real vs simulated; target <5% overhead |

---

## GitHub Submodule Integration

### Current State
- Location: `/home/pv/middleware/src/ctv_middleware/vast_client/` (embedded directory)
- Status: Production-ready, 4,500+ lines of code
- Files: 12 core modules + 3 documentation files

### Extraction Plan
1. Create standalone GitHub repo: `github.com/ormwish/vast-client`
2. Push current code with v1.0.0 tag
3. Add `.gitignore`, `LICENSE`, `pyproject.toml` for packaging
4. Remove from middleware git tracking: `git rm --cached src/ctv_middleware/vast_client`
5. Create `.gitmodules` file
6. Add submodule: `git submodule add https://github.com/ormwish/vast-client src/ctv_middleware/vast_client`
7. Test fresh clone with `git clone --recursive`
8. Update middleware `pyproject.toml` to depend on submodule
9. Update GitHub Actions workflows to initialize submodules

**Duration**: 14 hours (Phase 1-2 of submodule work)

---

## Backward Compatibility

✅ **VastPlayer public interface unchanged**
- Existing code: `player = VastPlayer(client, ad_data); await player.play()` still works
- New inheritance: VastPlayer inherits from BaseVastPlayer (internal change)
- No breaking changes to public methods or parameters

✅ **Configuration backward compatible**
- PlaybackSessionConfig optional field in VastTrackerConfig
- Defaults to 'real' mode for existing code
- No changes to existing VastParserConfig or VastTrackerConfig fields

✅ **Gradual migration path**
- Old: `VastPlayer(client, ad_data)`
- New: `PlayerFactory.create(client, ad_data, mode='headless')`
- Both work simultaneously during transition

---

## Success Criteria

### Definition of Done

- [ ] All 320+ tests passing (95%+ core coverage)
- [ ] TimeProvider abstraction working with both implementations
- [ ] BaseVastPlayer → VastPlayer/HeadlessPlayer hierarchy functional
- [ ] Configuration precedence tested across all 4 levels
- [ ] PlaybackSession serialization/deserialization working
- [ ] ARCHITECTURE.md updated with playback layers
- [ ] README.md includes configuration reference + quick-start examples
- [ ] PLAYBACK_GUIDE.md created with comprehensive coverage
- [ ] 3 example scenarios documented and working
- [ ] Backward compatibility verified with existing code
- [ ] All pre-commit hooks passing
- [ ] GitHub submodule integration tested
- [ ] Team documentation and training complete

---

## Next Steps

1. **Review & Approve** this architecture (30 min)
2. **Create GitHub repository** for standalone vast-client (2 hours)
3. **Integrate submodule** into middleware (2 hours)
4. **Begin Phase 1** with configuration foundation (15 hours sequential)
5. **Execute Phase 2** with parallel tracks TRACK A/B (14 hours actual)
6. **Run Phase 3-4** in parallel (16-18 hours actual)
7. **Total completion**: 3-4 dev-weeks with team of 2 developers
