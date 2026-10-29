import { test, expect } from './fixtures';

// The server for these tests runs with the invented test catalogue (backend/tests/catalogue_fixture.py).
// The profile from fixtures.js is goal "Reduce Sugar" with Milk as an allergen.
const BHUJIA = 'OFF_2000000000015';
const CHEESE_PUFFS = 'OFF_2000000000039';
const OAT_CRACKERS = 'OFF_2000000000053';
const MYSTERY = 'OFF_2000000000114';
const ORANGE_DRINK = 'OFF_2000000000077';
const NOODLES = 'OFF_2000000000084';

const cards = (page) => page.locator('.product-catalogue .card h3');

test('catalogue lists products with categories, scores and pagination', async ({ page }) => {
  await page.goto('/catalogue');
  await expect(cards(page)).toHaveCount(12);
  await expect(page.getByRole('button', { name: 'Snacks', exact: true })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Catalogue pages' })).toHaveCount(0);
  const first = page.locator('.product-catalogue .card').first();
  await expect(first.locator('.score-pair')).toContainText('Nutrition grade');
  await expect(first.locator('.score-pair')).toContainText('Goal Match');
  await expect(page.locator('footer')).toContainText('Informational only, not medical advice');
});

test('a product missing a few key values is listed honestly; a severely incomplete one is not listed', async ({ page }) => {
  await page.goto('/catalogue?q=label');
  await expect(cards(page)).toHaveText(['Partial Label Test']);
  const card = page.locator('.product-catalogue .card').filter({ hasText: 'Partial Label Test' });
  await expect(card.locator('.goal-meter')).toContainText('Not enough data');
  await expect(card.getByRole('img', { name: /Nutrition grade unavailable/ })).toBeVisible();
  await expect(card.locator('.score-pair-reason')).toHaveText('Not graded: Total Sugars, Saturated Fat, Sodium not stated on the label.');
});

test('chocolates are graded with EATGOOD\'s own method and say so on the card and product page', async ({ page }) => {
  await page.goto('/catalogue?q=chocolate');
  const card = page.locator('.product-catalogue .card').filter({ hasText: 'Milk Chocolate Bar Test' });
  await expect(card.getByRole('img', { name: /Nutrition grade E/ })).toBeVisible();
  await expect(card.locator('.score-pair-reason')).toHaveText("EATGOOD's own method, not an official grade");
  await card.getByRole('button', { name: /View Assessment/ }).click();
  await expect(page.locator('.grade-method-notice')).toContainText('not an official WHO or FSSAI grade');
});

test('category filter is kept in the URL across reloads', async ({ page }) => {
  await page.goto('/catalogue');
  await page.getByRole('button', { name: 'Dairy', exact: true }).click();
  await expect(page).toHaveURL(/category=Dairy/);
  await page.reload();
  await expect(page).toHaveURL(/category=Dairy/);
  await expect(cards(page)).toHaveCount(1);
  await expect(cards(page).first()).toHaveText('Plain Yogurt Test');
});

test('search trims spaces, clearing restores the list, and only a real miss shows the empty state', async ({ page }) => {
  await page.goto('/catalogue');
  const box = page.getByRole('searchbox', { name: 'Search products' });
  await box.fill('  Cheese Puffs  ');
  await expect(cards(page)).toHaveText(['Cheese Puffs Test']);
  await expect(page).toHaveURL(/q=Cheese\+Puffs$/);
  await box.fill('');
  await expect(cards(page)).toHaveCount(12);
  await box.fill('zzzznotaproduct');
  await expect(page.getByText('No matching products found')).toBeVisible();
});

test('nutrient filters wrap without overlapping and still filter', async ({ page }) => {
  await page.goto('/catalogue');
  await page.getByRole('button', { name: /Open Filters/ }).click();
  const groups = page.locator('.nutrient-filter');
  await expect(groups).toHaveCount(5);
  const boxes = await groups.evaluateAll((els) => els.flatMap((el) => [el, ...el.querySelectorAll('legend, button')])
    .map((el) => { const r = el.getBoundingClientRect(); return { group: el.closest('.nutrient-filter') === el, r: [r.left, r.top, r.right, r.bottom] }; }));
  const groupRects = boxes.filter((b) => b.group).map((b) => b.r);
  for (let i = 0; i < groupRects.length; i += 1) {
    for (let j = i + 1; j < groupRects.length; j += 1) {
      const [a, b] = [groupRects[i], groupRects[j]];
      const overlap = a[0] < b[2] - 1 && b[0] < a[2] - 1 && a[1] < b[3] - 1 && b[1] < a[3] - 1;
      expect(overlap, `filter groups ${i} and ${j} overlap`).toBe(false);
    }
  }
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(page.viewportSize().width);
  await page.locator('.nutrient-filter').filter({ hasText: 'Sodium' }).getByRole('button', { name: 'Low (≤140mg)' }).click();
  await expect(page).toHaveURL(/sodium=low/);
  await expect(cards(page)).toHaveCount(4);
  const lowSodium = await cards(page).allTextContents();
  expect(lowSodium.sort()).toEqual(['Baked Oat Crackers Test', 'Milk Chocolate Bar Test', 'Orange Drink Test', 'Plain Yogurt Test']);
});

test('allergen in the profile overrides the score on the product page', async ({ page }) => {
  await page.goto(`/product/${CHEESE_PUFFS}`);
  await expect(page.getByRole('alert').first()).toContainText('Not suitable for you: contains Milk');
  await expect(page.locator('.score-summary .goal-meter')).toContainText('Allergen conflict');
});

test('product page separates the nutrition grade from Goal Match and explains both', async ({ page }) => {
  await page.goto(`/product/${BHUJIA}`);
  const summary = page.locator('.score-summary');
  await expect(summary).toContainText('Same for everyone');
  await expect(summary).toContainText('Personal to you');
  await expect(summary.getByRole('meter', { name: 'Goal Match' })).toBeVisible();
  const explain = page.getByRole('button', { name: 'How are these scores worked out?' });
  await expect(explain).toHaveAttribute('aria-expanded', 'false');
  await explain.click();
  await expect(explain).toHaveAttribute('aria-expanded', 'true');
  await expect(page.locator('.score-explainer-calc')).toContainText(/50 − 7 × \d+ \+ 8 × \d+ = \d+ → grade [A-E]/);
});

test('additives are compact boxes that open one at a time', async ({ page }) => {
  await page.goto(`/product/${NOODLES}`);
  const toggles = page.locator('.additive-toggle');
  await expect(toggles).toHaveCount(2);
  await expect(toggles.nth(0)).toContainText('INS 627');
  await expect(toggles.nth(0)).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('Synergistic umami enhancer')).toBeHidden();
  await toggles.nth(0).click();
  await expect(toggles.nth(0)).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByText('Synergistic umami enhancer')).toBeVisible();
  await expect(toggles.nth(1)).toHaveAttribute('aria-expanded', 'false');
  await toggles.nth(1).focus();
  await page.keyboard.press('Enter');
  await expect(toggles.nth(1)).toHaveAttribute('aria-expanded', 'true');
  await toggles.nth(0).click();
  await expect(toggles.nth(0)).toHaveAttribute('aria-expanded', 'false');
  await expect(toggles.nth(1)).toHaveAttribute('aria-expanded', 'true');
});

test('entered values page keeps Edit Entered Data and no longer repeats it in the banner', async ({ page }) => {
  await page.goto('/scanner');
  await page.getByRole('button', { name: 'Manual Entry' }).click();
  await page.getByPlaceholder('e.g. Marie Gold Biscuits').fill('Home Chakli');
  await page.getByPlaceholder('e.g. 520').fill('500');
  await page.getByPlaceholder('e.g. 4.5').fill('3');
  await page.getByPlaceholder('e.g. 650').fill('600');
  await page.getByPlaceholder('e.g. 10.5').fill('6');
  await page.getByRole('button', { name: 'Generate Assessment' }).click();
  await expect(page.getByText(/Need to change your entered values/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Edit Values Now' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Edit Entered Data/ })).toBeVisible();
});

test('compare recovers from a stale product and keeps the rest of the matrix', async ({ page }) => {
  await page.goto(`/compare?ids=IND_PKG_001,${BHUJIA},${OAT_CRACKERS}`);
  const notice = page.locator('.compare-unavailable');
  await expect(notice).toContainText('IND_PKG_001');
  await expect(notice).toContainText('old built-in catalogue');
  await expect(page.locator('.compare-table thead th')).toHaveCount(3);
  await page.getByRole('button', { name: 'Remove unavailable products' }).click();
  await expect(notice).toHaveCount(0);
  await expect(page).toHaveURL(new RegExp(`/compare\\?ids=${BHUJIA},${OAT_CRACKERS}$`));
  await page.reload();
  await expect(page.locator('.compare-table thead th')).toHaveCount(3);
});

test('compare starts empty, then adding and removing products updates the matrix', async ({ page }) => {
  await page.goto('/compare');
  await expect(page.getByText('No products selected yet')).toBeVisible();
  const add = async (term, name) => {
    await page.getByRole('button', { name: 'Add Product to Compare' }).first().click();
    await page.getByPlaceholder('Search product name or brand...').fill(term);
    await page.getByRole('button', { name: new RegExp(name) }).click();
  };
  await add('bhujia', 'Masala Bhujia Test');
  await expect(page.getByText(/is selected\. Add at least one more product/)).toBeVisible();
  await add('oat', 'Baked Oat Crackers Test');
  await expect(page.locator('.compare-table thead th')).toHaveCount(3);
  await page.getByRole('button', { name: 'Remove Baked Oat Crackers Test from comparison' }).click();
  await expect(page.getByText(/Masala Bhujia Test is selected/)).toBeVisible();
});

test('profile sections collapse independently and saved items persist', async ({ page }) => {
  await page.goto('/catalogue');
  await page.locator('.product-catalogue .card').first().getByTitle(/Save Product/).click();
  await page.goto('/profile');
  await expect(page.getByText('1 saved')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Configure Profile & Activity' })).toHaveClass(/btn-primary/);
  const recent = page.getByRole('button', { name: /Recent Assessments/ });
  const saved = page.getByRole('button', { name: /Saved Items/ });
  await expect(recent).toHaveAttribute('aria-expanded', 'true');
  await recent.click();
  await expect(recent).toHaveAttribute('aria-expanded', 'false');
  await expect(saved).toHaveAttribute('aria-expanded', 'true');
  await saved.focus();
  await page.keyboard.press('Enter');
  await expect(saved).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByText('1 saved')).toBeVisible();
});

const KURKURE_RESULTS = {
  query: 'kurkure', page: 1, page_size: 24, count: 1, has_more: false,
  products: [{ barcode: '8901491101837', product_name: 'Kurkure Masala Munch', brand: 'PepsiCo',
    category: 'Snacks', measurement_basis: 'per 100g', image_url: null, nutrition_summary: { energy_kcal: 554 } }],
};

test('matching products appear while typing and open the chosen product', async ({ page }) => {
  const requests = [];
  await page.route('**/api/products/search/openfoodfacts**', (route) => {
    requests.push(new URL(route.request().url()).searchParams.get('q'));
    return route.fulfill({ json: KURKURE_RESULTS });
  });
  await page.route('**/api/**/OFF_8901491101837*', (route) => route.abort());
  await page.goto('/scanner');
  await expect(page.getByText('Upload Label (OCR)')).toHaveCount(0);
  await page.getByLabel('Product or brand name').pressSequentially('kurkure', { delay: 40 });
  await expect(page.getByRole('button', { name: /Kurkure Masala Munch/ })).toBeVisible();
  await expect(page.locator('main').getByText(/open food facts/i)).toHaveCount(0);
  await page.getByRole('button', { name: /Kurkure Masala Munch/ }).click();
  await expect(page).toHaveURL(/\/product\/OFF_8901491101837$/);
  expect(requests).toEqual(['kurkure']);
});

test('the Search button searches immediately, once', async ({ page }) => {
  const requests = [];
  await page.route('**/api/products/search/openfoodfacts**', (route) => {
    requests.push(new URL(route.request().url()).searchParams.get('q'));
    return route.fulfill({ json: KURKURE_RESULTS });
  });
  await page.goto('/scanner');
  await page.getByLabel('Product or brand name').fill('kurkure');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('button', { name: /Kurkure Masala Munch/ })).toBeVisible();
  await page.waitForTimeout(600);
  expect(requests).toEqual(['kurkure']);
});

test.describe('when the product database is busy', () => {
  test.use({ allowedFailures: ['/api/products/search/openfoodfacts'] });

  test('a failed product search is shown as an error, not as no results', async ({ page }) => {
    await page.route('**/api/products/search/openfoodfacts**', (route) => route.fulfill({
      status: 429, json: { detail: { error_code: 'OFF_RATE_LIMITED', message: 'The product database is receiving too many requests.' } },
    }));
    await page.goto('/scanner');
    await page.getByLabel('Product or brand name').fill('maggi');
    await page.getByRole('button', { name: 'Search', exact: true }).click();
    await expect(page.getByRole('alert')).toContainText('too many requests');
    await expect(page.getByText(/No products match/)).toHaveCount(0);
  });
});

test('score calculation stays hidden until its arrow is clicked', async ({ page }) => {
  await page.goto(`/product/${BHUJIA}`);
  const toggle = page.getByRole('button', { name: 'Show score calculation' });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('#score-ledger')).toHaveCount(0);
  await toggle.click();
  await expect(page.locator('#score-ledger table')).toBeVisible();
});

test('comparison highlights better values, explains the verdict and hides small differences', async ({ page }) => {
  await page.goto(`/compare?ids=${BHUJIA},${MYSTERY}`);
  await expect(page.getByRole('heading', { name: 'Verdict for your goal' })).toBeVisible();
  await expect(page.locator('.compare-verdict')).toContainText('Goal Match');
  await expect(page.getByRole('row', { name: /^Total Sugars/ }).getByText('Lowest')).toHaveCount(1);
  await expect(page.getByRole('row', { name: /^Energy/ }).getByText(/Lowest|Highest/)).toHaveCount(0);
  await expect(page.getByRole('row', { name: /^Allergen Alerts/ })).toContainText('Allergen information not stated');
  await page.getByRole('button', { name: 'Differences only' }).click();
  await expect(page.getByRole('button', { name: 'Differences only' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('row', { name: /^Energy/ })).toHaveCount(0);
  await expect(page.getByRole('row', { name: /^Allergen Alerts/ })).toBeVisible();
  await expect(page.getByText(/row.* with no meaningful difference hidden/)).toBeVisible();
});

test('comparing a food with a drink does not compare their nutrient values', async ({ page }) => {
  await page.goto(`/compare?ids=${BHUJIA},${ORANGE_DRINK}`);
  await expect(page.getByText(/different bases .* so nutrient values are not compared/)).toBeVisible();
  await expect(page.locator('.compare-table').getByText(/^(Lowest|Highest)$/)).toHaveCount(0);
});

test('assistant answers render as formatted text without markdown symbols', async ({ page }) => {
  await page.goto(`/product/${BHUJIA}`);
  await page.getByRole('button', { name: 'Is this high in sodium for blood pressure?' }).click();
  const answer = page.locator('.assistant-answer');
  await expect(answer.locator('.assistant-value').first()).toContainText('mg per 100 g');
  await expect(answer).not.toContainText('**');
  await expect(answer).toContainText('not clinical medical advice');
});

test('"Sold in India" appears only when the product data says so', async ({ page }) => {
  await page.goto('/catalogue');
  const card = (name) => page.locator('.product-catalogue .card').filter({ hasText: name });
  await expect(card('Masala Bhujia Test').getByText('Sold in India')).toBeVisible();
  await expect(card('Orange Drink Test').getByText('Sold in India')).toHaveCount(0);
  await expect(card('Mystery Snack Test').getByText('Sold in India')).toHaveCount(0);
});

test('no source or community-contribution labels appear anywhere a product is shown', async ({ page }) => {
  const forbidden = /community[\s-]contributed|^source:|data source|product database \(|user contributed/i;
  const checkMain = async () => {
    const text = await page.locator('main').innerText();
    for (const line of text.split('\n')) expect(line.trim()).not.toMatch(forbidden);
  };
  await page.goto(`/product/${BHUJIA}`);
  await expect(page.locator('.score-summary')).toBeVisible();
  await checkMain();
  await page.goto(`/product/${CHEESE_PUFFS}`);
  await expect(page.getByText('Community Ratings')).toBeVisible();  // ratings and NOVA group are kept
  await expect(page.getByText('Group 4')).toBeVisible();
  await checkMain();
  await page.goto('/catalogue');
  await expect(cards(page).first()).toBeVisible();
  await checkMain();
  await page.goto(`/compare?ids=${BHUJIA},${OAT_CRACKERS}`);
  await expect(page.locator('.compare-table')).toBeVisible();
  await checkMain();
  await page.goto('/scanner');
  await page.getByRole('button', { name: 'Barcode Lookup' }).click();
  await page.getByPlaceholder('Enter 8-13 digit barcode...').fill('2000000000015');
  await page.getByRole('button', { name: 'Lookup', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Masala Bhujia Test' })).toBeVisible();
  await checkMain();
  await page.goto('/profile');
  await expect(page.getByText(/\d+ logged/)).toBeVisible();
  await checkMain();
});
