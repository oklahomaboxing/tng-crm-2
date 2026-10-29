import { useEffect, useState } from 'react';
import { API, authHeaders } from '../services/api';
export default function useOperationsOverview(enabled = true) {
  const [data, setData] = useState(null), [error, setError] = useState(''), [loading, setLoading] = useState(enabled), [version, setVersion] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    setLoading(true); setError('');
    (async () => { try {
      const response = await fetch(`${API}/api/operations/overview`, { headers: authHeaders(), signal: controller.signal });
      const result = await response.json();
      if (!response.ok) throw new Error(response.status === 401 ? 'Your session expired. Sign in again.' : typeof result.detail === 'string' ? result.detail : 'Operations data could not be loaded.');
      if (!controller.signal.aborted) setData(result);
    } catch (err) { if (!controller.signal.aborted) setError(err.message); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    })();
    return () => controller.abort();
  }, [enabled, version]);
  return { data, error, loading, refresh: () => setVersion(v => v + 1) };
}
