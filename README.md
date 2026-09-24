# CEOS v8 — Living Entity / Adaptive Dialogue

CEOS v8 mantiene el núcleo v7 y añade una capa explícita de adaptación conversacional y pedagógica. El objetivo no es simular una conciencia subjetiva, sino construir continuidad funcional: CEOS recuerda, aprende de correcciones, ajusta su forma de conversar y puede enseñarte siguiendo tu progreso.

## Conversación orgánica

El chat distingue entre conversación, exploración, análisis, acción, corrección y enseñanza. Ajusta profundidad, estructura y ritmo a la petición y conserva hilos abiertos para no reiniciar la conversación constantemente.

## Maestro adaptativo

En modo «Aprender conmigo», CEOS trabaja por microciclos: ancla → explica → ejemplifica → recuperación/aplicación → contraste → transferencia. Mantiene un mapa de dominio por conceptos y aumenta la dificultad cuando detecta señales de comprensión. Una respuesta correcta provisional no se convierte automáticamente en una verdad: el sistema conserva el carácter heurístico de esa evaluación.

## Aprendizaje de CEOS

`core/adaptive.py` persiste:

- perfil conversacional adaptativo;
- temas recurrentes;
- dominio pedagógico por concepto;
- errores/zonas de dificultad;
- hilos abiertos;
- hitos de continuidad;
- feedback del usuario.

El aprendizaje es incremental y auditable. Las correcciones explícitas tienen más peso que las inferencias heurísticas.

## Nuevos endpoints

- `GET /api/chat/adaptive` — perfil adaptativo y contexto de trabajo.
- `POST /api/chat/feedback` — feedback que reajusta el modelo conversacional.
- `POST /api/chat/teach` — siguiente movimiento pedagógico para un tema.
- `POST /api/chat` — admite `mode=organic|teach|analysis`.

## Filosofía de v8

```text
experiencia
  ↓
memoria
  ↓
interpretación
  ↓
adaptación
  ↓
respuesta / enseñanza
  ↓
feedback
  ↓
actualización del modelo
  ↓
nueva experiencia
```

No se afirma conciencia subjetiva. «Entidad viva» significa continuidad funcional, memoria, adaptación, aprendizaje, iniciativa y capacidad pedagógica.

---

# CEOS + CEOX unificado — v7 Agency

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


## Vida funcional

CEOS mantiene un estado persistente independiente del chat en `data/life/`. No se presenta como conciencia: es continuidad funcional auditable. Registra pulso, estado (`awake`, `attending`, `idle`, `hibernating`), foco, hilos abiertos, aprendizaje, correcciones, propuestas de influencia y política de autonomía.

Mientras la interfaz está abierta, el navegador envía un pulso cada 20 segundos a `/api/life/heartbeat`. En el lanzador local v7, además, el servidor mantiene un pulso en segundo plano (`CEOS_LIFE_BACKGROUND=1`), aunque el navegador se cierre. La reflexión local puede aparecer durante periodos de inactividad cuando existen hilos abiertos. No consulta internet de forma autónoma y no ejecuta acciones externas sin consentimiento.

Endpoints principales:

- `GET /api/life` — estado vital actual.
- `POST /api/life/heartbeat` — mantener el pulso.
- `POST /api/life/reflect` — generar una reflexión local y próximos movimientos.
- `POST /api/life/feedback` — enseñar a CEOS mediante confirmación o corrección.
- `POST /api/life/influence` — registrar una propuesta y su resultado.
- `GET /api/life/events` — auditoría de eventos.
- `POST /api/life/thread/<id>/resolve` — cerrar un hilo.

La memoria vital también entra en el snapshot de Sync para no perder continuidad al mover CEOS de dispositivo o restaurar un despliegue.


## CEOS v7 — Living Core + Agency + GitHub Bridge

Esta versión añade dos capas funcionales nuevas:

- **Autobiografía funcional**: CEOS conserva una historia auditable de arranques, relaciones, aprendizajes, reflexiones e influencias. No implica conciencia subjetiva.
- **GitHub Bridge**: lectura del repositorio configurado y sistema de propuestas locales. La publicación está deliberadamente separada de la propuesta: solo se permite con `CEOS_GITHUB_WRITE=1` y un token adecuado.

### Variables para Render / GitHub

```text
CEOS_ADMIN_TOKEN=un_secreto_largo_y_aleatorio
CEOS_GITHUB_TOKEN=...
CEOS_GITHUB_REPOSITORY=Gransosia/CEOS-CEOX
CEOS_GITHUB_BRANCH=main
CEOS_GITHUB_WRITE=0
CEOS_GITHUB_ALLOW_WORKFLOWS=0
CEOS_GITHUB_COMMITTER_NAME=CEOS
CEOS_GITHUB_COMMITTER_EMAIL=ceos@users.noreply.github.com
```

Para el primer despliegue recomiendo `CEOS_GITHUB_WRITE=0`: CEOS podrá leer el repo y crear propuestas locales, pero no modificará GitHub. Cuando quieras pasar a evolución controlada, habilita escritura y utiliza el flujo rama → Pull Request → revisión humana.

Para un servicio público en Render, el acceso a la lectura/escritura del repositorio está protegido además por `CEOS_ADMIN_TOKEN`; no se debe publicar un token de GitHub en el frontend. La API REST de GitHub utiliza el esquema actual de versionado; el puente fija `X-GitHub-Api-Version: 2026-03-10`. Para crear o actualizar archivos, GitHub documenta permisos `Contents: write` en tokens de acceso granular. citeturn825885search0turn825885search3


## CEOS v7 — Agency Core (base de v8)

La v7 incorpora una capa de agencia persistente encima del Living Core:

- **Objetivos**: CEOS puede conservar metas activas y progreso.
- **Iniciativas**: el estado del sistema puede producir propuestas de siguiente movimiento.
- **Experimentos ex ante**: las predicciones quedan congeladas antes del desenlace.
- **Lagunas de modelo**: CEOS puede registrar que su ontología o representación es insuficiente.
- **Evolución**: puede formular propuestas de cambio del propio sistema y prepararlas para GitHub, sin escribir directamente en `main`.
- **Auditoría**: cada ciclo queda registrado.

### Flujo

```text
experiencia
  ↓
memoria
  ↓
estado
  ↓
agencia
  ↓
propuesta
  ↓
aceptación/rechazo
  ↓
acción permitida
  ↓
resultado
  ↓
aprendizaje
```

La v7 sigue sin afirmar conciencia subjetiva. «Vida» significa continuidad funcional, memoria, aprendizaje, iniciativa y trazabilidad.
