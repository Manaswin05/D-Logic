import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Proxy API calls to Flask backend during local development
    proxy: {
      '/simulation_data': 'http://localhost:5000',
      '/simulation_control': 'http://localhost:5000',
      '/agent_details': 'http://localhost:5000',
      '/add_agent': 'http://localhost:5000',
      '/remove_agent': 'http://localhost:5000',
      '/video_feed': 'http://localhost:5000',
      '/traffic_status': 'http://localhost:5000',
      '/algorithms_info': 'http://localhost:5000'
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
