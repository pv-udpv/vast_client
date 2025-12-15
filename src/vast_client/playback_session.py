"""
Playback Session Domain Object

Manages playback state, progress tracking, and event recording for ad playback sessions.
Supports both real-time and simulated (headless) playback modes with optional persistence.
"""

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .log_config import get_context_logger


class PlaybackStatus(str, Enum):
    """Playback session status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CLOSED = "closed"
    ERROR = "error"


class PlaybackEventType(str, Enum):
    """Types of playback events that can be recorded."""
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    QUARTILE = "quartile"
    PROGRESS = "progress"
    INTERRUPT = "interrupt"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class PlaybackEvent:
    """Individual playback event record."""

    timestamp: float  # Unix timestamp
    event_type: PlaybackEventType
    offset_sec: float  # Offset from session start
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type.value,
            'offset_sec': self.offset_sec,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PlaybackEvent':
        """Create event from dictionary."""
        return cls(
            timestamp=data['timestamp'],
            event_type=PlaybackEventType(data['event_type']),
            offset_sec=data['offset_sec'],
            metadata=data.get('metadata', {}),
        )


@dataclass
class QuartileTracker:
    """Tracks which quartiles have been recorded."""

    start: bool = False
    first_quartile: bool = False
    midpoint: bool = False
    third_quartile: bool = False
    complete: bool = False

    def to_dict(self) -> dict[str, bool]:
        """Convert to dictionary."""
        return {
            'start': self.start,
            'firstQuartile': self.first_quartile,
            'midpoint': self.midpoint,
            'thirdQuartile': self.third_quartile,
            'complete': self.complete,
        }

    @classmethod
    def from_dict(cls, data: dict[str, bool]) -> 'QuartileTracker':
        """Create from dictionary."""
        return cls(
            start=data.get('start', False),
            first_quartile=data.get('firstQuartile', False),
            midpoint=data.get('midpoint', False),
            third_quartile=data.get('thirdQuartile', False),
            complete=data.get('complete', False),
        )

    def mark_quartile(self, quartile_num: int) -> None:
        """Mark a quartile as tracked."""
        if quartile_num == 0:
            self.start = True
        elif quartile_num == 1:
            self.first_quartile = True
        elif quartile_num == 2:
            self.midpoint = True
        elif quartile_num == 3:
            self.third_quartile = True
        elif quartile_num == 4:
            self.complete = True

    def is_quartile_tracked(self, quartile_num: int) -> bool:
        """Check if a quartile has been tracked."""
        if quartile_num == 0:
            return self.start
        elif quartile_num == 1:
            return self.first_quartile
        elif quartile_num == 2:
            return self.midpoint
        elif quartile_num == 3:
            return self.third_quartile
        elif quartile_num == 4:
            return self.complete
        return False


@dataclass
class PlaybackSession:
    """
    Domain object representing a single ad playback session.

    Tracks playback progress, events, quartiles, interruptions, and metadata.
    Supports serialization for persistence and recovery.

    Attributes:
        session_id: Unique session identifier
        ad_id: Creative/ad identifier
        duration_sec: Total duration of ad in seconds
        status: Current playback status
        start_time: Unix timestamp when session started
        end_time: Unix timestamp when session ended (if completed)
        current_offset_sec: Current playback position in seconds
        events: List of recorded playback events
        quartiles: Quartile tracking status
        interruption_type: Type of interruption if session was interrupted
        interruption_offset_sec: Offset where interruption occurred
        metadata: Additional session metadata
    """

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ad_id: str = ""
    duration_sec: float = 0.0
    status: PlaybackStatus = PlaybackStatus.PENDING
    start_time: float = 0.0
    end_time: float | None = None
    current_offset_sec: float = 0.0
    events: list[PlaybackEvent] = field(default_factory=list)
    quartiles: QuartileTracker = field(default_factory=QuartileTracker)
    interruption_type: str = ""
    interruption_offset_sec: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    logger: Any = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Initialize logger after dataclass initialization."""
        if self.logger is None:
            self.logger = get_context_logger("playback_session")

    def start(self, start_time: float) -> None:
        """Start the playback session."""
        if self.status != PlaybackStatus.PENDING:
            self.logger.warning(
                "Session already started",
                session_id=self.session_id,
                current_status=self.status.value
            )
            return

        self.status = PlaybackStatus.RUNNING
        self.start_time = start_time
        self.logger.info("Session started", session_id=self.session_id)

    def advance(self, offset_sec: float, current_time: float) -> None:
        """Advance playback position."""
        if self.status != PlaybackStatus.RUNNING:
            return

        self.current_offset_sec = offset_sec

        # Check if we've reached completion
        if offset_sec >= self.duration_sec:
            self.complete(current_time)

    def record_event(
        self,
        event_type: PlaybackEventType,
        offset_sec: float,
        current_time: float,
        metadata: dict[str, Any] | None = None
    ) -> PlaybackEvent:
        """Record a playback event."""
        event = PlaybackEvent(
            timestamp=current_time,
            event_type=event_type,
            offset_sec=offset_sec,
            metadata=metadata or {},
        )
        self.events.append(event)

        self.logger.info(
            "Event recorded",
            session_id=self.session_id,
            event_type=event_type.value,
            offset_sec=offset_sec
        )

        return event

    def should_track_quartile(self, quartile_num: int) -> bool:
        """Check if a quartile should be tracked."""
        return not self.quartiles.is_quartile_tracked(quartile_num)

    def mark_quartile_tracked(self, quartile_num: int, current_time: float) -> None:
        """Mark a quartile as tracked and record event."""
        self.quartiles.mark_quartile(quartile_num)

        quartile_names = {
            0: "start",
            1: "firstQuartile",
            2: "midpoint",
            3: "thirdQuartile",
            4: "complete",
        }

        self.record_event(
            PlaybackEventType.QUARTILE,
            self.current_offset_sec,
            current_time,
            metadata={'quartile': quartile_num, 'name': quartile_names.get(quartile_num, 'unknown')}
        )

    def interrupt(
        self,
        interruption_type: str,
        offset_sec: float,
        current_time: float
    ) -> None:
        """Record a playback interruption."""
        if self.status == PlaybackStatus.RUNNING:
            self.status = PlaybackStatus.CLOSED
            self.end_time = current_time
            self.interruption_type = interruption_type
            self.interruption_offset_sec = offset_sec

            self.record_event(
                PlaybackEventType.INTERRUPT,
                offset_sec,
                current_time,
                metadata={'interruption_type': interruption_type}
            )

            self.logger.info(
                "Session interrupted",
                session_id=self.session_id,
                interruption_type=interruption_type,
                offset_sec=offset_sec
            )

    def complete(self, current_time: float) -> None:
        """Mark session as successfully completed."""
        if self.status == PlaybackStatus.RUNNING:
            self.status = PlaybackStatus.COMPLETED
            self.end_time = current_time
            self.current_offset_sec = self.duration_sec

            self.record_event(
                PlaybackEventType.COMPLETE,
                self.duration_sec,
                current_time
            )

            self.logger.info(
                "Session completed",
                session_id=self.session_id,
                total_duration=self.duration_sec
            )

    def error(self, error_message: str, current_time: float) -> None:
        """Mark session with error."""
        self.status = PlaybackStatus.ERROR
        self.end_time = current_time

        self.record_event(
            PlaybackEventType.ERROR,
            self.current_offset_sec,
            current_time,
            metadata={'error': error_message}
        )

        self.logger.error(
            "Session error",
            session_id=self.session_id,
            error=error_message
        )

    def duration(self) -> float:
        """Get session duration in seconds."""
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    def to_dict(self) -> dict[str, Any]:
        """Serialize session to dictionary."""
        return {
            'session_id': self.session_id,
            'ad_id': self.ad_id,
            'duration_sec': self.duration_sec,
            'status': self.status.value,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'current_offset_sec': self.current_offset_sec,
            'events': [event.to_dict() for event in self.events],
            'quartiles': self.quartiles.to_dict(),
            'interruption_type': self.interruption_type,
            'interruption_offset_sec': self.interruption_offset_sec,
            'metadata': self.metadata,
        }

    def to_json(self) -> str:
        """Serialize session to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'PlaybackSession':
        """Create session from dictionary."""
        session = cls(
            session_id=data.get('session_id', str(uuid.uuid4())),
            ad_id=data.get('ad_id', ''),
            duration_sec=data.get('duration_sec', 0.0),
            status=PlaybackStatus(data.get('status', 'pending')),
            start_time=data.get('start_time', 0.0),
            end_time=data.get('end_time'),
            current_offset_sec=data.get('current_offset_sec', 0.0),
            events=[PlaybackEvent.from_dict(e) for e in data.get('events', [])],
            quartiles=QuartileTracker.from_dict(data.get('quartiles', {})),
            interruption_type=data.get('interruption_type', ''),
            interruption_offset_sec=data.get('interruption_offset_sec', 0.0),
            metadata=data.get('metadata', {}),
        )
        return session

    @classmethod
    def from_json(cls, json_str: str) -> 'PlaybackSession':
        """Create session from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


__all__ = [
    "PlaybackStatus",
    "PlaybackEventType",
    "PlaybackEvent",
    "QuartileTracker",
    "PlaybackSession",
]
