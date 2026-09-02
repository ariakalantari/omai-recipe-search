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
  if (total) return `${total} total`;
  const cook = formatDuration(recipe.cook_time);
  if (cook) return `${cook} cook`;
  const prep = formatDuration(recipe.prep_time);
  return prep ? `${prep} prep` : null;
};

export const compactRecipeYield = (value, maxLength = 36) => {
  const text = String(value ?? "").trim();
  return text && text.length <= maxLength ? text : null;
};

export const recipeFacts = (recipe) => [
  recipeTimeFact(recipe),
  compactRecipeYield(recipe.recipe_yield),
  `${recipe.ingredients.length} ingredients`,
].filter(Boolean).join(" · ");

export const sourceLabel = (source) => {
  const text = String(source ?? "").trim();
  if (!text) return null;
  const known = SOURCE_LABELS[text.toLocaleLowerCase()];
  if (known) return known;
  return text.replace(/[_-]+/g, " ").replace(/\s+/g, " ");
};
