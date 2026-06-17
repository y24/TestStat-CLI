import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  const appBase = env.VITE_APP_BASE_PATH || '/'
  const apiBasePath = (env.VITE_API_BASE_PATH || '').replace(/\/$/, '')
  const backendUrl = env.VITE_BACKEND_URL || env.VITE_API_BASE_URL || 'http://localhost:18000'
  const proxy = apiBasePath
    ? {
        [`${apiBasePath}/api`]: {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (path: string) => path.replace(`${apiBasePath}/api`, '/api'),
        },
        [`${apiBasePath}/health`]: {
          target: backendUrl,
          changeOrigin: true,
          rewrite: () => '/health',
        },
      }
    : {
        '/api': { target: backendUrl, changeOrigin: true },
        '/health': { target: backendUrl, changeOrigin: true },
      }

  return {
    base: appBase,
    plugins: [react()],
    server: {
      port: 5173,
      proxy,
    },
  }
})
