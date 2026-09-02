const SOURCE_LABELS = {
  allrecipes: "Allrecipes",
  "allrecipes.com": "Allrecipes",
  bonappetit: "Bon Appétit",
  "bonappetit.com": "Bon Appétit",
  epicurious: "Epicurious",
  "epicurious.com": "Epicurious",
  sample: "Sample data",
  "development fixture": "Development fixture",
};

const SOURCE_ICONS = {
  allrecipes: "source-icons/allrecipes.svg?v=1",
  "allrecipes.com": "source-icons/allrecipes.svg?v=1",
  bonappetit: "source-icons/bonappetit.svg?v=1",
  "bonappetit.com": "source-icons/bonappetit.svg?v=1",
  epicurious: "source-icons/epicurious.svg?v=1",
  "epicurious.com": "source-icons/epicurious.svg?v=1",
};

export const formatDuration = (value) => {
  if (!value) return null;
  const match = /^PT(?:(\d+)H)?(?:(\d+)M)?$/i.exec(value);
  if (!match || (!match[1] && !match[2])) return value;
  const parts = [];
  if (match[1]) parts.push(`${match[1]} hr`);
  if (match[2]) parts.push(`${match[2]} min`);
  return parts.join(" ");
};

export const formatMinutes = (value) => {
  if (!Number.isInteger(value) || value < 0) return null;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  const parts = [];
  if (hours) parts.push(`${hours} hr`);
  if (minutes || !hours) parts.push(`${minutes} min`);
  return parts.join(" ");
};

export const recipeTimeFact = (recipe) => {
  const total = formatMinutes(recipe.total_minutes);
  if (total) return { kind: "time", value: total, label: `${total} total time` };
  const cook = formatDuration(recipe.cook_time);
  if (cook) return { kind: "time", value: cook, label: `${cook} cooking time` };
  const prep = formatDuration(recipe.prep_time);
  return prep ? { kind: "time", value: prep, label: `${prep} preparation time` } : null;
};

export const compactRecipeYield = (value, maxLength = 36) => {
  const text = String(value ?? "").trim();
  return text && text.length <= maxLength ? text : null;
};

export const recipeFactItems = (recipe) => {
  const time = recipeTimeFact(recipe);
  const recipeYield = compactRecipeYield(recipe.recipe_yield);
  const ingredientCount = Array.isArray(recipe.ingredients) ? recipe.ingredients.length : 0;
  const items = [];
  if (time) items.push(time);
  if (recipeYield) {
    items.push({
      kind: "yield",
      value: recipeYield,
      label: /^makes?\b/i.test(recipeYield) ? recipeYield : `Makes ${recipeYield}`,
    });
  }
  items.push({
    kind: "ingredients",
    value: `${ingredientCount} ${ingredientCount === 1 ? "ingredient" : "ingredients"}`,
    label: `${ingredientCount} ${ingredientCount === 1 ? "ingredient" : "ingredients"}`,
  });
  return items;
};

export const recipeFacts = (recipe) => recipeFactItems(recipe).map((fact) => fact.label).join(" · ");

export const sourceLabel = (source) => {
  const text = String(source ?? "").trim();
  if (!text) return null;
  const known = SOURCE_LABELS[text.toLocaleLowerCase()];
  if (known) return known;
  return text.replace(/[_-]+/g, " ").replace(/\s+/g, " ");
};

export const sourceIconPath = (source) => {
  const text = String(source ?? "").trim().toLocaleLowerCase();
  return SOURCE_ICONS[text] ?? null;
};
