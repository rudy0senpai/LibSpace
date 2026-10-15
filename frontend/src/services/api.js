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

export async function reviewLoanRequest(loanId, decision) {
  return fetchWithAuth(`/api/librarian/loan-requests/${loanId}/review`, {
    method: 'POST', body: JSON.stringify({ decision }),
  });
}

export async function issueApprovedLoan(loanId) {
  return fetchWithAuth(`/api/librarian/loan-requests/${loanId}/issue`, { method: 'POST' });
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
