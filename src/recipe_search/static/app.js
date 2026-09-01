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
let inputKind = "query";
let searchResults = [];
let currentPage = 1;
let searchMeta = null;
let activeRequest = null;
let requestSequence = 0;
let lockedScrollY = 0;

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[character]);

const formatDuration = (value) => {
  if (!value) return null;
  const match = /^PT(?:(\d+)H)?(?:(\d+)M)?$/i.exec(value);
  if (!match) return value;
  const parts = [];
  if (match[1]) parts.push(`${match[1]} hr`);
  if (match[2]) parts.push(`${match[2]} min`);
  return parts.join(" ") || value;
};

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

const recipeFacts = (recipe) => {
  const time = formatDuration(recipe.cook_time || recipe.prep_time);
  return [`${recipe.ingredients.length} ingredients`, time].filter(Boolean).join(" · ");
};

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
        <span class="recipe-facts">${escapeHtml(recipeFacts(recipe))}</span>
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
    ["Prep", formatDuration(recipe.prep_time)],
    ["Cook", formatDuration(recipe.cook_time)],
    ["Makes", recipe.recipe_yield],
  ].filter(([, value]) => value);
  if (!items.length) return "";
  return `<div class="detail-meta">${items.map(([label, value]) => `<span><strong>${label}:</strong> ${escapeHtml(value)}</span>`).join("")}</div>`;
};

const methodMarkup = (recipe) => {
  if (!recipe.instructions) {
    return '<p class="missing-detail">Method instructions were not included in this dataset record.</p>';
  }
  const steps = recipe.instructions.split(/\n+/).map((step) => step.trim()).filter(Boolean);
  return `<ol class="method-list">${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>`;
};

const sourceMarkup = (recipe) => recipe.url
  ? `<a class="original-link" href="${escapeHtml(recipe.url)}" target="_blank" rel="noreferrer">Open original recipe <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 17 17 7M8 7h9v9" /></svg></a>`
  : "";

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
          <ul class="ingredient-list">${recipe.ingredients.map((ingredient) => `<li>${escapeHtml(ingredient)}</li>`).join("")}</ul>
        </section>
        <section class="detail-section">
          <h3>Method</h3>
          ${methodMarkup(recipe)}
        </section>
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
  const timeout = window.setTimeout(() => controller.abort("timeout"), 15000);

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
    const response = await fetch("/api/search", {
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
