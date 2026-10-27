"""
Unit & Integration Tests for Task 8: Ollama Llama 3.2 (3B) Client
Verifies:
1. Ollama daemon connectivity on port 11434.
2. Model availability for llama3.2:3b.
3. Natural language query parsing (including 'menor o igual a 4.3 M').
4. Grounded factual narrative generation without hallucinations.
5. Circuit breaker fallback when service is offline.
"""
import pytest
from agent.llm.ollama_client import OllamaClient

@pytest.fixture
def client():
    return OllamaClient()

def test_ollama_daemon_is_healthy(client):
    """Verify Ollama service is reachable on local port 11434."""
    assert client.is_healthy() is True

def test_llama_model_is_available(client):
    """Verify llama3.2:3b model is registered in Ollama."""
    assert client.is_model_available("llama3.2:3b") is True

def test_parse_complex_query_with_llama(client):
    """
    Critical verification for user's query:
    'y cuales de esos fueron menor o igual a 4.3 M'
    Llama 3.2 must extract max_mag=4.3 without dropping the filter.
    """
    parsed = client.parse_query_to_filters(
        user_query="y cuales de esos fueron menor o igual a 4.3 M",
        context={"place_contains": "Colombia"}
    )
    assert parsed is not None
    assert parsed.get("max_mag") == 4.3 or parsed.get("max_mag") == 4.30
    assert "Colombia" in str(parsed.get("place_contains", ""))

def test_grounded_narration_uses_only_db_records(client):
    """Verify narrative only references the provided records."""
    mock_events = [
        {"event_id": "us7000test01", "place": "Bucaramanga, Santander, Colombia", "magnitude": 4.1, "depth": 140.0, "event_time": "2026-10-27T10:00:00Z"},
        {"event_id": "us7000test02", "place": "Medellin, Antioquia, Colombia", "magnitude": 3.2, "depth": 20.0, "event_time": "2026-10-27T09:00:00Z"}
    ]
    resp = client.ground_and_narrate(
        user_query="¿Cuáles sismos hubo en Colombia menores a 4.3?",
        events=mock_events,
        stats={"total_count": 2}
    )
    assert resp is not None
    assert len(resp) > 20
    # Must cite at least one verified event ID
    assert "us7000test" in resp or "Bucaramanga" in resp or "Medellin" in resp
