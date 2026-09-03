/* CEOS v5 — frontend multi-dispositivo */
const DEVICE_ID_KEY = "ceos_device_id";

function getDeviceId() {
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = "dev-" + Math.random().toString(36).slice(2, 10);
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

async function api(path, opts = {}) {
  const headers = Object.assign(
    { "Content-Type": "application/json", "X-Device-Id": getDeviceId() },
    opts.headers || {}
  );
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

// ---------- Tabs + cambio por voz ----------
function showView(name) {
  const btn = document.querySelector(`.tab[data-view="${name}"]`);
  const view = document.getElementById("view-" + name);
  if (!view) return false;
  document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  if (btn) btn.classList.add("active");
  view.classList.add("active");
  if (name === "chat") try { focusChat(); } catch (e) {}
  if (name === "home") try { refreshHome(); } catch (e) {}
  if (name === "maestro") try { refreshMaestro(); } catch (e) {}
  if (name === "learn") try { refreshTrajectories(); } catch (e) {}
  if (name === "research") try { refreshResearch(); } catch (e) {}
  if (name === "grammar") try { refreshGrammar(); } catch (e) {}
  if (name === "sync") try { refreshSync(); } catch (e) {}
  if (name === "lang") try { loadLangRoles(); } catch (e) {}
  if (name === "coaching") try { loadCoachingCourse(); } catch (e) {}
  return true;
}

const VOICE_ROUTES = [
  { re: /\b(chat|conversaci[oó]n|hablar con ceos)\b/i, view: "chat" },
  { re: /\b(inicio|home|principal)\b/i, view: "home" },
  { re: /\b(maestro|mentor)\b/i, view: "maestro" },
  { re: /\b(caso|an[aá]lisis)\b/i, view: "case" },
  { re: /\b(aprendizaje|aprender|trayector)/i, view: "learn" },
  { re: /\b(idioma|idiomas|ceox|ingl[eé]s|pr[aá]ctica de idiomas)\b/i, view: "lang" },
  { re: /\b(coaching|calidad|formaci[oó]n y calidad|curso de coaching)\b/i, view: "coaching" },
  { re: /\b(investigar|investigaci[oó]n|buscar en (internet|la red))\b/i, view: "research" },
  { re: /\b(infinitud|gram[aá]tica|c[oó]dice)\b/i, view: "grammar" },
  { re: /\b(sync|sincroniz)/i, view: "sync" },
];

function matchVoiceRoute(transcript) {
  const t = (transcript || "").trim();
  if (!t) return null;
  // Prefijos de orden: "abre", "ve a", "modo", "cambiar a", "ir a"
  const cleaned = t.replace(/^(abre|abrir|ve a|vamos a|modo|cambiar a|cambia a|ir a|pon|activa)\s+/i, "");
  for (const r of VOICE_ROUTES) {
    if (r.re.test(t) || r.re.test(cleaned)) return r.view;
  }
  return null;
}

let _voiceNavRec = null;
let _voiceNavListening = false;

function speakStatus(msg) {
  speakWithSelectedVoice(msg, "es-ES");
}

function startVoiceNavigation() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const status = document.getElementById("voice-nav-status");
  const btn = document.getElementById("voice-nav-btn");
  if (!SR) {
    alert("Tu navegador no soporta reconocimiento de voz. Prueba Chrome o Edge.");
    return;
  }
  if (_voiceNavListening && _voiceNavRec) {
    try { _voiceNavRec.stop(); } catch (e) {}
    _voiceNavListening = false;
    if (btn) btn.classList.remove("listening");
    if (status) status.textContent = "";
    return;
  }
  const rec = new SR();
  _voiceNavRec = rec;
  rec.lang = "es-ES";
  rec.interimResults = false;
  rec.maxAlternatives = 3;
  rec.onstart = () => {
    _voiceNavListening = true;
    if (btn) btn.classList.add("listening");
    if (status) status.textContent = "Escuchando… di por ejemplo: «abre coaching»";
  };
  rec.onerror = () => {
    _voiceNavListening = false;
    if (btn) btn.classList.remove("listening");
    if (status) status.textContent = "No te he entendido. Intenta de nuevo.";
  };
  rec.onend = () => {
    _voiceNavListening = false;
    if (btn) btn.classList.remove("listening");
  };
  rec.onresult = (ev) => {
    let best = "";
    for (let i = 0; i < ev.results.length; i++) {
      best += (ev.results[i][0]?.transcript || "") + " ";
    }
    best = best.trim();
    if (status) status.textContent = "Has dicho: «" + best + "»";
    const view = matchVoiceRoute(best);
    if (view && showView(view)) {
      const labels = {
        chat: "Chat", home: "Inicio", maestro: "Maestro", case: "Caso",
        learn: "Aprendizaje", lang: "Idiomas", coaching: "Coaching",
        research: "Investigar", grammar: "Infinitud", sync: "Sync",
      };
      speakStatus("Abriendo " + (labels[view] || view));
      if (status) status.textContent = "→ " + (labels[view] || view);
    } else {
      if (status) status.textContent = "No reconocí la modalidad. Prueba: chat, coaching, idiomas…";
      speakStatus("No reconocí la modalidad");
    }
  };
  try {
    rec.start();
  } catch (e) {
    if (status) status.textContent = "No se pudo iniciar el micrófono.";
  }
}

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    showView(btn.dataset.view);
});


// ---------- Chat conversacional ----------
const CHAT_SESSION_KEY = "ceos_chat_session_id";
let chatBusy = false;

function getChatSessionId() {
  let id = localStorage.getItem(CHAT_SESSION_KEY);
  if (!id) {
    id = "s-" + Math.random().toString(36).slice(2, 12);
    localStorage.setItem(CHAT_SESSION_KEY, id);
  }
  return id;
}

function setChatSessionId(id) {
  localStorage.setItem(CHAT_SESSION_KEY, id);
  const el = document.getElementById("chat-session-label");
  if (el) el.textContent = id.slice(0, 14);
}

function focusChat() {
  const input = document.getElementById("chat-input");
  if (input) setTimeout(() => input.focus(), 80);
  refreshChatBadge();
}

function refreshChatBadge(engine) {
  const badge = document.getElementById("chat-engine-badge");
  if (!badge) return;
  if (engine === "local") {
    badge.textContent = "local";
    badge.classList.add("local");
  } else if (engine) {
    badge.textContent = engine;
    badge.classList.remove("local");
  }
}

function appendChatBubble(role, content, meta) {
  const box = document.getElementById("chat-messages");
  if (!box) return null;
  const div = document.createElement("div");
  div.className = "chat-bubble " + role;
  const who = role === "user" ? "Tú" : "CEOS";
  const metaLine = meta ? `<div class="bubble-meta">${escapeHtml(who)} · ${escapeHtml(meta)}</div>` : `<div class="bubble-meta">${escapeHtml(who)}</div>`;
  div.innerHTML = metaLine + `<div class="bubble-body">${escapeHtml(content)}</div>`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function setChatTyping(on) {
  const box = document.getElementById("chat-messages");
  if (!box) return;
  let el = document.getElementById("chat-typing");
  if (on) {
    if (!el) {
      el = document.createElement("div");
      el.id = "chat-typing";
      el.className = "chat-bubble assistant typing";
      el.innerHTML = `<div class="bubble-meta">CEOS</div><div class="bubble-body">Escribiendo…</div>`;
      box.appendChild(el);
    }
    box.scrollTop = box.scrollHeight;
  } else if (el) {
    el.remove();
  }
}

function setChatStatus(msg) {
  const el = document.getElementById("chat-status");
  if (el) el.textContent = msg || "";
}

async function loadChatHistory() {
  const sid = getChatSessionId();
  setChatSessionId(sid);
  try {
    const data = await api("/api/chat/history?session_id=" + encodeURIComponent(sid));
    const box = document.getElementById("chat-messages");
    if (!box) return;
    const msgs = data.messages || [];
    if (!msgs.length) return;
    box.innerHTML = "";
    msgs.forEach((m) => {
      const role = m.role === "user" ? "user" : "assistant";
      appendChatBubble(role, m.content || "", m.engine || "");
      if (m.engine) refreshChatBadge(m.engine);
    });
  } catch (e) {
    console.warn("chat history", e);
  }
}

async function sendChatMessage(text) {
  text = (text || "").trim();
  if (!text || chatBusy) return;
  chatBusy = true;
  const input = document.getElementById("chat-input");
  const sendBtn = document.getElementById("btn-chat-send");
  if (input) input.value = "";
  autoSizeChatInput();
  if (sendBtn) sendBtn.disabled = true;

  appendChatBubble("user", text);
  setChatTyping(true);
  setChatStatus("Pensando…");

  // ocultar sugerencias tras el primer mensaje real
  const sug = document.getElementById("chat-suggestions");
  if (sug) sug.style.display = "none";

  try {
    const longOpt = document.getElementById("chat-opt-long");
    const webOpt = document.getElementById("chat-opt-web");
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        message: text,
        session_id: getChatSessionId(),
        long: !!(longOpt && longOpt.checked),
        web: !!(webOpt && webOpt.checked),
      }),
    });
    setChatTyping(false);
    appendChatBubble("assistant", res.reply || "(sin respuesta)", res.engine || res.mode || "");
    refreshChatBadge(res.engine || res.mode);
    if (res.reply) speakChatText(res.reply);
    refreshMemoryBadge();
    refreshFractalBadge();
    refreshFractalBadge(res.fractal);
    if (res.web && res.web_meta && res.web_meta.ok) {
      setChatStatus((document.getElementById("chat-status").textContent || "") + " · web " + (res.web_meta.results || 0) + " fuentes");
    }
    const mem = res.memory || {};
    const absF = mem.absorbed_facts || 0;
    const absT = mem.absorbed_topics || 0;
    let statusMsg = res.mode === "local" ? "Modo local (sin API LLM)" : "";
    if (absF || absT) {
      statusMsg = (statusMsg ? statusMsg + " · " : "") + "Memoria +" + absF + " hechos, +" + absT + " temas";
    }
    setChatStatus(statusMsg);
  } catch (e) {
    setChatTyping(false);
    appendChatBubble("assistant", "No pude responder: " + (e.message || e));
    setChatStatus("Error de conexión");
  } finally {
    chatBusy = false;
    if (sendBtn) sendBtn.disabled = false;
    if (input) input.focus();
  }
}

function autoSizeChatInput() {
  const input = document.getElementById("chat-input");
  if (!input) return;
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 140) + "px";
}


// ---------- Voz del navegador (Web Speech API) + memoria UI ----------
const VOICE_PREF_KEY = "ceos_chat_tts";
let chatTtsEnabled = localStorage.getItem(VOICE_PREF_KEY) === "1";
let chatRecognizing = false;
let chatRecognition = null;

const VOICE_PREF_KEY = "ceos_tts_voice";

function isFemaleVoiceName(name) {
  const n = (name || "").toLowerCase();
  // Nombres / etiquetas frecuentes de voces femeninas en navegadores
  return /female|femenin|woman|mujer|sabina|monica|mónica|paulina|lucia|lucía|maria|maría|carmen|pilar|elena|soledad|helen|zira|hazel|susan|linda|catherine|karen|moira|fiona|veena|tessa|samantha|victoria|google español|microsoft sabina|microsoft helena|microsoft haruka/.test(n);
}

function getPreferredVoice() {
  if (!("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices() || [];
  if (!voices.length) return null;
  const saved = localStorage.getItem(VOICE_PREF_KEY);
  if (saved) {
    const hit = voices.find((v) => v.name === saved);
    if (hit) return hit;
  }
  // 1) Español femenina
  const esFem = voices.find((v) => /es(-|_)|spanish|español/i.test(v.lang + " " + v.name) && isFemaleVoiceName(v.name));
  if (esFem) return esFem;
  // 2) Cualquier femenina
  const anyFem = voices.find((v) => isFemaleVoiceName(v.name));
  if (anyFem) return anyFem;
  // 3) Cualquier español
  const es = voices.find((v) => /es(-|_)|spanish|español/i.test(v.lang + " " + v.name));
  if (es) return es;
  return voices[0] || null;
}

function populateVoiceSelect() {
  const sel = document.getElementById("voice-select");
  if (!sel || !("speechSynthesis" in window)) return;
  const voices = window.speechSynthesis.getVoices() || [];
  const saved = localStorage.getItem(VOICE_PREF_KEY);
  // Orden: femeninas ES primero, luego otras femeninas, luego resto ES, luego todas
  const scored = voices.map((v) => {
    let s = 0;
    const es = /es(-|_)|spanish|español/i.test(v.lang + " " + v.name);
    const fem = isFemaleVoiceName(v.name);
    if (es && fem) s = 3;
    else if (fem) s = 2;
    else if (es) s = 1;
    return { v, s };
  });
  scored.sort((a, b) => b.s - a.s || a.v.name.localeCompare(b.v.name));
  sel.innerHTML = scored
    .map(({ v, s }) => {
      const tag = s === 3 ? " · ♀ ES" : s === 2 ? " · ♀" : s === 1 ? " · ES" : "";
      const selAttr = (saved && saved === v.name) || (!saved && s === 3) ? " selected" : "";
      return `<option value="${v.name.replace(/"/g, "&quot;")}"${selAttr}>${v.name}${tag}</option>`;
    })
    .join("");
  if (!saved && sel.value) localStorage.setItem(VOICE_PREF_KEY, sel.value);
  sel.onchange = () => {
    localStorage.setItem(VOICE_PREF_KEY, sel.value);
  };
}

function speakWithSelectedVoice(text, lang) {
  if (!text || !("speechSynthesis" in window)) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang || "es-ES";
    u.rate = 1.0;
    const voice = getPreferredVoice();
    if (voice) {
      u.voice = voice;
      if (voice.lang) u.lang = voice.lang;
    }
    window.speechSynthesis.speak(u);
  } catch (e) {
    console.warn("tts", e);
  }
}

function speakChatText(text) {
  if (!chatTtsEnabled) return;
  if (!("speechSynthesis" in window)) {
    setChatStatus("Este navegador no soporta voz");
    return;
  }
  speakWithSelectedVoice(text, "es-ES");
}

function stopChatSpeech() {
  if ("speechSynthesis" in window) {
    try { window.speechSynthesis.cancel(); } catch (e) {}
  }
}

function updateVoiceToggleUI() {
  const btn = document.getElementById("btn-chat-voice-toggle");
  if (!btn) return;
  if (chatTtsEnabled) {
    btn.classList.add("active");
    btn.title = "Voz alta: ON (clic para apagar)";
    btn.textContent = "🔊";
  } else {
    btn.classList.remove("active");
    btn.title = "Voz alta: OFF (clic para activar)";
    btn.textContent = "🔈";
  }
}

function getSpeechRecognition() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  if (chatRecognition) return chatRecognition;
  const rec = new SR();
  rec.lang = "es-ES";
  rec.interimResults = true;
  rec.continuous = false;
  rec.onresult = (ev) => {
    let finalText = "";
    let interim = "";
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const t = ev.results[i][0].transcript;
      if (ev.results[i].isFinal) finalText += t;
      else interim += t;
    }
    const input = document.getElementById("chat-input");
    if (input) {
      if (finalText) {
        input.value = (input.value ? input.value + " " : "") + finalText.trim();
        autoSizeChatInput();
      } else if (interim) {
        setChatStatus("Escuchando: " + interim);
      }
    }
  };
  rec.onerror = (ev) => {
    chatRecognizing = false;
    const mic = document.getElementById("btn-chat-mic");
    if (mic) mic.classList.remove("listening");
    setChatStatus(ev.error === "not-allowed" ? "Micrófono bloqueado por el navegador" : "Error de dictado");
  };
  rec.onend = () => {
    chatRecognizing = false;
    const mic = document.getElementById("btn-chat-mic");
    if (mic) mic.classList.remove("listening");
    setChatStatus("");
  };
  chatRecognition = rec;
  return rec;
}

function toggleDictation() {
  const rec = getSpeechRecognition();
  const mic = document.getElementById("btn-chat-mic");
  if (!rec) {
    setChatStatus("Dictado no disponible en este navegador");
    return;
  }
  if (chatRecognizing) {
    try { rec.stop(); } catch (e) {}
    chatRecognizing = false;
    if (mic) mic.classList.remove("listening");
    setChatStatus("");
    return;
  }
  stopChatSpeech();
  try {
    rec.start();
    chatRecognizing = true;
    if (mic) mic.classList.add("listening");
    setChatStatus("Escuchando… habla ahora");
  } catch (e) {
    setChatStatus("No se pudo iniciar el micrófono");
  }
}

async function refreshFractalBadge(state) {
  const badge = document.getElementById("chat-fractal-badge");
  if (!badge) return;
  try {
    const s = state || (await api("/api/codex/fractal"));
    const g = (s && (s.generation || s.logarithm)) || 0;
    badge.textContent = "G" + g;
    badge.title = "Logaritmo de re-cifrado fractal del Codex: generación " + g
      + " · cristales " + (s.crystals_now || "?")
      + "/" + (s.budget_crystals || "?");
  } catch (e) {
    badge.textContent = "G—";
  }
}

async function refreshMemoryBadge() {
  const badge = document.getElementById("chat-memory-badge");
  if (!badge) return;
  try {
    const data = await api("/api/memory/long");
    const s = (data && data.stats) || {};
    const n = (s.facts || 0) + (s.topics || 0);
    badge.textContent = n ? ("mem " + n) : "mem —";
    badge.title = "Memoria a largo plazo: " + (s.facts || 0) + " hechos, " + (s.topics || 0) + " temas, " + (s.insights || 0) + " insights";
  } catch (e) {
    badge.textContent = "mem —";
  }
}

function bindChatUI() {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      sendChatMessage(input && input.value);
    });
  }
  if (input) {
    input.addEventListener("input", autoSizeChatInput);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage(input.value);
      }
    });
  }
  document.querySelectorAll("#chat-suggestions .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const p = chip.getAttribute("data-prompt") || chip.textContent;
      sendChatMessage(p);
    });
  });
  const btnNew = document.getElementById("btn-chat-new");
  if (btnNew) {
    btnNew.addEventListener("click", async () => {
      try {
        const res = await api("/api/chat/session", { method: "POST", body: "{}" });
        setChatSessionId(res.session_id);
        const box = document.getElementById("chat-messages");
        if (box) {
          box.innerHTML = "";
          appendChatBubble(
            "assistant",
            "Nueva conversación. ¿En qué quieres trabajar?"
          );
        }
        const sug = document.getElementById("chat-suggestions");
        if (sug) sug.style.display = "";
        setChatStatus("");
        focusChat();
      } catch (e) {
        setChatStatus(e.message || "No se pudo crear sesión");
      }
    });
  }
  const btnClear = document.getElementById("btn-chat-clear");
  if (btnClear) {
    btnClear.addEventListener("click", async () => {
      try {
        await api("/api/chat/clear", {
          method: "POST",
          body: JSON.stringify({ session_id: getChatSessionId() }),
        });
        const box = document.getElementById("chat-messages");
        if (box) {
          box.innerHTML = "";
          appendChatBubble(
            "assistant",
            "Conversación limpia. Puedes empezar de nuevo cuando quieras."
          );
        }
        const sug = document.getElementById("chat-suggestions");
        if (sug) sug.style.display = "";
        setChatStatus("");
      } catch (e) {
        setChatStatus(e.message || "No se pudo limpiar");
      }
    });
  }
  const btnVoice = document.getElementById("btn-chat-voice-toggle");
  if (btnVoice) {
    updateVoiceToggleUI();
    btnVoice.addEventListener("click", () => {
      chatTtsEnabled = !chatTtsEnabled;
      localStorage.setItem(VOICE_PREF_KEY, chatTtsEnabled ? "1" : "0");
      updateVoiceToggleUI();
      if (!chatTtsEnabled) stopChatSpeech();
      else setChatStatus("Voz alta activada");
    });
  }
  const btnMic = document.getElementById("btn-chat-mic");
  if (btnMic) {
    btnMic.addEventListener("click", () => toggleDictation());
  }
}


// ---------- Home ----------
async function refreshHome() {
  try {
    const [ident, status, cases] = await Promise.all([
      api("/api/identity"),
      api("/api/sync/status"),
      api("/api/cases?limit=8"),
    ]);
    document.getElementById("status").textContent = "en línea · " + getDeviceId();
    try {
      const user = await api("/api/user");
      const g = document.getElementById("greeting");
      if (g && user.greeting) g.textContent = user.greeting;
      const nameEl = document.getElementById("user-name");
      if (nameEl && user.name) nameEl.value = user.name;
      const nivEl = document.getElementById("user-nivel");
      if (nivEl && user.nivel) nivEl.value = user.nivel;
      const vEl = document.getElementById("user-voice");
      if (vEl && user.voice_label) vEl.value = user.voice_label;
    } catch (e) {}
    document.getElementById("identity-box").innerHTML = `
      <div><strong>${ident.core.name}</strong> · ${ident.core.version}</div>
      <div style="margin-top:6px;color:var(--muted)">${ident.core.mission}</div>
      <div style="margin-top:8px"><em>Objetivo:</em> ${ident.goal}</div>
    `;
    document.getElementById("corpus-stats").innerHTML = `
      <div class="stat"><div class="n">${status.cases}</div><div class="l">Casos</div></div>
      <div class="stat"><div class="n">${status.hitos}</div><div class="l">Hitos</div></div>
      <div class="stat"><div class="n">${status.trajectories}</div><div class="l">Trayectorias</div></div>
      <div class="stat"><div class="n">${status.grammar.fragmentos}</div><div class="l">Fragmentos</div></div>
    `;
    const ul = document.getElementById("recent-cases");
    if (!cases.length) {
      ul.innerHTML = "<li class='muted'>Aún no hay casos.</li>";
    } else {
      ul.innerHTML = cases
        .slice()
        .reverse()
        .map(
          (c) =>
            `<li><span class="tag">${c.arquetipo}</span> ${escapeHtml(
              (c.identidad || "").slice(0, 90)
            )}</li>`
        )
        .join("");
    }
  } catch (e) {
    document.getElementById("status").textContent = "error de conexión";
    console.error(e);
  }
}

// ---------- Caso ----------
async function loadMeta() {
  const meta = await api("/api/meta");
  const sel = document.getElementById("case-rol");
  meta.arquetipos.forEach((a) => {
    const opt = document.createElement("option");
    opt.value = a;
    opt.textContent = a;
    sel.appendChild(opt);
  });
  document.getElementById("lan-url").textContent = `http://${meta.lan_ip}:5000`;
}

document.getElementById("btn-analyze").addEventListener("click", async () => {
  const body = {
    identidad: document.getElementById("case-identidad").value.trim(),
    modo: document.getElementById("case-modo").value,
    regla: document.getElementById("case-regla").value,
    kappa: document.getElementById("case-kappa").value,
    sigma: document.getElementById("case-sigma").value,
    rol_declarado: document.getElementById("case-rol").value || null,
    choque_externo: document.getElementById("case-choque").checked,
    device: getDeviceId(),
  };
  if (!body.identidad) {
    alert("Escribe una descripción del sistema.");
    return;
  }
  const box = document.getElementById("case-result");
  try {
    const saved = await api("/api/cases", { method: "POST", body: JSON.stringify(body) });
    box.classList.remove("hidden");
    box.className = "result ok";
    let msg = `Arquetipo: ${saved.arquetipo}\n`;
    if (saved.descripcion_arquetipo) msg += `(${saved.descripcion_arquetipo})\n`;
    if (saved.desajuste_declarado_operativo) {
      msg += `\n⚠ Desajuste declarado/operativo: declaraba «${saved.rol_declarado}», opera como «${saved.rol_operativo_calculado}».`;
    }
    msg += `\n\nCaso guardado · id ${saved.id.slice(0, 8)}…`;
    box.textContent = msg;
    document.getElementById("case-identidad").value = "";
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = "Error: " + e.message;
  }
});

// ---------- Aprendizaje ----------
document.getElementById("btn-design").addEventListener("click", async () => {
  const learner = document.getElementById("learn-desc").value.trim();
  const objetivo = document.getElementById("learn-objetivo").value.trim() || "Avanzar en la Espiral";
  if (!learner) {
    alert("Describe al aprendiz.");
    return;
  }
  const box = document.getElementById("traj-result");
  try {
    const traj = await api("/api/learning/trajectory", {
      method: "POST",
      body: JSON.stringify({ learner, objetivo }),
    });
    box.classList.remove("hidden");
    box.className = "result ok";
    let msg = `Trayectoria creada (${traj.pasos.length} pasos)\nObjetivo: ${traj.objetivo}\n\n`;
    traj.pasos.forEach((p) => {
      msg += `${p.orden}. [${p.fase}] ${p.guia}\n`;
    });
    box.textContent = msg;
    refreshTrajectories();
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = "Error: " + e.message;
  }
});

async function refreshTrajectories() {
  const list = document.getElementById("traj-list");
  try {
    const trajs = await api("/api/learning/trajectories");
    if (!trajs.length) {
      list.innerHTML = "<li class='muted'>Ninguna trayectoria aún.</li>";
      return;
    }
    list.innerHTML = trajs
      .slice()
      .reverse()
      .map((t) => {
        const prog = t.progreso || 0;
        const total = (t.pasos || []).length;
        return `<li>
          <span class="tag">${t.estado || "activa"}</span>
          <strong>${escapeHtml((t.objetivo || "").slice(0, 50))}</strong><br/>
          <span class="muted">${escapeHtml((t.learner || "").slice(0, 60))} · ${prog}/${total}</span>
          ${
            t.estado !== "completada"
              ? `<br/><button data-advance="${t.id}" style="margin-top:6px;padding:6px 10px;font-size:0.8rem">Avanzar paso</button>`
              : ""
          }
        </li>`;
      })
      .join("");

    list.querySelectorAll("[data-advance]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.advance;
        await api(`/api/learning/trajectory/${id}/advance`, {
          method: "POST",
          body: JSON.stringify({}),
        });
        refreshTrajectories();
      });
    });
  } catch (e) {
    list.innerHTML = `<li class="muted">Error: ${e.message}</li>`;
  }
}

// ---------- Maestro CRONOS ----------
let lastLessonBody = "";

async function refreshMaestro() {
  try {
    const st = await api("/api/mentor/stats");
    try {
      const llm = await api("/api/llm/status");
      const el = document.getElementById("llm-status");
      if (el) {
        el.textContent = llm.available
          ? "Redacción profunda ACTIVA (" + llm.providers.join(", ") + ")"
          : (llm.hint || "Sin API key — modo local");
        el.style.color = llm.available ? "var(--ok)" : "var(--muted)";
      }
      const cs = await api("/api/codex/stats");
      const csel = document.getElementById("codex-stats");
      if (csel) {
        csel.innerHTML = `
          <div class="stat"><div class="n">${cs.atoms}</div><div class="l">Átomos</div></div>
          <div class="stat"><div class="n">${cs.molecules}</div><div class="l">Moléculas</div></div>
          <div class="stat"><div class="n">${cs.crystals}</div><div class="l">Cristales</div></div>
          <div class="stat"><div class="n">${cs.maps}</div><div class="l">Mapas</div></div>
        `;
      }
    } catch (e) {}
    document.getElementById("mentor-stats").innerHTML = `
      <div class="stat"><div class="n">${st.documentos}</div><div class="l">Documentos</div></div>
      <div class="stat"><div class="n">${st.fragmentos_grammar}</div><div class="l">Fragmentos</div></div>
      <div class="stat"><div class="n">${st.lecciones_generadas}</div><div class="l">Lecciones</div></div>
      <div class="stat"><div class="n">${(st.docs || []).length}</div><div class="l">En biblioteca</div></div>
    `;
    const ul = document.getElementById("library-list");
    if (!st.docs || !st.docs.length) {
      ul.innerHTML = "<li class='muted'>Biblioteca vacía. Carga el conocimiento semilla o pega texto.</li>";
    } else {
      ul.innerHTML = st.docs
        .map(
          (d) =>
            `<li><span class="tag">${d.chunks} frag.</span> <strong>${escapeHtml(
              d.title
            )}</strong> ${(d.tags || []).map((t) => `<span class="muted">#${t}</span>`).join(" ")}</li>`
        )
        .join("");
    }
  } catch (e) {
    document.getElementById("mentor-stats").textContent = "Error: " + e.message;
  }
}

document.getElementById("btn-seed-knowledge").addEventListener("click", async () => {
  const box = document.getElementById("seed-result");
  box.classList.remove("hidden");
  box.className = "result";
  box.textContent = "Incorporando conocimiento semilla CRONOS…";
  try {
    const res = await api("/api/mentor/ingest/seed", { method: "POST", body: "{}" });
    box.className = "result ok";
    box.textContent =
      "Conocimiento semilla procesado:\n" +
      (res.results || []).map((r) => `· ${r.file}: ${r.status}${r.fragments != null ? " (" + r.fragments + " frag.)" : ""}`).join("\n") +
      `\n\nBiblioteca: ${res.stats?.documentos || "?"} docs · ${res.stats?.fragmentos_grammar || "?"} fragmentos`;
    refreshMaestro();
  } catch (e) {
    box.className = "result warn";
    box.textContent = "Error: " + e.message;
  }
});

document.getElementById("btn-diagnose").addEventListener("click", async () => {
  const perfil = document.getElementById("mentor-perfil").value.trim() || "Aprendiz de CRONOS";
  const nivel = document.getElementById("mentor-nivel").value;
  const box = document.getElementById("diagnose-result");
  try {
    const d = await api("/api/mentor/diagnose", {
      method: "POST",
      body: JSON.stringify({ perfil, nivel }),
    });
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent =
      d.mensaje +
      "\n\nFocos recomendados:\n" +
      (d.focos_recomendados || []).map((f, i) => `${i + 1}. ${f}`).join("\n");
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});

document.getElementById("btn-lesson").addEventListener("click", async () => {
  const topic = document.getElementById("lesson-topic").value.trim();
  const estilo = document.getElementById("lesson-estilo").value;
  const nivel = document.getElementById("mentor-nivel").value;
  const box = document.getElementById("lesson-result");
  if (!topic) {
    alert("Escribe un tema.");
    return;
  }
  try {
    const lesson = await api("/api/mentor/lesson", {
      method: "POST",
      body: JSON.stringify({ topic, estilo, nivel }),
    });
    lastLessonBody = lesson.body || "";
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent = lesson.body;
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});

document.getElementById("btn-lesson-speak").addEventListener("click", async () => {
  const text = lastLessonBody || document.getElementById("lesson-result").textContent;
  if (!text || text.length < 20) {
    alert("Genera primero una lección.");
    return;
  }
  const box = document.getElementById("lesson-result");
  try {
    const res = await api("/api/voice/speak", {
      method: "POST",
      body: JSON.stringify({ text: text.slice(0, 1500) }),
    });
    if (res.ok) {
      box.className = "result ok";
    } else {
      alert((res.error || "Sin voz") + "\n\n" + (res.hint || "Instala pyttsx3 y una voz en español en Windows."));
    }
  } catch (e) {
    alert(e.message);
  }
});

document.getElementById("btn-path").addEventListener("click", async () => {
  const perfil = document.getElementById("mentor-perfil").value.trim() || "Aprendiz de CRONOS";
  const objetivo =
    document.getElementById("path-objetivo").value.trim() ||
    "Dominar el protocolo CRONOS-Espiral";
  const nivel = document.getElementById("mentor-nivel").value;
  const box = document.getElementById("path-result");
  try {
    const path = await api("/api/mentor/path", {
      method: "POST",
      body: JSON.stringify({ perfil, objetivo, nivel }),
    });
    box.classList.remove("hidden");
    box.className = "result ok";
    let msg = `Trayectoria de enseñanza creada\nObjetivo: ${path.objetivo}\n\n`;
    (path.pasos || []).forEach((p) => {
      msg += `${p.orden}. [${p.fase}] ${p.leccion_tema || ""}\n   ${p.guia}\n`;
    });
    box.textContent = msg;
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});

document.getElementById("btn-guide").addEventListener("click", async () => {
  const topic = document.getElementById("guide-topic").value.trim();
  const box = document.getElementById("guide-result");
  if (!topic) {
    alert("Escribe el tema de la guía.");
    return;
  }
  try {
    const guide = await api("/api/mentor/guide", {
      method: "POST",
      body: JSON.stringify({ topic }),
    });
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent = guide.markdown || JSON.stringify(guide, null, 2);
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});

document.getElementById("btn-ingest").addEventListener("click", async () => {
  const title = document.getElementById("ingest-title").value.trim() || "Nota";
  const text = document.getElementById("ingest-text").value.trim();
  const box = document.getElementById("ingest-result");
  if (!text) {
    alert("Pega algún texto.");
    return;
  }
  try {
    const entry = await api("/api/mentor/ingest/text", {
      method: "POST",
      body: JSON.stringify({ title, text, tags: ["manual"] }),
    });
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent = `Incorporado: «${entry.title}» — ${entry.fragments_added || 0} fragmentos nuevos (${entry.chunks} trozos).`;
    document.getElementById("ingest-text").value = "";
    refreshMaestro();
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});


document.getElementById("btn-deep").addEventListener("click", async () => {
  const topic = document.getElementById("deep-topic").value.trim();
  const pedido = document.getElementById("deep-pedido").value.trim() || null;
  const use_web = document.getElementById("deep-web").checked;
  const box = document.getElementById("deep-result");
  if (!topic) { alert("Escribe un tema."); return; }
  box.classList.remove("hidden");
  box.className = "result";
  box.textContent = "Generando documento (puede tardar si hay API)…";
  try {
    const doc = await api("/api/mentor/deep", {
      method: "POST",
      body: JSON.stringify({ topic, pedido, use_web }),
    });
    box.className = "result ok";
    box.textContent = `[modo: ${doc.mode} · motor: ${doc.engine || "local"} · fragmentos contexto: ${doc.context_fragments || 0}]\n\n` + (doc.markdown || "");
    lastLessonBody = doc.markdown || "";
    refreshMaestro();
  } catch (e) {
    box.className = "result warn";
    box.textContent = e.message;
  }
});

document.getElementById("btn-compress").addEventListener("click", async () => {
  const topic = document.getElementById("codex-topic").value.trim() || "general";
  const text = document.getElementById("codex-text").value.trim();
  const box = document.getElementById("compress-result");
  if (!text) { alert("Pega texto para comprimir."); return; }
  try {
    const r = await api("/api/codex/compress", {
      method: "POST",
      body: JSON.stringify({ topic, text }),
    });
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent = `Comprimido en Codex\nÁtomos: ${(r.atoms_detected||[]).join(", ") || "—"}\nCristales: ${r.crystals}\nMoléculas: ${r.molecules}\nFragmentos grammar: ${r.grammar_fragments_added||0}`;
    document.getElementById("codex-text").value = "";
    refreshMaestro();
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});



document.getElementById("btn-save-keys").addEventListener("click", async () => {
  const body = {};
  const g = document.getElementById("key-groq").value.trim();
  const m = document.getElementById("key-gemini").value.trim();
  if (g) body.GROQ_API_KEY = g;
  if (m) body.GEMINI_API_KEY = m;
  const box = document.getElementById("keys-result");
  if (!g && !m) { alert("Pega al menos una clave."); return; }
  try {
    const res = await api("/api/llm/keys", { method: "POST", body: JSON.stringify(body) });
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent = "Claves guardadas. Proveedores activos: " + (res.status.providers || []).join(", ");
    document.getElementById("key-groq").value = "";
    document.getElementById("key-gemini").value = "";
    refreshMaestro();
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});


document.getElementById("btn-upload").addEventListener("click", async () => {
  const input = document.getElementById("upload-files");
  const box = document.getElementById("upload-result");
  if (!input.files || !input.files.length) {
    alert("Elige uno o más archivos (PDF, DOCX, TXT, MD).");
    return;
  }
  const fd = new FormData();
  for (const f of input.files) fd.append("file", f);
  box.classList.remove("hidden");
  box.className = "result";
  box.textContent = "Subiendo e incorporando…";
  try {
    const res = await fetch("/api/mentor/ingest/file", {
      method: "POST",
      headers: { "X-Device-Id": getDeviceId() },
      body: fd,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    box.className = "result ok";
    box.textContent = (data.results || [])
      .map((r) =>
        r.status === "ok"
          ? `✓ ${r.file}: ${r.fragments} fragmentos, ${r.chunks} trozos`
          : `✗ ${r.file}: ${r.error || r.status}`
      )
      .join("\n");
    input.value = "";
    refreshMaestro();
  } catch (e) {
    box.className = "result warn";
    box.textContent = "Error: " + e.message;
  }
});

document.getElementById("btn-save-user").addEventListener("click", async () => {
  const name = document.getElementById("user-name").value.trim();
  const nivel = document.getElementById("user-nivel").value;
  const voice_label = document.getElementById("user-voice").value.trim();
  const box = document.getElementById("user-result");
  if (!name) { alert("Escribe tu nombre."); return; }
  try {
    const u = await api("/api/user", {
      method: "POST",
      body: JSON.stringify({ name, nivel, voice_label }),
    });
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent = u.greeting || ("Perfil guardado: " + u.display_name);
    const g = document.getElementById("greeting");
    if (g) g.textContent = u.greeting || "";
  } catch (e) {
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = e.message;
  }
});


document.getElementById("btn-refine").addEventListener("click", async () => {
  const pedido = document.getElementById("refine-pedido").value.trim();
  const n = parseInt(document.getElementById("refine-n").value || "3", 10);
  const use_web = document.getElementById("refine-web").checked;
  const box = document.getElementById("refine-result");
  if (!pedido) { alert("Escribe el pedido."); return; }
  box.classList.remove("hidden");
  box.className = "result";
  box.textContent = "Refinando en " + n + " interacciones… puede tardar.";
  try {
    const res = await api("/api/mentor/refine", {
      method: "POST",
      body: JSON.stringify({ pedido, n, use_web }),
    });
    let msg = (res.note || "") + "\n\n";
    (res.steps || []).forEach((s) => {
      msg += `--- Paso ${s.step} (${s.mode}/${s.engine || "local"}) ---\n${s.preview}\n\n`;
    });
    if (res.final && res.final.markdown) {
      msg += "===== SÍNTESIS FINAL =====\n" + res.final.markdown;
      lastLessonBody = res.final.markdown;
    }
    box.className = "result ok";
    box.textContent = msg;
    refreshMaestro();
  } catch (e) {
    box.className = "result warn";
    box.textContent = e.message;
  }
});

// ---------- Investigación + Voz ----------
async function refreshResearch() {
  // Estado de voz
  try {
    const vs = await api("/api/voice/status");
    const el = document.getElementById("voice-status");
    if (vs.available) {
      el.textContent = `Motor de voz activo: ${vs.engine} (preferencia: voz femenina).`;
      el.style.color = "var(--ok)";
    } else {
      el.textContent = vs.hint || "Sin motor TTS. Instala pyttsx3 para voz en Windows.";
      el.style.color = "var(--warn)";
    }
  } catch (e) {
    document.getElementById("voice-status").textContent = "No se pudo comprobar la voz.";
  }

  // Historial de temas
  try {
    const hist = await api("/api/research/history");
    const ul = document.getElementById("research-history");
    if (!hist.length) {
      ul.innerHTML = "<li class='muted'>Aún no se ha investigado ningún tema.</li>";
    } else {
      ul.innerHTML = hist
        .slice()
        .reverse()
        .map(
          (h) =>
            `<li><span class="tag">${h.fragments_added || 0} frag.</span> ${escapeHtml(
              (h.topic || "").slice(0, 80)
            )}${h.youtube_limit_applied ? " <span class='muted'>(límite YT)</span>" : ""}</li>`
        )
        .join("");
    }
  } catch (e) {
    document.getElementById("research-history").innerHTML =
      `<li class="muted">Error: ${e.message}</li>`;
  }
}

document.getElementById("btn-research").addEventListener("click", async () => {
  const topic = document.getElementById("research-topic").value.trim();
  const focus = document.getElementById("research-focus").value.trim() || null;
  const learn = document.getElementById("research-learn").checked;
  const box = document.getElementById("research-result");
  if (!topic) {
    alert("Escribe un tema o URL.");
    return;
  }
  box.classList.remove("hidden");
  box.className = "result";
  box.textContent = "Investigando… esto puede tardar unos segundos.";
  try {
    const report = await api("/api/research", {
      method: "POST",
      body: JSON.stringify({ topic, focus, learn, device: getDeviceId() }),
    });
    if (!report.ok) {
      box.className = "result warn";
      box.textContent = report.error || "No se pudo completar la investigación.";
      return;
    }
    let msg = "";
    if (report.youtube_limit_applied) {
      msg += "⚠ Límite YouTube aplicado: solo texto publicado (transcripciones/reseñas).\n\n";
    }
    msg += report.disclaimer + "\n\n";
    if (report.key_points && report.key_points.length) {
      msg += "Puntos clave:\n";
      report.key_points.slice(0, 5).forEach((p, i) => {
        msg += `${i + 1}. ${p}\n`;
      });
    }
    if (report.learned) {
      msg += `\n✓ Aprendizaje: ${report.fragments_added || 0} fragmentos incorporados a la infinitud discreta.`;
    }
    if (report.sources && report.sources.length) {
      msg += `\n\nFuentes (${report.sources.length}):\n`;
      report.sources.slice(0, 4).forEach((s) => {
        msg += `· ${s.title || s.url}\n`;
      });
    }
    box.className = "result ok";
    box.textContent = msg;
    refreshResearch();
  } catch (e) {
    box.className = "result warn";
    box.textContent = "Error: " + e.message;
  }
});

document.getElementById("btn-speak").addEventListener("click", async () => {
  const text = document.getElementById("voice-text").value.trim();
  const box = document.getElementById("voice-result");
  if (!text) {
    alert("Escribe el texto a leer.");
    return;
  }
  box.classList.remove("hidden");
  box.className = "result";
  box.textContent = "Generando voz…";
  try {
    const res = await api("/api/voice/speak", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    if (res.ok) {
      box.className = "result ok";
      box.textContent =
        res.message ||
        `Reproducido con motor ${res.engine || "local"}.` +
          (res.path ? `\nArchivo: ${res.path}` : "");
    } else {
      box.className = "result warn";
      box.textContent = (res.error || "No se pudo hablar") + "\n\n" + (res.hint || "");
    }
  } catch (e) {
    box.className = "result warn";
    box.textContent = "Error: " + e.message;
  }
});

// ---------- Gramática ----------
async function refreshGrammar() {
  const st = await api("/api/grammar/stats");
  document.getElementById("grammar-stats").innerHTML = `
    <div class="stat"><div class="n">${st.fragmentos}</div><div class="l">Fragmentos</div></div>
    <div class="stat"><div class="n">${st.casos_aprendidos}</div><div class="l">Aprendidos</div></div>
  `;
}

async function generate(kind) {
  const out = document.getElementById("gen-output");
  try {
    const res = await api(`/api/grammar/generate?kind=${kind}&recursion=1`);
    out.classList.remove("hidden");
    out.className = "result";
    out.textContent = res.text;
  } catch (e) {
    out.classList.remove("hidden");
    out.className = "result warn";
    out.textContent = e.message;
  }
}
document.getElementById("btn-gen-case").addEventListener("click", () => generate("case"));
document.getElementById("btn-gen-q").addEventListener("click", () => generate("question"));
document.getElementById("btn-gen-traj").addEventListener("click", () => generate("trajectory"));

// ---------- Sync ----------
async function refreshSync() {
  const st = await api("/api/sync/status");
  document.getElementById("sync-status").innerHTML = `
    <div class="stat"><div class="n">${st.cases}</div><div class="l">Casos</div></div>
    <div class="stat"><div class="n">${st.grammar.fragmentos}</div><div class="l">Fragmentos</div></div>
    <div class="stat"><div class="n">${st.trajectories}</div><div class="l">Trayectorias</div></div>
    <div class="stat"><div class="n">${st.hitos}</div><div class="l">Hitos</div></div>
  `;
}

document.getElementById("btn-export").addEventListener("click", async () => {
  const data = await api("/api/sync/export");
  document.getElementById("sync-payload").value = JSON.stringify(data, null, 2);
  const box = document.getElementById("sync-result");
  box.classList.remove("hidden");
  box.className = "result ok";
  box.textContent = "Corpus exportado. Copia el JSON y pégalo en otro dispositivo, o guárdalo.";
});

document.getElementById("btn-import").addEventListener("click", async () => {
  const raw = document.getElementById("sync-payload").value.trim();
  if (!raw) {
    alert("Pega primero un JSON exportado.");
    return;
  }
  try {
    const foreign = JSON.parse(raw);
    const res = await api("/api/sync/import", {
      method: "POST",
      body: JSON.stringify(foreign),
    });
    const box = document.getElementById("sync-result");
    box.classList.remove("hidden");
    box.className = "result ok";
    box.textContent =
      "Importación completada:\n" +
      JSON.stringify(res.stats, null, 2) +
      "\n\nEl conocimiento de ambos dispositivos se ha fusionado.";
    refreshSync();
  } catch (e) {
    const box = document.getElementById("sync-result");
    box.classList.remove("hidden");
    box.className = "result warn";
    box.textContent = "Error al importar: " + e.message;
  }
});

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------- Boot ----------
(async function init() {
  try {
    bindChatUI();
    setChatSessionId(getChatSessionId());
    await loadChatHistory();
    refreshMemoryBadge();
    updateVoiceToggleUI();
    if ("speechSynthesis" in window) {
      try { window.speechSynthesis.getVoices(); } catch (e) {}
      window.speechSynthesis.onvoiceschanged = function () {
        try { window.speechSynthesis.getVoices(); } catch (e) {}
      };
    }
    api("/api/llm/status").then(function (s) {
      if (s && s.available && s.providers && s.providers.length) {
        refreshChatBadge(s.providers[0]);
      } else {
        refreshChatBadge("local");
      }
    }).catch(function () { refreshChatBadge("local"); });
    await loadMeta();
    await refreshHome();
  } catch (e) {
    document.getElementById("status").textContent = "servidor no disponible";
    console.error(e);
  }
})();

/* ===== Idiomas (CEOX integrado) ===== */
const langState = {
  roleId: null,
  target: "en",
  history: [],
};

async function loadLangRoles() {
  const box = document.getElementById("lang-roles");
  if (!box) return;
  try {
    const data = await api("/api/lang/roles");
    const roles = data.roles || [];
    box.innerHTML = roles
      .map(
        (r) =>
          `<button type="button" class="lang-role-btn" data-role="${r.id}">
            <strong>${r.name_es}</strong>
            <span>${r.goal}</span>
          </button>`,
      )
      .join("");
    box.querySelectorAll(".lang-role-btn").forEach((btn) => {
      btn.addEventListener("click", () => startLangRole(btn.dataset.role));
    });
  } catch (e) {
    box.innerHTML = "<p class='muted'>No se pudieron cargar los roles.</p>";
  }
}

function langAppend(role, text) {
  const box = document.getElementById("lang-messages");
  if (!box) return;
  const div = document.createElement("div");
  div.className = "lang-bubble " + role;
  div.textContent = text;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

async function startLangRole(roleId) {
  langState.roleId = roleId;
  langState.target = document.getElementById("lang-target")?.value || "en";
  langState.history = [];
  const res = await api("/api/lang/start", {
    method: "POST",
    body: JSON.stringify({ role_id: roleId, target_lang: langState.target }),
  });
  if (!res.ok) return;
  document.getElementById("lang-roles").classList.add("hidden");
  const sess = document.getElementById("lang-session");
  sess.classList.remove("hidden");
  document.getElementById("lang-role-name").textContent =
    (res.role?.name_es || roleId) + " · " + (res.role?.setting || "");
  document.getElementById("lang-messages").innerHTML = "";
  document.getElementById("lang-corrections").innerHTML = "";
  langAppend("partner", res.partner_message || "");
  langState.history.push({ role: "partner", content: res.partner_message || "" });
  const sug = document.getElementById("lang-suggestions");
  sug.innerHTML = (res.suggestions || [])
    .map((s) => `<button type="button" class="chip" data-prompt="${s.replace(/"/g, "&quot;")}">${s}</button>`)
    .join("");
  sug.querySelectorAll(".chip").forEach((c) => {
    c.addEventListener("click", () => {
      document.getElementById("lang-input").value = c.dataset.prompt || c.textContent;
    });
  });
}

async function sendLangTurn() {
  const input = document.getElementById("lang-input");
  const text = (input?.value || "").trim();
  if (!text || !langState.roleId) return;
  input.value = "";
  langAppend("user", text);
  langState.history.push({ role: "user", content: text });
  document.getElementById("lang-status").textContent = "…";
  const long = !!document.getElementById("lang-long")?.checked;
  try {
    const res = await api("/api/lang/turn", {
      method: "POST",
      body: JSON.stringify({
        role_id: langState.roleId,
        target_lang: langState.target,
        message: text,
        history: langState.history,
        native_lang: "es",
        long,
      }),
    });
    if (res.partner_message) {
      langAppend("partner", res.partner_message);
      langState.history.push({ role: "partner", content: res.partner_message });
    }
    const corr = document.getElementById("lang-corrections");
    if (res.corrections && res.corrections.length) {
      corr.innerHTML = res.corrections
        .map((c) => `<div>→ <strong>${c.corrected}</strong> — ${c.explanation}</div>`)
        .join("");
    } else {
      corr.innerHTML = "";
    }
    document.getElementById("lang-status").textContent = "motor: " + (res.engine || "local");
  } catch (e) {
    document.getElementById("lang-status").textContent = "Error de red";
  }
}

function bindLangUI() {
  document.getElementById("lang-send")?.addEventListener("click", sendLangTurn);
  document.getElementById("lang-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendLangTurn();
    }
  });
  document.getElementById("lang-end")?.addEventListener("click", () => {
    document.getElementById("lang-session")?.classList.add("hidden");
    document.getElementById("lang-roles")?.classList.remove("hidden");
    langState.roleId = null;
    langState.history = [];
  });
  const mic = document.getElementById("lang-mic");
  if (mic) {
    mic.addEventListener("click", () => {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {
        alert("Dictado no disponible en este navegador");
        return;
      }
      const rec = new SR();
      const langMap = { en: "en-US", es: "es-ES", fr: "fr-FR", it: "it-IT", pt: "pt-BR" };
      rec.lang = langMap[langState.target] || "en-US";
      rec.onresult = (ev) => {
        const t = ev.results[0][0].transcript;
        const input = document.getElementById("lang-input");
        if (input) input.value = (input.value + " " + t).trim();
      };
      rec.start();
    });
  }
  // load roles when switching to lang tab
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      if (tab.dataset.view === "lang") loadLangRoles();
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  try {
    bindLangUI();
  } catch (e) {
    console.warn("lang ui", e);
  }
});

/* ===== Curso Coaching Formación y Calidad ===== */
async function loadCoachingCourse() {
  const list = document.getElementById("coach-modules");
  const progBox = document.getElementById("coach-progress");
  if (!list) return;
  try {
    const data = await api("/api/coaching/modules");
    const p = data.progress || {};
    progBox.textContent =
      `Progreso: ${p.completed || 0}/${p.total_modules || 0} módulos (${p.percent || 0}%) · Curso indefinido — puedes repetir y profundizar`;
    const done = new Set(data.completed_ids || []);
    list.innerHTML = (data.modules || [])
      .map(
        (m) =>
          `<button type="button" class="coach-mod-btn ${done.has(m.id) ? "done" : ""}" data-id="${m.id}">
            <strong>${m.order}. ${m.title}</strong>
            <small>${m.level} · ~${m.minutes} min ${done.has(m.id) ? "· ✓" : ""}</small>
          </button>`,
      )
      .join("");
    list.querySelectorAll(".coach-mod-btn").forEach((btn) => {
      btn.addEventListener("click", () => openCoachModule(btn.dataset.id));
    });
    // tools
    const toolsData = await api("/api/coaching/tools");
    const tbox = document.getElementById("coach-tools-box");
    if (tbox && toolsData.tools) {
      tbox.innerHTML = Object.entries(toolsData.tools)
        .map(
          ([k, t]) =>
            `<button type="button" class="lang-role-btn" data-tool="${k}">
              <strong>${t.name}</strong>
              <span>${(t.fields || []).slice(0, 3).join(" · ")}…</span>
            </button>`,
        )
        .join("");
      tbox.querySelectorAll("[data-tool]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const tool = toolsData.tools[btn.dataset.tool];
          const detail = document.getElementById("coach-detail");
          detail.innerHTML = `<h3>${tool.name}</h3><ul>${(tool.fields || [])
            .map((f) => `<li><strong>${f}</strong></li>`)
            .join("")}</ul>
            <textarea id="coach-tool-text" placeholder="Escribe aquí tu práctica con esta plantilla…"></textarea>
            <p style="margin-top:10px">
              <button type="button" class="primary" id="coach-tool-save">Guardar práctica en CEOS</button>
            </p>`;
          document.getElementById("coach-tool-save")?.addEventListener("click", async () => {
            const text = document.getElementById("coach-tool-text")?.value || "";
            if (!text.trim()) return;
            await api("/api/coaching/practice", {
              method: "POST",
              body: JSON.stringify({ kind: btn.dataset.tool, text }),
            });
            alert("Práctica guardada en memoria/códice CEOS");
          });
        });
      });
    }
  } catch (e) {
    progBox.textContent = "No se pudo cargar el curso.";
  }
}

async function openCoachModule(id) {
  const detail = document.getElementById("coach-detail");
  document.querySelectorAll(".coach-mod-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.id === id);
  });
  try {
    const data = await api("/api/coaching/module/" + id);
    const m = data.module;
    detail.innerHTML = `
      <h3>${m.order}. ${m.title}</h3>
      <p class="muted">${m.level} · ~${m.minutes} min ${m.model ? "· Modelo: " + m.model : ""}</p>
      <p><strong>Objetivos</strong></p>
      <ul>${(m.objectives || []).map((o) => `<li>${o}</li>`).join("")}</ul>
      <p><strong>Contenido</strong></p>
      <pre>${m.content}</pre>
      <p><strong>Práctica</strong></p>
      <p>${m.practice}</p>
      <textarea id="coach-note" placeholder="Tu respuesta / notas de práctica…">${data.note || ""}</textarea>
      <p style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">
        <button type="button" class="primary" id="coach-complete">Marcar módulo completado</button>
        <button type="button" class="ghost" id="coach-save-practice">Solo guardar práctica</button>
      </p>`;
    document.getElementById("coach-complete")?.addEventListener("click", async () => {
      const note = document.getElementById("coach-note")?.value || "";
      await api("/api/coaching/complete", {
        method: "POST",
        body: JSON.stringify({ module_id: id, note }),
      });
      loadCoachingCourse();
      openCoachModule(id);
    });
    document.getElementById("coach-save-practice")?.addEventListener("click", async () => {
      const note = document.getElementById("coach-note")?.value || "";
      if (!note.trim()) return;
      await api("/api/coaching/practice", {
        method: "POST",
        body: JSON.stringify({ kind: id, text: note }),
      });
      alert("Práctica guardada");
    });
  } catch (e) {
    detail.innerHTML = "<p class='muted'>Error al cargar el módulo.</p>";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      if (tab.dataset.view === "coaching") loadCoachingCourse();
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("voice-nav-btn")?.addEventListener("click", startVoiceNavigation);
});


/* ===== Simulador auditoría + selector de voces ===== */
async function runCallAudit() {
  const ta = document.getElementById("audit-transcript");
  const box = document.getElementById("audit-result");
  if (!ta || !box) return;
  const text = ta.value.trim();
  if (text.length < 40) {
    box.innerHTML = "<p class=\"muted\">Pega una transcripción más larga.</p>";
    return;
  }
  box.innerHTML = "<p class=\"muted\">Auditando…</p>";
  try {
    const res = await api("/api/coaching/audit", {
      method: "POST",
      body: JSON.stringify({ transcript: text }),
    });
    const dims = (res.dimensions || [])
      .map(
        (d) =>
          `<div class="audit-dim"><strong>${d.label}</strong> ${d.score}/${d.max} — ${d.comment}</div>`,
      )
      .join("");
    const ecam = res.ecam || {};
    box.innerHTML = `
      <p><strong>${res.summary || ""}</strong></p>
      <div class="audit-dims">${dims}</div>
      ${(res.risks || []).length ? "<p><strong>Riesgos</strong></p><ul>" + res.risks.map((r) => "<li>" + r.message + "</li>").join("") + "</ul>" : ""}
      ${(res.strengths || []).length ? "<p><strong>Fortalezas</strong></p><ul>" + res.strengths.map((s) => "<li>" + s + "</li>").join("") + "</ul>" : ""}
      <div class="ecam-box">
        <h4>Feedback E-C-A-M sugerido</h4>
        <p><strong>Evidencia:</strong> ${ecam.evidencia || ""}</p>
        <p><strong>Consecuencia:</strong> ${ecam.consecuencia || ""}</p>
        <p><strong>Alternativa:</strong> ${ecam.alternativa || ""}</p>
        <p><strong>Medición:</strong> ${ecam.medicion || ""}</p>
      </div>`;
  } catch (e) {
    box.innerHTML = "<p class=\"muted\">Error al auditar.</p>";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-audit-run")?.addEventListener("click", runCallAudit);
  document.getElementById("voice-test-btn")?.addEventListener("click", () => {
    speakWithSelectedVoice(
      "Hola. Esta es la voz seleccionada en CEOS. Lista para coaching e idiomas.",
      "es-ES",
    );
  });
  const bootVoices = () => {
    try {
      populateVoiceSelect();
    } catch (e) {}
  };
  if ("speechSynthesis" in window) {
    bootVoices();
    window.speechSynthesis.onvoiceschanged = bootVoices;
    setTimeout(bootVoices, 500);
  }
});
