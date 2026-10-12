import { API } from './authService';

async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };
  const response = await fetch(`${API}${url}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.error?.message || 'Request failed');
  return payload;
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
