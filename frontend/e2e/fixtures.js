import { test as base, expect } from '@playwright/test';

// Every test starts with onboarding completed and a known profile in localStorage,
// and fails if the page logs an error or a same-origin request fails.
export const test = base.extend({
  profile: [{ goal: 'Reduce Sugar', dietary_preference: 'No preference', allergens_to_avoid: 'Milk' }, { option: true }],
  // URL fragments a test expects to fail on purpose (for example a mocked upstream error).
  allowedFailures: [[], { option: true }],
  page: async ({ page, profile, baseURL, allowedFailures }, use) => {
    const problems = [];
    page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
    page.on('console', (m) => {
      // Product photos come from Open Food Facts; their availability is outside this app.
      if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) problems.push(`console: ${m.text()}`);
    });
    page.on('response', (r) => {
      const allowed = allowedFailures.some((fragment) => r.url().includes(fragment));
      if (r.url().startsWith(baseURL) && r.status() >= 400 && !r.url().includes('/_vercel/') && !allowed) {
        problems.push(`${r.status()} ${r.url()}`);
      }
    });
    await page.addInitScript((p) => {
      localStorage.setItem('eatgood_onboarding_completed', 'true');
      localStorage.setItem('eatgood_user_profile', JSON.stringify(p));
    }, profile);
    await use(page);
    expect(problems, 'page errors or failed requests').toEqual([]);
  },
});

export { expect };
