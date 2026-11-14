import { apiBaseUrl } from './config'

export class ApiClientError extends Error {
  readonly status: number
  readonly detail?: unknown

  constructor(message: string, status: number, detail?: unknown) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.detail = detail
  }
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

function joinUrl(baseUrl: string, path: string): string {
  const normalizedPath = path.replace(/^\/+/, '')
  return `${baseUrl}/${normalizedPath}`
}

function isJsonResponse(response: Response): boolean {
  return response.headers.get('content-type')?.includes('application/json') ?? false
}

/**
 * Small fetch wrapper reserved for the agreed FastAPI contract. It makes no
 * request until a feature explicitly invokes `request`.
 */
export class ApiClient {
  private readonly baseUrl: string
  private readonly fetchImplementation: typeof fetch

  constructor(baseUrl = apiBaseUrl, fetchImplementation: typeof fetch = fetch) {
    this.baseUrl = baseUrl
    this.fetchImplementation = fetchImplementation
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { body, headers, ...init } = options
    const requestHeaders = new Headers(headers)

    if (body !== undefined && !requestHeaders.has('content-type')) {
      requestHeaders.set('content-type', 'application/json')
    }

    if (!requestHeaders.has('accept')) {
      requestHeaders.set('accept', 'application/json')
    }

    // Native browser fetch must not receive the ApiClient instance as `this`.
    const fetchRequest = this.fetchImplementation
    const response = await fetchRequest(joinUrl(this.baseUrl, path), {
      ...init,
      headers: requestHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    })

    const payload: unknown = isJsonResponse(response) ? await response.json() : undefined

    if (!response.ok) {
      const message =
        typeof payload === 'object' && payload !== null && 'detail' in payload
          ? String(payload.detail)
          : `Request failed with status ${response.status}`

      throw new ApiClientError(message, response.status, payload)
    }

    return payload as T
  }
}

export function isApiClientError(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError
}
