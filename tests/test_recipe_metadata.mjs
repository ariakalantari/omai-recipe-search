import assert from "node:assert/strict";
import test from "node:test";

import {
  compactRecipeYield,
  formatDuration,
  formatMinutes,
  recipeFacts,
  recipeTimeFact,
  sourceLabel,
} from "../src/recipe_search/static/recipe-metadata.mjs";

test("formats API durations and totals for readers", () => {
  assert.equal(formatDuration("PT1H20M"), "1 hr 20 min");
  assert.equal(formatMinutes(80), "1 hr 20 min");
  assert.equal(formatMinutes(0), "0 min");
  assert.equal(formatMinutes(-1), null);
});

test("only presents a total supplied by the API", () => {
  assert.equal(recipeTimeFact({ total_minutes: 45, prep_time: "PT10M", cook_time: "PT35M" }), "45 min total");
  assert.equal(recipeTimeFact({ total_minutes: null, prep_time: "PT10M", cook_time: "PT35M" }), "35 min cook");
  assert.equal(recipeTimeFact({ total_minutes: null, prep_time: "PT10M", cook_time: null }), "10 min prep");
});

test("keeps card facts useful and omits unusually long yields", () => {
  const recipe = {
    total_minutes: 90,
    prep_time: "PT30M",
    cook_time: "PT1H",
    recipe_yield: "4 servings",
    ingredients: ["rice", "beans"],
  };
  assert.equal(recipeFacts(recipe), "1 hr 30 min total · 4 servings · 2 ingredients");
  assert.equal(compactRecipeYield("Makes a very long and highly specific banquet-sized quantity for a crowd"), null);
});

test("uses friendly publisher labels without inventing unknown names", () => {
  assert.equal(sourceLabel("bonappetit"), "Bon Appétit");
  assert.equal(sourceLabel("epicurious"), "Epicurious");
  assert.equal(sourceLabel("my_recipe_archive"), "my recipe archive");
  assert.equal(sourceLabel(null), null);
});
