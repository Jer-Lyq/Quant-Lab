const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export async function apiRequest(path, options = {}) {
  const { token = '', headers = {}, ...fetchOptions } = options
  const response = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers
    }
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.message || data.error || '请求失败')
  }
  return data
}
