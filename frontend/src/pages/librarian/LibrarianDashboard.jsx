import { useEffect, useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, BookOpen, LayoutDashboard, Lightbulb, LogOut, Users } from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import { useAuth } from '../../context/AuthContext';
import { getLibrarianDashboard } from '../../services/reportService';
import { getLibrarianLoanRequests, reviewLoanRequest, issueApprovedLoan } from '../../services/api';
import LibrarianUsers from './LibrarianUsers';
import LibrarianWorkflows from './LibrarianWorkflows';


export default function LibrarianDashboard() {
  const { user, token, signOut } = useAuth();
  const [page, setPage] = useState('dashboard');
  const [userSearch, setUserSearch] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [dashboardError, setDashboardError] = useState('');
  const [loanRequests, setLoanRequests] = useState([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState('');
  const [queueActionId, setQueueActionId] = useState('');
  const [queueMessage, setQueueMessage] = useState('');
  useEffect(() => {
    if (!token) return undefined;
    let active = true;
    getLibrarianDashboard(token)
      .then(data => { if (active) setDashboard(data); })
      .catch(error => { if (active) setDashboardError(error.message || 'Unable to load library analytics.'); });
    getLibrarianLoanRequests()
      .then(result => { if (active) { setLoanRequests(result.data || []); setQueueError(''); } })
      .catch(error => { if (active) setQueueError(error.message || 'Unable to load borrowing requests.'); })
      .finally(() => { if (active) setQueueLoading(false); });
    return () => { active = false; };
  }, [token]);
  const summary = dashboard?.summary;
  const formatCount = value => value == null ? '—' : new Intl.NumberFormat('en-IN').format(value);
  async function refreshDashboard() {
    try { const result = await getLibrarianDashboard(token); setDashboard(result); setDashboardError(''); }
    catch (error) { setDashboardError(error.message || 'Unable to load library analytics.'); }
  }
  async function refreshQueue() {
    setQueueLoading(true);
    setQueueError('');
    try {
      const result = await getLibrarianLoanRequests();
      setLoanRequests(result.data || []);
    } catch (error) {
      setQueueError(error.message || 'Unable to load borrowing requests.');
    } finally {
      setQueueLoading(false);
    }
  }
  async function handleReview(loanId, decision) {
    setQueueActionId(loanId);
    setQueueMessage('');
    setQueueError('');
    try {
      await reviewLoanRequest(loanId, decision);
      setQueueMessage(`Request ${decision.toLowerCase()}.`);
      await refreshQueue();
    } catch (error) {
      setQueueError(error.message || 'Unable to update request.');
    } finally {
      setQueueActionId('');
    }
  }
  async function handleIssue(loanId) {
    setQueueActionId(loanId);
    setQueueMessage('');
    setQueueError('');
    try {
      await issueApprovedLoan(loanId);
      setQueueMessage('Book issued successfully.');
      await refreshQueue();
    } catch (error) {
      setQueueError(error.message || 'Unable to issue this book.');
    } finally {
      setQueueActionId('');
    }
  }
  const nav = [['dashboard', LayoutDashboard, 'Dashboard'], ['catalogue', BookOpen, 'Manage Catalogue'], ['issue', ArrowUpFromLine, 'Borrowing Requests'], ['return', ArrowDownToLine, 'Return Books'], ['suggestions', Lightbulb, 'Suggestions'], ['users', Users, 'Users']];
  const navItems = nav.map(([id, icon, label]) => ({ id, icon, label }));
  const pageTitle = { dashboard: 'Librarian Dashboard', catalogue: 'Manage Catalogue', issue: 'Borrowing Requests', return: 'Return Books', suggestions: 'Suggestions', users: 'User Management' }[page] || 'Librarian Dashboard';
  return (
    <DashboardLayout user={user} role="LIBRARIAN" title={pageTitle} subtitle="Library control center" navItems={navItems} activeItem={page} onNavigate={setPage} onLogout={signOut} onOpenUsers={value => { setUserSearch(value || ''); setPage('users'); }}>
    <div className="prototype-shell librarian-shell">
      <aside className="prototype-sidebar librarian-sidebar">
        <div className="prototype-brand"><b>MITRC <span>LibSphere</span></b>
          <small>Library Management</small>
        </div>
        {nav.map(([key, Icon, label]) =>
          <button key={key} className={`prototype-nav ${page === key ? 'active' : ''}`} onClick={() => setPage(key)}>
            <Icon size={17} />
            {label}
          </button>)}
        <div className="prototype-divider" />
        <button className="prototype-nav" onClick={signOut}>
          <LogOut size={17} />Logout
        </button>
        <div className="prototype-user">
          <div className="prototype-avatar">{(user?.name || 'L')[0]}</div>
          <div><b>{user?.name || 'Librarian'}</b>
            <small>LIBRARIAN · MITRC Alwar</small>
          </div>
        </div>
      </aside>
      <main className="prototype-main">
        <header className="prototype-header">
          <div>
            <b>{page === 'dashboard' ? 'Librarian Dashboard' : page === 'catalogue' ? 'Manage Catalogue' : page === 'issue' ? 'Borrowing Requests' : page === 'return' ? 'Return Books' : page === 'suggestions' ? 'Acquisition Demand' : 'Users'}</b>
            <small>Library control center</small>
          </div>
          <span>
            {new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}
          </span>
        </header>
        <section className="prototype-content">{page === 'dashboard' && <>
          <h1>Library Control Center</h1>
          <p className="prototype-muted">{dashboardError || (dashboard?.meta?.source ? `Live figures from ${dashboard.meta.source}.` : 'Loading library analytics from the API…')}</p>
          <div className="prototype-stats six">
            <Stat value={formatCount(summary?.total_books)} label="Total Books" onActivate={() => setPage('catalogue')} />
            <Stat value={formatCount(summary?.total_copies)} label="Total Copies" onActivate={() => setPage('catalogue')} />
            <Stat value={formatCount(summary?.available_copies)} label="Available" onActivate={() => setPage('catalogue')} />
            <Stat value={formatCount(summary?.borrowed_copies)} label="Borrowed" onActivate={() => setPage('return')} />
            <Stat value={formatCount(summary?.overdue_loans)} label="Overdue" onActivate={() => setPage('return')} />
            <Stat value={formatCount(summary?.suggestion_votes)} label="Suggestion Votes" onActivate={() => setPage('suggestions')} />
          </div>
          <Panel title="Available actions">
            <div className="prototype-action-grid">
              <button type="button" onClick={() => setPage('issue')}><ArrowUpFromLine size={16} />Borrowing Requests</button>
              <button type="button" onClick={() => setPage('users')}><Users size={16} />Manage Users</button>
            </div>
            <p className="prototype-muted">Catalogue management, returns, and librarian suggestion review are unavailable until their API workflows are implemented.</p>
          </Panel>
        </>
        }
          {page === 'catalogue' && <LibrarianWorkflows page="catalogue" onChanged={refreshDashboard} />}

          {page === 'issue' &&
            <RequestQueue requests={loanRequests} loading={queueLoading} error={queueError} message={queueMessage} actionId={queueActionId} onRefresh={refreshQueue} onReview={handleReview} onIssue={handleIssue} />
          }
          {page === 'return' && <LibrarianWorkflows page="return" onChanged={refreshDashboard} />}
          {page === 'suggestions' && <LibrarianWorkflows page="suggestions" onChanged={refreshDashboard} />}
          {page === 'users' &&
            <Panel title="User Management">
              <LibrarianUsers token={token} initialSearch={userSearch} />
            </Panel>}
        </section>
      </main>
    </div>
    </DashboardLayout>
  );
}
function Stat({ value, label, onActivate }) {
  return (
    <button type="button" className="prototype-stat" onClick={onActivate} aria-label={`${label}: ${value}. Open details`}>
      <b>{value}</b>
      <small>{label}</small>
    </button>);
}
function Panel({ title, children }) {
  return (
    <section className="prototype-panel">
      <div className="prototype-panel-head">
        <b>{title}</b>
      </div>
      <div className="prototype-panel-body">
        {children}
      </div>
    </section>);
}
function RequestQueue({ requests, loading, error, message, actionId, onRefresh, onReview, onIssue }) {
  return (
    <Panel title="Borrowing Requests">
      <div className="prototype-page-title">
        <p className="prototype-muted">Review incoming student/faculty requests; approved copies remain reserved until issued.</p>
        <button type="button" onClick={onRefresh} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button>
      </div>
      {message && <div className="notice success" role="status">{message}</div>}
      {error && <div className="notice error" role="alert">{error} <button type="button" onClick={onRefresh}>Retry</button></div>}
      {loading && requests.length === 0 && <p className="prototype-muted">Loading requests…</p>}
      {!loading && !error && requests.length === 0 && <p className="prototype-muted">No pending borrowing requests.</p>}
      {requests.map(request => (
        <article className="prototype-book-row" key={request.id}>
          <div>
            <b>{request.book_title}</b>
            <small>{request.book_author} · {request.requester_name} ({request.requester_role}) · {request.requester_id}</small>
            <small>Submitted {request.request_submitted_at ? new Date(request.request_submitted_at).toLocaleString() : '—'}</small>
          </div>
          <span className={`loan-status loan-status-${request.status.toLowerCase()}`}>{request.status}</span>
          {request.status === 'REQUESTED' && <div className="loan-actions">
            <button type="button" disabled={actionId === request.id} onClick={() => onReview(request.id, 'APPROVED')}>Approve</button>
            <button type="button" disabled={actionId === request.id} onClick={() => onReview(request.id, 'REJECTED')}>Reject</button>
          </div>}
          {request.status === 'APPROVED' && <button type="button" disabled={actionId === request.id} onClick={() => onIssue(request.id)}>{actionId === request.id ? 'Issuing…' : 'Issue book'}</button>}
        </article>
      ))}
    </Panel>
  );
}
