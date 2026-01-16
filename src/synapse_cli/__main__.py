from asyncio import run

from .main import main

__all__ = ["main"]

# Si se ejecuta el módulo directamente, corre main()
if __name__ == "__main__":
    run(main())
