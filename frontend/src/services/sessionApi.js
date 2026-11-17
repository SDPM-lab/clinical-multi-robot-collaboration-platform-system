export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
let csrfToken = null
let csrfRequest = null

export class ApiError extends Error {
  constructor(code, status = 0) { super(code); this.code = code; this.status = status }
}

export const resetCsrf = () => { csrfToken = null; csrfRequest = null }

async function rawFetch(url, options) {
  try { return await fetch(url, { ...options, credentials: 'include' }) }
  catch { throw new ApiError('connection_error') }
}

async function csrf() {
  if (csrfToken) return csrfToken
  if (!csrfRequest) csrfRequest = (async () => {
    const response = await rawFetch(`${apiBaseUrl}/api/auth/csrf`)
    if (!response.ok) throw new ApiError('server_error', response.status)
    const body = await response.json()
    if (!body.token) throw new ApiError('server_error')
    return csrfToken = body.token
  })().finally(() => { csrfRequest = null })
  return csrfRequest
}

// 所有會改動伺服器資料的 Cookie 請求都附上防偽權杖。
export async function sessionFetch(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = new Headers(options.headers)
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) headers.set('X-CSRF-TOKEN', await csrf())
  const response = await rawFetch(url, { ...options, headers })
  if (response.status === 401 && !url.endsWith('/api/auth/login')) {
    resetCsrf()
    window.dispatchEvent(new Event('auth:expired'))
  }
  return response
}

export async function authRequest(path, options = {}) {
  const response = await sessionFetch(`${apiBaseUrl}/api/auth${path}`, options)
  if (!response.ok) {
    let body = {}
    try { body = await response.json() } catch { /* Empty HTTP errors are mapped by status. */ }
    throw new ApiError(body.code || (response.status === 400 ? 'invalid_input' : response.status === 401 ? 'session_expired' : 'server_error'), response.status)
  }
  return response.status === 204 ? null : response.json()
}

export const jsonOptions = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
export const developmentLogin = () => authRequest('/dev-login', jsonOptions('POST', {}))
