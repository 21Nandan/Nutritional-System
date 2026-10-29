// Per-device storage. Profile, saved products and history never leave this browser
// except as the per-request profile header. Storage can be unavailable (private mode,
// blocked site data); reads then return defaults and writes report failure to the caller.

const KEYS = {
  profile: 'eatgood_user_profile',
  saved: 'eatgood_saved_products',
  history: 'eatgood_interaction_history',
  onboarding: 'eatgood_onboarding_completed',
  termsAcceptedAt: 'eatgood_terms_accepted_at',
};

const HISTORY_LIMIT = 30;

export const DEFAULT_PROFILE = {
  name: 'Guest',
  goal: 'Balanced Choices',
  dietary_preference: 'No preference',
  allergens_to_avoid: '',
  age_group: '18-24',
  activity_level: 'Moderately active',
};

function read(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export function loadProfile() {
  const stored = read(KEYS.profile, null);
  if (!stored || typeof stored !== 'object') return null;
  return { ...DEFAULT_PROFILE, ...stored };
}

export function saveProfile(profile) {
  return write(KEYS.profile, profile);
}

export function loadSavedProducts() {
  const items = read(KEYS.saved, []);
  return Array.isArray(items) ? items : [];
}

export function isSaved(productId) {
  return loadSavedProducts().some((p) => p.product_id === productId);
}

// Returns the new saved state, or throws if the browser refused to store it.
export function toggleSavedProduct(product) {
  const items = loadSavedProducts();
  const exists = items.some((p) => p.product_id === product.product_id);
  const next = exists ? items.filter((p) => p.product_id !== product.product_id) : [{ ...product, saved_at: new Date().toISOString() }, ...items];
  if (!write(KEYS.saved, next)) {
    throw new Error('Your browser blocked saving. Check that site data is allowed for this site.');
  }
  return !exists;
}

export function loadHistory() {
  const items = read(KEYS.history, []);
  return Array.isArray(items) ? items : [];
}

export function recordHistory(assessment) {
  if (!assessment || !assessment.product_id) return;
  const entry = {
    product_id: assessment.product_id,
    product_name: assessment.product_name || 'Food product',
    brand: assessment.brand || '',
    category: assessment.category || '',
    personalized_score: assessment.layer2_personalized?.personalized_score ?? null,
    general_grade: assessment.layer1_general?.grade || 'N/A',
    allergen_conflict: Boolean(assessment.safety_override?.allergen_conflict),
    analysis_source: assessment.is_custom ? 'Label scan / manual entry' : 'Catalogue',
    timestamp: new Date().toISOString(),
  };
  const next = [entry, ...loadHistory().filter((h) => h.product_id !== entry.product_id)].slice(0, HISTORY_LIMIT);
  write(KEYS.history, next);
}

export function clearHistory() {
  try {
    window.localStorage.removeItem(KEYS.history);
  } catch {
    // Nothing to clear if storage is unavailable.
  }
}

export function isOnboardingComplete() {
  return read(KEYS.onboarding, false) === true;
}

export function completeOnboarding() {
  write(KEYS.onboarding, true);
  write(KEYS.termsAcceptedAt, new Date().toISOString());
}

// Session-scoped state (scanner form, custom assessment, compare list). Losing it only
// means the user re-enters data, so failures return the fallback / false explicitly.
export function readSession(key, fallback) {
  try {
    const raw = window.sessionStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function writeSession(key, value) {
  try {
    if (value === null || value === undefined) window.sessionStorage.removeItem(key);
    else window.sessionStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
