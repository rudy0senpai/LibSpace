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

export async function lookupBookCover(bookId, { refresh = false, failed = false } = {}) {
  const params = new URLSearchParams();
  if (refresh) params.set('refresh', '1');
  if (failed) params.set('failed', '1');
  const query = params.toString();
  const suffix = query ? `?${query}` : '';
  return fetchWithAuth(`/api/books/${encodeURIComponent(bookId)}/cover${suffix}`);
}

export async function getMyLoans() {
  return fetchWithAuth('/api/users/me/loans');
}

export async function requestBook(bookId) {
  return fetchWithAuth('/api/users/me/loans/requests', {
    method: 'POST',
    body: JSON.stringify({ book_id: bookId }),
  });
}

export async function cancelMyLoan(loanId) {
  return fetchWithAuth(`/api/users/me/loans/${loanId}/cancel`, { method: 'POST' });
}

export async function getLibrarianLoanRequests() {
  return fetchWithAuth('/api/librarian/loan-requests');
}

export async function getLibrarianUsers(params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''));
  return fetchWithAuth(`/api/librarian/users?${query}`);
}

export async function reviewLoanRequest(loanId, decision) {
  return fetchWithAuth(`/api/librarian/loan-requests/${loanId}/review`, {
    method: 'POST', body: JSON.stringify({ decision }),
  });
}

export async function issueApprovedLoan(loanId) {
  return fetchWithAuth(`/api/librarian/loan-requests/${loanId}/issue`, { method: 'POST' });
}

export async function getLibrarianCatalogue(params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''));
  return fetchWithAuth(`/api/librarian/catalogue?${query}`);
}

export async function createCatalogueBook(data) {
  return fetchWithAuth('/api/librarian/catalogue', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateCatalogueBook(id, data) {
  return fetchWithAuth(`/api/librarian/catalogue/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function getCatalogueAvailability(id) {
  return fetchWithAuth(`/api/librarian/catalogue/${encodeURIComponent(id)}/availability`);
}

export async function updateCatalogueAvailability(id, data) {
  return fetchWithAuth(`/api/librarian/catalogue/${encodeURIComponent(id)}/availability`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function addCatalogueCopy(id, data) {
  return fetchWithAuth(`/api/librarian/catalogue/${encodeURIComponent(id)}/copies`, { method: 'POST', body: JSON.stringify(data) });
}

export async function getLibrarianLoans(params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''));
  return fetchWithAuth(`/api/librarian/loans?${query}`);
}

export async function returnLibrarianLoan(id) {
  return fetchWithAuth(`/api/librarian/loans/${encodeURIComponent(id)}/return`, { method: 'POST' });
}

export async function getLibrarianSuggestions(params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''));
  return fetchWithAuth(`/api/librarian/suggestions?${query}`);
}

export async function reviewLibrarianSuggestion(id, status) {
  return fetchWithAuth(`/api/librarian/suggestions/${encodeURIComponent(id)}/review`, { method: 'POST', body: JSON.stringify({ status }) });
}

export async function getMyNotifications() {
  return fetchWithAuth('/api/users/me/notifications');
}

export async function markMyNotificationRead(id) {
  return fetchWithAuth(`/api/users/me/notifications/${encodeURIComponent(id)}/read`, { method: 'POST' });
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
  return fetchWithAuth(`/api/suggestions/${encodeURIComponent(suggestionId)}/vote`, {
    method: 'POST',
  });
}

export async function getCategories() {
  return fetchWithAuth('/api/categories');
}

export async function getMe() {
  return fetchWithAuth('/api/auth/me');
}
