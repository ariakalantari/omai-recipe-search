import assert from "node:assert/strict";
import test from "node:test";

import {
  compactRecipeYield,
  formatDuration,
  formatMinutes,
  recipeFactItems,
  recipeFacts,
  recipeTimeFact,
  sourceIconPath,
  sourceLabel,
} from "../src/recipe_search/static/recipe-metadata.mjs";

test("formats API durations and totals for readers", () => {
  assert.equal(formatDuration("PT1H20M"), "1 hr 20 min");
  assert.equal(formatMinutes(80), "1 hr 20 min");
  assert.equal(formatMinutes(0), "0 min");
  assert.equal(formatMinutes(-1), null);
});

test("only presents a total supplied by the API", () => {
  assert.deepEqual(
    recipeTimeFact({ total_minutes: 45, prep_time: "PT10M", cook_time: "PT35M" }),
    { kind: "time", value: "45 min", label: "45 min total time" },
  );
  assert.deepEqual(
    recipeTimeFact({ total_minutes: null, prep_time: "PT10M", cook_time: "PT35M" }),
    { kind: "time", value: "35 min", label: "35 min cooking time" },
  );
  assert.deepEqual(
    recipeTimeFact({ total_minutes: null, prep_time: "PT10M", cook_time: null }),
    { kind: "time", value: "10 min", label: "10 min preparation time" },
  );
});

test("keeps card facts useful and omits unusually long yields", () => {
  const recipe = {
    total_minutes: 90,
    prep_time: "PT30M",
    cook_time: "PT1H",
    recipe_yield: "4 servings",
    ingredients: ["rice", "beans"],
  };
  assert.deepEqual(recipeFactItems(recipe), [
    { kind: "time", value: "1 hr 30 min", label: "1 hr 30 min total time" },
    { kind: "yield", value: "4 servings", label: "Makes 4 servings" },
    { kind: "ingredients", value: "2 ingredients", label: "2 ingredients" },
  ]);
  assert.equal(recipeFacts(recipe), "1 hr 30 min total time · Makes 4 servings · 2 ingredients");
  assert.equal(compactRecipeYield("Makes a very long and highly specific banquet-sized quantity for a crowd"), null);
});

test("keeps visible facts compact while preserving full accessible labels", () => {
  const facts = recipeFactItems({
    total_minutes: null,
    prep_time: null,
    cook_time: null,
    recipe_yield: null,
    ingredients: ["salt"],
  });
  assert.deepEqual(facts, [{ kind: "ingredients", value: "1 ingredient", label: "1 ingredient" }]);
});

test("uses friendly publisher labels without inventing unknown names", () => {
  assert.equal(sourceLabel("bonappetit"), "Bon Appétit");
  assert.equal(sourceLabel("epicurious"), "Epicurious");
  assert.equal(sourceLabel("my_recipe_archive"), "my recipe archive");
  assert.equal(sourceLabel(null), null);
  assert.equal(sourceIconPath("allrecipes"), "source-icons/allrecipes.svg?v=1");
  assert.equal(sourceIconPath("bonappetit.com"), "source-icons/bonappetit.svg?v=1");
  assert.equal(sourceIconPath("epicurious"), "source-icons/epicurious.svg?v=1");
  assert.equal(sourceIconPath("my_recipe_archive"), null);
});
