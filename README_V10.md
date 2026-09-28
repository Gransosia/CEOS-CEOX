# CEOS v10.2 — Grafo Vivo / Maestro-Aprendiz / Fractal Mind

CEOS v10 añade el **Grafo Vivo de Coevolución** a las capacidades de v9.

## Qué hace

- representa explícitamente el usuario, sus obras/proyectos y los dominios de conocimiento;
- registra relaciones con procedencia y nivel de evidencia;
- conserva postura: apoyo, rechazo, incertidumbre o desconocimiento;
- estima dominio de cada concepto para decidir la próxima acción pedagógica;
- distingue lo que CEOS debería enseñar de lo que primero debe investigar;
- mantiene una cola dinámica de siguientes movimientos;
- sincroniza el grafo en los snapshots completos de CEOS;
- se integra en el contexto de conversación para que las respuestas nazcan de la trayectoria compartida.

## Nuevos endpoints

- `GET /api/coevolution/status`
- `GET /api/coevolution/search?q=...`
- `GET /api/coevolution/graph`
- `GET /api/coevolution/next`
- `GET /api/coevolution/teacher`
- `GET /api/coevolution/research`
- `GET /api/coevolution/autopilot`
- `POST /api/coevolution/learn`
- `POST /api/coevolution/feedback`
- `POST /api/coevolution/stance`
- `POST /api/coevolution/mastery`
- `POST /api/coevolution/connect`

## Conocimiento semilla

Incluye el corpus y mapa de autor disponible; CRONOS-Espiral-OCa; astroteología; gnosis; astrología; teoría de números; historia de ciencia e invención; y los autores/figuras que se han solicitado como ejes de estudio.

## Maestro y aprendiz

CEOS no debe enseñar una hipótesis como si fuera un hecho. La evidencia queda marcada E1–E5 y el motor del siguiente movimiento prioriza investigación cuando la incertidumbre es alta.

## Instalación

Local: `INICIAR_CEOS.bat`.

Online: desplegar el contenido del repositorio conectado a Render. Mantener `CEOS_MIND_KEY` como secreto y conservar `CEOS_DATA_DIR` en almacenamiento persistente.
