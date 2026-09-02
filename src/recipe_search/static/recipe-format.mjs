const FRACTION = String.raw`(?:\d+\s+\d+\/\d+|\d+\s*[¼½¾⅓⅔⅛⅜⅝⅞]|\d+\/\d+|[¼½¾⅓⅔⅛⅜⅝⅞])`;
const NUMBER = String.raw`(?:${FRACTION}|\d+(?:\.\d+)?|\.\d+)`;
const QUANTITY = String.raw`(?:${NUMBER}|a|an)`;
const RANGE = String.raw`${QUANTITY}(?:\s*(?:-|–|to)\s*${QUANTITY})?`;

const TIME_UNIT = String.raw`(?:seconds?|secs?\.?|minutes?|mins?\.?|hours?|hrs?\.?|days?)`;
const AMOUNT_UNIT = String.raw`(?:teaspoons?|tsp\.?|tablespoons?|tbsp\.?|cups?|fluid\s+ounces?|fl\.?\s*oz\.?|ounces?|oz\.?|pounds?|lbs?\.?|grams?|kilograms?|millilit(?:er|re)s?|lit(?:er|re)s?|gallons?|quarts?|pints?|kg|mg|ml|g|l|pinches?|dashes?|drops?|cans?|packages?|pkgs?\.?|sticks?|cloves?|slices?|pieces?|heads?|bunches?|sprigs?|stalks?|inches?|cm)`;

const ANNOTATIONS = Object.freeze([
  {
    kind: "temperature",
    pattern: String.raw`${NUMBER}(?:\s*(?:-|–|to)\s*${NUMBER})?\s*(?:°\s*[cf]|degrees?(?:\s+(?:celsius|fahrenheit)|\s*[cf])?)`,
    priority: 3,
  },
  {
    kind: "time",
    pattern: String.raw`${RANGE}(?:\s+|-\s*)${TIME_UNIT}`,
    priority: 2,
  },
  {
    kind: "amount",
    pattern: String.raw`${RANGE}(?:\s+|-\s*)${AMOUNT_UNIT}`,
    priority: 1,
  },
]);

const WRAPPERS = Object.freeze({
  amount: ["<span class=\"recipe-amount\">", "</span>"],
  temperature: ["<span class=\"recipe-temperature\">", "</span>"],
  time: ["<span class=\"recipe-time\">", "</span>"],
});

const TOKEN_CHARACTER = /[\p{L}\p{N}_]/u;

const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
})[character]);

const hasTokenBoundaries = (text, start, end) => {
  const before = start > 0 ? text[start - 1] : "";
  const after = end < text.length ? text[end] : "";
  return !TOKEN_CHARACTER.test(before) && !TOKEN_CHARACTER.test(after);
};

const collectAnnotations = (text, { includeLeadingQuantity }) => {
  const candidates = [];

  ANNOTATIONS.forEach(({ kind, pattern, priority }) => {
    for (const match of text.matchAll(new RegExp(pattern, "giu"))) {
      const start = match.index;
      const end = start + match[0].length;
      if (hasTokenBoundaries(text, start, end)) {
        candidates.push({ start, end, kind, priority });
      }
    }
  });

  if (includeLeadingQuantity) {
    const leading = new RegExp(String.raw`^\s*(${QUANTITY})`, "iu").exec(text);
    if (leading) {
      const start = leading[0].length - leading[1].length;
      candidates.push({ start, end: start + leading[1].length, kind: "amount", priority: 0 });
    }
  }

  candidates.sort((left, right) => (
    left.start - right.start
    || right.end - left.end
    || right.priority - left.priority
  ));

  const accepted = [];
  let cursor = 0;
  candidates.forEach((candidate) => {
    if (candidate.start >= cursor) {
      accepted.push(candidate);
      cursor = candidate.end;
    }
  });
  return accepted;
};

const formatText = (value, options) => {
  const text = String(value ?? "");
  const annotations = collectAnnotations(text, options);
  if (!annotations.length) return escapeHtml(text);

  const parts = [];
  let cursor = 0;
  annotations.forEach(({ start, end, kind }) => {
    parts.push(escapeHtml(text.slice(cursor, start)));
    const [open, close] = WRAPPERS[kind];
    parts.push(open, escapeHtml(text.slice(start, end)), close);
    cursor = end;
  });
  parts.push(escapeHtml(text.slice(cursor)));
  return parts.join("");
};

export const formatIngredientText = (value) => formatText(value, { includeLeadingQuantity: true });

export const formatInstructionText = (value) => formatText(value, { includeLeadingQuantity: false });
