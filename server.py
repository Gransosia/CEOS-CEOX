"""Punto de entrada compatible de CEOS.

La implementación canónica vive en ``core.server``. Mantener un único backend
elimina divergencias entre el servidor usado por ``run.py`` y este archivo.
"""
from core.server import app, main, start_life_background_worker  # noqa: F401


if __name__ == "__main__":
    main()
