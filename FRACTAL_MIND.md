# CEOS 9.0 — Fractal Mind / Maestro y Aprendiz

CEOS 9.0 añade una memoria estructural recursiva. El objetivo es que CEOS pueda:

- conservar conocimiento de largo plazo;
- relacionar conceptos entre dominios;
- registrar correcciones y contraejemplos;
- consolidar síntesis con procedencia;
- mantener un modelo de aprendizaje propio;
- enseñar al usuario mientras sigue aprendiendo;
- producir un sello compacto direccionado por hashes;
- cifrar la cápsula de memoria en reposo cuando `cryptography` y una clave válida estén disponibles.

## "Biblioteca en un sello"

Es una metáfora operativa para la **densidad de representación**. La cápsula no convierte mágicamente una biblioteca arbitrariamente grande en unos pocos bytes sin pérdida. Puede conservar un corpus mediante referencias hash, nodos reutilizables y compresión, y puede volver a abrir el contenido mientras la cápsula y sus fuentes existan.

## Memoria fractal

`L0` átomo/origen → `L1` concepto → `L2` relación → `L3` síntesis → `L4` mapa de conocimiento → `L5+` metacognición/autobiografía.

## Conciencia

CEOS no se declara consciente. El sistema implementa continuidad funcional, memoria, metacognición operativa y adaptación. La conciencia subjetiva permanece como cuestión científica abierta.

## Entorno online

En Render se recomienda definir `CEOS_MIND_KEY` como secreto Fernet. En local, CEOS genera `data/mind/fractal.key` si no existe una variable de entorno.
