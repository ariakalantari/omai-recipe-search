import assert from "node:assert/strict";
import test from "node:test";

import {
  formatIngredientText,
  formatInstructionText,
  instructionSteps,
} from "../src/recipe_search/static/recipe-format.mjs";

test("formats measurement amounts and ingredient counts", () => {
  assert.equal(
    formatIngredientText("1 tablespoon butter"),
    '<span class="recipe-amount">1 tablespoon</span> butter',
  );
  assert.equal(
    formatIngredientText("2 3/4 cups hot water"),
    '<span class="recipe-amount">2 3/4 cups</span> hot water',
  );
  assert.equal(
    formatIngredientText("3 eggs"),
    '<span class="recipe-amount">3</span> eggs',
  );
  assert.equal(
    formatIngredientText("1 (3 ounce) package cream cheese"),
    '<span class="recipe-amount">1</span> (<span class="recipe-amount">3 ounce</span>) package cream cheese',
  );
});

test("formats durations, ranges, and temperatures in method prose", () => {
  assert.equal(
    formatInstructionText("Cook 25 minutes, rest 5-10 mins., then bake at 350 degrees F."),
    'Cook <span class="recipe-time">25 minutes</span>, rest <span class="recipe-time">5-10 mins.</span>, then bake at <span class="recipe-temperature">350 degrees F</span>.',
  );
  assert.equal(
    formatInstructionText("Simmer for ½ hour and add 2 tbsp. oil."),
    'Simmer for <span class="recipe-time">½ hour</span> and add <span class="recipe-amount">2 tbsp.</span> oil.',
  );
});

test("does not style unrelated method numbers", () => {
  assert.equal(
    formatInstructionText("Divide between 4 plates using a 5-year-old pan."),
    "Divide between 4 plates using a 5-year-old pan.",
  );
});

test("escapes recipe text before adding trusted formatting wrappers", () => {
  const output = formatInstructionText('<img src=x onerror="alert(1)"> Cook 3 minutes.');
  assert.doesNotMatch(output, /<img/);
  assert.match(output, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/);
  assert.match(output, /<span class="recipe-time">3 minutes<\/span>/);
});

test("normalizes source numbering before rendering an ordered method", () => {
  assert.deepEqual(
    instructionSteps("1. Preheat the oven.\nStep 2: Mix well.\n3) Serve."),
    ["Preheat the oven.", "Mix well.", "Serve."],
  );
});

test("removes a combined source paragraph when its full steps also follow", () => {
  assert.deepEqual(
    instructionSteps(
      "Cookie method: 1. Preheat the oven until it reaches temperature. 2. Mix everything.\n"
      + "1. Preheat the oven until it reaches temperature.\n2. Mix everything.",
    ),
    ["Preheat the oven until it reaches temperature.", "Mix everything."],
  );
});
