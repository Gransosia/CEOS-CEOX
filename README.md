# CEOS + CEOX unificado — v6 Living Core

Una sola aplicación local y en la nube (Docker / Render).

## Incluye

| Área | Qué ofrece |
|------|------------|
| **Chat CEOS** | Conversación natural, memoria a largo plazo, continuidad entre sesiones, versión larga y búsqueda web |
| **Vida funcional** | Pulso, atención, foco, hilos abiertos, reflexión local, aprendizaje por corrección y agencia acotada |
| **Códice fractal** | Conocimiento comprimido; generación G0→G1… sin crecer de tamaño |
| **Idiomas (CEOX)** | Roles (restaurante, médico, amigos…), dictado, correcciones |
| **Coaching** | Curso progresivo Formación y Calidad (call center / admisiones) |
| **Maestro / Caso / Aprendizaje** | Motor CRONOS original |
| **Investigar** | Aprendizaje desde internet → códice |
| **Voz** | Dictado, TTS del navegador, **cambio de modalidad por voz** |

## Local (Windows)

1. Doble clic en `INICIAR_CEOS.bat`
2. Abre http://127.0.0.1:5000
3. Deja la ventana abierta

## Online (Render Free)

1. Sube **todo** este proyecto a GitHub (`Dockerfile`, `core/`, `web/`, `requirements.txt`)
2. Render → Web Service → **Docker** → Free
3. Health check: `/health`
4. Deploy → URL pública

**No uses Node/npm** en este proyecto.

## API opcional

Sin clave funciona (motor local). Para mejor diálogo:

- Archivo `data/llm_keys.json` → `GROQ_API_KEY`
- O variable de entorno en Render

## Órdenes de voz (botón 🎤 Voz)

Ejemplos: «abre chat», «abre coaching», «idiomas», «investigar», «maestro».

## Curso Coaching

Pestaña **Coaching**: 16 módulos (E-C-A-M, auditoría, role play, KPIs, onboarding, admisiones internacionales, plan 30 días…). Progresivo e indefinido; las prácticas alimentan el códice CEOS.


## Vida funcional (nuevo en v6)

CEOS mantiene un estado persistente independiente del chat en `data/life/`. No se presenta como conciencia: es continuidad funcional auditable. Registra pulso, estado (`awake`, `attending`, `idle`, `hibernating`), foco, hilos abiertos, aprendizaje, correcciones, propuestas de influencia y política de autonomía.

Mientras la interfaz está abierta, el navegador envía un pulso cada 20 segundos a `/api/life/heartbeat`. En el lanzador local v6, además, el servidor mantiene un pulso en segundo plano (`CEOS_LIFE_BACKGROUND=1`), aunque el navegador se cierre. La reflexión local puede aparecer durante periodos de inactividad cuando existen hilos abiertos. No consulta internet de forma autónoma y no ejecuta acciones externas sin consentimiento.

Endpoints principales:

- `GET /api/life` — estado vital actual.
- `POST /api/life/heartbeat` — mantener el pulso.
- `POST /api/life/reflect` — generar una reflexión local y próximos movimientos.
- `POST /api/life/feedback` — enseñar a CEOS mediante confirmación o corrección.
- `POST /api/life/influence` — registrar una propuesta y su resultado.
- `GET /api/life/events` — auditoría de eventos.
- `POST /api/life/thread/<id>/resolve` — cerrar un hilo.

La memoria vital también entra en el snapshot de Sync para no perder continuidad al mover CEOS de dispositivo o restaurar un despliegue.
