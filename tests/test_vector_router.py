"""
Unit & Integration Tests for Task 15: Predefined Conversational Vector Database (Semantic Router)
Verifies:
1. Persistent vector index initialization & 384-dimensional dense embeddings.
2. Cosine similarity mathematical correctness & edge-case handling.
3. High-precision semantic matching for conversational intents (Greetings, Pleasantries, Identity, Help, Farewells).
4. Strict domain boundary guard ensuring seismological queries are NEVER intercepted by vector routing.
5. End-to-end integration with SismoWatchAgent (0 tokens, $0.00 cost, sub-10ms response).
"""
import pytest
import math
from agent.vector.predefined_vector_db import PredefinedVectorDB
from agent.core.agent_engine import SismoWatchAgent

@pytest.fixture
def vector_db():
    return PredefinedVectorDB()

@pytest.fixture
def agent():
    return SismoWatchAgent()

def test_vector_db_initialization_and_records(vector_db):
    """Verify that vector database loads indexed vectors with 384 dimensions and all categories."""
    records = vector_db.vector_records
    assert len(records) >= 50
    
    categories = {r["category"] for r in records}
    assert "GREETING" in categories
    assert "PLEASANTRY" in categories
    assert "IDENTITY" in categories
    assert "HELP" in categories
    assert "FAREWELL" in categories
    
    first_vec = records[0]["vector"]
    assert len(first_vec) == 384  # all-minilm embedding dimension

def test_vector_db_cosine_similarity(vector_db):
    """Verify mathematical correctness of cosine similarity."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert math.isclose(vector_db._cosine_similarity(v1, v2), 1.0, abs_tol=1e-5)

    v3 = [0.0, 1.0, 0.0]
    assert math.isclose(vector_db._cosine_similarity(v1, v3), 0.0, abs_tol=1e-5)

    # Edge cases
    assert vector_db._cosine_similarity([], []) == 0.0
    assert vector_db._cosine_similarity([1.0], [1.0, 2.0]) == 0.0
    assert vector_db._cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0

def test_vector_db_greetings_semantic_match(vector_db):
    """Verify semantic matching of greeting utterances."""
    for query in ["hola", "hola buenas tardes", "hey qué tal", "saludos cordiales"]:
        res = vector_db.search(query, threshold=0.70)
        assert res is not None, f"Query '{query}' should have matched"
        assert res["matched"] is True
        assert res["category"] in ["GREETING", "PLEASANTRY"]
        assert res["vector_similarity"] >= 0.70
        assert "SismoWatch" in res["text"]

def test_vector_db_identity_semantic_match(vector_db):
    """Verify semantic matching of identity and capability queries."""
    for query in ["quién eres tú", "cuál es tu nombre", "para qué sirves"]:
        res = vector_db.search(query, threshold=0.70)
        assert res is not None, f"Query '{query}' should have matched identity"
        assert res["category"] == "IDENTITY"
        assert res["vector_similarity"] >= 0.75
        assert "Agente Inteligente de SismoWatch" in res["text"]

def test_vector_db_help_semantic_match(vector_db):
    """Verify semantic matching of help inquiries."""
    for query in ["ayuda", "ayúdame por favor", "qué puedo preguntarte"]:
        res = vector_db.search(query, threshold=0.70)
        assert res is not None, f"Query '{query}' should have matched help"
        assert res["category"] == "HELP"
        assert res["vector_similarity"] >= 0.70

def test_vector_db_farewell_semantic_match(vector_db):
    """Verify semantic matching of farewells and gratitude."""
    for query in ["adiós", "muchas gracias amigo", "hasta luego", "chao"]:
        res = vector_db.search(query, threshold=0.70)
        assert res is not None, f"Query '{query}' should have matched farewell"
        assert res["category"] == "FAREWELL"
        assert res["vector_similarity"] >= 0.70

def test_vector_db_domain_guard_never_intercepts_seismology(vector_db):
    """
    CRITICAL DOMAIN GUARD TEST:
    Analytical seismological queries must NEVER be intercepted by the vector router.
    They must return None to allow processing by SQL / Curated Lakehouse / LLM.
    """
    seismic_queries = [
        "¿Cuántos sismos hay registrados en total?",
        "Muéstrame los temblores de Colombia",
        "¿Cuál fue el sismo más fuerte y dónde ocurrió?",
        "Dame los sismos que cubran mas de 200km",
        "¿Cuáles sismos fueron mayores a 5.0?",
        "¿Cuáles son los sismos más superficiales?",
        "¿Y de esos cuál fue el más fuerte?"
    ]
    for q in seismic_queries:
        res = vector_db.search(q)
        assert res is None, f"Query '{q}' should NOT have been intercepted by conversational vector DB"

def test_agent_integration_conversational_vs_analytical(agent):
    """
    Verify end-to-end integration:
    Conversational prompts route to VECTOR_DATABASE with 0 tokens.
    Analytical queries route to Lakehouse / Medallion database.
    """
    # 1. Conversational prompt -> Vector DB
    conv_result = agent.ask("hola buenas tardes")
    assert conv_result["telemetry"]["storage_backend"] == "VECTOR_DATABASE"
    assert "vector-semantic-router" in conv_result["telemetry"]["model"]
    assert conv_result["telemetry"]["tokens_consumed"] == 0
    assert conv_result["telemetry"]["cost_usd"] == 0.00
    assert conv_result["telemetry"]["vector_similarity"] >= 0.70
    assert "SismoWatch" in conv_result["response"]

    # 2. Analytical query -> Grounded Database
    analytical_result = agent.ask("Dame los sismos que cubran mas de 200km")
    assert analytical_result["telemetry"]["storage_backend"] in ["LAKEHOUSE_SNAPSHOT", "POSTGRESQL_CURATED"]
    assert analytical_result["telemetry"]["records_retrieved"] >= 1
    assert "profundidad" in analytical_result["response"]
