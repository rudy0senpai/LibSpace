import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getDepartmentDashboard } from '../services/reportService';

export function useDepartmentDashboard(token, params) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const key = useMemo(() => JSON.stringify(params || {}), [params]);
  const requestSequence = useRef(0);

  const load = useCallback(async () => {
    if (!token) return;
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError('');
    try {
      const result = await getDepartmentDashboard(token, params);
      if (sequence === requestSequence.current) setData(result);
    } catch (err) {
      if (sequence === requestSequence.current) setError(err.message || 'Unable to load dashboard');
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
