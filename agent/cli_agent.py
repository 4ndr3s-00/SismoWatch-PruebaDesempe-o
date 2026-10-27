"""
SismoWatch - Interactive AI Agent Terminal Console
Run this script to chat directly with the agent in real-time.
"""
import sys
import json
from agent.core.agent_engine import SismoWatchAgent

def main():
    print("=" * 70)
    print("🌍⚡ SISMO-WATCH: AGENTE INTELIGENTE DE MONITOREO SÍSMICO")
    print("   Arquitectura: 100% Local | Cero Tokens | Cero Alucinaciones")
    print("   Escribe 'salir' o 'exit' para terminar.")
    print("=" * 70)

    agent = SismoWatchAgent()
    print("\nAgente SismoWatch: ¡Hola! Sistema listo. Puedes preguntarme lo que desees.\n")

    while True:
        try:
            query = input("Usuario > ").strip()
            if not query:
                continue
            if query.lower() in ["salir", "exit", "quit"]:
                print("\nAgente SismoWatch: ¡Hasta pronto! Vigilancia sísmica activa.")
                break

            result = agent.ask(query)
            print("\n" + "-" * 70)
            print(f"Agente SismoWatch:\n{result['response']}")
            print("-" * 70)
            t = result["telemetry"]
            print(f"📊 [Telemetría: {t['latency_ms']} ms | Tokens: {t['tokens_consumed']} | Costo: ${t['cost_usd']} | Alucinación: {t['hallucination_probability']} | Fuente: {t.get('storage_backend')}]")
            print("-" * 70 + "\n")

        except (KeyboardInterrupt, EOFError):
            print("\nSesión finalizada.")
            break

if __name__ == "__main__":
    main()
