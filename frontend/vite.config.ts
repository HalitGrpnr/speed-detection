import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// https://vite.dev/config/
// Build çıktısı backend'in servis ettiği klasöre üretilir (src/ui/web) →
// FastAPI bunu "/"'te servis eder, PyInstaller paketine girer.
// Dev'de /api istekleri uvicorn'a (127.0.0.1:8000) proxy'lenir; HMR çalışır.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    outDir: '../src/ui/web',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
