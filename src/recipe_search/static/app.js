const form = document.querySelector("#search-form");
const input = document.querySelector("#search-input");
const submit = document.querySelector("#submit-button");
const resultsSection = document.querySelector("#results-section");
const results = document.querySelector("#results");
const resultMeta = document.querySelector("#result-meta");
const resultTitle = document.querySelector("#results-title");
const notice = document.querySelector("#notice");
const inputHint = document.querySelector("#input-hint");
let inputKind = "query";

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[char]);

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".mode-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    inputKind = button.dataset.kind;
    input.placeholder = inputKind === "query"
      ? "Something quick and spicy with chicken"
      : "Eggs, potatoes, onion";
    inputHint.textContent = inputKind === "query"
      ? "Try English, svenska, or español"
      : "Separate ingredients with commas";
    input.focus();
  });
});

document.querySelectorAll("#examples button").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.query;
    inputKind = "query";
    document.querySelectorAll(".mode-button").forEach((item) => {
      item.classList.toggle("active", item.dataset.kind === "query");
    });
    form.requestSubmit();
  });
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

const sourceMarkup = (recipe) => {
  if (recipe.url) {
    return `<a class="source-link" href="${escapeHtml(recipe.url)}" target="_blank" rel="noreferrer">View recipe <svg viewBox="0 0 24 24"><path d="M7 17 17 7M8 7h9v9" /></svg></a>`;
  }
  return `<span class="source-link muted">${escapeHtml(recipe.source || "Dataset recipe")}</span>`;
};

const renderRecipe = (recipe, index) => `
  <article class="recipe-card">
    <div class="card-top">
      <span class="rank">${index + 1}</span>
      <div class="card-copy">
        <h3>${escapeHtml(recipe.name)}</h3>
        <span class="reason"><svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>${escapeHtml(recipe.match_reason.summary)}</span>
      </div>
    </div>
    <p class="ingredients">${recipe.ingredients.slice(0, 7).map(escapeHtml).join(" · ")}</p>
    <div class="card-footer">
      <span class="score-pill">Score ${recipe.score.toFixed(2)}</span>
      ${sourceMarkup(recipe)}
    </div>
  </article>`;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value) return;

  const payload = inputKind === "ingredients"
    ? { ingredients: value.split(",").map((item) => item.trim()).filter(Boolean), limit: 8 }
    : { query: value, limit: 8 };

  submit.disabled = true;
  resultsSection.hidden = false;
  notice.hidden = true;
  resultTitle.textContent = `Results for “${value}”`;
  resultMeta.textContent = "Searching…";
  results.innerHTML = '<div class="recipe-card skeleton"></div><div class="recipe-card skeleton"></div>';
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      const message = data.detail?.[0]?.msg || data.detail || "Search request failed";
      throw new Error(message);
    }
    resultMeta.textContent = `${data.meta.returned} of ${data.meta.total_recipes.toLocaleString()} recipes · ${data.meta.mode}`;
    results.innerHTML = data.results.map(renderRecipe).join("");
    if (data.meta.confidence === "low" || data.meta.query_understanding.warning) {
      notice.hidden = false;
      notice.textContent = data.meta.query_understanding.warning || "These are weak matches—the dataset may not contain what you asked for.";
    }
  } catch (error) {
    resultMeta.textContent = "Unable to search";
    results.innerHTML = "";
    notice.hidden = false;
    notice.textContent = error.message || "Something went wrong. Please try again.";
  } finally {
    submit.disabled = false;
  }
});
