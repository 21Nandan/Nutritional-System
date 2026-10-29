import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
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
          if (id.includes('node_modules/lucide-react/')) return 'icons';
          return undefined;
        }
      }
    },
    chunkSizeWarningLimit: 600
  }
});
