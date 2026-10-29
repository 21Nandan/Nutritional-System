// Post-deploy smoke test: BASE_URL=https://eatgood26.vercel.app npx playwright test e2e/smoke.spec.js --project=desktop
import { test, expect } from '@playwright/test';

test('deployment is healthy, ready and serving the catalogue', async ({ request }) => {
  const health = await request.get('/api/health');
  expect(health.status()).toBe(200);
  const ready = await request.get('/api/ready');
  expect(ready.status(), await ready.text()).toBe(200);
  const products = await (await request.get('/api/products?limit=30')).json();
  expect(products.products.length, 'the catalogue returns products from Open Food Facts').toBeGreaterThan(0);
  expect(products.products[0]).toHaveProperty('general_grade');
  const withImage = products.products.find((p) => p.image_small_url || p.image_url);
  expect(withImage, 'at least one product has an image').toBeTruthy();
  const image = await request.get(withImage.image_small_url || withImage.image_url);
  expect(image.status()).toBe(200);
  const cadbury = await (await request.get('/api/products?query=cadbury%20da')).json();
  expect(cadbury.products.some((p) => /dairy milk/i.test(p.product_name)), 'partial search finds Dairy Milk').toBe(true);
  const search = await request.get('/api/products/search/openfoodfacts?q=maggi');
  expect(search.status(), await search.text()).toBe(200);
  expect((await search.json()).products.length).toBeGreaterThan(0);
});
