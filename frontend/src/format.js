// One place for nutrient number formatting so every screen shows the same value the same way.
// Missing values are shown as "Not stated", never as 0.

const UNITS = {
  energy_kcal: 'kcal',
  sodium_mg: 'mg',
  cholesterol_mg: 'mg',
};

export function formatNutrient(key, value) {
  if (value === null || value === undefined || value === '' || Number.isNaN(Number(value))) return 'Not stated';
  const num = Number(value);
  const unit = UNITS[key] || 'g';
  if (unit === 'kcal' || unit === 'mg') return `${Math.round(num)} ${unit}`;
  const rounded = Math.round(num * 10) / 10;
  return `${rounded} g`;
}

export function basisLabel(basis) {
  if (!basis) return 'basis not stated';
  const b = String(basis).toLowerCase().replace(/\s+/g, '');
  if (b.includes('100ml')) return 'per 100 ml';
  if (b.includes('100g')) return 'per 100 g';
  if (b.includes('serving')) return 'per serving';
  return 'basis not stated';
}
