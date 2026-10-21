const tabs = document.querySelectorAll(".nav-btn");
const panels = document.querySelectorAll(".tab");
const overlay = document.getElementById("overlay");
const results = document.getElementById("results");
const resultsBody = document.getElementById("results-body");
const historyList = document.getElementById("history-list");

const TYPE_LABELS = {
  text: "Текст",
  image: "Изображение",
  parse: "Сайт",
  monitor: "Обход",
};

function showTab(name) {
  tabs.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === name));
  panels.forEach((panel) => panel.classList.toggle("active", panel.id === `tab-${name}`));
  if (name === "history") loadHistory();
}

tabs.forEach((btn) => btn.addEventListener("click", () => showTab(btn.dataset.tab)));

function setLoading(on, message) {
  overlay.hidden = !on;
  const label = overlay.querySelector("p");
  if (label) label.textContent = message || "Анализирую…";
}

function showError(message) {
  results.hidden = false;
  resultsBody.innerHTML = `<div class="error"></div>`;
  resultsBody.querySelector(".error").textContent = message;
}

function listBlock(title, items) {
  if (!items || !items.length) return "";
  const list = items.map((item) => `<li></li>`).join("");
  const wrap = document.createElement("template");
  wrap.innerHTML = `<div class="block"><h3></h3><ul>${list}</ul></div>`;
  wrap.content.querySelector("h3").textContent = title;
  wrap.content.querySelectorAll("li").forEach((li, index) => {
    li.textContent = items[index];
  });
  return wrap.innerHTML;
}

function textBlock(title, value) {
  if (!value) return "";
  const wrap = document.createElement("template");
  wrap.innerHTML = `<div class="block"><h3></h3><div class="summary"></div></div>`;
  wrap.content.querySelector("h3").textContent = title;
  wrap.content.querySelector(".summary").textContent = value;
  return wrap.innerHTML;
}

function scoreLine(analysis) {
  if (!analysis) return "";
  const wrap = document.createElement("template");
  wrap.innerHTML = `<div class="block"><div class="score"></div></div>`;
  wrap.content.querySelector(".score").textContent =
    `Дизайн ${analysis.design_score ?? 0}/10    Анимация ${analysis.animation_potential ?? 0}/10`;
  return wrap.innerHTML;
}

function renderAnalysis(analysis) {
  return (
    scoreLine(analysis) +
    textBlock("Заключение", analysis.conclusion) +
    textBlock("Анимация", analysis.animation_notes) +
    textBlock("Резюме", analysis.summary) +
    listBlock("Сильные стороны", analysis.strengths) +
    listBlock("Слабые стороны", analysis.weaknesses) +
    listBlock("Уникальные предложения", analysis.unique_offers) +
    listBlock("Рекомендации", analysis.recommendations)
  );
}

function renderImage(analysis) {
  const score = document.createElement("template");
  score.innerHTML = `<div class="block"><h3>Оценка визуального стиля</h3><div class="score"></div></div>`;
  score.content.querySelector(".score").textContent = `${analysis.visual_style_score}/10`;
  return (
    textBlock("Описание", analysis.description) +
    score.innerHTML +
    scoreLine(analysis) +
    textBlock("Разбор стиля", analysis.visual_style_analysis) +
    textBlock("Анимация", analysis.animation_notes) +
    listBlock("Маркетинговые инсайты", analysis.marketing_insights) +
    listBlock("Рекомендации", analysis.recommendations)
  );
}

function renderParse(data) {
  const meta = document.createElement("template");
  meta.innerHTML = `<div class="meta"></div>`;
  const lines = [
    data.url ? `URL: ${data.url}` : "",
    data.title ? `Заголовок: ${data.title}` : "",
  ].filter(Boolean);
  meta.content.querySelector(".meta").textContent = lines.join("\n");

  let shot = "";
  if (data.screenshot) {
    const frame = document.createElement("template");
    frame.innerHTML = `<div class="block"><h3>Страница в Chrome</h3><img class="page-shot" alt="Скриншот страницы"></div>`;
    frame.content.querySelector("img").src = `data:image/png;base64,${data.screenshot}`;
    shot = frame.innerHTML;
  }

  const analysis = data.analysis ? renderAnalysis(data.analysis) : "";
  return `${shot}<div class="block"><h3>Что открыто</h3>${meta.innerHTML}</div>${analysis}`;
}

function showHtml(html) {
  results.hidden = false;
  resultsBody.innerHTML = html;
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || "Запрос не выполнен");
  }
  return data;
}

document.getElementById("text-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = document.getElementById("competitor-text").value.trim();
  setLoading(true);
  try {
    const data = await postJson("/analyze_text", { text });
    if (!data.success) throw new Error(data.error || "Анализ не выполнен");
    showHtml(renderAnalysis(data.analysis || {}));
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
});

const imageInput = document.getElementById("image-input");
const preview = document.getElementById("image-preview");
const dropLabel = document.getElementById("drop-label");
const imageSubmit = document.getElementById("image-submit");
const dropzone = document.getElementById("dropzone");

function setFile(file) {
  if (!file) return;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  dropLabel.hidden = true;
  imageSubmit.disabled = false;
}

imageInput.addEventListener("change", () => setFile(imageInput.files[0]));

["dragover", "dragleave", "drop"].forEach((name) => {
  dropzone.addEventListener(name, (event) => {
    event.preventDefault();
    dropzone.classList.toggle("drag", name === "dragover");
    if (name === "drop" && event.dataTransfer.files[0]) {
      imageInput.files = event.dataTransfer.files;
      setFile(event.dataTransfer.files[0]);
    }
  });
});

document.getElementById("image-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = imageInput.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  setLoading(true);
  try {
    const response = await fetch("/analyze_image", { method: "POST", body: form });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.success) {
      const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
      throw new Error(detail || data.error || "Анализ изображения не выполнен");
    }
    showHtml(renderImage(data.analysis || {}));
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
});

document.getElementById("parse-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = document.getElementById("url-input").value.trim();
  setLoading(true, "Собираю страницу через Selenium…");
  try {
    const data = await postJson("/parse_demo", { url });
    if (!data.success) throw new Error(data.error || "Страницу не удалось разобрать");
    showHtml(renderParse(data.data || {}));
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
});

function formatTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function loadHistory() {
  historyList.innerHTML = "";
  try {
    const response = await fetch("/history");
    const data = await response.json();
    if (!data.items || !data.items.length) {
      historyList.innerHTML = `<p class="empty">История пуста</p>`;
      return;
    }
    data.items.forEach((item) => {
      const row = document.createElement("article");
      row.className = "history-item";
      const tag = document.createElement("div");
      tag.className = "tag";
      tag.textContent = TYPE_LABELS[item.request_type] || item.request_type;
      const summary = document.createElement("div");
      summary.textContent = item.request_summary || "";
      const time = document.createElement("div");
      time.className = "time";
      time.textContent = formatTime(item.timestamp);
      row.append(tag, summary, time);
      historyList.append(row);
    });
  } catch (error) {
    historyList.innerHTML = `<p class="error"></p>`;
    historyList.querySelector(".error").textContent = error.message;
  }
}

document.getElementById("clear-history").addEventListener("click", async () => {
  await fetch("/history", { method: "DELETE" });
  loadHistory();
});

document.getElementById("close-results").addEventListener("click", () => {
  results.hidden = true;
});

function formatStamp(value) {
  return formatTime(value);
}

function fillMonitor(state) {
  document.getElementById("niche-input").value = state.niche || "";
  const urls = (state.urls && state.urls.length ? state.urls : state.defaults) || [];
  document.querySelectorAll(".competitor-url").forEach((input, index) => {
    input.value = urls[index] || "";
  });
  const schedule = document.getElementById("schedule-label");
  if (state.next_run_at) {
    schedule.textContent = `Последний анализ: ${formatStamp(state.last_run_at)}. Следующая проверка: ${formatStamp(state.next_run_at)}.`;
  } else if (state.urls && state.urls.length) {
    schedule.textContent = "После анализа следующая проверка будет через сутки.";
  } else {
    schedule.textContent = "Адреса уже подставлены: запустите анализ. Пока сервер запущен, следующая проверка будет через сутки.";
  }

  const competitors = document.getElementById("competitors");
  competitors.replaceChildren();
  const sites = state.sites || [];
  if (!sites.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Разбор каждого конкурента появится после первого анализа.";
    competitors.append(empty);
    return;
  }
  const changes = state.changes || [];
  sites.forEach((site) => {
    const own = changes.filter((change) => sameUrl(change.url, site.url));
    competitors.append(siteCard(site, own));
  });
}

function sameUrl(left, right) {
  return String(left || "").replace(/\/+$/, "") === String(right || "").replace(/\/+$/, "");
}

function appendText(parent, title, value) {
  if (!value) return;
  const block = document.createElement("div");
  block.className = "block";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const text = document.createElement("div");
  text.className = "summary";
  text.textContent = value;
  block.append(heading, text);
  parent.append(block);
}

function appendList(parent, title, items) {
  if (!items || !items.length) return;
  const block = document.createElement("div");
  block.className = "block";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const list = document.createElement("ul");
  items.forEach((item) => {
    const line = document.createElement("li");
    line.textContent = item;
    list.append(line);
  });
  block.append(heading, list);
  parent.append(block);
}

function siteCard(site, changes) {
  const card = document.createElement("article");
  card.className = "card competitor-card";
  const title = document.createElement("h2");
  title.textContent = site.title || site.url;
  const meta = document.createElement("div");
  meta.className = "meta";
  const lines = [site.url];
  if (site.analyzed_at) lines.push(`Снято: ${formatStamp(site.analyzed_at)}`);
  if (site.design_score !== null && site.design_score !== undefined) {
    lines.push(`Дизайн: ${site.design_score}/10    Потенциал анимации: ${site.animation_potential}/10`);
  }
  meta.textContent = lines.filter(Boolean).join("\n");
  card.append(title, meta);
  if (site.error) {
    const error = document.createElement("div");
    error.className = "error";
    error.textContent = site.error;
    card.append(error);
  }
  appendText(card, "Заключение", site.conclusion);
  appendText(card, "Резюме", site.summary);
  appendText(card, "Анимация", site.animation_notes);
  appendList(card, "Сильные стороны", site.strengths);
  appendList(card, "Слабые стороны", site.weaknesses);
  appendList(card, "Уникальные предложения", site.unique_offers);
  appendList(card, "Рекомендации", site.recommendations);
  card.append(changesBlock(changes));
  return card;
}

function changesBlock(changes) {
  const block = document.createElement("div");
  block.className = "change-card";
  const title = document.createElement("h3");
  title.textContent = "Изменения";
  block.append(title);
  if (!changes || !changes.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Пока пусто. После суточной проверки отличия этого сайта появятся здесь с датой.";
    block.append(empty);
    return block;
  }
  changes.forEach((change) => {
    const when = document.createElement("p");
    when.className = "change-date";
    when.textContent = formatStamp(change.changed_at);
    block.append(when);
    (change.items || []).forEach((item) => {
      const line = document.createElement("p");
      line.textContent = `${item.field}: ${item.before || "—"} → ${item.after || "—"}`;
      block.append(line);
    });
  });
  return block;
}

async function loadMonitor() {
  try {
    const response = await fetch("/monitor");
    fillMonitor(await response.json());
  } catch (error) {
    document.getElementById("schedule-label").textContent = error.message;
  }
}

document.getElementById("monitor-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const urls = [...document.querySelectorAll(".competitor-url")]
    .map((input) => input.value.trim())
    .filter(Boolean);
  if (!urls.length) {
    showError("Укажите хотя бы один сайт конкурента.");
    return;
  }
  setLoading(true, "Собираю страницы и сравниваю с прошлой проверкой…");
  try {
    const data = await postJson("/monitor/run", {
      urls,
      niche: document.getElementById("niche-input").value.trim(),
    });
    fillMonitor(data);
    document.getElementById("competitors").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
});

loadMonitor();
