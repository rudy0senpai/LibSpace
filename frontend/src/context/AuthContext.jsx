import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { login as apiLogin } from '../services/authService';

const STORAGE_KEY = 'libsphere_session';
const AuthContext = createContext(null);

function readSession() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); }
  catch { return null; }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession);
  const signIn = useCallback(async (email, password) => {
    const next = await apiLogin(email, password);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    localStorage.setItem('libsphere_user', JSON.stringify(next.user));
    setSession(next);
    return next;
  }, []);
  const signOut = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem('libsphere_user');
    setSession(null);
    window.location.hash = '#/login';
  }, []);
  const value = useMemo(() => ({ session, user: session?.user || null, token: session?.access_token || null, signIn, signOut }), [session, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
