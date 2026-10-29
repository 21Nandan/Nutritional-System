// In-browser OCR with tesseract.js. The photo never leaves the device: only the
// recognised text is sent to the server for parsing. All OCR assets (worker, WebAssembly
// core, English model) are served from this site under /ocr/, copied there at build time
// by scripts/copy-ocr-assets.mjs, so no third-party CDN is contacted.

const ASSET_BASE = '/ocr/v7';
const MAX_FILE_BYTES = 15 * 1024 * 1024;
const MAX_DIMENSION = 2400;
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export class OcrError extends Error {}

// Large phone photos make OCR slow without improving accuracy; scale the longest side down.
async function prepareImage(file) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
  if (scale === 1) {
    bitmap.close();
    return file;
  }
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new OcrError('Could not process this image.'))), 'image/png');
  });
}

export function validateImageFile(file) {
  if (!file) throw new OcrError('Choose a photo of the nutrition label first.');
  if (!ACCEPTED_TYPES.includes(file.type)) throw new OcrError('Please choose a JPEG, PNG or WebP photo.');
  if (file.size > MAX_FILE_BYTES) throw new OcrError('That photo is larger than 15 MB. Please choose a smaller one.');
}

// onProgress receives a number from 0 to 1 and a short status label.
export async function recognizeLabel(file, onProgress = () => {}) {
  validateImageFile(file);
  let image;
  try {
    image = await prepareImage(file);
  } catch (err) {
    throw err instanceof OcrError ? err : new OcrError('This file could not be opened as an image.');
  }

  let worker;
  try {
    // Loaded on demand so the main bundle stays small for visitors who never scan.
    const { createWorker, OEM } = await import('tesseract.js');
    worker = await createWorker('eng', OEM.LSTM_ONLY, {
      workerPath: `${ASSET_BASE}/worker.min.js`,
      corePath: `${ASSET_BASE}/core`,
      langPath: `${ASSET_BASE}/lang`,
      workerBlobURL: false,
      logger: (m) => {
        if (m.status === 'recognizing text') onProgress(m.progress, 'Reading the label…');
        else if (m.status && m.status.startsWith('loading')) onProgress(0, 'Loading the text reader (first time only)…');
      },
    });
  } catch {
    throw new OcrError('The text reader could not start in this browser. Please enter the values manually.');
  }

  try {
    const { data } = await worker.recognize(image);
    return { text: data.text || '', confidence: Math.max(0, Math.min(1, (data.confidence || 0) / 100)), engine: 'tesseract.js 7 (in browser)' };
  } catch {
    throw new OcrError('The text reader failed on this photo. Try a sharper, well-lit photo, or enter the values manually.');
  } finally {
    await worker.terminate();
  }
}
