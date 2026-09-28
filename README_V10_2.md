# CEOS v10.2 — Grafo Visual + Charla Continua

Esta versión toma como base CEOS 10.1 y lleva las dos capas a la interfaz de forma utilizable.

## 1. Grafo

El backend añade `GET /api/coevolution/view` para devolver una vista curada del grafo. La interfaz la dibuja con SVG nativo, sin librerías externas. Se priorizan usuario, CEOS, obras/proyectos, dominios y nodos relevantes para el foco. Los nodos se pueden pulsar para abrir su detalle.

## 2. Charla

Al abrir el chat se recupera el historial persistido de la sesión. Las respuestas muestran estado de escritura, feedback `✓/↺`, nueva sesión y limpieza. El estado conversacional (`intención`, `tema`, `modo`, `turnos`) vuelve a la interfaz después de cada respuesta.

## 3. Límites honestos

La continuidad y el aprendizaje dependen de los almacenamientos y, cuando se use, del proveedor LLM configurado. El grafo representa memoria y relaciones funcionales; no demuestra conciencia subjetiva.
