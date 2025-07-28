import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8501,
    host: '0.0.0.0',  // Allow external connections
    hmr: {
      host: '194.165.140.77',  // Use external IP for HMR
      port: 8501
    }
  }
})
