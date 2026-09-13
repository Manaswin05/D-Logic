import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    // Proxy API calls to Flask backend during local development
    proxy: {
      '/simulation_data': 'http://127.0.0.1:5000',
      '/simulation_control': 'http://127.0.0.1:5000',
      '/agent_details': 'http://127.0.0.1:5000',
      '/add_agent': 'http://127.0.0.1:5000',
      '/remove_agent': 'http://127.0.0.1:5000',
      '/video_feed': 'http://127.0.0.1:5000',
      '/traffic_status': 'http://127.0.0.1:5000',
      '/algorithms_info': 'http://127.0.0.1:5000'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
