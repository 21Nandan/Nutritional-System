// Reads the text on a photo of a pack, in the visitor's own browser: the photo is never uploaded.
// The worker, engine and English data come from this site (/ocr/, see vite.config.js).

let workerPromise = null;
let progressListener = null;

function getWorker() {
  if (!workerPromise) {
    workerPromise = import('tesseract.js').then(({ createWorker }) =>
      createWorker('eng', 1, {
        workerPath: '/ocr/worker.min.js',
        corePath: '/ocr/tesseract-core-lstm.wasm.js',
        langPath: '/ocr',
        workerBlobURL: false,
        logger: (m) => {
          if (progressListener && typeof m.progress === 'number') progressListener(m.status, m.progress);
        },
      }),
    );
    workerPromise.catch(() => { workerPromise = null; });
  }
  return workerPromise;
}

// onProgress(status, 0..1) is called while the engine loads and while it reads.
export async function readTextFromImage(image, onProgress) {
  progressListener = onProgress || null;
  try {
    const worker = await getWorker();
    const { data } = await worker.recognize(image);
    return data.text || '';
  } finally {
    progressListener = null;
  }
}

// Words that front-of-pack claims are made of; lines without any of them are other pack text.
const CLAIM_WORDS = /\b(protein|fib(re|er)|sugar|fat|sodium|salt|gluten|preservatives?|organic|natural|whole\s?(grain|wheat)|multi\s?grain|millets?|vitamins?|calcium|iron|cholesterol|msg|colou?rs?|flavou?rs?|baked|added|free|rich|high|low|zero|lite|light|healthy|energy|immunity|digest\w*|heart)\b|\d+\s?%/i;

// The lines of recognised text that look like claims, tidied, without duplicates.
export function claimsFromText(text) {
  const seen = new Set();
  const out = [];
  for (const raw of String(text || '').split(/[\n•|·]+/)) {
    const line = raw.replace(/[^\w%+&'\-\s.]/g, ' ').replace(/\s+/g, ' ').trim();
    const letters = (line.match(/[a-z]/gi) || []).length;
    if (line.length < 3 || line.length > 60 || letters < line.length * 0.5) continue;
    if (!CLAIM_WORDS.test(line)) continue;
    const key = line.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(line);
  }
  return out.slice(0, 12);
}
