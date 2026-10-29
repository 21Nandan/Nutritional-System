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

test('label photo is read in the browser and fills the form', async ({ page }) => {
  const label = await page.context().newPage();
  await label.setContent(`<div id="l" style="font:28px Arial;padding:30px;background:#fff;width:640px;line-height:1.6">
    <b>NUTRITION INFORMATION</b><br>Per 100g<br>Energy 520 kcal<br>Protein 7.2 g<br>Carbohydrate 61.5 g<br>
    Total Sugars 4.1 g<br>Total Fat 27.0 g<br>Saturated Fat 11.8 g<br>Sodium 690 mg</div>`);
  const png = await label.locator('#l').screenshot();
  await label.close();

  const uploads = [];
  page.on('request', (r) => { if (r.method() === 'POST') uploads.push(r.url()); });
  await page.goto('/scanner');
  await page.locator('input[type=file]').first().setInputFiles({ name: 'label.png', mimeType: 'image/png', buffer: png });
  await expect(page.locator('form input[value="520"]')).toHaveCount(1, { timeout: 60_000 });
  await expect(page.locator('form input[value="690"]')).toHaveCount(1);
  expect(uploads.every((u) => u.endsWith('/api/analyze/label-text'))).toBe(true);
});
