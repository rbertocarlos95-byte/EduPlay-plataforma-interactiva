const $ = (id) => document.getElementById(id);
let player = null,
  questions = {},
  subject = "",
  qi = 0,
  chosen = null,
  avatar = "🐉",
  authMode = "register";
const tokenKey = "eduplay.session";
async function api(path, body) {
  const res = await fetch(
    path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : {},
  );
  const data = await res.json();
  if (!res.ok) throw Error(data.error || "No se pudo conectar");
  return data;
}
function showLogin(mode = "register") {
  $("login").classList.remove("hidden");
  setAuthMode(mode);
  setTimeout(
    () => (mode === "register" ? $("playerName") : $("username")).focus(),
    50,
  );
}
function setAuthMode(mode) {
  authMode = mode;
  document
    .querySelectorAll(".auth-tab")
    .forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  $("registerFields").classList.toggle("hidden", mode === "login");
  $("loginTitle").innerHTML =
    mode === "register"
      ? "Tu próxima aventura<br><em>empieza aquí.</em>"
      : "Qué bueno verte<br><em>de regreso.</em>";
  $("loginDescription").textContent =
    mode === "register"
      ? "Crea tu cuenta para guardar tu nivel, insignias y misiones. Tu contraseña se protege en el servidor."
      : "Inicia sesión y continúa exactamente donde dejaste tu aventura.";
  $("startBtn").innerHTML =
    mode === "register"
      ? "Crear mi aventura <span>↗</span>"
      : "Entrar a mi aventura <span>↗</span>";
  $("password").autocomplete =
    mode === "register" ? "new-password" : "current-password";
}
function setState(s) {
  player = s;
  localStorage.setItem(tokenKey, s.token || localStorage.getItem(tokenKey));
  $("helloName").textContent = s.name;
  $("topAvatar").textContent = s.avatar;
  $("xp").textContent = s.xp;
  $("answered").textContent = s.answered;
  $("accuracy").textContent = s.answered
    ? Math.round((s.correct / s.answered) * 100) + "%"
    : "—";
  $("streak").textContent = s.streak;
  $("levelNumber").textContent = s.level;
  $("levelText").textContent = s.level;
  $("levelXp").textContent = s.levelProgress;
  $("levelBar").style.width = (s.levelProgress / 50) * 100 + "%";
  $("dailyCount").textContent = Math.min(s.daily, 3);
  [
    ["Palabras", "wordsProgress"],
    ["Ciencia", "scienceProgress"],
    ["Matemáticas", "mathProgress"],
  ].forEach(([name, id]) => ($(id).textContent = s.subjects[name]?.total || 0));
  const icons = {
    "Primer paso": "🌱",
    "Mente curiosa": "🔎",
    "Estrella brillante": "⭐",
    "Gran explorador": "🚀",
    "Leyenda EduPlay": "🏆",
  };
  $("badgeList").innerHTML = s.badges.length
    ? s.badges
        .map(
          (b) =>
            `<div class="badge"><span>${b.icon}</span><b>${b.title}</b></div>`,
        )
        .join("")
    : '<span class="empty-badges">Completa tu primer reto para ganar una insignia ✨</span>';
}
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 2700);
}
async function auth() {
  try {
    const body = {
      username: $("username").value,
      password: $("password").value,
    };
    if (authMode === "register") {
      body.name = $("playerName").value;
      body.avatar = avatar;
    }
    setState(
      await api(authMode === "register" ? "/api/register" : "/api/login", body),
    );
    $("login").classList.add("hidden");
    $("password").value = "";
  } catch (e) {
    toast(e.message);
  }
}
async function refresh() {
  const token = localStorage.getItem(tokenKey);
  if (!token) return showLogin();
  try {
    const s = await api("/api/state?token=" + encodeURIComponent(token));
    s.token = token;
    setState(s);
  } catch {
    localStorage.removeItem(tokenKey);
    showLogin("login");
  }
}
function openQuiz(name) {
  if (!player) return showLogin();
  subject = name;
  qi = 0;
  chosen = null;
  $("quizLabel").textContent = "MISIÓN · " + name.toUpperCase();
  $("quizSymbol").textContent =
    name === "Palabras" ? "Aa" : name === "Ciencia" ? "⚛" : "＋";
  $("quiz").classList.remove("hidden");
  renderQuestion();
}
function renderQuestion() {
  const q = questions[subject][qi];
  $("qCount").textContent = `RETO ${qi + 1} DE ${questions[subject].length}`;
  $("qBar").style.width = ((qi + 1) / questions[subject].length) * 100 + "%";
  $("question").textContent = q.q;
  $("feedback").classList.add("hidden");
  $("nextBtn").classList.add("hidden");
  $("options").innerHTML = "";
  q.opts.forEach((opt, i) => {
    const b = document.createElement("button");
    b.className = "option";
    b.textContent = String.fromCharCode(65 + i) + ".  " + opt;
    b.onclick = () => answer(i, b);
    $("options").append(b);
  });
}
async function answer(choice, btn) {
  if (chosen !== null) return;
  chosen = choice;
  const q = questions[subject][qi];
  try {
    const result = await api("/api/answer", {
      token: localStorage.getItem(tokenKey),
      subject,
      question: qi,
      choice,
    });
    result.state.token = localStorage.getItem(tokenKey);
    setState(result.state);
    document.querySelectorAll(".option").forEach((el, i) => {
      el.disabled = true;
      if (i === q.answer) el.classList.add("correct");
    });
    if (!result.correct) btn.classList.add("wrong");
    const fb = $("feedback");
    fb.textContent = result.correct
      ? "¡Muy bien! +" + result.xpEarned + " XP ✨"
      : `¡Buen intento! ${result.hint} (+${result.xpEarned} XP por practicar)`;
    fb.classList.remove("hidden");
    $("nextBtn").classList.remove("hidden");
    $("nextBtn").innerHTML =
      qi === questions[subject].length - 1
        ? "Terminar misión <span>✦</span>"
        : "Siguiente reto <span>→</span>";
  } catch (e) {
    toast(e.message);
    chosen = null;
  }
}
function next() {
  if (qi < questions[subject].length - 1) {
    qi++;
    chosen = null;
    renderQuestion();
  } else {
    $("quiz").classList.add("hidden");
    toast("¡Misión completada! Sigue explorando ✨");
  }
}
document
  .querySelectorAll(".auth-tab")
  .forEach((b) => (b.onclick = () => setAuthMode(b.dataset.mode)));
document.querySelectorAll(".avatar").forEach(
  (b) =>
    (b.onclick = () => {
      document.querySelector(".avatar.active").classList.remove("active");
      b.classList.add("active");
      avatar = b.textContent;
    }),
);
$("startBtn").onclick = auth;
["playerName", "username", "password"].forEach(
  (id) =>
    ($(id).onkeydown = (e) => {
      if (e.key === "Enter") auth();
    }),
);
document
  .querySelectorAll(".route")
  .forEach((c) => (c.onclick = () => openQuiz(c.dataset.subject)));
$("continueBtn").onclick = () => openQuiz("Palabras");
$("practiceNav").onclick = () => openQuiz("Ciencia");
$("homeNav").onclick = () => window.scrollTo({ top: 0, behavior: "smooth" });
$("closeQuiz").onclick = () => $("quiz").classList.add("hidden");
$("nextBtn").onclick = next;
$("exitBtn").onclick = async () => {
  const token = localStorage.getItem(tokenKey);
  try {
    await api("/api/logout", { token });
  } catch {}
  localStorage.removeItem(tokenKey);
  player = null;
  showLogin("login");
};
(async () => {
  try {
    questions = await api("/api/questions");
    await refresh();
  } catch (e) {
    toast("Inicia el servidor con python server.py");
  }
})();
