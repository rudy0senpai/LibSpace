import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getCurrentUser, login as apiLogin } from '../services/authService';
import { isPortalRole, normalizePortalRole } from '../services/roleRoutes';

const STORAGE_KEY = 'libsphere_session';
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);
  const [restoreError, setRestoreError] = useState('');

  useEffect(() => {
    let active = true;
    async function restoreSession() {
      try {
        const cached = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
        if (!cached?.access_token) throw new Error('No saved authentication session');
        const user = await getCurrentUser(cached.access_token);
        const normalizedUser = { ...user, role: normalizePortalRole(user?.role) };
        if (!normalizedUser?.id || !isPortalRole(normalizedUser.role)) {
          throw new Error('Unsupported or invalid user session');
        }
        if (active) setSession({ access_token: cached.access_token, user: normalizedUser });
      } catch (error) {
        if (error?.isNetworkError || error?.status >= 500) {
          if (active) setRestoreError(error.message);
        } else {
          localStorage.removeItem(STORAGE_KEY);
          localStorage.removeItem('libsphere_user');
        }
      } finally {
        if (active) setReady(true);
      }
    }
    restoreSession();
    return () => { active = false; };
  }, []);

  const signIn = useCallback(async (credentials) => {
    const next = await apiLogin(credentials);
    if (!next?.access_token || !next?.user) {
      throw new Error('The backend returned an invalid authentication response.');
    }
    const normalizedUser = { ...next.user, role: normalizePortalRole(next.user.role) };
    if (!isPortalRole(normalizedUser.role)) {
      throw new Error('This account is not permitted to use the public portal.');
    }
    const normalizedSession = { ...next, user: normalizedUser };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizedSession));
    setSession(normalizedSession);
    setRestoreError('');
    return normalizedSession;
  }, []);
  const signOut = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem('libsphere_user');
    setSession(null);
    window.location.hash = '#/login';
  }, []);
  const value = useMemo(() => ({ session, user: session?.user || null, token: session?.access_token || null, ready, restoreError, signIn, signOut }), [session, ready, restoreError, signIn, signOut]);
  return (
  <AuthContext.Provider value={value}>{children}</AuthContext.Provider>);
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
