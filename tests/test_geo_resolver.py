"""
Unit & Integration Tests for Task 16: Geopolitical Territory Resolution & Complete Information Delivery
Verifies:
1. GeoEntityResolver correctly maps US states, postal codes, and territories.
2. Comma-based disambiguation guarantees 0 false positives for international events (e.g. Chile, Australia).
3. Country disambiguation: New Mexico is US, NOT the country of Mexico.
4. CuratedDataClient multi-alias queries for United States ('Estados Unidos', 'EEUU', 'USA').
5. Negation handling ('fuera de Estados Unidos') retrieving 100% international events.
6. End-to-end AI Agent delivering complete structured information (count, subregion breakdown, top event, full list).
7. Grammar integrity: elimination of 'con en la región' typo.
"""
import pytest
from agent.core.geo_resolver import GeoEntityResolver
from agent.database.curated_client import CuratedDataClient
from agent.core.agent_engine import SismoWatchAgent

@pytest.fixture
def db_client():
    return CuratedDataClient()

@pytest.fixture
def agent():
    return SismoWatchAgent()

def test_geo_resolver_us_states_and_postal_codes():
    """Verify standard USGS US place patterns are identified accurately."""
    us_samples = [
        "13 km NE of Hollister, CA",
        "5 km SE of Pāhala, Hawaii",
        "43 km NW of Tatitlek, Alaska",
        "14 km ESE of Pearsall, Texas",
        "13 km SSW of Alamo, Nevada",
        "5 km NW of Saratoga Springs, Utah",
        "17 km SE of Waynoka, Oklahoma",
        "39 km WSW of Stella, Puerto Rico",
        "30 km N of Charlotte Amalie, U.S. Virgin Islands",
        "19 km ENE of West Yellowstone, Montana",
        "37 km ESE of Malaga, New Mexico"
    ]
    for place in us_samples:
        is_us, subregion = GeoEntityResolver.is_us_event(place)
        assert is_us is True, f"'{place}' should be identified as US"
        assert subregion is not None

def test_geo_resolver_international_not_confused_with_us():
    """CRITICAL DISAMBIGUATION TEST: Foreign locations with 'LA', 'NE', etc. must NOT match US."""
    international_samples = [
        "100 km E of La Tirana, Chile",
        "20 km NNW of La Ligua, Chile",
        "9 km NE of Korumburra, Australia",
        "27 km W of Río Grande, Panama",
        "128 km S of Pundong, Indonesia",
        "5 km ENE of Tierra y Libertad, Mexico",
        "100 km W of El Aguilar, Argentina",
        "191 km NW of Port-Olry, Vanuatu",
        "95 km NNE of Hihifo, Tonga",
        "203 km SSE of Tateyama, Japan",
        "south of the Fiji Islands"
    ]
    for place in international_samples:
        is_us, _ = GeoEntityResolver.is_us_event(place)
        assert is_us is False, f"'{place}' should NOT be identified as US"

def test_geo_resolver_mexico_vs_new_mexico_disambiguation():
    """Verify New Mexico belongs to US, not to the country of Mexico."""
    nm_place = "37 km ESE of Malaga, New Mexico"
    mx_place = "5 km ENE of Tierra y Libertad, Mexico"
    bc_place = "11 km WSW of Delta, B.C., MX"

    # Mexico query
    assert GeoEntityResolver.matches_territory(mx_place, "México") is True
    assert GeoEntityResolver.matches_territory(bc_place, "México") is True
    assert GeoEntityResolver.matches_territory(nm_place, "México") is False

    # US query
    assert GeoEntityResolver.matches_territory(nm_place, "Estados Unidos") is True
    assert GeoEntityResolver.matches_territory(mx_place, "Estados Unidos") is False

def test_curated_client_us_queries(db_client):
    """Verify CuratedDataClient queries for United States with multiple aliases return full count."""
    aliases = ["Estados Unidos", "EEUU", "USA", "territorio de estados unidos"]
    expected_count = None

    for alias in aliases:
        events, _ = db_client.query_events(place_contains=alias)
        assert len(events) >= 150, f"Alias '{alias}' should return at least 150 events in US"
        if expected_count is None:
            expected_count = len(events)
        else:
            assert len(events) == expected_count, f"Alias '{alias}' count should match other US aliases"

def test_curated_client_negation_us(db_client):
    """Verify 'fuera de Estados Unidos' returns only international events."""
    all_events, _ = db_client.fetch_all_events()
    intl_events, _ = db_client.query_events(place_excludes="Estados Unidos")

    assert len(intl_events) >= 20
    assert len(intl_events) < len(all_events)
    # Ensure no US events slipped into international results
    for e in intl_events:
        is_us, _ = GeoEntityResolver.is_us_event(e.get("place", ""))
        assert is_us is False, f"US event '{e.get('place')}' should have been excluded"

def test_agent_us_query_complete_information(agent):
    """
    CRITICAL USER ACCEPTANCE TEST:
    'Cuantos sismos se produjeron en territorio de estados unidos?'
    Must deliver complete, structured information:
    1. Certified count of events (>= 150).
    2. Subregion breakdown across states (California, Alaska, Hawaii, Texas...).
    3. Most significant event highlight.
    4. Full certified listing.
    """
    result = agent.ask("Cuantos sismos se produjeron en territorio de estados unidos?")
    resp = result["response"]

    assert "eventos sísmicos en territorio de Estados Unidos" in resp
    assert "Distribución por estados/regiones:" in resp
    assert "California" in resp
    assert "Alaska" in resp
    assert "Evento más significativo:" in resp
    assert "Listado completo certificado:" in resp
    assert result["telemetry"]["records_retrieved"] >= 150

def test_agent_zero_match_clean_grammar(agent):
    """Verify that zero-result territory message does not contain 'con en' typo."""
    result = agent.ask("¿Cuántos sismos se produjeron en territorio de Colombia?")
    resp = result["response"]

    assert "con en la región" not in resp
    assert "en la región 'Colombia'" in resp
    assert result["telemetry"]["records_retrieved"] == 0
