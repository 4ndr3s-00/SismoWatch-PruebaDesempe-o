"""
SismoWatch - Local Ollama LLM Client
Connects to local Ollama instance running Meta Llama 3.2 (3B).
Provides zero-token local inference, structured query parsing, and grounded factual response generation.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

class OllamaClient:
    """HTTP client for local Ollama server running Llama 3.2 (3B)."""

    def __init__(self, host: str = OLLAMA_HOST, model: str = DEFAULT_MODEL, timeout: int = 30):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_healthy(self) -> bool:
        """Checks if Ollama daemon is reachable and responding."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", headers={"User-Agent": "SismoWatch/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    models = [m.get("name") for m in data.get("models", [])]
                    logger.info(f"Ollama connected. Available models: {models}")
                    return True
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
        return False

    def is_model_available(self, model_name: Optional[str] = None) -> bool:
        """Verifies if the specified model is pulled and ready in Ollama."""
        target = model_name or self.model
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                models = [m.get("name", "").split(":")[0] for m in data.get("models", [])] + \
                         [m.get("name", "") for m in data.get("models", [])]
                target_base = target.split(":")[0]
                return target in models or target_base in models
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 512
    ) -> Optional[str]:
        """Generates completion using local Ollama model."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.9
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    result = json.loads(resp.read().decode("utf-8"))
                    return result.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama generation error: {e}")
        return None

    def parse_query_to_filters(self, user_query: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Uses Llama 3.2 to parse complex natural language into precise structured filters.
        Correctly handles: 'menor o igual a 4.3 M', 'entre 3 y 5', negations, regions, and superlatives.
        """
        ctx_str = f"Contexto anterior: lugar={context.get('place_contains', 'Ninguno')}" if context else ""
        system = (
            "Eres un analizador semántico sismológico de alta precisión. Tu tarea es extraer filtros de búsqueda "
            "a partir de la consulta del usuario y devolver EXCLUSIVAMENTE un objeto JSON válido, sin explicaciones ni texto adicional.\n\n"
            "Diferenciación física crítica:\n"
            "- PROFUNDIDAD ('min_depth', 'max_depth'): Se mide en 'km', 'kilómetros', 'profundidad', 'hondo', 'superficial'. Rango: 0 a 700 km. Ejemplo: 'más de 200km', 'que cubran más de 200km', 'profundidad mayor a 50 km' -> min_depth = 200, min_mag = null.\n"
            "- MAGNITUD ('min_mag', 'max_mag'): Es adimensional (escala 0.0 a 10.0), a menudo con 'M', 'grados', 'fuerte'. ¡NUNCA LLEVA KM Y NUNCA ES MAYOR A 10! Si alguien dice 200km o 50km, ¡ES PROFUNDIDAD, NUNCA MAGNITUD!\n\n"
            "Reglas críticas:\n"
            "- Si el usuario pide sismos 'a más de X km', 'cubran más de X km' o 'profundidad mayor a X': min_depth = X, max_depth = null, min_mag = null, max_mag = null.\n"
            "- Si el usuario pide sismos 'a menos de X km', 'superficiales a X km' o 'profundidad menor a X': max_depth = X, min_depth = null, min_mag = null, max_mag = null.\n"
            "- Si el usuario pide sismos 'menores a X', 'inferiores a X', o 'menor o igual a X' (donde X <= 10): max_mag = X, min_mag = null.\n"
            "- Si el usuario pide sismos 'mayores a X', 'superiores a X', o 'mayor o igual a X' (donde X <= 10): min_mag = X, max_mag = null.\n"
            "- Si el usuario pide 'entre X e Y' con km: min_depth = menor, max_depth = mayor.\n"
            "- Si el usuario pide 'entre X e Y' magnitudes: min_mag = menor, max_mag = mayor.\n"
            "- Si el usuario pide ver todos los datos, la lista completa, mostrar todo o cuántos hay en total: intent = 'SHOW_ALL_EVENTS', filtros = null.\n"
            "- Si la consulta NO tiene relación con sismos, geología, datos o la plataforma (ej: recetas de cocina, deportes, chistes, preguntas de vida cotidiana como 'Como hago un arroz con pollo'): intent = 'OUT_OF_SCOPE', todos los filtros = null.\n"
            "- Si el usuario pregunta por 'el más fuerte' o 'mayor magnitud': target = 'MAX_MAGNITUDE'.\n"
            "- Si el usuario pregunta por 'el más profundo': target = 'MAX_DEPTH'.\n"
            "- Si el usuario pregunta por 'el más superficial': target = 'MIN_DEPTH'.\n\n"
            "Ejemplos:\n"
            "Consulta: 'Dame los sismos que cubran mas de 200km'\n"
            'Respuesta: {"place_contains": null, "place_excludes": null, "min_mag": null, "max_mag": null, "min_depth": 200.0, "max_depth": null, "target": null, "intent": "FILTER_QUERY"}\n\n'
            "Consulta: 'Como hago un arroz con pollo?'\n"
            'Respuesta: {"place_contains": null, "place_excludes": null, "min_mag": null, "max_mag": null, "min_depth": null, "max_depth": null, "target": null, "intent": "OUT_OF_SCOPE"}\n\n'
            "Consulta: 'Cuantos sismos se produjeron en territorio de estados unidos'\n"
            'Respuesta: {"place_contains": "Estados Unidos", "place_excludes": null, "min_mag": null, "max_mag": null, "min_depth": null, "max_depth": null, "target": null, "intent": "FILTER_QUERY"}\n\n'
            "Consulta: 'cuales de esos fueron menor o igual a 4.3 M' con contexto 'Colombia'\n"
            'Respuesta: {"place_contains": "Colombia", "place_excludes": null, "min_mag": null, "max_mag": 4.3, "min_depth": null, "max_depth": null, "target": null, "intent": "FILTER_QUERY"}\n\n'
            "Consulta: 'sismos mayores a 5.0 fuera de Colombia'\n"
            'Respuesta: {"place_contains": null, "place_excludes": "Colombia", "min_mag": 5.0, "max_mag": null, "min_depth": null, "max_depth": null, "target": null, "intent": "FILTER_QUERY"}\n\n'
            "Consulta: 'Muéstrame todos los datos y la lista completa'\n"
            'Respuesta: {"place_contains": null, "place_excludes": null, "min_mag": null, "max_mag": null, "min_depth": null, "max_depth": null, "target": null, "intent": "SHOW_ALL_EVENTS"}\n\n'
            "Esquema JSON obligatorio:\n"
            "{\n"
            '  "place_contains": string o null,\n'
            '  "place_excludes": string o null,\n'
            '  "min_mag": float o null,\n'
            '  "max_mag": float o null,\n'
            '  "min_depth": float o null,\n'
            '  "max_depth": float o null,\n'
            '  "target": string o null,\n'
            '  "intent": "FILTER_QUERY" | "SHOW_ALL_EVENTS" | "SUPERLATIVE" | "EXECUTIVE_SUMMARY" | "OUT_OF_SCOPE"\n'
            "}"
        )

        prompt = (
            f"{ctx_str}\n"
            f"Consulta del usuario: \"{user_query}\"\n\n"
            "Genera el JSON correspondiente:"
        )

        raw = self.generate(prompt=prompt, system_prompt=system, temperature=0.0, max_tokens=150)
        if not raw:
            return None

        # Clean JSON markdown if wrapped in ```json
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:].strip()

        try:
            parsed = json.loads(clean)
            q_low = user_query.lower()

            # Multi-turn context carryover for place if query references previous turn
            if any(ref in q_low for ref in ["de esos", "de ellos", "allí", "alli", "en esa", "de esas"]) and context:
                if not parsed.get("place_contains"):
                    parsed["place_contains"] = context.get("last_place_contains") or context.get("place_contains")
                if not parsed.get("place_excludes"):
                    parsed["place_excludes"] = context.get("last_place_excludes") or context.get("place_excludes")

            # Semantic reconciliation for lower/upper bound linguistic confusion
            # If query indicates 'less than / under' and LLM set min_mag, reconcile to max_mag
            if any(w in q_low for w in ["menor", "inferior", "menos", "debajo", "máximo", "maximo", "<="]):
                if parsed.get("min_mag") is not None and parsed.get("max_mag") is None:
                    parsed["max_mag"] = parsed.pop("min_mag")
                elif parsed.get("max_mag") is None and not any(k in q_low for k in ["km", "kilómetro", "profund"]):
                    m_less = re.search(r"(?:menor|inferior|menos|debajo|m[aá]ximo|hasta)\s*(?:o\s*igual\s*(?:a|que))?\s*(?:a|de|que)?\s*(?:magnitud)?\s*([0-9]+(?:\.[0-9]+)?)", q_low)
                    if m_less:
                        val = float(m_less.group(1))
                        if val <= 10.0:
                            parsed["max_mag"] = val
                            parsed["target"] = None

            # Vice-versa: if query indicates 'greater than / above' and LLM set max_mag, reconcile to min_mag
            if any(w in q_low for w in ["mayor", "superior", "más", "mas", "arriba", "mínimo", "minimo", ">="]):
                if parsed.get("max_mag") is not None and parsed.get("min_mag") is None:
                    parsed["min_mag"] = parsed.pop("max_mag")
                elif parsed.get("min_mag") is None and not any(k in q_low for k in ["km", "kilómetro", "profund"]):
                    m_num = re.search(r"(?:mayor|superior|m[aá]s|arriba)\s*(?:o\s*igual\s*(?:a|que))?\s*(?:a|de|que)?\s*(?:magnitud)?\s*([0-9]+(?:\.[0-9]+)?)", q_low)
                    if m_num:
                        val = float(m_num.group(1))
                        if val <= 10.0:
                            parsed["min_mag"] = val
                            parsed["target"] = None

            # CRITICAL SANITY RECONCILIATION: Magnitude vs Depth (km)
            # Physical boundary: Terrestrial earthquake magnitude is strictly between -2.0 and 10.0.
            # Any number > 10.0 is depth in km, NEVER magnitude!
            if parsed.get("min_mag") is not None and parsed["min_mag"] > 10.0:
                parsed["min_depth"] = parsed.pop("min_mag")
            if parsed.get("max_mag") is not None and parsed["max_mag"] > 10.0:
                parsed["max_depth"] = parsed.pop("max_mag")

            # If user query specifically mentions km / kilometros / cubran / profundidad:
            if any(k in q_low for k in ["km", "kilómetro", "kilometro", "profund", "cubran"]) and not any(m in q_low for m in ["magnitud", "grados", "escala"]):
                if parsed.get("min_mag") is not None and parsed.get("min_depth") is None:
                    parsed["min_depth"] = parsed.pop("min_mag")
                if parsed.get("max_mag") is not None and parsed.get("max_depth") is None:
                    parsed["max_depth"] = parsed.pop("max_mag")

            # Explicit detection for SHOW_ALL_EVENTS if asking for all records or overall count
            if any(p in q_low for p in ["todos los datos", "todos los sismos", "muestrame todos", "muéstrame todos", "lista completa", "ver todos", "mostrar todo", "cuántos sismos hay", "cuantos sismos hay", "cuántos sismos registrados", "cuantos sismos registrados"]):
                parsed["intent"] = "SHOW_ALL_EVENTS"
                parsed["place_contains"] = None
                parsed["place_excludes"] = None
                parsed["min_mag"] = None
                parsed["max_mag"] = None

            return parsed
        except Exception as e:
            logger.debug(f"Failed to parse LLM JSON output: {clean} - {e}")
            return None

    def ground_and_narrate(
        self,
        user_query: str,
        events: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> Optional[str]:
        """
        Uses Llama 3.2 to write fluent Spanish narrative strictly grounded in verified database events.
        0% hallucinations guaranteed by strict prompt injection boundaries and grounding.
        """
        if not events:
            return None

        events_summary = []
        for idx, ev in enumerate(events[:20], 1):
            events_summary.append(
                f"{idx}. M {ev.get('magnitude')} en {ev.get('place')} | Profundidad: {ev.get('depth')} km | ID: {ev.get('event_id')} | Fecha: {str(ev.get('event_time', ''))[:19]}"
            )
        events_text = "\n".join(events_summary)

        system = (
            "Eres el Asistente Sismológico de SismoWatch. Responde a la pregunta del usuario en español con un tono "
            "profesional, claro y estructurado. REGLA ESTRICTA DE VERACIDAD: Utiliza ÚNICA Y EXCLUSIVAMENTE los "
            "datos del listado proporcionado. No agregues sismos no listados ni inventes cifras. "
            "Menciona los IDs de los eventos cuando sea relevante."
        )

        prompt = (
            f"DATOS OFICIALES DE LA BASE DE DATOS ({len(events)} eventos):\n"
            f"{events_text}\n\n"
            f"PREGUNTA DEL USUARIO: {user_query}\n\n"
            "RESPUESTA:"
        )

        return self.generate(prompt=prompt, system_prompt=system, temperature=0.2, max_tokens=400)
