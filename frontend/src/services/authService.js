const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function login(email, password) {
  const response = await fetch(`${API}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || 'Login failed');
  return payload;
}

export { API };
