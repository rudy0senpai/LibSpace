import { apiRequest } from './authService';

export async function getDepartmentDashboard(token, params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''));
  const payload = await apiRequest(`/api/reports/department/dashboard?${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return payload.data ?? payload;
}

export async function getLibrarianDashboard(token, params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''));
  const url = query.toString() ? `/api/reports/librarian/dashboard?${query}` : '/api/reports/librarian/dashboard';
  const payload = await apiRequest(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return payload.data ?? payload;
}
