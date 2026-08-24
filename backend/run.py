import argparse

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Controle de Treinamentos")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="127.0.0.1 = apenas esta máquina (padrão). 0.0.0.0 = acessível na rede local.",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Recarrega automaticamente ao salvar (desenvolvimento)")
    args = parser.parse_args()

    print(f"  -> {__import__('app.config', fromlist=['settings']).settings.APP_NAME}")
    print(f"  -> http://{args.host}:{args.port}")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
