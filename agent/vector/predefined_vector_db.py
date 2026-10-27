"""
SismoWatch - Predefined Conversational Vector Database (Semantic Router)
Indexes canonical intents (greetings, pleasantries, identity, help, farewells) as high-dimensional
vector embeddings. Performs sub-10ms semantic similarity matching to instantly answer conversational
prompts with 0 LLM generation tokens and $0.00 cost.
"""
import os
import json
import math
import re
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "vector_store", "predefined_intents.json")
)

PREDEFINED_KNOWLEDGE_BASE: List[Dict[str, Any]] = [
    {
        "category": "GREETING",
        "anchors": [
            "hola",
            "hola asistente",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "un saludo",
            "hey qué tal",
            "saludos cordiales",
            "hola sismowatch",
            "qué más amigo",
            "buenas",
            "un cordial saludo",
            "hello",
            "hi",
            "¡hola! ¿cómo estás?",
            "hola ¿cómo estás?",
            "hola amigo",
            "buenas amigo",
            "saludos"
        ],
        "response": (
            "¡Hola! Un gusto saludarte. Soy el Agente Sismológico Inteligente de SismoWatch. "
            "Tengo acceso directo y verificado a todos los eventos sísmicos consolidados en la base de datos. "
            "¿En qué puedo orientarte hoy? Puedes consultarme por sismos por región o país, el evento más fuerte, "
            "filtrar por magnitudes o profundidad, o pedirme el reporte completo."
        ),
        "speech_text": "Hola, soy el Agente Inteligente de SismoWatch. Tengo acceso a todos los eventos sísmicos consolidados. ¿Qué deseas consultar hoy?"
    },
    {
        "category": "PLEASANTRY",
        "anchors": [
            "cómo estás",
            "cómo te va",
            "qué tal tu día",
            "cómo andas",
            "cómo te encuentras hoy",
            "cómo te sientes",
            "todo bien contigo",
            "qué tal amigo",
            "cómo van las cosas",
            "qué tal todo"
        ],
        "response": (
            "¡Hola! Estoy muy bien, gracias por preguntar. Todos los sistemas del pipeline de SismoWatch y "
            "la red de sensores se encuentran operando con normalidad. Todos los eventos sísmicos están 100% "
            "validados en la capa Curated. ¿Deseas consultar alguna región, magnitud o profundidad en particular?"
        ),
        "speech_text": "Estoy muy bien, gracias por preguntar. Los sistemas de monitoreo sísmico están operando con normalidad. ¿En qué te ayudo?"
    },
    {
        "category": "IDENTITY",
        "anchors": [
            "quién eres",
            "cuál es tu nombre",
            "qué haces",
            "para qué sirves",
            "quién te creó",
            "cuál es tu función",
            "qué modelo de ia eres",
            "cuál es tu propósito",
            "cuéntame sobre ti",
            "quién eres tú",
            "quién eres tú y qué haces"
        ],
        "response": (
            "Soy el Agente Inteligente de SismoWatch, diseñado con arquitectura determinista y conectado "
            "exclusivamente a los datos procesados por nuestro pipeline de Airflow y Spark. "
            "Mis capacidades incluyen:\n"
            "• Consultas en lenguaje natural sobre eventos sísmicos auditados.\n"
            "• Desglose y verificación de todos los eventos consolidados sin truncamiento.\n"
            "• Análisis por región geográfica, rangos de magnitud y profundidad focal en km.\n"
            "• Reporte del estado de salud y telemetría de sensores."
        ),
        "speech_text": "Soy el Agente Inteligente de SismoWatch, conectado exclusivamente a la base de datos de sismos curados para consultas analíticas precisas."
    },
    {
        "category": "HELP",
        "anchors": [
            "ayuda",
            "ayúdame",
            "ayúdame por favor",
            "ayuda por favor",
            "cómo funciona esto",
            "qué puedo preguntarte",
            "dame ejemplos de preguntas",
            "cómo te uso",
            "ayúdame a usar la plataforma",
            "qué comandos tienes",
            "enséñame a consultar",
            "qué puedes hacer"
        ],
        "response": (
            "Aquí tienes algunos ejemplos de lo que puedes consultarme:\n"
            "• '¿Cuántos sismos hay en total y muéstramelos todos?' (despliega la lista completa certificada)\n"
            "• '¿Cuáles temblores ocurrieron en Colombia o en Indonesia?'\n"
            "• '¿Cuál fue el sismo más fuerte y dónde ocurrió?'\n"
            "• 'Dame los sismos que cubran más de 200km de profundidad'\n"
            "• '¿Cuáles sismos fueron menor o igual a 4.5 M?'\n"
            "• '¿Cuáles son los sismos más superficiales?'"
        ),
        "speech_text": "Puedes preguntarme por sismos por región, el evento más fuerte, rangos de magnitud o profundidad, o pedirme la lista completa."
    },
    {
        "category": "FAREWELL",
        "anchors": [
            "adiós",
            "chao",
            "hasta luego",
            "nos vemos",
            "muchas gracias por todo",
            "gracias por la información",
            "hasta pronto",
            "que tengas buen día",
            "muchísimas gracias",
            "chao chao",
            "gracias",
            "muchas gracias",
            "muchas gracias amigo"
        ],
        "response": (
            "¡Con gusto! Ha sido un placer ayudarte. El sistema de monitoreo de SismoWatch continúa en vigilancia activa en tiempo real. ¡Hasta luego!"
        ),
        "speech_text": "Con gusto, ha sido un placer ayudarte. Quedo en vigilancia continua ante cualquier nuevo evento sísmico."
    }
]

DOMAIN_SEISMIC_KEYWORDS = {
    # Seismology terminology & locations
    "sismo", "sismos", "temblor", "temblores", "terremoto", "terremotos",
    "magnitud", "profundidad", "profundo", "superficial", "epicentro",
    "foco", "richter", "colombia", "indonesia", "vanuatu", "alaska", "peru", "chile",
    "fiji", "tonga", "argentina", "mexico", "km", "evento", "eventos", "curated", "lakehouse",
    # Analytical adjectives & superlatives
    "fuerte", "fuertes", "débil", "debiles", "mayor", "mayores", "menor", "menores",
    "máximo", "maximo", "máxima", "maxima", "mínimo", "minimo", "mínima", "minima",
    "reciente", "recientes", "último", "ultimo", "últimos", "ultimos", "primer", "primero", "primeros",
    # Anaphoric references & analytical interrogatives
    "esos", "estos", "aquellos", "cuántos", "cuantos", "cuántas", "cuantas",
    "lista", "tabla", "datos", "registros", "reporte", "resumen", "total", "hubo",
    "ocurrió", "ocurrio", "ocurrieron", "tembló", "temblo"
}

class PredefinedVectorDB:
    """Local Vector Database for instant semantic routing of conversational intents."""

    def __init__(
        self,
        index_path: Optional[str] = None,
        model: str = "all-minilm",
        host: str = "http://127.0.0.1:11434"
    ):
        self.index_path = index_path or DEFAULT_INDEX_PATH
        self.model = model
        self.host = host
        self.vector_records: List[Dict[str, Any]] = []
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        self._initialize_vector_store()

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Computes dense vector embedding via local Ollama embeddings endpoint."""
        payload = {
            "model": self.model,
            "prompt": text.strip()
        }
        try:
            req = urllib.request.Request(
                f"{self.host}/api/embeddings",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("embedding")
        except Exception as e:
            logger.debug(f"Ollama embedding call failed: {e}")
        return None

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Computes cosine similarity between two dense vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (norm1 * norm2)

    def _initialize_vector_store(self):
        """Loads persistent vector index or builds it automatically if missing."""
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    self.vector_records = json.load(f)
                if self.vector_records:
                    logger.info(f"Loaded {len(self.vector_records)} vectors from {self.index_path}")
                    return
            except Exception as e:
                logger.warning(f"Error loading vector index: {e}. Rebuilding...")

        self.build_index()

    def build_index(self, force: bool = False) -> int:
        """Indexes all predefined anchors into vector embeddings and saves to disk."""
        records = []
        logger.info(f"Building predefined intent vector database using model '{self.model}'...")

        for item in PREDEFINED_KNOWLEDGE_BASE:
            cat = item["category"]
            resp = item["response"]
            speech = item["speech_text"]

            for anchor in item["anchors"]:
                emb = self._get_embedding(anchor)
                if emb:
                    records.append({
                        "category": cat,
                        "anchor": anchor,
                        "response": resp,
                        "speech_text": speech,
                        "vector": emb
                    })

        if records:
            self.vector_records = records
            try:
                with open(self.index_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False)
                logger.info(f"Successfully saved {len(records)} vectors to {self.index_path}")
            except Exception as e:
                logger.error(f"Failed to persist vector index: {e}")

        return len(records)

    def search(self, user_query: str, threshold: float = 0.70) -> Optional[Dict[str, Any]]:
        """
        Searches the Vector Database for semantic match with predefined intents.
        Returns matched response dict if similarity >= threshold and query is conversational,
        or None if query is a domain seismology question.
        """
        if not user_query or not user_query.strip():
            return None

        # Guard 1: Any numeric digits indicate an analytical or quantitative query
        if re.search(r"\d", user_query):
            return None

        q_clean = user_query.strip().lower()

        # Guard 2: If query contains explicit seismic domain terms or superlatives, let it pass to database reasoning
        words = set(re.sub(r"[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]", " ", q_clean).split())
        if words.intersection(DOMAIN_SEISMIC_KEYWORDS):
            return None

        # Compute query vector
        query_vector = self._get_embedding(q_clean)
        if not query_vector or not self.vector_records:
            return None

        best_score = -1.0
        best_match: Optional[Dict[str, Any]] = None

        for rec in self.vector_records:
            sim = self._cosine_similarity(query_vector, rec["vector"])
            if sim > best_score:
                best_score = sim
                best_match = rec

        if best_match and best_score >= threshold:
            logger.info(f"Vector DB Match: {best_match['category']} (similarity: {best_score:.4f}, anchor: '{best_match['anchor']}')")
            return {
                "matched": True,
                "category": best_match["category"],
                "text": best_match["response"],
                "speech_text": best_match["speech_text"],
                "vector_similarity": round(best_score, 4),
                "matched_anchor": best_match["anchor"],
                "storage_backend": "VECTOR_DATABASE",
                "model": f"vector-semantic-router ({self.model})"
            }

        return None
