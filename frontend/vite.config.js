import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  define: {
    // expose env vars to the app
    __WS_SERVER__: JSON.stringify(process.env.VITE_DEFAULT_SERVER_IP || 'localhost:8765'),
  },
})
