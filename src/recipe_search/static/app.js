import {
  formatIngredientText,
  formatInstructionText,
  instructionSteps,
} from "./recipe-format.mjs?v=2";
import {
  formatDuration,
  formatMinutes,
  recipeFactItems,
  sourceIconPath,
  sourceLabel,
} from "./recipe-metadata.mjs?v=2";

const ICON_PATHS = {
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v5l3.2 1.9"/>',
  flame: '<path d="M12.2 21c3.7 0 6.3-2.8 6.3-6.6 0-3.2-1.8-6.2-5.4-9.5.2 3.1-1.4 4.2-2.8 5.7-1 1-1.5 2.1-1.4 3.4.1 1.3.7 2.3 1.7 3-.1-2.1 1.2-3.6 2.7-5.1.2 2 2.1 3.3 2.1 5.2 0 2.2-1.5 3.9-3.2 3.9Z"/>',
  hourglass: '<path d="M7 3h10M7 21h10M8 3c0 4.2 1.2 6.3 4 9-2.8 2.7-4 4.8-4 9M16 3c0 4.2-1.2 6.3-4 9 2.8 2.7 4 4.8 4 9"/>',
  users: '<path d="M16 20v-1.6c0-2.2-1.8-4-4-4H7.5c-2.2 0-4 1.8-4 4V20"/><circle cx="9.8" cy="7.8" r="3.2"/><path d="M16 14.8c2.5.2 4.5 1.4 4.5 3.6V20M15.7 4.8a3.2 3.2 0 0 1 0 6.1"/>',
  ingredients: '<path d="M8.5 5.5h11M8.5 12h11M8.5 18.5h11"/><path d="m3.7 5.5.9.9 1.7-1.8M3.7 12l.9.9 1.7-1.8M3.7 18.5l.9.9 1.7-1.8"/>',
  globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.8 12h16.4M12 3.5c2.2 2.3 3.3 5.1 3.3 8.5s-1.1 6.2-3.3 8.5c-2.2-2.3-3.3-5.1-3.3-8.5S9.8 5.8 12 3.5Z"/>',
  external: '<path d="M7 17 17 7M8 7h9v9"/>',
};

const iconMarkup = (name, className = "") => (
  `<svg class="${className}" viewBox="0 0 24 24" aria-hidden="true">${ICON_PATHS[name]}</svg>`
);

const form = document.querySelector("#search-form");
const input = document.querySelector("#search-input");
const submit = document.querySelector("#submit-button");
const resultsSection = document.querySelector("#results-section");
const results = document.querySelector("#results");
const resultMeta = document.querySelector("#result-meta");
const resultsTitle = document.querySelector("#results-title");
const resultsQuery = document.querySelector("#results-query");
const notice = document.querySelector("#notice");
const pagination = document.querySelector("#pagination");
const dialog = document.querySelector("#recipe-dialog");
const dialogClose = document.querySelector("#dialog-close");
const recipeDetail = document.querySelector("#recipe-detail");
const howButton = document.querySelector("#how-button");
const howDialog = document.querySelector("#how-dialog");
const howClose = document.querySelector("#how-close");
const howTitle = document.querySelector("#how-title");

const PAGE_SIZE = 10;
const PUBLIC_API_ORIGIN = "https://recipe-search-production-aa6b.up.railway.app";
const apiOrigin = window.location.hostname === "ariakalantari.github.io" ? PUBLIC_API_ORIGIN : "";
const apiUrl = (path) => `${apiOrigin}${path}`;
let inputKind = "query";
let searchResults = [];
let currentPage = 1;
let searchMeta = null;
let activeRequest = null;
let requestSequence = 0;
let lockedScrollY = 0;

document.querySelectorAll("[data-api-path]").forEach((link) => {
  link.href = apiUrl(link.dataset.apiPath);
});
if (apiOrigin) {
  void fetch(apiUrl("/readyz"), { cache: "no-store" }).catch(() => {});
}

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[character]);

const relevanceLabel = (rank) => {
  if (searchMeta?.strategy === "adventurous") return "Adventurous pick";
  if (searchMeta?.strategy === "discovery") return "Idea to explore";
  if (searchMeta?.confidence === "low") return "Closest available";
  if (rank === 1) return "Best match";
  if (searchMeta?.confidence === "medium") return rank <= 3 ? "Top pick" : "Worth exploring";
  if (rank <= 3) return "Close match";
  if (rank <= 10) return "Strong match";
  return "Relevant match";
};

const recipeOverview = (recipe) => {
  if (recipe.summary) return recipe.summary;
  if (recipe.description) return recipe.description;
  return "Open the recipe to explore its ingredients and available details.";
};

const recipeFactsMarkup = (recipe) => recipeFactItems(recipe).map((fact) => `
  <span class="recipe-fact" title="${escapeHtml(fact.label)}" aria-label="${escapeHtml(fact.label)}">
    ${iconMarkup(fact.kind === "time" ? "clock" : fact.kind === "yield" ? "users" : "ingredients")}
    <span aria-hidden="true">${escapeHtml(fact.value)}</span>
  </span>`).join("");

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".mode-button").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".mode-button").forEach((item) => item.setAttribute("aria-pressed", "false"));
    button.classList.add("active");
    button.setAttribute("aria-pressed", "true");
    inputKind = button.dataset.kind;
    input.placeholder = inputKind === "query"
      ? "Something quick and spicy with chicken"
      : "Eggs, potatoes, onion";
    input.focus();
  });
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

const renderRecipe = (recipe, index) => {
  const rank = index + 1;
  return `
    <button class="recipe-card" type="button" data-result-index="${index}" aria-label="Open ${escapeHtml(recipe.name)}">
      <span class="card-top">
        <span class="rank">${rank}</span>
        <span class="card-copy">
          <span class="match-label">${relevanceLabel(rank)}</span>
          <span class="recipe-title">${escapeHtml(recipe.name)}</span>
        </span>
      </span>
      <span class="recipe-overview">${escapeHtml(recipeOverview(recipe))}</span>
      <span class="card-bottom">
        <span class="recipe-facts">${recipeFactsMarkup(recipe)}</span>
        <span class="view-label">View recipe <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg></span>
      </span>
    </button>`;
};

const renderPagination = () => {
  const pageCount = Math.ceil(searchResults.length / PAGE_SIZE);
  if (pageCount <= 1) {
    pagination.hidden = true;
    pagination.innerHTML = "";
    return;
  }
  const pageButtons = Array.from({ length: pageCount }, (_, index) => {
    const page = index + 1;
    return `<button type="button" class="page-button${page === currentPage ? " active" : ""}" data-page="${page}"${page === currentPage ? ' aria-current="page"' : ""}>${page}</button>`;
  }).join("");
  pagination.innerHTML = `
    <button type="button" class="page-button" data-direction="previous" ${currentPage === 1 ? "disabled" : ""}>Previous</button>
    ${pageButtons}
    <button type="button" class="page-button" data-direction="next" ${currentPage === pageCount ? "disabled" : ""}>Next</button>`;
  pagination.hidden = false;
};

const renderPage = ({ scroll = false, animate = false } = {}) => {
  const start = (currentPage - 1) * PAGE_SIZE;
  const pageRecipes = searchResults.slice(start, start + PAGE_SIZE);
  results.classList.toggle("animate-results", animate);
  results.innerHTML = pageRecipes.map((recipe, offset) => renderRecipe(recipe, start + offset)).join("");
  const end = Math.min(start + PAGE_SIZE, searchResults.length);
  if (!pageRecipes.length) {
    results.innerHTML = '<div class="empty-state"><h3>No useful matches found</h3><p>Try adding an ingredient, cuisine, mood, or cooking time.</p></div>';
    resultMeta.textContent = "No results";
    pagination.hidden = true;
    return;
  }
  resultMeta.textContent = `Showing ${start + 1} to ${end} of ${searchResults.length} results`;
  renderPagination();
  if (scroll) resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
};

pagination.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button || button.disabled) return;
  const pageCount = Math.ceil(searchResults.length / PAGE_SIZE);
  if (button.dataset.page) currentPage = Number(button.dataset.page);
  if (button.dataset.direction === "previous") currentPage = Math.max(1, currentPage - 1);
  if (button.dataset.direction === "next") currentPage = Math.min(pageCount, currentPage + 1);
  renderPage({ scroll: true });
  pagination.querySelector('[aria-current="page"]')?.focus({ preventScroll: true });
});

const metadataMarkup = (recipe) => {
  const items = [
    ["prep", formatDuration(recipe.prep_time), "clock"],
    ["cook", formatDuration(recipe.cook_time), "flame"],
    ["total", formatMinutes(recipe.total_minutes), "hourglass"],
    [null, recipe.recipe_yield, "users"],
  ].filter(([, value]) => value);
  if (!items.length) return "";
  return `<div class="detail-meta" aria-label="Recipe facts">${items.map(([label, value, icon]) => `
    <div class="detail-metric">
      <span class="metric-icon">${iconMarkup(icon)}</span>
      <span class="metric-copy"><strong>${escapeHtml(value)}</strong>${label ? `<span>${label}</span>` : ""}</span>
    </div>`).join("")}</div>`;
};

const methodSectionMarkup = (recipe) => {
  if (!recipe.instructions) return "";
  const steps = instructionSteps(recipe.instructions);
  if (!steps.length) return "";
  const provenance = recipe.instruction_source === "matched_corpus"
    ? '<p class="method-provenance">Recovered from a high-confidence title and ingredient match in the instruction corpus.</p>'
    : "";
  return `
    <section class="detail-section">
      <h3>Method</h3>
      ${provenance}
      <ol class="method-list">${steps.map((step) => `<li>${formatInstructionText(step)}</li>`).join("")}</ol>
    </section>`;
};

const sourceMarkup = (recipe) => {
  const label = sourceLabel(recipe.source);
  if (!recipe.url) return "";
  const iconPath = sourceIconPath(recipe.source);
  const publisherMark = iconPath
    ? `<img class="source-favicon" src="${escapeHtml(iconPath)}" alt="" aria-hidden="true" width="20" height="20" />`
    : `<span class="source-favicon source-favicon-fallback">${iconMarkup("globe")}</span>`;
  return `
    <div class="source-block">
      <a class="source-link" href="${escapeHtml(recipe.url)}" target="_blank" rel="noreferrer noopener">
        <span>View on</span>
        ${publisherMark}
        <strong>${escapeHtml(label || "original source")}</strong>
        ${iconMarkup("external", "source-external")}
      </a>
    </div>`;
};

const showDialog = (target) => {
  const scrollbarWidth = Math.max(0, window.innerWidth - document.documentElement.clientWidth);
  lockedScrollY = window.scrollY;
  target.showModal();
  document.body.style.setProperty("--scrollbar-compensation", `${scrollbarWidth}px`);
  document.body.style.setProperty("--locked-scroll-offset", `-${lockedScrollY}px`);
  document.documentElement.classList.add("modal-open");
  document.body.classList.add("modal-open");
};

const releaseDialogScroll = () => {
  if (document.querySelector("dialog[open]")) return;
  document.documentElement.classList.remove("modal-open");
  document.body.classList.remove("modal-open");
  document.body.style.removeProperty("--scrollbar-compensation");
  document.body.style.removeProperty("--locked-scroll-offset");
  window.scrollTo(0, lockedScrollY);
};

[dialog, howDialog].forEach((item) => item.addEventListener("close", releaseDialogScroll));

const openRecipe = (index) => {
  const recipe = searchResults[index];
  if (!recipe) return;
  recipeDetail.innerHTML = `
    <div class="detail-grid">
      <article class="detail-content">
        <p class="detail-kicker">${relevanceLabel(index + 1)} · Recipe ${index + 1} of ${searchResults.length}</p>
        <h2 id="detail-title" tabindex="-1">${escapeHtml(recipe.name)}</h2>
        <p class="detail-summary">${escapeHtml(recipeOverview(recipe))}</p>
        ${metadataMarkup(recipe)}
        <section class="detail-section">
          <h3>Ingredients</h3>
          <ul class="ingredient-list">${recipe.ingredients.map((ingredient) => `<li>${formatIngredientText(ingredient)}</li>`).join("")}</ul>
        </section>
        ${methodSectionMarkup(recipe)}
        ${sourceMarkup(recipe)}
      </article>
    </div>`;
  showDialog(dialog);
  document.querySelector("#detail-title")?.focus();
};

results.addEventListener("click", (event) => {
  const card = event.target.closest("[data-result-index]");
  if (card) openRecipe(Number(card.dataset.resultIndex));
});

dialogClose.addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});

howButton.addEventListener("click", () => {
  showDialog(howDialog);
  howTitle.focus();
});
howClose.addEventListener("click", () => howDialog.close());
howDialog.addEventListener("click", (event) => {
  if (event.target === howDialog) howDialog.close();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value) return;
  input.blur();

  activeRequest?.abort();
  const controller = new AbortController();
  activeRequest = controller;
  const sequence = ++requestSequence;
  const timeout = window.setTimeout(() => controller.abort("timeout"), 30000);

  const payload = inputKind === "ingredients"
    ? { ingredients: value.split(/[,;\n]+/).map((item) => item.trim()).filter(Boolean), limit: 50 }
    : { query: value, limit: 50 };

  const hadResults = searchResults.length > 0;
  const previousResultMeta = resultMeta.textContent;

  submit.disabled = true;
  form.setAttribute("aria-busy", "true");
  notice.hidden = true;
  notice.setAttribute("role", "status");
  results.classList.remove("animate-results");
  if (hadResults) resultMeta.textContent = "Searching…";

  try {
    const response = await fetch(apiUrl("/api/search"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const data = await response.json();
    if (!response.ok) {
      const message = data.detail?.[0]?.msg || data.detail || "Search request failed";
      throw new Error(message);
    }
    if (sequence !== requestSequence) return;
    searchResults = data.results;
    searchMeta = data.meta;
    currentPage = 1;
    document.body.classList.add("has-results");
    resultsSection.hidden = false;
    resultsQuery.textContent = `For “${value}”`;
    if (data.meta.strategy === "adventurous") resultsTitle.textContent = "Adventurous picks";
    else if (data.meta.strategy === "discovery") resultsTitle.textContent = "Ideas to explore";
    else resultsTitle.textContent = "Best matches";
    renderPage({ animate: true });
    const messages = [];
    if (data.meta.strategy === "adventurous") {
      messages.push("We do not know your cooking history, so these picks favor less common ingredient combinations in this collection.");
    } else if (data.meta.strategy === "discovery" && !data.meta.retrieval_warning) {
      messages.push("This was a broad request, so these are varied ideas from the collection.");
    } else if (data.meta.confidence === "low") {
      messages.push("These are the closest available matches. Add an ingredient, cuisine, mood, or cooking time for better results.");
    }
    if (data.meta.query_understanding.warning) messages.push(data.meta.query_understanding.warning);
    if (data.meta.retrieval_warning) messages.push(data.meta.retrieval_warning);
    if (messages.length) {
      notice.hidden = false;
      notice.textContent = messages.join(" ");
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    if (sequence !== requestSequence) return;
    if (hadResults) {
      resultMeta.textContent = previousResultMeta;
    } else {
      searchResults = [];
      searchMeta = null;
      document.body.classList.add("has-results");
      resultsSection.hidden = false;
      resultMeta.textContent = "Unable to search";
      results.innerHTML = "";
      pagination.hidden = true;
    }
    notice.hidden = false;
    notice.setAttribute("role", "alert");
    if (error.name === "AbortError") {
      notice.textContent = "The search took too long. Please try again.";
    } else if (!navigator.onLine) {
      notice.textContent = "You appear to be offline. Check your connection and try again.";
    } else {
      notice.textContent = error.message || "Something went wrong. Please try again.";
    }
  } finally {
    window.clearTimeout(timeout);
    if (sequence === requestSequence) {
      submit.disabled = false;
      form.setAttribute("aria-busy", "false");
      activeRequest = null;
    }
  }
});
