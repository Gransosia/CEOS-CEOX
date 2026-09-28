# CEOS v10 — Grafo Vivo de Coevolución

CEOS 10 añade una capa por encima de la Mente Fractal: un grafo que conserva **quién aprende, qué se estudia y qué necesita aprender el propio CEOS**.

## Tres sistemas relacionados

**Usuario** → objetivos, dominio, preguntas, posiciones y correcciones.

**Obra/proyecto** → libros, inventos, investigaciones, conceptos y líneas de trabajo.

**CEOS** → conocimiento disponible, incertidumbres, relaciones, lagunas y siguiente acción.

## El ciclo

`experiencia → observación → relación → diagnóstico → enseñanza/investigación → resultado → nuevo estado`

La coevolución no implica conciencia. Es continuidad funcional, persistente y auditable.

## Decisión del siguiente movimiento

CEOS pondera:

- importancia del nodo;
- dominio estimado del usuario;
- nivel de evidencia;
- incertidumbre;
- relación con el contexto actual;
- necesidad de transferencia.

Reglas:

- **research** cuando hay incertidumbre o evidencia débil;
- **teach** cuando el conocimiento está suficientemente sostenido y el dominio del usuario es bajo;
- **practice** cuando el dominio es intermedio;
- **connect** cuando el concepto ya está consolidado y conviene transferirlo a otro dominio;
- **reflect** para detectar qué debería aprender CEOS de sí mismo.

## Infinitud discreta

El grafo no promete una biblioteca física infinita dentro de un sello. La "biblioteca en un sello" se implementa como representación relacional densa: nodos direccionables, referencias, deduplicación, compresión y recuperación estructural. La información original sigue siendo necesaria para reconstruir literalmente el corpus completo.

## Seguridad y persistencia

El grafo se almacena como cápsula comprimida y, si `cryptography` está disponible, cifrada con la misma estrategia de `CEOS_MIND_KEY`. En Render, la clave debe permanecer en Environment Secrets y el almacenamiento persistente debe apuntar a una ruta que no se elimine entre despliegues.
