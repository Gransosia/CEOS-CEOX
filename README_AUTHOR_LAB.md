# CEOS v8.4 — Laboratorio de Autor

Esta versión incorpora un módulo específico para analizar una obra literaria y al autor como sistema de aprendizaje, sin convertir la crítica en una puntuación numérica.

## Qué hace

1. Lee el corpus ingerido en `data/library`.
2. Compara muestras de inicio, centro y final y busca pasajes representativos.
3. Construye un diagnóstico de voz, ritmo, diálogo, personajes, exposición, metanarrativa, imaginación, poda y precisión.
4. Separa observación textual, interpretación y propuesta de mejora.
5. Aplica una segunda capa CRONOS-Espiral-OCa: génesis, pérdida, encuentro, desafío, transformación, sustitución, integración, estados, relaciones y retorno transformado.
6. Genera ejercicios pedagógicos para convertir crítica en práctica.
7. Con LLM operativo, genera un informe profundo; sin LLM, funciona con una heurística explícita y reproducible.

## API

- `GET /api/author/corpus?author=...`
- `POST /api/author/analyze`
- `POST /api/author/lesson`
- `GET /api/author/reports`

## Principio de diseño

CEOS debe proteger lo singular de la voz y atacar lo que limita su potencia. No debe decir simplemente que una obra «es buena» o «mala»: debe explicar qué mecanismo textual produce el efecto, qué lo debilita y qué experimento de reescritura permitiría comprobarlo.
