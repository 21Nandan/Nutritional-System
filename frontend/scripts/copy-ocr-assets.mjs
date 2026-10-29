// Copies the tesseract.js worker, WebAssembly cores and English model from node_modules
// into public/ocr/v7 so the app serves them itself (no CDN). Runs before dev and build.
import { cpSync, mkdirSync, readdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = join(root, 'public', 'ocr', 'v7');

const tesseractDir = dirname(require.resolve('tesseract.js/package.json'));
const coreDir = dirname(require.resolve('tesseract.js-core/package.json'));
const langDir = join(dirname(require.resolve('@tesseract.js-data/eng/package.json')), '4.0.0_best_int');

rmSync(join(root, 'public', 'ocr'), { recursive: true, force: true });
mkdirSync(join(out, 'core'), { recursive: true });
mkdirSync(join(out, 'lang'), { recursive: true });

cpSync(join(tesseractDir, 'dist', 'worker.min.js'), join(out, 'worker.min.js'));
const cores = readdirSync(coreDir).filter((f) => f.endsWith('lstm.wasm.js'));
if (cores.length === 0) throw new Error(`No LSTM cores found in ${coreDir}`);
for (const f of cores) cpSync(join(coreDir, f), join(out, 'core', f));
cpSync(join(langDir, 'eng.traineddata.gz'), join(out, 'lang', 'eng.traineddata.gz'));

console.log(`OCR assets copied to public/ocr/v7 (${cores.length} cores, English model).`);
