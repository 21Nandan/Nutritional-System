// Comparison rules for the Product Comparison Matrix. Pure functions over the /api/compare rows,
// so highlights, the "Differences only" filter and the verdict always agree and update together.
// Nothing here scores products: Goal Match and grades come from the server's existing scoring.

import { formatNutrient, basisLabel } from './format';

// direction: which way is generally preferable; null = depends on context (never highlighted).
// minDiff: smallest absolute difference worth pointing out; a difference must also be at least
// MIN_RELATIVE_DIFF of the larger value, so 1 g vs 2 g of fibre counts but 40.1 g vs 41 g of carbs doesn't.
export const COMPARE_METRICS = [
  { key: 'energy_kcal', label: 'Energy', direction: null, minDiff: 25,
    note: 'Calories depend on how much you eat and what you need, so neither side is marked better.' },
  { key: 'sugars_g', label: 'Total Sugars', direction: 'lower', minDiff: 1, less: 'less sugar', more: 'more sugar' },
  { key: 'sodium_mg', label: 'Sodium', direction: 'lower', minDiff: 50, less: 'less sodium', more: 'more sodium' },
  { key: 'protein_g', label: 'Protein', direction: 'higher', minDiff: 1, less: 'less protein', more: 'more protein' },
  { key: 'saturated_fat_g', label: 'Saturated Fat', direction: 'lower', minDiff: 0.5, less: 'less saturated fat', more: 'more saturated fat' },
  { key: 'dietary_fibre_g', label: 'Dietary Fibre', direction: 'higher', minDiff: 0.5, less: 'less fibre', more: 'more fibre' },
];

const MIN_RELATIVE_DIFF = 0.1;
// Goal Match scores closer than this are treated as a tie.
export const GOAL_MATCH_MIN_DIFF = 5;
// Keep the verdict short: at most this many advantages and trade-offs.
const MAX_POINTS = 3;
const GRADE_RANK = { A: 1, B: 2, C: 3, D: 4, E: 5 };

// Which goal emphasises which nutrient, so the verdict mentions the goal's nutrient first.
const GOAL_METRIC = {
  'Reduce Sugar': 'sugars_g',
  'Reduce Sodium': 'sodium_mg',
  'Increase Fibre': 'dietary_fibre_g',
  'Increase Protein': 'protein_g',
};

function basisKey(basis) {
  const label = basisLabel(basis);
  if (label === 'per 100 g') return '100g';
  if (label === 'per 100 ml') return '100ml';
  return null; // per serving or unstated: serving sizes differ, so values can't be compared
}

// Values are compared as displayed (whole kcal and mg, grams to one decimal), so a difference
// that disappears on screen never gets highlighted.
function displayedNumber(key, value) {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return null;
  const num = Number(value);
  return key === 'energy_kcal' || key.endsWith('_mg') ? Math.round(num) : Math.round(num * 10) / 10;
}

function isMeaningful(metric, a, b) {
  const diff = Math.abs(a - b);
  return diff >= metric.minDiff && diff >= MIN_RELATIVE_DIFF * Math.max(Math.abs(a), Math.abs(b));
}

export function basisComparison(products) {
  const keys = products.map((p) => basisKey(p.measurement_basis));
  const comparable = keys.every((k) => k !== null) && new Set(keys).size === 1;
  let reason = null;
  if (!comparable) {
    const labels = [...new Set(products.map((p) => basisLabel(p.measurement_basis)))];
    reason = labels.length > 1
      ? `These products state values on different bases (${labels.join(', ')}), so nutrient values are not compared.`
      : `Values are stated ${labels[0]}, and serving sizes differ, so nutrient values are not compared.`;
  }
  return { comparable, reason };
}

// For one metric row: each cell's displayed value, whether it is the favourable value and whether
// it is above the product's category limit (same thresholds as the grade and catalogue red values).
export function compareMetric(metric, products, comparable) {
  const values = products.map((p) => displayedNumber(metric.key, p[metric.key]));
  const available = values.filter((v) => v !== null);
  let meaningful = false;
  let bestValue = null;
  if (comparable && available.length >= 2) {
    const max = Math.max(...available);
    const min = Math.min(...available);
    meaningful = isMeaningful(metric, max, min);
    if (meaningful && metric.direction) bestValue = metric.direction === 'lower' ? min : max;
  }
  const cells = products.map((p, i) => {
    const value = values[i];
    const isBest = bestValue !== null && value !== null && !isMeaningful(metric, value, bestValue);
    const isConcern = p.nutrient_flags?.[metric.key]?.level === 'high';
    return {
      display: formatNutrient(metric.key, p[metric.key]),
      missing: value === null,
      isBest,
      bestLabel: isBest ? (metric.direction === 'lower' ? 'Lowest' : 'Highest') : null,
      isConcern,
      concernLimit: isConcern ? p.nutrient_flags[metric.key].threshold : null,
    };
  });
  return { metric, meaningful, cells };
}

export function compareGrades(products) {
  const ranks = products.map((p) => GRADE_RANK[p.general_grade] ?? null);
  const sameCategory = new Set(products.map((p) => p.category)).size === 1;
  const allGraded = ranks.every((r) => r !== null);
  let note = null;
  if (!allGraded) note = 'Some products have no grade, so grades are not compared.';
  else if (!sameCategory) note = 'Grades use each product\'s own category limits, so grades from different categories are not compared.';
  const comparable = allGraded && sameCategory;
  const best = comparable ? Math.min(...ranks) : null;
  const differs = comparable && new Set(ranks).size > 1;
  return {
    note,
    cells: products.map((p, i) => ({ grade: p.general_grade || 'N/A', reason: p.grade_reason || null, note: p.grade_note || null, isBest: differs && ranks[i] === best })),
  };
}

export function compareGoalMatch(products) {
  const eligible = products.filter((p) => p.personalized_score != null && !p.has_allergen_conflict);
  const scores = eligible.map((p) => p.personalized_score);
  const top = scores.length ? Math.max(...scores) : null;
  const leaders = eligible.filter((p) => top - p.personalized_score < GOAL_MATCH_MIN_DIFF);
  const clearLeader = leaders.length === 1 && eligible.length >= 2 ? leaders[0] : null;
  return {
    clearLeader,
    leaders,
    eligible,
    cells: products.map((p) => ({ isBest: clearLeader?.product_id === p.product_id })),
  };
}

// 'conflict' | 'no-profile-allergens' | 'unknown' | 'none-found'
export function allergenState(product, profileAllergens) {
  if (product.has_allergen_conflict) return 'conflict';
  if (!profileAllergens) return 'no-profile-allergens';
  if (product.allergen_status_unknown) return 'unknown';
  return 'none-found';
}

function nutrientDifferences(subject, other, comparable, goal) {
  if (!comparable) return { advantages: [], tradeoffs: [] };
  const goalKey = GOAL_METRIC[goal];
  const ordered = [...COMPARE_METRICS].sort((a, b) => (b.key === goalKey) - (a.key === goalKey));
  const advantages = [];
  const tradeoffs = [];
  for (const metric of ordered) {
    if (!metric.direction) continue;
    const a = displayedNumber(metric.key, subject[metric.key]);
    const b = displayedNumber(metric.key, other[metric.key]);
    if (a === null || b === null || !isMeaningful(metric, a, b)) continue;
    const subjectBetter = metric.direction === 'lower' ? a < b : a > b;
    const phrase = `${a < b ? metric.less : metric.more} (${formatNutrient(metric.key, a)} vs ${formatNutrient(metric.key, b)})`;
    (subjectBetter ? advantages : tradeoffs).push(phrase);
  }
  return { advantages: advantages.slice(0, MAX_POINTS), tradeoffs: tradeoffs.slice(0, MAX_POINTS) };
}

function names(list) {
  const n = list.map((p) => p.product_name);
  return n.length <= 2 ? n.join(' and ') : `${n.slice(0, -1).join(', ')} and ${n[n.length - 1]}`;
}

// A short verdict built only from the returned data and the server's Goal Match scores.
export function buildVerdict(products, goal, profileAllergens) {
  const { comparable } = basisComparison(products);
  const goalMatch = compareGoalMatch(products);
  const conflicts = products.filter((p) => p.has_allergen_conflict);
  const unknownAllergens = profileAllergens ? products.filter((p) => !p.has_allergen_conflict && p.allergen_status_unknown) : [];
  const unscored = products.filter((p) => p.personalized_score == null && !p.has_allergen_conflict);

  const notes = [];
  if (conflicts.length) {
    notes.push(`${names(conflicts)} ${conflicts.length === 1 ? 'contains' : 'contain'} an allergen from your profile, so ${conflicts.length === 1 ? 'it is' : 'they are'} left out of the verdict.`);
  }
  if (unknownAllergens.length) {
    notes.push(`Allergen information is not stated for ${names(unknownAllergens)}: that is not the same as being free of your allergens.`);
  }
  if (unscored.length) notes.push(`${names(unscored)} could not be scored because of missing data.`);

  let headline;
  let advantages = [];
  let tradeoffs = [];
  let subject = null;
  let comparedWith = null;
  if (goalMatch.clearLeader) {
    const leader = goalMatch.clearLeader;
    const runnerUp = [...goalMatch.eligible]
      .filter((p) => p.product_id !== leader.product_id)
      .sort((a, b) => b.personalized_score - a.personalized_score)[0];
    subject = leader;
    comparedWith = runnerUp;
    headline = `${leader.product_name} is the better match for your goal (${goal}): Goal Match ${leader.personalized_score} vs ${runnerUp.personalized_score} for ${runnerUp.product_name}.`;
    ({ advantages, tradeoffs } = nutrientDifferences(leader, runnerUp, comparable, goal));
  } else if (goalMatch.leaders.length > 1) {
    const scores = goalMatch.leaders.map((p) => p.personalized_score).join(' vs ');
    headline = `${names(goalMatch.leaders)} match your goal (${goal}) about equally (Goal Match ${scores}).`;
    if (goalMatch.leaders.length === 2) {
      [subject, comparedWith] = goalMatch.leaders;
      ({ advantages, tradeoffs } = nutrientDifferences(goalMatch.leaders[0], goalMatch.leaders[1], comparable, goal));
    }
  } else if (goalMatch.eligible.length === 1) {
    const only = goalMatch.eligible[0];
    headline = `${only.product_name} is the only product here that can be matched to your goal (${goal}): Goal Match ${only.personalized_score}.`;
  } else {
    headline = 'None of these products can be matched to your goal.';
  }
  if (!comparable && comparedWith) notes.push('Nutrient values are on different bases, so they are not compared.');
  return { headline, advantages, tradeoffs, subject, comparedWith, tie: !goalMatch.clearLeader && goalMatch.leaders.length > 1, notes };
}
