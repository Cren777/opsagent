export interface AuthenticatedFetchDependencies {
  request: typeof fetch
  getToken: () => string | null
  clearToken: () => void
  redirectToLogin: () => void
}

export function createAuthenticatedFetch({
  request,
  getToken,
  clearToken,
  redirectToLogin,
}: AuthenticatedFetchDependencies): typeof fetch {
  return async (input, init = {}) => {
    const headers = new Headers(init.headers)
    const token = getToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    const response = await request(input, { ...init, headers })
    if (response.status === 401) {
      clearToken()
      redirectToLogin()
    }
    return response
  }
}
