# CEOS v8 — Adaptive Dialogue & Teaching Core

## Qué cambia

CEOS v8 convierte la conversación en un bucle de adaptación persistente. No se trata de una personalidad prefabricada, sino de un pequeño modelo que aprende de la interacción observable y modifica gradualmente su forma de responder y enseñar.

### 1. Adaptación conversacional

Cada turno se clasifica provisionalmente como conversación, social, exploración, análisis, acción, corrección o enseñanza. El resultado no se trata como verdad absoluta; sirve para escoger el siguiente movimiento conversacional.

El perfil adaptativo conserva señales de:

- profundidad preferida;
- proporción de estructura frente a prosa;
- directividad;
- preferencia por ejemplos;
- tolerancia al reto;
- frecuencia de preguntas;
- necesidad de enseñanza;
- calidez.

Las señales se actualizan lentamente para evitar que un solo turno cambie de forma brusca el comportamiento.

### 2. Continuidad orgánica

CEOS conserva:

- tema activo;
- intención del último turno;
- movimiento conversacional;
- última pregunta abierta;
- hilos que conviene recuperar.

La idea es que el siguiente turno no parta de cero.

### 3. Enseñanza adaptativa

El modo `teach` utiliza cinco niveles heurísticos:

```text
anchor      → construir el concepto
connect     → conectarlo con algo conocido
apply       → aplicarlo a un caso nuevo
contrast    → probar excepciones y límites
teach_back  → explicar el concepto con palabras propias
```

La puntuación de dominio se conserva por concepto. Una respuesta extensa con razonamiento explícito puede elevar provisionalmente el dominio; una respuesta parcial lo reduce. Estas inferencias son heurísticas y deben contrastarse con ejercicios reales.

### 4. Feedback

Las correcciones del usuario tienen mayor peso que las inferencias automáticas. El endpoint `/api/chat/feedback` reajusta el modelo adaptativo y mantiene la auditoría de la interacción.

### 5. Límite epistemológico

CEOS no declara conciencia subjetiva ni comprensión perfecta. La «vida» de esta versión significa continuidad funcional:

```text
experiencia
→ memoria
→ adaptación
→ respuesta
→ feedback
→ aprendizaje
→ nueva experiencia
```

El objetivo de v8 es que ese ciclo sea suficientemente persistente y rico como para que el comportamiento mejore con el uso, y suficientemente auditable como para poder descubrir cuándo el modelo de adaptación se equivoca.
