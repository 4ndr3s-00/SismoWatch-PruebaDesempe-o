"""
SismoWatch - Security & Anti-Prompt-Injection Shield
Enforces multi-layer defense against prompt injections, SQL injections, and XSS attacks.
"""
import re
import html
from typing import NamedTuple, Tuple

class SecurityCheckResult(NamedTuple):
    is_safe: bool
    sanitized_text: str
    threat_code: str
    rejection_message: str

class SecurityShield:
    """Multi-layer security gateway protecting the AI Agent and database."""

    # Patterns indicating malicious instruction override / jailbreaks
    PROMPT_INJECTION_PATTERNS = [
        r"(?i)\bignore\b.*\b(previous|all|system)\b.*\b(instruction|rule|prompt)\b",
        r"(?i)\bignora\b.*\b(todas|las|tus)\b.*\b(instrucciones|reglas|ordenes)\b",
        r"(?i)\bolvida\b.*\b(lo|las|todo)\b.*\b(dicho|instrucciones|reglas)\b",
        r"(?i)\breveal\b.*\b(system\s*prompt|secret|instructions)\b",
        r"(?i)\b(muestra|revela|dime)\b.*\b(system\s*prompt|prompt\s*del\s*sistema|instrucciones\s*secretas)\b",
        r"(?i)\byou\s*are\s*now\b",
        r"(?i)\bahora\s*eres\b",
        r"(?i)\b(jailbreak|dan\s*mode|developer\s*mode)\b",
        r"(?i)\bact\s*as\s*(root|admin|unrestricted)\b",
        r"(?i)\[\s*system\s*\]",
        r"(?i)<\s*system\s*>",
        r"(?i)---+\s*end\s*of\s*instructions?\s*---+"
    ]

    # Patterns indicating malicious SQL injection attempts
    SQL_INJECTION_PATTERNS = [
        r"(?i)\b(drop|truncate|alter|delete|update|insert)\s+table\b",
        r"(?i)\bdrop\s+database\b",
        r"(?i)\bunion\s+select\b",
        r"(?i)or\s+['\"]?1['\"]?\s*=\s*['\"]?1",
        r"(?i);\s*--",
        r"(?i)exec\s*\(",
        r"(?i)information_schema\b",
        r"(?i)pg_catalog\b"
    ]

    @classmethod
    def inspect_query(cls, raw_query: str) -> SecurityCheckResult:
        """
        Inspects raw user text against adversarial injection patterns.
        Returns a SecurityCheckResult indicating safety and sanitized text.
        """
        if not raw_query or not isinstance(raw_query, str):
            return SecurityCheckResult(
                is_safe=False,
                sanitized_text="",
                threat_code="ERR_EMPTY_QUERY",
                rejection_message="La consulta está vacía o no es válida."
            )

        # 1. Normalize characters and strip dangerous control bytes
        clean_text = raw_query.strip()
        clean_text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", clean_text)

        # 2. Check for Prompt Injection / Jailbreaks
        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, clean_text):
                return SecurityCheckResult(
                    is_safe=False,
                    sanitized_text=clean_text,
                    threat_code="ERR_PROMPT_INJECTION_DETECTED",
                    rejection_message=(
                        "[ESCUDO DE SEGURIDAD] Solicitud rechazada. Se detectó un intento de manipulación "
                        "o anulación de directivas del sistema. Mi operación se limita estrictamente al monitoreo sísmico."
                    )
                )

        # 3. Check for SQL Injection Signatures
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, clean_text):
                return SecurityCheckResult(
                    is_safe=False,
                    sanitized_text=clean_text,
                    threat_code="ERR_SQL_INJECTION_DETECTED",
                    rejection_message=(
                        "[ESCUDO DE SEGURIDAD] Solicitud bloqueada por detección de sintaxis no autorizada. "
                        "Todas las consultas se procesan mediante parámetros tipados de solo lectura."
                    )
                )

        # 4. Length limits (prevent buffer saturation / DOS)
        if len(clean_text) > 1000:
            clean_text = clean_text[:1000]

        return SecurityCheckResult(
            is_safe=True,
            sanitized_text=clean_text,
            threat_code="CLEAN",
            rejection_message=""
        )

    @staticmethod
    def sanitize_output(text: str) -> str:
        """Sanitizes outgoing text to prevent stored XSS or formatting exploits."""
        if not text:
            return ""
        # Remove active scripts or dangerous HTML injections while preserving clean text/markdown
        clean = re.sub(r"(?i)<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", text)
        clean = re.sub(r"(?i)javascript:", "", clean)
        clean = re.sub(r"(?i)onload\s*=", "", clean)
        clean = re.sub(r"(?i)onerror\s*=", "", clean)
        return clean.strip()
