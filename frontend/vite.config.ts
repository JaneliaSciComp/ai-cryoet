import { tanstackStart } from '@tanstack/react-start/plugin/vite'
import { defineConfig, loadEnv } from 'vite'
import viteReact from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.API_PROXY_TARGET || 'http://localhost:8000'
  // SSR-side fetches read process.env.CRYOET_API_BASE_URL; mirror API_PROXY_TARGET into it
  // so a single .env.local var configures both the browser proxy and the SSR base URL.
  process.env.CRYOET_API_BASE_URL ??= apiTarget
  return {
    server: {
      port: Number(env.FRONTEND_PORT) || 3000,
      host: true,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
        },
      },
    },
    ssr: {
      noExternal: ['@mui/*'],
    },
    resolve: {
      tsconfigPaths: true,
    },
    plugins: [tanstackStart(), viteReact()],
  }
})
