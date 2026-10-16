import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { getLibrarianUsers } from '../../services/api';

const ROLES = ['STUDENT', 'FACULTY', 'DEPARTMENT', 'LIBRARIAN', 'ADMIN'];
const ROLE_LABELS = { STUDENT: 'Student', FACULTY: 'Faculty', DEPARTMENT: 'Department', LIBRARIAN: 'Librarian', ADMIN: 'Admin' };

export default function LibrarianUsers({ token, initialSearch = '' }) {
  const [searchInput, setSearchInput] = useState(initialSearch);
  const [search, setSearch] = useState(initialSearch.trim());
  const [role, setRole] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [accountStatus, setAccountStatus] = useState('');
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState('name');
  const [direction, setDirection] = useState('asc');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    setSearchInput(initialSearch);
    setSearch(initialSearch.trim());
    setPage(1);
  }, [initialSearch]);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError('');
    getLibrarianUsers({
      q: search, role, department_id: departmentId, account_status: accountStatus,
      page, per_page: 20, sort, direction,
    }).then(payload => {
      if (current) setResult(payload.data || null);
    }).catch(requestError => {
      if (current) setError(requestError.message || 'Unable to load user records.');
    }).finally(() => {
      if (current) setLoading(false);
    });
    return () => { current = false; };
  }, [token, search, role, departmentId, accountStatus, page, sort, direction, retryCount]);

  const pagination = result?.pagination || { page, per_page: 20, total: 0, pages: 0 };
  const summary = result?.summary || { total_accounts: 0, enabled_accounts: 0, disabled_accounts: 0, by_role: {} };
  const pages = Math.max(1, pagination.pages || 0);

  function changeFilter(setter, value) {
    setter(value);
    setPage(1);
  }

  function changeSort(field) {
    if (sort === field) setDirection(value => value === 'asc' ? 'desc' : 'asc');
    else { setSort(field); setDirection('asc'); }
    setPage(1);
  }

  function clearFilters() {
    setSearchInput(''); setSearch(''); setRole(''); setDepartmentId(''); setAccountStatus(''); setPage(1);
  }

  function sortableHeader(label, field) {
    const ariaSort = sort !== field ? 'none' : direction === 'asc' ? 'ascending' : 'descending';
    return <th aria-sort={ariaSort}><button type="button" className="user-sort" onClick={() => changeSort(field)}>{label}{sort === field ? (direction === 'asc' ? ' ↑' : ' ↓') : ''}</button></th>;
  }

  return (
    <div className="librarian-users">
      <div className="users-summary" aria-label="Account totals">
        <div><b>{summary.total_accounts}</b><span>Total accounts</span></div>
        <div><b>{summary.enabled_accounts}</b><span>Enabled accounts</span></div>
        <div><b>{summary.disabled_accounts}</b><span>Disabled accounts</span></div>
        {ROLES.filter(item => ['STUDENT', 'FACULTY'].includes(item)).map(item => (
          <div key={item}><b>{summary.by_role?.[item]?.enabled ?? 0}</b><span>Enabled {ROLE_LABELS[item].toLowerCase()} accounts</span></div>
        ))}
      </div>
      <p className="prototype-muted user-status-note">Enabled/Disabled reflects the account status stored in the database, not online presence or borrowing activity.</p>
      <div className="users-toolbar" role="search" aria-label="Filter users">
        <label className="users-search"><Search size={16} aria-hidden="true" /><span className="sr-only">Search name or user ID</span><input value={searchInput} onChange={event => changeFilter(setSearchInput, event.target.value)} placeholder="Search name or user ID" /></label>
        <label><span className="sr-only">Filter by role</span><select value={role} onChange={event => changeFilter(setRole, event.target.value)}><option value="">All roles</option>{ROLES.map(item => <option key={item} value={item}>{ROLE_LABELS[item]}</option>)}</select></label>
        <label><span className="sr-only">Filter by department</span><select value={departmentId} onChange={event => changeFilter(setDepartmentId, event.target.value)}><option value="">All departments</option>{(result?.departments || []).map(department => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
        <label><span className="sr-only">Filter by account status</span><select value={accountStatus} onChange={event => changeFilter(setAccountStatus, event.target.value)}><option value="">All account statuses</option><option value="enabled">Enabled</option><option value="disabled">Disabled</option></select></label>
        <button type="button" className="users-clear" onClick={clearFilters}>Clear filters</button>
      </div>
      {error && <div className="notice error" role="alert">{error}<button type="button" onClick={() => setRetryCount(value => value + 1)}>Retry</button></div>}
      <div className="users-table-wrap" aria-busy={loading}>
        <table className="prototype-table users-table">
          <thead><tr>{sortableHeader('Name', 'name')}{sortableHeader('User ID', 'user_id')}{sortableHeader('Role', 'role')}{sortableHeader('Department', 'department')}{sortableHeader('Account status', 'status')}</tr></thead>
          <tbody>
            {result?.items?.map(account => (
              <tr key={`${account.role}:${account.user_id || account.name}`}>
                <td><b>{account.name}</b></td>
                <td>{account.user_id || '—'}</td>
                <td>{ROLE_LABELS[account.role] || account.role}</td>
                <td>{account.department?.name || '—'}</td>
                <td><span className={`account-status ${account.is_active ? 'enabled' : 'disabled'}`}>{account.is_active ? 'Enabled' : 'Disabled'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && !result && <p className="prototype-muted" role="status">Loading user records…</p>}
        {!loading && !error && result?.items?.length === 0 && <p className="prototype-muted" role="status">No accounts match these filters.</p>}
        {!loading && error && !result && <p className="prototype-muted">User records could not be loaded. Retry to try again.</p>}
      </div>
      <div className="users-pagination">
        <span>{loading ? 'Updating…' : `${pagination.total} account${pagination.total === 1 ? '' : 's'}`}</span>
        <div>
          <button type="button" onClick={() => setPage(value => Math.max(1, value - 1))} disabled={loading || page <= 1}>Previous</button>
          <span aria-live="polite">Page {page} of {pages}</span>
          <button type="button" onClick={() => setPage(value => Math.min(pages, value + 1))} disabled={loading || page >= pages}>Next</button>
        </div>
      </div>
    </div>
  );
}
