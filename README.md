# CEOS + CEOX unificado

Una sola aplicación local y en la nube (Docker / Render).

## Incluye

| Área | Qué ofrece |
|------|------------|
| **Chat CEOS** | Conversación natural, memoria a largo plazo, versión larga, búsqueda web |
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
