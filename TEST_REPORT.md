# CEOS v8.4 — Informe de auditoría + Laboratorio de Autor

Fecha: 26-09-2026

## Resultado

**22/22 pruebas unitarias pasan.**

También pasan:

- compilación de todos los módulos Python (`compileall`);
- sintaxis de `web/app.js`;
- sintaxis de `app.js`;
- validación de todos los JSON del proyecto;
- auditoría de secretos del árbol de código/documentación.

## Lo que se ha revisado

### LLM

- selección dinámica basada en modelos realmente visibles;
- rechazo de fallback supuesto tras 401/403/404 del descubrimiento;
- fallback controlado para fallos transitorios;
- fallback entre modelos;
- fallback entre proveedores;
- circuit breaker por proveedor y modelo;
- limpieza del cooldown después de un éxito;
- Retry-After y backoff;
- probe real y cacheado;
- bloqueo contra sondas concurrentes;
- OpenAI Responses API + compatibilidad Chat Completions;
- Gemini Interactions API + compatibilidad generateContent;
- claves fuera de las URLs;
- redacción de secretos incluso cuando proceden del archivo local;
- detección de modelos no conversacionales;
- compatibilidad con la API privada de versiones anteriores del puente.

### Servidor

- healthcheck robusto que no consume LLM;
- healthcheck degradado sin convertir fallos opcionales en una caída HTTP del servicio;
- sondas públicas rate-limitadas por dirección de conexión;
- refresh de descubrimiento rate-limitado;
- almacenamiento de claves bloqueado por defecto en Render;
- límite de subida configurable (64 MB por defecto).

### Frontend

- la interfaz ya no llama «LLM activo» a una API solamente configurada;
- distingue «LLM listo» de «API configurada pero no probada»;
- `Comprobar API` realiza una generación real y muestra proveedor/modelo.

## Limitación importante

El entorno de auditoría actual no contiene Flask/Gunicorn y no permite instalar dependencias desde Internet. Por eso no se ha ejecutado aquí una prueba HTTP completa de Flask/Render con una clave real del usuario. Esa última prueba debe hacerse en el despliegue, con las claves reales configuradas como secretos.

La auditoría local sí prueba la lógica de selección, fallback, diagnóstico, redacción de secretos, caché, circuit breakers, adaptador Gemini, extracción OpenAI y los ciclos de agencia/adaptación.


## Laboratorio de Autor

- análisis reproducible del corpus por autor;
- diagnóstico de voz, ritmo, diálogo, exposición, metanarrativa, imaginación, poda y precisión;
- lectura CRONOS-Espiral-OCA de génesis, pérdida, encuentro, desafío, transformación, sustitución, integración y retorno;
- ejercicios de reescritura y enseñanza;
- API `/api/author/*`;
- pestaña **Autor** en la interfaz;
- modo conversacional **Autor**.

El laboratorio funciona con heurística local cuando no hay LLM y usa el LLM operativo para profundizar cuando está disponible.
