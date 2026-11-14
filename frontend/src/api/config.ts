const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()

/**
 * A relative default keeps the UI deployable behind a reverse proxy. The
 * backend URL is intentionally environment-configured rather than hard-coded.
 */
export const apiBaseUrl = (configuredBaseUrl || '/api/v1').replace(/\/+$/, '')
