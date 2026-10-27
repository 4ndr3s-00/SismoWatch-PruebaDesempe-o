"""
SismoWatch - Seismological Semantic Parser (NLU Engine)
Extracts intents, geographic entities with fuzzy matching, numeric bounds,
negation, and superlatives without requiring external LLM token expenditure.
"""
import re
import difflib
from typing import Dict, Any, Optional

class SeismologicalNLU:
    """Natural Language Understanding parser for seismic monitoring queries."""

    KNOWN_LOCATIONS = [
        "Colombia", "Santander", "Antioquia", "Mesa de Los Santos",
        "Dabeiba", "Tumaco", "Nariño", "Zapatoca", "Esmeraldas", "Ecuador",
        "Murindó", "Tauramena", "Casanare", "Chile", "Cucuta",
        "Norte de Santander", "Panama", "Puerto Armuelles", "Betulia",
        "Meta", "El Calvario", "Atlantic", "Lenguazaque", "Cundinamarca",
        "Peru", "Jordan", "Valdivia", "Venezuela", "Merida", "Mexico", "Chiapas"
    ]

    @classmethod
    def parse(cls, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parses a natural language query into a structured execution intent and filters.
        Accepts conversation context for multi-turn reference resolution.
        """
        q = query.lower().strip()
        context = context or {}

        # 1. Detect 'Show All Events' Intent (The 20-Record Integrity Query)
        if any(p in q for p in ["todos", "todos los datos", "mostrar todo", "muestrame todos", "muéstramelos todos", "lista completa", "ver todos", "los 20", "cuántos sismos hay", "cuantos sismos hay"]):
            return {
                "intent": "SHOW_ALL_EVENTS",
                "filters": {},
                "order_by": "time_desc",
                "limit": 50
            }

        # 2. Detect 'Summary / General Report' Intent
        if any(p in q for p in ["resumen", "reporte", "informe", "estad[ií]stica", "panorama", "balance"]):
            return {
                "intent": "EXECUTIVE_SUMMARY",
                "filters": {},
                "order_by": "time_desc",
                "limit": 50
            }

        # 3. Detect Superlative Intents (Strongest, Weakest, Shallowest, Deepest, Most Recent, Oldest)
        if any(p in q for p in ["m[aá]s fuerte", "m[aá]s grande", "mayor magnitud", "m[aá]ximo", "terremoto m[aá]s bravo"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "MAX_MAGNITUDE",
                "order_by": "magnitude_desc",
                "limit": 1
            }

        if any(p in q for p in ["m[aá]s leve", "m[aá]s suave", "menor magnitud", "m[ií]nimo", "m[aá]s bajito"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "MIN_MAGNITUDE",
                "order_by": "magnitude_asc",
                "limit": 1
            }

        if any(p in q for p in ["m[aá]s profundo", "m[aá]s hondo", "mayor profundidad"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "DEEPEST",
                "order_by": "depth_desc",
                "limit": 1
            }

        if any(p in q for p in ["m[aá]s superficial", "menor profundidad", "menos profundo", "playo"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "SHALLOWEST",
                "order_by": "depth_asc",
                "limit": 1
            }

        if any(p in q for p in ["m[aá]s reciente", "[uú]ltimo sismo", "[uú]ltimo temblor"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "MOST_RECENT",
                "order_by": "time_desc",
                "limit": 1
            }

        if any(p in q for p in ["primer sismo", "primer temblor", "m[aá]s antiguo", "primero"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "OLDEST",
                "order_by": "time_asc",
                "limit": 1
            }

        # 4. Extract Magnitude Bounds
        min_mag = None
        max_mag = None

        # Pattern: mayor a X / superior a X / más de X / mayor o igual a X / >= X / mínimo X
        m_greater = re.search(
            r"(?:mayor|superior|m[aá]s|arriba|m[ií]nimo|desde)?\s*(?:o\s*igual\s*(?:a|que))?\s*(?:a|de|que)?\s*(?:magnitud)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?",
            q
        )
        if m_greater and any(w in q for w in ["mayor", "superior", "m[aá]s", "mínimo", "minimo", "desde", ">="]):
            min_mag = float(m_greater.group(1))

        # Pattern: menor a X / inferior a X / menos de X / menor o igual a X / <= X / máximo X
        m_less = re.search(
            r"(?:menor|inferior|menos|debajo|m[aá]ximo|hasta)?\s*(?:o\s*igual\s*(?:a|que))?\s*(?:a|de|que)?\s*(?:magnitud)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?",
            q
        )
        if m_less and any(w in q for w in ["menor", "inferior", "menos", "debajo", "máximo", "maximo", "hasta", "<="]):
            max_mag = float(m_less.group(1))

        # Pattern: entre X y Y
        m_range = re.search(r"entre\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?\s*y\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?", q)
        if m_range:
            min_mag = float(m_range.group(1))
            max_mag = float(m_range.group(2))

        # 5. Extract Depth Bounds
        min_depth = None
        max_depth = None
        if "superficial" in q:
            max_depth = 30.0  # Geological standard for shallow events: < 30 km
        elif "profundo" in q or "hondo" in q:
            min_depth = 70.0  # Intermediate to deep events

        d_less = re.search(r"profundidad\s*(?:menor|inferior|menos)?\s*(?:a|de)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km)?", q)
        if d_less:
            max_depth = float(d_less.group(1))

        # 6. Extract Geographic Entities & Negation
        place_contains = None
        place_excludes = None

        # Check for negation: "no en X", "que no sean de X", "fuera de X"
        negation_match = re.search(r"(?:no\s*en|fuera\s*de|que\s*no\s*sean?\s*de)\s*([a-záéíóúñ\s]+)", q)
        if negation_match:
            cand = negation_match.group(1).strip()
            # Match against known locations
            matches = difflib.get_close_matches(cand.capitalize(), cls.KNOWN_LOCATIONS, n=1, cutoff=0.6)
            if matches:
                place_excludes = matches[0]

        if not place_excludes:
            for loc in cls.KNOWN_LOCATIONS:
                if loc.lower() in q:
                    place_contains = loc
                    break
            if not place_contains:
                # Fuzzy matching for user typos (e.g. 'antioqia', 'santandr')
                words = [w for w in re.findall(r"[a-záéíóúñ]{4,}", q) if w not in ["sismo", "temblor", "terremoto", "mayor", "menor", "profundo"]]
                for w in words:
                    matches = difflib.get_close_matches(w.capitalize(), cls.KNOWN_LOCATIONS, n=1, cutoff=0.7)
                    if matches:
                        place_contains = matches[0]
                        break

        # 7. Multi-Turn Context Carryover:
        # If user says "y de esos cuál fue el más fuerte?" carry over place filter from context
        if any(ref in q for ref in ["de esos", "de ellos", "en esa regi[oó]n", "all[ií]", "de esas"]):
            cand_contains = context.get("last_place_contains") or context.get("place_contains")
            cand_excludes = context.get("last_place_excludes") or context.get("place_excludes")
            if cand_contains and not place_contains:
                place_contains = cand_contains
            if cand_excludes and not place_excludes:
                place_excludes = cand_excludes

        filters = {}
        if min_mag is not None:
            filters["min_mag"] = min_mag
        if max_mag is not None:
            filters["max_mag"] = max_mag
        if min_depth is not None:
            filters["min_depth"] = min_depth
        if max_depth is not None:
            filters["max_depth"] = max_depth
        if place_contains:
            filters["place_contains"] = place_contains
        if place_excludes:
            filters["place_excludes"] = place_excludes

        # Determine general filter query vs count query
        intent = "FILTER_QUERY"
        if any(c in q for c in ["cu[aá]ntos", "conteo", "n[uú]mero de sismos", "cantidad"]):
            intent = "COUNT_QUERY"

        return {
            "intent": intent,
            "filters": filters,
            "order_by": "magnitude_desc",
            "limit": 20
        }
