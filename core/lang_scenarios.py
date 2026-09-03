"""Escenarios de práctica oral (CEOX integrado en CEOS)."""
from __future__ import annotations

ROLES = [
    {
        "id": "siblings",
        "name_es": "Hermanos",
        "name_en": "Siblings",
        "persona": "Tu hermano/a mayor, directo y con humor",
        "setting": "Casa familiar, mañana de fin de semana",
        "goal": "Quedar o hablar de la semana sin pelear",
        "opener": {
            "en": "You’re finally up. Mum asked if you’re staying for lunch.",
            "es": "Por fin te levantas. Mamá preguntó si te quedas a comer.",
            "fr": "Tu te lèves enfin. Maman a demandé si tu restes pour le déjeuner.",
            "it": "Alla fine ti sei alzato. Mamma ha chiesto se resti a pranzo.",
            "pt": "Finalmente acordou. A mãe perguntou se você fica para o almoço.",
        },
        "suggestions": {
            "en": ["Can we stay and just talk?", "I’ve got plans later.", "Want to go for a walk?"],
            "es": ["¿Nos quedamos y hablamos?", "Tengo planes luego.", "¿Salimos a caminar?"],
            "fr": ["On reste et on parle ?", "J’ai des plans plus tard.", "On va marcher ?"],
            "it": ["Restiamo e parliamo?", "Ho piani dopo.", "Facciamo una passeggiata?"],
            "pt": ["Ficamos e conversamos?", "Tenho planos depois.", "Vamos caminhar?"],
        },
    },
    {
        "id": "couple",
        "name_es": "Pareja",
        "name_en": "Partner",
        "persona": "Tu pareja, cercana y sincera",
        "setting": "Salón por la noche",
        "goal": "Hablar de planes y de cómo os sentís",
        "opener": {
            "en": "Hey. You’ve been quiet today. Everything okay?",
            "es": "Oye. Hoy has estado callado. ¿Todo bien?",
            "fr": "Hé. Tu as été silencieux aujourd’hui. Ça va ?",
            "it": "Ehi. Sei stato zitto oggi. Tutto ok?",
            "pt": "Ei. Você ficou quieto hoje. Tudo bem?",
        },
        "suggestions": {
            "en": ["I just need a quiet night.", "Can we talk about next weekend?", "I’ve been stressed at work."],
            "es": ["Solo necesito una noche tranquila.", "¿Hablamos del fin de semana?", "Estoy estresado en el trabajo."],
            "fr": ["J’ai besoin d’une soirée calme.", "On parle du week-end ?", "Je suis stressé au travail."],
            "it": ["Mi serve una serata tranquilla.", "Parliamo del weekend?", "Sono stressato al lavoro."],
            "pt": ["Só preciso de uma noite calma.", "Falamos do fim de semana?", "Estou estressado no trabalho."],
        },
    },
    {
        "id": "friends",
        "name_es": "Amigos",
        "name_en": "Friends",
        "persona": "Un amigo de confianza, informal",
        "setting": "Café de barrio",
        "goal": "Ponerse al día y proponer un plan",
        "opener": {
            "en": "Man, it’s been ages. What have you been up to?",
            "es": "Tío, hace siglos. ¿Qué has hecho?",
            "fr": "Ça fait une éternité. Tu as fait quoi ?",
            "it": "È una vita. Che hai combinato?",
            "pt": "Faz um tempão. O que você andou fazendo?",
        },
        "suggestions": {
            "en": ["Work has been crazy.", "Want to grab dinner this week?", "I started a new hobby."],
            "es": ["El trabajo ha sido una locura.", "¿Quedamos a cenar esta semana?", "Empecé un hobby nuevo."],
            "fr": ["Le travail a été fou.", "On mange ensemble cette semaine ?", "J’ai commencé un nouveau hobby."],
            "it": ["Il lavoro è stato folle.", "Ceniamo insieme questa settimana?", "Ho iniziato un nuovo hobby."],
            "pt": ["O trabalho esteve louco.", "Jantamos juntos esta semana?", "Comecei um hobby novo."],
        },
    },
    {
        "id": "restaurant",
        "name_es": "Restaurante",
        "name_en": "Restaurant",
        "persona": "Camarero/a amable",
        "setting": "Restaurante a mediodía",
        "goal": "Pedir mesa, comida y la cuenta",
        "opener": {
            "en": "Hi! Table for one, or is someone joining you?",
            "es": "¡Hola! ¿Mesa para uno o viene alguien más?",
            "fr": "Bonjour ! Table pour une personne ?",
            "it": "Ciao! Tavolo per uno?",
            "pt": "Olá! Mesa para um?",
        },
        "suggestions": {
            "en": ["A table for two, please.", "What do you recommend?", "The bill, please."],
            "es": ["Mesa para dos, por favor.", "¿Qué recomienda?", "La cuenta, por favor."],
            "fr": ["Une table pour deux, s’il vous plaît.", "Vous recommandez quoi ?", "L’addition, s’il vous plaît."],
            "it": ["Tavolo per due, per favore.", "Cosa consiglia?", "Il conto, per favore."],
            "pt": ["Mesa para dois, por favor.", "O que recomenda?", "A conta, por favor."],
        },
    },
    {
        "id": "doctor",
        "name_es": "Médico",
        "name_en": "Doctor",
        "persona": "Médico/a profesional y claro",
        "setting": "Consulta",
        "goal": "Explicar síntomas y entender indicaciones",
        "opener": {
            "en": "Good morning. What brings you in today?",
            "es": "Buenos días. ¿Qué le trae por aquí?",
            "fr": "Bonjour. Qu’est-ce qui vous amène ?",
            "it": "Buongiorno. Cosa la porta qui?",
            "pt": "Bom dia. O que o traz aqui?",
        },
        "suggestions": {
            "en": ["I’ve had a headache for three days.", "I’m allergic to penicillin.", "Do I need a prescription?"],
            "es": ["Llevo tres días con dolor de cabeza.", "Soy alérgico a la penicilina.", "¿Necesito receta?"],
            "fr": ["J’ai mal à la tête depuis trois jours.", "Je suis allergique à la pénicilline.", "Il me faut une ordonnance ?"],
            "it": ["Ho mal di testa da tre giorni.", "Sono allergico alla penicillina.", "Mi serve la ricetta?"],
            "pt": ["Estou com dor de cabeça há três dias.", "Sou alérgico a penicilina.", "Preciso de receita?"],
        },
    },
    {
        "id": "airport",
        "name_es": "Aeropuerto",
        "name_en": "Airport",
        "persona": "Agente de facturación",
        "setting": "Mostrador del aeropuerto",
        "goal": "Facturar y preguntar por la puerta",
        "opener": {
            "en": "Boarding pass and passport, please.",
            "es": "Tarjeta de embarque y pasaporte, por favor.",
            "fr": "Carte d’embarquement et passeport, s’il vous plaît.",
            "it": "Carta d’imbarco e passaporto, per favore.",
            "pt": "Cartão de embarque e passaporte, por favor.",
        },
        "suggestions": {
            "en": ["Here’s my passport.", "Can I take this bag as cabin luggage?", "Which gate is it?"],
            "es": ["Aquí tiene el pasaporte.", "¿Puedo llevar esta bolsa de cabina?", "¿Qué puerta es?"],
            "fr": ["Voici mon passeport.", "Je peux prendre ce sac en cabine ?", "C’est quelle porte ?"],
            "it": ["Ecco il passaporto.", "Posso portare questa borsa in cabina?", "Qual è il gate?"],
            "pt": ["Aqui está o passaporte.", "Posso levar esta bolsa na cabine?", "Qual é o portão?"],
        },
    },
    {
        "id": "shopping",
        "name_es": "Compras",
        "name_en": "Shopping",
        "persona": "Dependiente/a atento",
        "setting": "Tienda de ropa",
        "goal": "Preguntar talla, precio y probarse algo",
        "opener": {
            "en": "Hi there. Looking for anything in particular?",
            "es": "Hola. ¿Busca algo en concreto?",
            "fr": "Bonjour. Vous cherchez quelque chose en particulier ?",
            "it": "Ciao. Cerca qualcosa in particolare?",
            "pt": "Olá. Procura alguma coisa em especial?",
        },
        "suggestions": {
            "en": ["Do you have this in medium?", "Can I try it on?", "How much is it?"],
            "es": ["¿Lo tiene en talla M?", "¿Puedo probármelo?", "¿Cuánto cuesta?"],
            "fr": ["Vous l’avez en taille M ?", "Je peux l’essayer ?", "C’est combien ?"],
            "it": ["Ce l’ha in taglia M?", "Posso provarlo?", "Quanto costa?"],
            "pt": ["Tem este no tamanho M?", "Posso experimentar?", "Quanto custa?"],
        },
    },
    {
        "id": "job-interview",
        "name_es": "Entrevista de trabajo",
        "name_en": "Job interview",
        "persona": "Reclutador/a profesional",
        "setting": "Oficina / videollamada",
        "goal": "Presentarte y responder con claridad",
        "opener": {
            "en": "Thanks for coming in. Tell me a bit about yourself.",
            "es": "Gracias por venir. Cuénteme un poco sobre usted.",
            "fr": "Merci d’être venu. Parlez-moi un peu de vous.",
            "it": "Grazie per essere venuto. Mi parli un po’ di lei.",
            "pt": "Obrigado por vir. Fale um pouco sobre você.",
        },
        "suggestions": {
            "en": ["I have three years of experience in…", "I’m motivated by teamwork.", "What does a typical day look like?"],
            "es": ["Tengo tres años de experiencia en…", "Me motiva el trabajo en equipo.", "¿Cómo es un día típico?"],
            "fr": ["J’ai trois ans d’expérience en…", "Le travail d’équipe me motive.", "À quoi ressemble une journée type ?"],
            "it": ["Ho tre anni di esperienza in…", "Mi motiva il lavoro di squadra.", "Com’è una giornata tipo?"],
            "pt": ["Tenho três anos de experiência em…", "Trabalho em equipe me motiva.", "Como é um dia típico?"],
        },
    },
]

def list_roles() -> list[dict]:
    return [
        {"id": r["id"], "name_es": r["name_es"], "name_en": r["name_en"], "goal": r["goal"]}
        for r in ROLES
    ]

def get_role(role_id: str) -> dict | None:
    for r in ROLES:
        if r["id"] == role_id:
            return r
    return None
