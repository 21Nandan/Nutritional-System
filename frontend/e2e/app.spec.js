import { test, expect } from './fixtures';

test('catalogue loads 30 products with categories and real pagination', async ({ page }) => {
  await page.goto('/catalogue');
  await expect(page.locator('.product-catalogue .card h3')).toHaveCount(30);
  await expect(page.getByRole('button', { name: 'Snacks', exact: true })).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Catalogue pages' })).toContainText('Page 1 of');
  await expect(page.locator('footer')).toContainText('Informational only, not medical advice');
});

test('category filter is kept in the URL across reloads', async ({ page }) => {
  await page.goto('/catalogue');
  await page.getByRole('button', { name: 'Dairy', exact: true }).click();
  await expect(page).toHaveURL(/category=Dairy/);
  await page.reload();
  await expect(page).toHaveURL(/category=Dairy/);
  await expect(page.getByRole('navigation', { name: 'Catalogue pages' })).toContainText('40 products');
  await expect(page.locator('.product-catalogue .card').first()).toContainText('Dairy');
});

test('search finds products and shows a genuine empty state', async ({ page }) => {
  await page.goto('/catalogue?q=maggi');
  await expect(page.locator('.product-catalogue .card h3').first()).toContainText('Maggi');
  await page.goto('/catalogue?q=zzzznotaproduct');
  await expect(page.getByText('No matching products found')).toBeVisible();
});

test('allergen in the profile overrides the score on the product page', async ({ page }) => {
  await page.goto('/product/IND_PKG_041');
  await expect(page.getByRole('alert').first()).toContainText('Not suitable for you: contains Milk');
});

test('compare shows both products', async ({ page }) => {
  await page.goto('/compare?ids=IND_PKG_001,IND_PKG_002');
  await expect(page.locator('table thead th')).toHaveCount(3);
});

test('profile page lists saved products from this device', async ({ page }) => {
  await page.goto('/catalogue');
  await page.locator('.product-catalogue .card').first().getByTitle(/Save Product/).click();
  await page.goto('/profile');
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
  await page.route('**/api/products/OFF_8901491101837', (route) => route.abort());
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
  await page.goto('/product/IND_PKG_001');
  const toggle = page.getByRole('button', { name: 'Show score calculation' });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('#score-ledger')).toHaveCount(0);
  await toggle.click();
  await expect(page.locator('#score-ledger table')).toBeVisible();
});

test('comparison highlights better values, explains the verdict and hides small differences', async ({ page }) => {
  await page.goto('/compare?ids=IND_PKG_001,IND_PKG_002,IND_PKG_005');
  await expect(page.getByRole('heading', { name: 'Verdict for your goal' })).toBeVisible();
  await expect(page.locator('.compare-verdict')).toContainText('Goal Match');
  const sodium = page.getByRole('row', { name: /^Sodium/ });
  await expect(sodium.getByText('Lowest')).toHaveCount(1);
  await expect(page.getByRole('row', { name: /^Energy/ }).getByText(/Lowest|Highest/)).toHaveCount(0);
  await page.getByRole('button', { name: 'Differences only' }).click();
  await expect(page.getByRole('button', { name: 'Differences only' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('row', { name: /^Energy/ })).toHaveCount(0);
  await expect(page.getByRole('row', { name: /^Allergen Alerts/ })).toBeVisible();
  await expect(page.getByText(/row.* with no meaningful difference hidden/)).toBeVisible();
});

test('comparing a food with a drink does not compare their nutrient values', async ({ page }) => {
  await page.goto('/compare?ids=IND_PKG_001,IND_PKG_381');
  await expect(page.getByText(/different bases .* so nutrient values are not compared/)).toBeVisible();
  await expect(page.locator('.compare-table').getByText(/^(Lowest|Highest)$/)).toHaveCount(0);
});

test('assistant answers render as formatted text without markdown symbols', async ({ page }) => {
  await page.goto('/product/IND_PKG_001');
  await page.getByRole('button', { name: 'Is this high in sodium for blood pressure?' }).click();
  const answer = page.locator('.assistant-answer');
  await expect(answer.locator('.assistant-value').first()).toContainText('mg per 100 g');
  await expect(answer).not.toContainText('**');
  await expect(answer).toContainText('not clinical medical advice');
});
