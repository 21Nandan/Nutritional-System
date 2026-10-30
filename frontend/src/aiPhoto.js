// Photos read on the server. Shrunk in the browser first (smaller upload, fewer tokens on a limited
// free tier). Returns null when server reading isn't available, so the caller uses its own fallback.
import { apiFetch } from './api';

const MAX_SIDE = 1280;

// Whether the server's reading and explaining help is on, asked once per page load and shared.
let availability = null;
export function assistAvailable() {
  if (!availability) {
    availability = apiFetch('/api/ai/status').then((d) => Boolean(d.available)).catch(() => false);
  }
  return availability;
}

async function shrink(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close?.();
  const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
  return dataUrl.slice(dataUrl.indexOf(',') + 1);
}

// endpoint: 'read-label' or 'read-claims'.
export async function readPhotoWithAi(endpoint, file) {
  let image;
  try {
    image = await shrink(file);
  } catch {
    return null;
  }
  try {
    return await apiFetch(`/api/ai/${endpoint}`, { method: 'POST', body: { image, mime_type: 'image/jpeg' } });
  } catch {
    return null; // unavailable, rate limited or failed: the caller falls back
  }
}
