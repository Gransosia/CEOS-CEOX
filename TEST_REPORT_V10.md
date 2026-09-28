# CEOS v10.0 — Informe de pruebas

## Pruebas ejecutadas

- `python -m unittest discover -s tests -p 'test_*.py' -q` → **27/27 OK**.
- `python tools/audit.py` → **AUDIT PASSED**.
- `compileall` Python → **OK**.
- `node --check web/app.js` → **OK**.
- `node --check app.js` → **OK**.
- JSON audit → **OK**.
- Secret scan → **OK**.

## Nuevas pruebas v10

`tests/test_v10_coevolution.py` comprueba:

1. semilla de usuario, obras, dominios y figuras de estudio;
2. modificación de dominio mediante feedback;
3. elección contextual de enseñanza e investigación;
4. ciclo de autopiloto con aprendizaje en ambos sentidos;
5. persistencia del grafo y sus relaciones.

## Prueba funcional adicional

Se instanció `CoEvolutionGraph` en un directorio temporal, se comprobó creación del grafo, búsqueda de corpus, recomendación de enseñanza, cola de investigación, autopiloto, persistencia y recuperación.

## Limitación del entorno de comprobación

El contenedor de auditoría no tiene Flask instalado. Por ello no se ejecutó una prueba HTTP real de `core.server` en este entorno. La aplicación sí incluye `requirements.txt` con Flask/Gunicorn y los endpoints se validan indirectamente mediante compilación y pruebas de núcleo.

La verificación final del servidor debe realizarse al arrancar localmente o tras el deploy en Render.
