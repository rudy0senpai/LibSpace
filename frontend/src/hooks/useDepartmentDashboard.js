import { useCallback, useEffect, useMemo, useState } from 'react';
import { getDepartmentDashboard } from '../services/reportService';

export function useDepartmentDashboard(token, params) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const key = useMemo(() => JSON.stringify(params || {}), [params]);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try { setData(await getDepartmentDashboard(token, params)); }
    catch (err) { setError(err.message || 'Unable to load dashboard'); }
    finally { setLoading(false); }
  }, [token, key]);

  useEffect(() => { load(); }, [load]);
  return { data, loading, error, reload: load };
}
