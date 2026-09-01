const form = document.querySelector("#search-form");
const input = document.querySelector("#search-input");
const submit = document.querySelector("#submit-button");
const resultsSection = document.querySelector("#results-section");
const results = document.querySelector("#results");
const resultMeta = document.querySelector("#result-meta");
const resultsQuery = document.querySelector("#results-query");
const notice = document.querySelector("#notice");
const pagination = document.querySelector("#pagination");
const dialog = document.querySelector("#recipe-dialog");
const dialogClose = document.querySelector("#dialog-close");
const recipeDetail = document.querySelector("#recipe-detail");

const PAGE_SIZE = 10;
let inputKind = "query";
let searchResults = [];
let currentPage = 1;

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
  if (rank === 1) return "Best match";
  if (rank <= 3) return "Excellent match";
  if (rank <= 10) return "Strong match";
  return "Relevant match";
};

const recipeOverview = (recipe) => {
  if (recipe.description) return recipe.description;
  if (recipe.instructions) {
    const method = recipe.instructions.replace(/\s+/g, " ").trim();
    const firstSentence = method.match(/^.*?[.!?](?:\s|$)/)?.[0]?.trim();
    return firstSentence || `${method.slice(0, 150)}${method.length > 150 ? "…" : ""}`;
  }
  return "Open the recipe to explore its ingredients and available details.";
};

const recipeFacts = (recipe) => {
  const time = formatDuration(recipe.cook_time || recipe.prep_time);
  return [`${recipe.ingredients.length} ingredients`, time].filter(Boolean).join(" · ");
};

document.querySelectorAll(".mode-button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".mode-button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
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

const renderPage = ({ scroll = false } = {}) => {
  const start = (currentPage - 1) * PAGE_SIZE;
  const pageRecipes = searchResults.slice(start, start + PAGE_SIZE);
  results.innerHTML = pageRecipes.map((recipe, offset) => renderRecipe(recipe, start + offset)).join("");
  const end = Math.min(start + PAGE_SIZE, searchResults.length);
  resultMeta.textContent = `Showing ${start + 1}–${end} of ${searchResults.length} top matches`;
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

const openRecipe = (index) => {
  const recipe = searchResults[index];
  if (!recipe) return;
  recipeDetail.innerHTML = `
    <div class="detail-grid">
      <article class="detail-content">
        <p class="detail-kicker">${relevanceLabel(index + 1)} · Recipe ${index + 1} of ${searchResults.length}</p>
        <h2 id="detail-title">${escapeHtml(recipe.name)}</h2>
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
  dialog.showModal();
};

results.addEventListener("click", (event) => {
  const card = event.target.closest("[data-result-index]");
  if (card) openRecipe(Number(card.dataset.resultIndex));
});

dialogClose.addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value) return;
  input.blur();

  const payload = inputKind === "ingredients"
    ? { ingredients: value.split(",").map((item) => item.trim()).filter(Boolean), limit: 50 }
    : { query: value, limit: 50 };

  submit.disabled = true;
  document.body.classList.add("has-results");
  resultsSection.hidden = false;
  pagination.hidden = true;
  notice.hidden = true;
  resultsQuery.textContent = `For “${value}”`;
  resultMeta.textContent = "Searching…";
  results.innerHTML = '<div class="recipe-card skeleton"></div><div class="recipe-card skeleton"></div>';
  window.scrollTo({ top: 0, behavior: "smooth" });

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
    searchResults = data.results;
    currentPage = 1;
    renderPage();
    if (data.meta.confidence === "low" || data.meta.query_understanding.warning) {
      notice.hidden = false;
      notice.textContent = data.meta.query_understanding.warning || "These are weak matches—the dataset may not contain what you asked for.";
    }
  } catch (error) {
    searchResults = [];
    resultMeta.textContent = "Unable to search";
    results.innerHTML = "";
    notice.hidden = false;
    notice.textContent = error.message || "Something went wrong. Please try again.";
  } finally {
    submit.disabled = false;
  }
});
