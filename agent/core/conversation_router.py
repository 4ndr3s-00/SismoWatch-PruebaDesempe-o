"""
SismoWatch - Conversational Fast Router
Handles single-turn conversational prompts (greetings, identity, pleasantries)
and out-of-scope domain boundaries with instant responses (0 ms, 0 tokens).
"""
import re
from typing import Optional, Dict, Any

class ConversationRouter:
    """Fast-path conversational handler for non-analytical interactions."""

    GREETING_PATTERNS = [
        r"^[\s¡!¿?]*\b(hola|buenos\s*d[ií]as|buenas\s*tardes|buenas\s*noches|hey|qu[eé]\s*tal|saludos|hello|hi)\b"
    ]

    HOW_ARE_YOU_PATTERNS = [
        r"\bc[oó]mo\s*(est[aá]s|te\s*va|andas|te\s*encuentras)\b",
        r"\bhow\s*are\s*you\b"
    ]

    IDENTITY_PATTERNS = [
        r"\b(qui[eé]n\s*eres|qu[eé]\s*(eres|haces)|cu[aá]l\s*es\s*tu\s*(funci[oó]n|nombre)|para\s*qu[eé]\s*sirves)\b",
        r"\bwho\s*are\s*you\b"
    ]

    HELP_PATTERNS = [
        r"^[\s¡!¿?]*\b(ayuda|help|qu[eé]\s*puedo\s*preguntar|instrucciones|comandos)\b"
    ]

    GRATITUDE_PATTERNS = [
        r"\b(gracias|muchas\s*gracias|te\s*lo\s*agradezco|thank\s*you|thanks)\b",
        r"\b(chao|adi[oó]s|hasta\s*luego|nos\s*vemos|bye)\b"
    ]

    OUT_OF_SCOPE_PATTERNS = [
        r"\b(receta|recetas|cocina|cocinar|arroz|pollo|ajiaco|pizza|hamburguesa|comida|almuerzo|cena|desayuno|pasta|carne|sopa|hacer\s+un\s+|c[oó]mo\s+hago|c[oó]mo\s+preparo|ingredientes|postre)\b",
        r"\b(bitcoin|criptomoneda|trading|inversi[oó]n|acciones|d[oó]lar|dinero|forex)\b",
        r"\b(chiste|poema|canci[oó]n|cuento|historieta|letra\s+de|pel[ií]cula|serie|netflix|actor|m[uú]sica)\b",
        r"\b(presidente|elecciones|pol[ií]tica|partido\s+pol[ií]tico|candidato)\b",
        r"\b(f[uú]tbol|campeonato|liga|partido|gol|champions|mundial|messi|ronaldo|baloncesto|nba|videojuego|minecraft)\b",
        r"\b(capital\s+de|qui[eé]n\s+(invent[oó]|descubri[oó]|gan[oó])|clima|tiempo\s+en|temperatura|pron[oó]stico|tarea|matem[aá]ticas)\b",
        r"\b(carro|auto|mec[aá]nica|bicicleta|reparar|arreglar|m[eé]dico|medicina|s[ií]ntomas?|enfermedad)\b"
    ]

    @classmethod
    def is_seismological_or_analytical(cls, query: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determines whether the query is relevant to seismology, database records,
        geographical territories, or previous multi-turn analytical context.
        """
        clean = query.lower()

        # Multi-turn reference ("de esos", "allí", "en ese lugar", "cuál de ellos")
        if context and context.get("last_intent") and re.search(r"\b(de\s+esos|de\s+estos|all[ií]|en\s+ese\s+lugar|cu[aá]l\s+de\s+ellos|y\s+de\s+esos)\b", clean):
            return True

        # Seismological domain keywords
        seismic_pattern = (
            r"\b(sismo|sismos|terremoto|terremotos|temblor|temblores|epicentro|hipocentro|falla|placas?|"
            r"tsunami|richter|magnitud|magnitudes|profundidad|profundidades|focal|tel[uú]rico|geol[oó]gic|"
            r"red\s*s[ií]smica|estaci[oó]n|estaciones|sensor|sensores|aceler[oó]metro|onda\s*[ps]|anomal[ií]a|"
            r"movimiento|sacudida)\b"
        )
        if re.search(seismic_pattern, clean):
            return True

        # Database / Data extraction keywords
        data_pattern = (
            r"\b(cu[aá]ntos?|total|registros?|datos?|mostrar|muestra|ver|listar?|listado|tabla|"
            r"base\s+de\s+datos|cat[aá]logo|lakehouse|curated|resumen|estad[ií]sticas?|sla|quarantine|"
            r"informaci[oó]n|reporte|reportes|todos|todo|eventos?)\b"
        )
        if re.search(data_pattern, clean):
            return True

        # Physical measurements / Superlatives
        phys_pattern = (
            r"\b(m[aá]s\s*fuerte|m[aá]s\s*profundo|m[aá]s\s*superficial|superficiales|fuerte|profundo|"
            r"mayor\s*a|menor\s*a|superior|inferior|igual\s*a|\d+(\.\d+)?\s*(m|km))\b"
        )
        if re.search(phys_pattern, clean):
            return True

        # Geographical territory check
        try:
            from agent.core.geo_resolver import GeoEntityResolver
            if GeoEntityResolver.is_us_query(clean):
                return True
            for canonical, aliases in GeoEntityResolver.INTERNATIONAL_CATALOG.items():
                if any(alias in clean for alias in aliases):
                    return True
        except Exception:
            pass

        return False

    @classmethod
    def evaluate(cls, query: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluates query for conversational fast paths.
        Returns response dict if matched, or None if it requires analytical database execution.
        """
        clean = query.strip()

        # 1. Greetings
        for pat in cls.GREETING_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return {
                    "matched": True,
                    "category": "GREETING",
                    "text": (
                        "¡Hola! Un gusto saludarte. Soy el Agente Sismológico Inteligente de SismoWatch. "
                        "Tengo acceso directo y verificado a todos los eventos sísmicos consolidados en la base de datos. "
                        "¿En qué puedo orientarte hoy? Puedes consultarme por sismos por región o país, el evento más fuerte, "
                        "filtrar por magnitudes o pedirme el reporte completo."
                    ),
                    "speech_text": "Hola, soy el Agente Inteligente de SismoWatch. Tengo acceso a todos los eventos sísmicos consolidados. ¿Qué deseas consultar hoy?",
                    "action_required": False
                }

        # 2. How are you / Pleasantries
        for pat in cls.HOW_ARE_YOU_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return {
                    "matched": True,
                    "category": "PLEASANTRY",
                    "text": (
                        "¡Estoy muy bien, gracias por preguntar! Todos los sistemas del pipeline de SismoWatch y "
                        "la red de sensores se encuentran operando con normalidad. Todos los eventos sísmicos están 100% "
                        "validados en la capa Curated. ¿Deseas consultar alguna región o magnitud en particular?"
                    ),
                    "speech_text": "Estoy muy bien, gracias por preguntar. Los sistemas de monitoreo sísmico están operando con normalidad. ¿En qué te ayudo?",
                    "action_required": False
                }

        # 3. Identity & Capabilities
        for pat in cls.IDENTITY_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return {
                    "matched": True,
                    "category": "IDENTITY",
                    "text": (
                        "Soy el Agente Inteligente de SismoWatch, diseñado con arquitectura determinista y conectado "
                        "exclusivamente a los datos procesados por nuestro pipeline de Airflow y Spark. "
                        "Mis capacidades incluyen:\n"
                        "• Consultas en lenguaje natural sobre eventos sísmicos auditados.\n"
                        "• Desglose y verificación de todos los eventos consolidados.\n"
                        "• Análisis por región geográfica, rangos de magnitud y profundidad focal.\n"
                        "• Reporte del estado de salud y telemetría de sensores."
                    ),
                    "speech_text": "Soy el Agente Inteligente de SismoWatch, conectado exclusivamente a la base de datos de sismos curados para consultas analíticas precisas.",
                    "action_required": False
                }

        # 4. Help
        for pat in cls.HELP_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return {
                    "matched": True,
                    "category": "HELP",
                    "text": (
                        "Aquí tienes algunos ejemplos de lo que puedes consultarme:\n"
                        "• '¿Cuántos sismos hay en total y muéstramelos todos?' (despliega la lista completa certificada)\n"
                        "• '¿Cuáles temblores ocurrieron en Colombia o en Indonesia?'\n"
                        "• '¿Cuál fue el sismo más fuerte y dónde ocurrió?'\n"
                        "• 'Muéstrame los sismos con magnitud mayor a 4.0'\n"
                        "• '¿Cuáles son los sismos más superficiales?'\n"
                        "• '¿Hubo sismos menores o iguales a 4.5 M?'"
                    ),
                    "speech_text": "Puedes preguntarme por sismos por región, el evento más fuerte, rangos de magnitud o pedirme la lista completa.",
                    "action_required": False
                }

        # 5. Gratitude / Farewells
        for pat in cls.GRATITUDE_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return {
                    "matched": True,
                    "category": "FAREWELL",
                    "text": (
                        "¡Con el mayor gusto! El sistema de monitoreo SismoWatch continúa en vigilancia constante. "
                        "Quedo a tu disposición cuando requieras consultar nuevos reportes sísmicos."
                    ),
                    "speech_text": "Con el mayor gusto. El sistema de monitoreo continúa activo. Hasta pronto.",
                    "action_required": False
                }

        # 6. Out-of-Scope Explicit Pattern Match
        for pat in cls.OUT_OF_SCOPE_PATTERNS:
            if re.search(pat, clean, re.IGNORECASE):
                return {
                    "matched": True,
                    "category": "OUT_OF_SCOPE",
                    "text": (
                        "Mi especialidad como Agente de SismoWatch se enfoca exclusivamente en el monitoreo y análisis "
                        "de eventos sísmicos en la plataforma. No puedo responder consultas fuera de contexto "
                        "(como recetas de cocina, cultura general o temas ajenos a la red sismológica). "
                        "Te invito a consultarme por sismos registrados por país o región, magnitudes, profundidades focales o estadísticas del catálogo."
                    ),
                    "speech_text": "Mi función se enfoca exclusivamente en monitoreo sísmico. No puedo responder consultas fuera de contexto.",
                    "action_required": False
                }

        # 7. Domain Boundary Guard: Reject queries with zero seismological or analytical relevance
        if not cls.is_seismological_or_analytical(clean, context):
            return {
                "matched": True,
                "category": "OUT_OF_SCOPE",
                "text": (
                    "Mi especialidad como Agente de SismoWatch se enfoca exclusivamente en el monitoreo y análisis "
                    "de eventos sísmicos en la plataforma. No puedo responder consultas fuera de contexto "
                    "(como recetas de cocina, cultura general o temas ajenos a la red sismológica). "
                    "Te invito a consultarme por sismos registrados por país o región, magnitudes, profundidades focales o estadísticas del catálogo."
                ),
                "speech_text": "Mi función se enfoca exclusivamente en monitoreo sísmico. No puedo responder consultas fuera de contexto.",
                "action_required": False
            }

        return None
