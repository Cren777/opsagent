import { clearStoredToken, getStoredToken } from './authToken'
import { createAuthenticatedFetch } from './authFetchCore'

export const authFetch = createAuthenticatedFetch({
  request: window.fetch.bind(window),
  getToken: getStoredToken,
  clearToken: clearStoredToken,
  redirectToLogin: () => {
    if (window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
  },
})
