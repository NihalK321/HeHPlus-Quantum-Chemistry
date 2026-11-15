import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const directory = fileURLToPath(new URL('.', import.meta.url))

/**
 * The public directory deliberately points to the challenge's verified exports.
 * Vite copies those files into `dist` for a standalone static build, without
 * importing or depending on the main PepperQ frontend.
 */
export default defineConfig({
  plugins: [react()],
  publicDir: fileURLToPath(new URL('../artifacts', import.meta.url)),
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    fs: {
      allow: [directory, fileURLToPath(new URL('..', import.meta.url))],
    },
  },
})
