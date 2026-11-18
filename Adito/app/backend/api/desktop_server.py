"""
Ponto de entrada do núcleo local do Adito (é o que o Tauri sobe, e o alvo do empacotamento).

Não abre porta: conversa com o Tauri por stdin/stdout (ver rpc/server.py).
O Tauri passa ORACULO_DATA_DIR e a chave do LLM no ambiente.
"""
import os
import sys


def main() -> None:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rpc.server import main as serve

    serve()


if __name__ == "__main__":
    main()
