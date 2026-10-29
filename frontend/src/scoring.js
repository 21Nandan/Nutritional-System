// How grades and Goal Match scores are described on screen. The numbers are calculated by the
// server (backend/core/nutrition_scoring.py); these bands and labels mirror its rules so every
// screen describes a score the same way. Nothing here calculates or adjusts a score.

// General Nutrition Grade: 50 − 7 × penalty points + 8 × bonus points, kept between 10 and 100.
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

export function goalInfo(score, { allergenConflict = false } = {}) {
  if (allergenConflict) return { available: true, score: 0, label: 'Allergen conflict', tone: 'conflict' };
  if (score === null || score === undefined) return { available: false, score: null, label: 'Not enough data', tone: 'none' };
  const band = GOAL_BANDS.find((b) => score >= b.min) || GOAL_BANDS[GOAL_BANDS.length - 1];
  return { available: true, score, label: band.label, tone: band.tone };
}
