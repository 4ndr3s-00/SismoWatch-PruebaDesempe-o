"""
SismoWatch - Seismological Semantic Parser (NLU Engine)
Extracts intents, geographic entities with fuzzy matching, numeric bounds,
negation, and superlatives without requiring external LLM token expenditure.
"""
import re
import difflib
from typing import Dict, Any, Optional
from agent.core.geo_resolver import GeoEntityResolver

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

        # 1. Detect 'Show All Events' Intent (Integrity Query without artificial limits)
        if any(p in q for p in ["todos", "todos los datos", "mostrar todo", "muestrame todos", "muéstramelos todos", "lista completa", "ver todos", "los 20", "cuántos sismos hay", "cuantos sismos hay"]):
            return {
                "intent": "SHOW_ALL_EVENTS",
                "filters": {},
                "order_by": "time_desc",
                "limit": None
            }

        # 2. Detect 'Summary / General Report' Intent
        if any(re.search(p, q, re.IGNORECASE) for p in ["resumen", "reporte", "informe", r"estad[ií]stica", "panorama", "balance"]):
            return {
                "intent": "EXECUTIVE_SUMMARY",
                "filters": {},
                "order_by": "time_desc",
                "limit": None
            }

        # 3. Detect Superlative Intents (Strongest, Weakest, Shallowest, Deepest, Most Recent, Oldest)
        if any(re.search(p, q, re.IGNORECASE) for p in [r"m[aá]s\s*fuerte", r"m[aá]s\s*grande", r"mayor\s*magnitud", r"m[aá]ximo", r"terremoto\s*m[aá]s\s*bravo", r"sismo\s*m[aá]s\s*fuerte"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "MAX_MAGNITUDE",
                "order_by": "magnitude_desc",
                "limit": 1
            }

        if any(re.search(p, q, re.IGNORECASE) for p in [r"m[aá]s\s*leve", r"m[aá]s\s*suave", r"menor\s*magnitud", r"m[ií]nimo", r"m[aá]s\s*bajito"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "MIN_MAGNITUDE",
                "order_by": "magnitude_asc",
                "limit": 1
            }

        if any(re.search(p, q, re.IGNORECASE) for p in [r"m[aá]s\s*profundo", r"m[aá]s\s*hondo", r"mayor\s*profundidad"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "DEEPEST",
                "order_by": "depth_desc",
                "limit": 1
            }

        if any(re.search(p, q, re.IGNORECASE) for p in [r"m[aá]s\s*superficial", r"menor\s*profundidad", r"menos\s*profundo", "playo", "superficiales"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "SHALLOWEST",
                "order_by": "depth_asc",
                "limit": 1
            }

        if any(re.search(p, q, re.IGNORECASE) for p in [r"m[aá]s\s*reciente", r"[uú]ltimo\s*sismo", r"[uú]ltimo\s*temblor"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "MOST_RECENT",
                "order_by": "time_desc",
                "limit": 1
            }

        if any(re.search(p, q, re.IGNORECASE) for p in ["primer sismo", "primer temblor", r"m[aá]s\s*antiguo", "primero"]):
            return {
                "intent": "SUPERLATIVE",
                "target": "OLDEST",
                "order_by": "time_asc",
                "limit": 1
            }

        # 4. Extract Depth Bounds (km / kilómetros / profundidad / cubran)
        min_depth = None
        max_depth = None
        has_km_unit = any(u in q for u in ["km", "kilómetro", "kilometro", "profund", "cubran"])

        if "superficial" in q:
            max_depth = 30.0  # Geological standard for shallow events: < 30 km
        elif "profundo" in q or "hondo" in q:
            min_depth = 70.0  # Intermediate to deep events

        # Depth range: entre X y Y km
        d_range = re.search(r"entre\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|kil[oó]metros)?\s*y\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|kil[oó]metros)", q)
        if d_range:
            v1, v2 = float(d_range.group(1)), float(d_range.group(2))
            min_depth, max_depth = min(v1, v2), max(v1, v2)

        # Depth greater than: más de X km / mayor a X km / cubran más de X km / profundidad mayor a X
        d_greater = re.search(r"(?:profundidad|cubran|alcancen)?\s*(?:m[aá]s|mayor|superior)\s*(?:a|de|que)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|kil[oó]metros)?", q)
        if d_greater and (has_km_unit or "profund" in q or "cubran" in q):
            min_depth = float(d_greater.group(1))

        # Depth less than: menos de X km / menor a X km / profundidad menor a X
        d_less = re.search(r"(?:profundidad)?\s*(?:menos|menor|inferior|debajo)\s*(?:a|de|que)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|kil[oó]metros)?", q)
        if d_less and (has_km_unit or "profund" in q):
            max_depth = float(d_less.group(1))

        # 5. Extract Magnitude Bounds (strictly dimensionless or 'M' / 'grados', max 10.0)
        min_mag = None
        max_mag = None

        if not has_km_unit or any(m in q for m in ["magnitud", "grados", "escala"]):
            # Pattern: mayor a X / superior a X / más de X / mayor o igual a X / >= X / mínimo X
            m_greater = re.search(
                r"(?:mayor|superior|m[aá]s|arriba|m[ií]nimo|desde)?\s*(?:o\s*igual\s*(?:a|que))?\s*(?:a|de|que)?\s*(?:magnitud)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?",
                q
            )
            if m_greater and any(w in q for w in ["mayor", "superior", "m[aá]s", "mínimo", "minimo", "desde", ">="]):
                val = float(m_greater.group(1))
                if val <= 10.0:  # Physical limit for terrestrial earthquake magnitude
                    min_mag = val
                elif min_depth is None:
                    min_depth = val

            # Pattern: menor a X / inferior a X / menos de X / menor o igual a X / <= X / máximo X
            m_less = re.search(
                r"(?:menor|inferior|menos|debajo|m[aá]ximo|hasta)?\s*(?:o\s*igual\s*(?:a|que))?\s*(?:a|de|que)?\s*(?:magnitud)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?",
                q
            )
            if m_less and any(w in q for w in ["menor", "inferior", "menos", "debajo", "máximo", "maximo", "hasta", "<="]):
                val = float(m_less.group(1))
                if val <= 10.0:
                    max_mag = val
                elif max_depth is None:
                    max_depth = val

            # Pattern: entre X y Y magnitudes
            m_range = re.search(r"entre\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?\s*y\s*([0-9]+(?:\.[0-9]+)?)\s*(?:m|grados)?", q)
            if m_range and not has_km_unit:
                v1, v2 = float(m_range.group(1)), float(m_range.group(2))
                if v1 <= 10.0 and v2 <= 10.0:
                    min_mag = min(v1, v2)
                    max_mag = max(v1, v2)

        # 6. Extract Geographic Entities & Negation
        place_contains = None
        place_excludes = None

        # Check for negation: "no en X", "que no sean de X", "fuera de X"
        negation_match = re.search(r"(?:no\s*en|fuera\s*de|que\s*no\s*sean?\s*de)\s*([a-záéíóúñ\s]+)", q)
        if negation_match:
            cand = negation_match.group(1).strip()
            if GeoEntityResolver.is_us_query(cand):
                place_excludes = "Estados Unidos"
            else:
                canon = GeoEntityResolver.get_canonical_name(cand)
                if canon and canon.lower() != cand.lower():
                    place_excludes = canon
                else:
                    matches = difflib.get_close_matches(cand.capitalize(), cls.KNOWN_LOCATIONS, n=1, cutoff=0.6)
                    if matches:
                        place_excludes = matches[0]

        if not place_excludes:
            # First check if user is querying for US territory
            if GeoEntityResolver.is_us_query(q):
                place_contains = "Estados Unidos"
            else:
                # Check international catalog
                for cat_id, meta in GeoEntityResolver.INTERNATIONAL_CATALOG.items():
                    for alias in meta["aliases"]:
                        if re.search(r"\b" + re.escape(alias) + r"\b", q, re.IGNORECASE):
                            place_contains = meta["canonical_name_es"]
                            break
                    if place_contains:
                        break

            if not place_contains:
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
            "limit": None
        }
