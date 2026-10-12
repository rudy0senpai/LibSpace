import { apiRequest } from './authService';

async function fetchWithAuth(url, options = {}) {
  let token = localStorage.getItem('access_token');
  if (!token) {
    try {
      token = JSON.parse(localStorage.getItem('libsphere_session') || 'null')?.access_token || null;
    } catch {
      token = null;
    }
  }
  return apiRequest(url, {
    ...options,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
}

export async function searchBooks(params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''));
  return fetchWithAuth(`/api/books/search?${query}`);
}

export async function getMyLoans() {
  return fetchWithAuth('/api/users/me/loans');
}

export async function getMySuggestions() {
  return fetchWithAuth('/api/users/me/suggestions');
}

export async function createSuggestion(data) {
  return fetchWithAuth('/api/suggestions', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function voteSuggestion(suggestionId) {
  return fetchWithAuth(`/api/suggestions/${suggestionId}/vote`, {
    method: 'POST',
  });
}

export async function getCategories() {
  return fetchWithAuth('/api/categories');
}

export async function getMe() {
  return fetchWithAuth('/api/auth/me');
}
