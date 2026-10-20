import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  build: { rollupOptions: { output: { manualChunks(id) {
    if (id.includes('/node_modules/recharts/') || id.includes('/node_modules/d3-')) return 'charts'
    if (id.includes('/node_modules/leaflet/') || id.includes('/node_modules/react-leaflet/') || id.includes('/node_modules/@react-leaflet/')) return 'map'
  } } } },
  test: { environment: 'jsdom', setupFiles: ['./tests/setup.tsx'], exclude: ['e2e/**', 'node_modules/**'], css: true },
})
