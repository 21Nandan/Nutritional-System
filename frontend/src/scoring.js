// How grades and Goal Match scores are described on screen. The numbers are calculated by the
// server (backend/core/nutrition_scoring.py); these bands and labels mirror its rules so every
// screen describes a score the same way. Nothing here calculates or adjusts a score.

// General Nutrition Grade: 50 − 7 × penalty points + 8 × bonus points (at most 3 if anything is over a limit),
// kept between 10 and 100.
export const GRADE_BANDS = [
  { grade: 'A', min: 80, label: 'Optimal nutritional profile' },
  { grade: 'B', min: 65, label: 'Favourable nutritional balance' },
  { grade: 'C', min: 48, label: 'Moderate: consume in moderation' },
  { grade: 'D', min: 32, label: 'Elevated nutrients of concern' },
  { grade: 'E', min: 10, label: 'High in sugar, sodium or saturated fat' },
];

// Goal Match: starts at 70, goal rules add or subtract points, kept between 1 and 100.
export const GOAL_BANDS = [
  { min: 75, label: 'Strong match', tone: 'strong' },
  { min: 50, label: 'Moderate match', tone: 'moderate' },
  { min: 1, label: 'Poor match', tone: 'poor' },
];

const UNGRADED = {
  'N/A': { short: 'N/A', label: 'Not graded', reason: 'No validated grading method for this category yet.' },
  'Insufficient Data': { short: '?', label: 'Not enough data', reason: 'Energy, sugars, saturated fat or sodium is missing from the label.' },
  'Data Contradiction': { short: '!', label: 'Conflicting label data', reason: 'Some label values contradict each other (for example sugars above carbohydrates).' },
};

export function gradeInfo(grade) {
  const band = GRADE_BANDS.find((b) => b.grade === grade);
  if (band) return { graded: true, letter: grade, label: band.label, className: `grade-${grade}` };
  const ungraded = UNGRADED[grade] || UNGRADED['N/A'];
  return { graded: false, letter: ungraded.short, label: ungraded.label, reason: ungraded.reason, className: 'grade-NA' };
}

// Nutrients that cost a product grade points, as the server's breakdown lists them.
const LIMIT_NUTRIENT_NAMES = { sugars: 'sugar', sodium: 'sodium', saturated_fat: 'saturated fat', trans_fat: 'trans fat', energy: 'calories' };

export function nutrientsOverLimit(layer1) {
  return Object.entries(layer1?.key_contributing_nutrients || {})
    .filter(([key, n]) => LIMIT_NUTRIENT_NAMES[key] && n?.points < 0)
    .map(([key]) => LIMIT_NUTRIENT_NAMES[key]);
}

// "sugar", "sugar and sodium", "sugar, sodium and saturated fat"
export function listNutrients(names) {
  return names.length < 2 ? names.join('') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

// D and E labels name this product's own nutrients over the limit; other grades keep the band label.
export function gradeLabelFor(layer1) {
  const over = listNutrients(nutrientsOverLimit(layer1));
  if (over && layer1?.grade === 'E') return `High in ${over}`;
  if (over && layer1?.grade === 'D') return `Elevated ${over}`;
  return gradeInfo(layer1?.grade).label;
}

export function goalInfo(score, { allergenConflict = false } = {}) {
  if (allergenConflict) return { available: true, score: 0, label: 'Allergen conflict', tone: 'conflict' };
  if (score === null || score === undefined) return { available: false, score: null, label: 'Not enough data', tone: 'none' };
  const band = GOAL_BANDS.find((b) => score >= b.min) || GOAL_BANDS[GOAL_BANDS.length - 1];
  return { available: true, score, label: band.label, tone: band.tone };
}
