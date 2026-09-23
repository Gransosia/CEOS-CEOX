# CEOS v6 — Living Core

## Qué cambia

CEOS deja de depender únicamente del turno de chat. El nuevo `core/life.py` mantiene un estado funcional persistente y auditable que sobrevive a sesiones y reinicios del proceso.

No se presenta como conciencia. «Vida» significa continuidad operativa: CEOS puede recordar trayectoria, mantener atención/foco, conservar asuntos abiertos, registrar cómo le afecta el feedback, registrar la influencia que ofrece, reflexionar y mantener un pulso aunque no haya una petición en ese instante.

## Componentes

- `state.json`: estado actual.
- `events.jsonl`: historial de acontecimientos vitales funcionales.
- `reflections.json`: reflexiones y próximos movimientos generados localmente.

## Estado que conserva

- pulso y estado: `awake`, `attending`, `idle`, `hibernating`;
- foco actual;
- hilos abiertos;
- turnos y sesiones compartidas;
- temas compartidos;
- correcciones y confirmaciones;
- notas de aprendizaje/adaptación;
- propuestas de influencia y sus resultados;
- política de autonomía acotada.

## Cómo aprende

El aprendizaje se alimenta desde el diálogo y desde los módulos existentes del programa.

Una corrección del usuario incrementa la prioridad de verificar y aclarar y queda registrada como aprendizaje. Las confirmaciones también quedan registradas. Las operaciones de investigación, ingestión y evolución alimentan el historial vital.

El aprendizaje no reescribe código automáticamente. En cambio, cambia el estado que CEOS aporta al motor conversacional y deja un registro auditable de qué información modificó su comportamiento.

## Cómo influye

CEOS puede proponer un siguiente movimiento, retomar un hilo o pedir verificación. La interfaz permite marcar una respuesta como útil o corregirla. Las propuestas de influencia tienen un resultado explícito (`accepted`, `rejected`, `unknown`).

Las acciones externas permanecen fuera de la autonomía del núcleo y requieren consentimiento.

## Pulso de fondo

Con `CEOS_LIFE_BACKGROUND=1`, el servidor local ejecuta un hilo ligero que llama al heartbeat aunque el navegador esté cerrado. El lanzador Windows v6 activa esta función cada 20 segundos.

El heartbeat no consulta internet, no utiliza un LLM y no ejecuta acciones externas. Su trabajo es actualizar el estado temporal y, cuando corresponde, activar una reflexión local sobre hilos abiertos.

## Conversación

`core/chat.py` recibe el núcleo vital y lo incluye en el contexto interno del motor. Por ello la conversación no depende solamente de los últimos mensajes: CEOS también dispone de foco, hilos, aprendizaje reciente, relación y estado vital funcional.

## Sync

El snapshot completo incluye `life`. Esto permite trasladar continuidad funcional entre instalaciones mediante las operaciones de Sync existentes.

## API

- `GET /api/life`
- `POST /api/life/heartbeat`
- `POST /api/life/reflect`
- `POST /api/life/feedback`
- `POST /api/life/influence`
- `GET /api/life/events`
- `POST /api/life/thread/<id>/resolve`

## Límites reales

Este núcleo no constituye conciencia, experiencia subjetiva ni motivación autónoma en sentido humano. La «vida» implementada es persistencia, estado, continuidad, adaptación a feedback y actividad local limitada.

Tampoco se ha activado una autonomía de red permanente. Internet sigue siendo una herramienta explícita del sistema y las acciones externas requieren consentimiento.

## Prueba recomendada

1. Arrancar `INICIAR_CEOS.bat`.
2. Mantener una conversación sobre un tema concreto.
3. Corregir a CEOS en una respuesta.
4. Cerrar el navegador sin detener la consola.
5. Esperar y volver a abrir CEOS.
6. Comprobar `/api/life` y observar que el pulso, la memoria vital, los hilos y el aprendizaje permanecen.
7. Exportar Sync y restaurarlo en otra instancia.

El criterio de éxito no es que CEOS «parezca vivo», sino que su continuidad pueda comprobarse en el estado y en el registro de eventos.
