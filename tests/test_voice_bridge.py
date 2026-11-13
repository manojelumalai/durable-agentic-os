"""Unit tests for LiveKit WebRTC Voice Streaming Bridge and turn-taking latency."""

import time

import pytest

from durable_agent.voice.stream_bridge import LiveKitVoiceBridge, VoiceEvent


def test_voice_turn_taking_latency_under_sla() -> None:
    bridge = LiveKitVoiceBridge(session_id="session-test-01", target_latency_budget_ms=500.0)

    # 1. User starts speaking
    start_evt = bridge.on_user_speech_started()
    assert start_evt["event"] == VoiceEvent.SPEECH_STARTED.value
    assert start_evt["barge_in"] is False

    time.sleep(0.05)  # User speaks for 50ms

    # 2. User stops speaking
    stop_evt = bridge.on_user_speech_stopped()
    assert stop_evt["event"] == VoiceEvent.SPEECH_STOPPED.value
    assert stop_evt["speech_duration_ms"] >= 45.0

    time.sleep(0.02)  # 20ms processing latency

    # 3. Agent response initiated with TTFT of 120ms
    telemetry = bridge.record_agent_response_start(ttft_ms=120.0)
    assert telemetry.session_id == "session-test-01"
    assert telemetry.within_target_sla is True
    assert telemetry.turn_taking_latency_ms < 500.0


def test_barge_in_interruption_cuts_off_agent() -> None:
    bridge = LiveKitVoiceBridge(session_id="session-bargein-01")

    # Set agent to actively speaking
    bridge.is_agent_speaking = True

    # User interrupts by speaking
    interruption = bridge.on_user_speech_started()
    assert interruption["event"] == VoiceEvent.BARGE_IN_INTERRUPTION.value
    assert interruption["barge_in"] is True
    assert bridge.is_agent_speaking is False


@pytest.mark.asyncio
async def test_stream_audio_chunks_aborts_on_interruption() -> None:
    bridge = LiveKitVoiceBridge(session_id="session-stream-01")
    bridge.is_agent_speaking = True

    fake_audio = b"\x00" * 4096  # 4KB audio
    chunks = []

    async for chunk in bridge.stream_audio_chunks(fake_audio, chunk_size=1024):
        chunks.append(chunk)
        if len(chunks) == 2:
            # Simulate interruption after 2 chunks
            bridge.on_user_speech_started()

    # Streaming should have aborted early (only 2 chunks received out of 4)
    assert len(chunks) == 2
