import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getDepartmentDashboard } from '../services/reportService';
import { normalizeDepartmentDashboardResponse } from '../components/department/departmentDashboardData';

export function useDepartmentDashboard(token, params) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const key = useMemo(() => JSON.stringify(params || {}), [params]);
  const requestSequence = useRef(0);

  const load = useCallback(async () => {
    if (!token) {
      setError('Your session is missing or expired. Sign in again to load department analytics.');
      setLoading(false);
      setData(null);
      return;
    }
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError('');
    try {
      const result = await getDepartmentDashboard(token, params);
      if (sequence === requestSequence.current) setData(normalizeDepartmentDashboardResponse(result));
    } catch (err) {
      if (sequence === requestSequence.current) {
        if (err?.isNetworkError) setError('Department analytics are temporarily unreachable. Check your connection and retry.');
        else if (err?.status === 401 || err?.status === 403) setError('Your session is no longer authorized to view this department data. Sign in again, then retry.');
        else if (err?.status >= 500) setError('Department analytics are temporarily unavailable. Please retry.');
        else setError(err?.message || 'Unable to load department analytics. Please retry.');
      }
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  }, [token, key]);

  useEffect(() => {
    load();
    return () => { requestSequence.current += 1; };
  }, [load]);
  return { data, loading, error, reload: load };
}
