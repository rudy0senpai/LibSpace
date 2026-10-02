import { API } from './authService';

export async function getDepartmentDashboard(token, params = {}) {
  const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''));
  const response = await fetch(`${API}/api/reports/department/dashboard?${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || 'Unable to load department analytics');
  return payload;
}
