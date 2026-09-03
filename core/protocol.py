"""
Protocolo de arquetipo v2 — lógica determinista, sin IA.
Fuente: síntesis Propp / Vogler / Jung / Eysenck (Nivel B — sin contraste empírico aún).
"""

ARCHETYPES = {
    "Heroe/Protagonista": "Rol estructurante, modo habitual, control alto. (Propp: Héroe; Vogler: Hero; Jung: Héroe)",
    "Sombra": "Modo oculto, sigma alto o creciente. (Propp: Agresor/Villano; Vogler: Shadow; Jung: Sombra)",
    "Mentor/Donante": "Rol estructurante, control alto, sin ser el protagonista. (Propp: Donante; Vogler: Mentor; Jung: Sabio/Mago)",
    "Auxiliar/Aliado": "Rol dependiente, control medio, modo habitual. (Propp: Auxiliar; Jung: Cuidador)",
    "Heraldo/Mandatario": "Sigma alto, control bajo — señales de Umbral sin capacidad de corregir. (Propp: Mandatario; Vogler: Herald)",
    "Guardian del Umbral": "Control alto, modo habitual, función de contención más que de avance. (Vogler: Threshold Guardian; Jung: Gobernante)",
    "Metamorfo": "Señales mixtas o inconsistentes — ambiguo por definición. (Vogler: Shapeshifter)",
    "Falso Heroe": "Declara un rol positivo (Héroe/Mentor/Guardián) pero el rol operativo calculado es negativo (Sombra/Embaucador/Forastero). (Propp: Falso Héroe)",
    "Embaucador": "Modo prohibido, ruptura de regla sin choque real contra un sustrato externo. (Vogler: Trickster; Jung: Bufón)",
    "Forastero": "Modo prohibido con choque real contra un sustrato externo no controlado.",
}

ROLES_POSITIVOS = {"Heroe/Protagonista", "Mentor/Donante", "Guardian del Umbral", "Auxiliar/Aliado"}
ROLES_NEGATIVOS = {"Sombra", "Embaucador", "Forastero", "Falso Heroe"}

VALID_MODOS = {"habitual", "oculto", "prohibido"}
VALID_REGLA = {"estructurante", "dependiente"}
VALID_NIVEL = {"bajo", "medio", "alto"}


def _validar(modo, regla, kappa, sigma):
    if modo not in VALID_MODOS:
        raise ValueError(f"modo inválido: {modo!r} (usa uno de {sorted(VALID_MODOS)})")
    if regla not in VALID_REGLA:
        raise ValueError(f"regla inválida: {regla!r} (usa uno de {sorted(VALID_REGLA)})")
    if kappa not in VALID_NIVEL or sigma not in VALID_NIVEL:
        raise ValueError(f"kappa/sigma deben ser uno de {sorted(VALID_NIVEL)}")


def compute_rol_operativo(modo, regla, kappa, sigma, choque_externo=False):
    """Calcula el arquetipo operativo real a partir de las señales del sistema.
    Devuelve None si ninguna condición encaja con suficiente claridad."""
    _validar(modo, regla, kappa, sigma)

    if modo == "prohibido":
        return "Forastero" if choque_externo else "Embaucador"
    if modo == "oculto" and sigma in ("alto", "medio"):
        return "Sombra"
    if sigma == "alto" and kappa == "bajo":
        return "Heraldo/Mandatario"
    if kappa == "alto" and regla == "estructurante" and modo == "habitual":
        return "Heroe/Protagonista"
    if kappa == "alto" and regla == "estructurante":
        return "Mentor/Donante"
    if kappa == "alto" and modo == "habitual":
        return "Guardian del Umbral"
    if sigma == "alto" and kappa == "medio":
        return "Metamorfo"
    if regla == "dependiente" and kappa == "medio" and modo == "habitual":
        return "Auxiliar/Aliado"
    return None


def build_case(identidad, modo, regla, kappa, sigma, rol_declarado=None, choque_externo=False, device=None):
    if rol_declarado is not None and rol_declarado not in ARCHETYPES:
        raise ValueError(f"rol_declarado inválido: {rol_declarado!r}")

    rol_operativo = compute_rol_operativo(modo, regla, kappa, sigma, choque_externo)

    desajuste = False
    rol_mostrado = rol_operativo
    if rol_declarado and rol_operativo:
        if rol_declarado in ROLES_POSITIVOS and rol_operativo in ROLES_NEGATIVOS:
            desajuste = True
            rol_mostrado = "Falso Heroe"

    return {
        "identidad": identidad,
        "modo": modo,
        "regla": regla,
        "kappa": kappa,
        "sigma": sigma,
        "choque_externo": bool(choque_externo),
        "rol_declarado": rol_declarado,
        "rol_operativo_calculado": rol_operativo,
        "arquetipo": rol_mostrado or "Sin clasificar -- perfil mixto, revisar a mano",
        "descripcion_arquetipo": ARCHETYPES.get(rol_mostrado or "", ""),
        "desajuste_declarado_operativo": desajuste,
        "nivel_evidencia": None,  # criterio A-E pendiente de definir
        "device": device,
    }
