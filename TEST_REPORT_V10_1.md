# CEOS v10.1 — Informe de pruebas

Fecha: 2026-09-28

## Pruebas realizadas
- Unit tests: 30/30 OK
- Python compileall: OK
- JavaScript web/app.js: OK
- JavaScript inline de web/index.html: 13/13 OK
- Secret scan: OK (auditoría existente)
- Grafo de coevolución: persistencia y nuevas obras/proyectos OK
- Conversación casual: detector y registro compacto OK

## Cambios específicamente auditados
- La charla cotidiana no activa web por defecto.
- Las solicitudes explícitas de investigación pueden activar web.
- La conversación casual no crea nodos léxicos por palabra.
- Se conserva estado conversacional de sesión.
- Se añaden al grafo FORMA 333 / Olla lenta, SAD / Tubería y CRONOS-333.
- Se añaden perfiles de obra/proyecto.
- La UI «Mis obras y proyectos» consulta el grafo vivo.

## Limitación
No se hizo una conversación LLM real contra una cuenta del usuario ni un deploy real de Render en este entorno porque no hay claves del usuario ni Flask instalado localmente. La batería de pruebas usa mocks cuando corresponde.
