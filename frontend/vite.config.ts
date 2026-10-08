import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    // The browser only ever talks to this origin; the backend is the one that calls the upstream.
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: { environment: 'node' },
})
