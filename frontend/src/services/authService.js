const API = import.meta.env.VITE_API_URL || 'http://localhost:5001';

export async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    });
  } catch {
    const error = new Error(`Could not reach the LibSphere API at ${API}. Check that the backend is running and that CORS allows this frontend origin.`);
    error.isNetworkError = true;
    throw error;
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.detail || payload.error?.message || `API request failed with status ${response.status}.`);
    error.status = response.status;
    throw error;
  }
  return payload;
}

export async function login(credentials) {
  const payload = await apiRequest('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
  return payload.data ?? payload;
}

export async function getCurrentUser(token) {
  const payload = await apiRequest('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  });
  return payload.data ?? payload;
}

export { API };
