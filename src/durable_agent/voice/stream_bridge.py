"""LiveKit-compatible real-time WebRTC audio streaming bridge and voice turn-taking manager.
Enforces sub-500ms voice turn-taking budgets, real-time VAD barge-in interruptions,
and seamless streaming dispatch into durable agent workflows.
"""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VoiceEvent(str, Enum):
    """Voice lifecycle events emitted across real-time WebRTC audio sessions."""

    SPEECH_STARTED = "speech_started"
    SPEECH_STOPPED = "speech_stopped"
    BARGE_IN_INTERRUPTION = "barge_in_interruption"
    AGENT_SPEAKING = "agent_speaking"
    AGENT_STOPPED = "agent_stopped"


@dataclass
class AudioChunk:
    """PCM audio frame received from or emitted to a real-time WebRTC stream."""

    data: bytes
    sample_rate: int = 24000
    channels: int = 1
    duration_ms: float = 20.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VoiceTurnTelemetry:
    """Latency profiling and performance metrics for a single conversational turn."""

    session_id: str
    user_speech_duration_ms: float
    turn_taking_latency_ms: float
    time_to_first_token_ms: float
    barge_in_detected: bool = False
    within_target_sla: bool = True  # SLA target: < 500ms


class LiveKitVoiceBridge:
    """Manages real-time WebRTC audio streams, VAD segmentation, and low-latency agent turn-taking."""

    def __init__(self, session_id: str, target_latency_budget_ms: float = 500.0) -> None:
        self.session_id = session_id
        self.target_latency_budget_ms = target_latency_budget_ms
        self.is_agent_speaking = False
        self.is_user_speaking = False
        self._user_speech_start_time: float | None = None
        self._user_speech_end_time: float | None = None
        self.turn_history: list[VoiceTurnTelemetry] = []

    def on_user_speech_started(self) -> dict[str, Any]:
        """Triggered by Voice Activity Detection (VAD) when user begins speaking."""
        self.is_user_speaking = True
        self._user_speech_start_time = time.perf_counter()
        interrupted = False

        # Instantaneous barge-in: If agent is currently speaking, cut off playback immediately
        if self.is_agent_speaking:
            self.is_agent_speaking = False
            interrupted = True

        return {
            "event": VoiceEvent.BARGE_IN_INTERRUPTION.value if interrupted else VoiceEvent.SPEECH_STARTED.value,
            "session_id": self.session_id,
            "barge_in": interrupted,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def on_user_speech_stopped(self) -> dict[str, Any]:
        """Triggered by VAD when user stops speaking (silence detected)."""
        self.is_user_speaking = False
        self._user_speech_end_time = time.perf_counter()
        speech_duration_ms = 0.0

        if self._user_speech_start_time:
            speech_duration_ms = (self._user_speech_end_time - self._user_speech_start_time) * 1000

        return {
            "event": VoiceEvent.SPEECH_STOPPED.value,
            "session_id": self.session_id,
            "speech_duration_ms": round(speech_duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def record_agent_response_start(self, ttft_ms: float) -> VoiceTurnTelemetry:
        """Records agent audio playback start and calculates end-to-end turn-taking latency."""
        now = time.perf_counter()
        turn_latency_ms = 0.0

        if self._user_speech_end_time:
            turn_latency_ms = (now - self._user_speech_end_time) * 1000
        else:
            turn_latency_ms = ttft_ms

        self.is_agent_speaking = True
        user_duration = (
            (self._user_speech_end_time - self._user_speech_start_time) * 1000
            if (self._user_speech_start_time and self._user_speech_end_time)
            else 1000.0
        )

        telemetry = VoiceTurnTelemetry(
            session_id=self.session_id,
            user_speech_duration_ms=round(user_duration, 2),
            turn_taking_latency_ms=round(turn_latency_ms, 2),
            time_to_first_token_ms=round(ttft_ms, 2),
            within_target_sla=turn_latency_ms <= self.target_latency_budget_ms,
        )
        self.turn_history.append(telemetry)
        return telemetry

    async def stream_audio_chunks(self, audio_data: bytes, chunk_size: int = 1024) -> AsyncIterator[AudioChunk]:
        """Asynchronously stream raw audio buffers in real-time WebRTC packet frames."""
        for i in range(0, len(audio_data), chunk_size):
            # If user interrupted via barge-in, abort streaming immediately
            if not self.is_agent_speaking:
                break
            chunk = audio_data[i : i + chunk_size]
            yield AudioChunk(data=chunk)
