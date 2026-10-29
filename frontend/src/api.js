// EATGOOD API client.
// Every request carries the visitor's profile (kept only in this browser) so the server
// can personalise the result without storing anything. Failures are thrown as ApiError
// with a plain-language message; callers must show them, never treat them as "no results".

import { loadProfile } from './storage';

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'NETWORK_ERROR', detail = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

const GENERIC_MESSAGES = {
  0: "We couldn't reach the EATGOOD server. Check your internet connection and try again.",
  429: 'Too many requests right now. Please wait a minute and try again.',
  500: 'Something went wrong on our side. Please try again.',
  502: 'A service we depend on is not responding. Please try again later.',
  503: 'The service is starting up or temporarily unavailable. Please try again shortly.',
  504: 'The request took too long. Please try again.',
};

function profileHeader() {
  const profile = loadProfile();
  if (!profile) return {};
  // Only what the server needs to personalise a result. Name, age and activity stay on the device.
  const { goal, dietary_preference, allergens_to_avoid } = profile;
  return {
    'X-Eatgood-Profile': encodeURIComponent(JSON.stringify({ goal, dietary_preference, allergens_to_avoid })),
  };
}

function messageFromDetail(detail, status) {
  if (detail && typeof detail === 'object' && !Array.isArray(detail) && detail.message) return detail.message;
  if (Array.isArray(detail)) return 'Some of the values you entered are not valid. Please check them and try again.';
  return GENERIC_MESSAGES[status] || GENERIC_MESSAGES[500];
}

export async function apiFetch(path, { method = 'GET', body, signal } = {}) {
  const headers = { ...profileHeader() };
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError(GENERIC_MESSAGES[0]);
  }

  let data = null;
  const isJson = (response.headers.get('content-type') || '').includes('application/json');
  if (isJson) {
    try {
      data = await response.json();
    } catch {
      throw new ApiError(GENERIC_MESSAGES[502], { status: response.status, code: 'BAD_RESPONSE' });
    }
  }

  if (!response.ok) {
    const detail = data?.detail ?? null;
    throw new ApiError(messageFromDetail(detail, response.status), {
      status: response.status,
      code: (detail && detail.error_code) || `HTTP_${response.status}`,
      detail,
    });
  }
  if (!isJson) {
    throw new ApiError(GENERIC_MESSAGES[502], { status: response.status, code: 'BAD_RESPONSE' });
  }
  return data;
}
