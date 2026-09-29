import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, the dashboard runs on :5173 and forwards API + WebSocket calls to FastAPI on :8000
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
