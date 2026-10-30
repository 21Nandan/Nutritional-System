import fs from 'node:fs';
import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Text recognition for pack photos runs in the visitor's browser (src/ocr.js). Its worker, engine and
// English data are served by the site itself under /ocr/, since the site's security policy allows
// only its own scripts and connections. Non-SIMD engine so older phones work too.
const OCR_FILES = {
  'worker.min.js': 'node_modules/tesseract.js/dist/worker.min.js',
  'tesseract-core-lstm.wasm.js': 'node_modules/tesseract.js-core/tesseract-core-lstm.wasm.js',
  'eng.traineddata.gz': 'node_modules/@tesseract.js-data/eng/4.0.0_best_int/eng.traineddata.gz',
};

function ocrAssets() {
  return {
    name: 'ocr-assets',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const name = req.url?.match(/^\/ocr\/([^?]+)/)?.[1];
        const source = name && OCR_FILES[name];
        if (!source) return next();
        res.setHeader('Content-Type', name.endsWith('.gz') ? 'application/octet-stream' : 'text/javascript');
        fs.createReadStream(path.resolve(source)).pipe(res);
      });
    },
    generateBundle() {
      for (const [name, source] of Object.entries(OCR_FILES)) {
        this.emitFile({ type: 'asset', fileName: `ocr/${name}`, source: fs.readFileSync(path.resolve(source)) });
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), ocrAssets()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        // Split large libraries into their own long-cached chunks.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'vendor';
          if (id.includes('node_modules/@zxing/')) return 'zxing';
          if (id.includes('node_modules/tesseract.js')) return 'ocr';
          if (id.includes('node_modules/lucide-react/')) return 'icons';
          return undefined;
        }
      }
    },
    chunkSizeWarningLimit: 600
  }
});
