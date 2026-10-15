import { useEffect, useMemo, useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, BookOpen, LayoutDashboard, Lightbulb, LogOut, Plus, Search, Users } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { getLibrarianDashboard } from '../../services/reportService';
import { getLibrarianLoanRequests, reviewLoanRequest, issueApprovedLoan } from '../../services/api';
import LibrarianUsers from './LibrarianUsers';

const booksSeed = [
  { id: 'BK-001', title: 'Clean Code', author: 'Robert C. Martin', copies: 5 },
  { id: 'BK-002', title: 'Deep Learning', author: 'Ian Goodfellow', copies: 2 },
  { id: 'BK-003', title: 'Computer Networks', author: 'Andrew S. Tanenbaum', copies: 7 },
  { id: 'BK-004', title: 'Database System Concepts', author: 'Abraham Silberschatz', copies: 6 },
];

export default function LibrarianDashboard() {
  const { user, token, signOut } = useAuth();
  const [page, setPage] = useState('dashboard');
  const [query, setQuery] = useState('');
  const [books, setBooks] = useState(booksSeed);
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
  const filtered = useMemo(() => books.filter(book => `${book.id} ${book.title} ${book.author}`.toLowerCase().includes(query.toLowerCase())), [books, query]);
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
  return (
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
            <Stat value={formatCount(summary?.total_books)} label="Total Books" />
            <Stat value={formatCount(summary?.total_copies)} label="Total Copies" />
            <Stat value={formatCount(summary?.available_copies)} label="Available" />
            <Stat value={formatCount(summary?.borrowed_copies)} label="Borrowed" />
            <Stat value={formatCount(summary?.overdue_loans)} label="Overdue" />
            <Stat value={formatCount(summary?.suggestion_votes)} label="Suggestion Votes" />
          </div>
          <Panel title="Quick Actions">
            <div className="prototype-action-grid">
              <button onClick={() => setPage('catalogue')}>
                <Plus size={16} />Add Book
              </button>
              <button onClick={() => setPage('catalogue')}>
                <Plus size={16} />Add Copy
              </button>
              <button onClick={() => setPage('issue')}>
                <ArrowUpFromLine size={16} />Issue Book
              </button>
              <button onClick={() => setPage('return')}>
                <ArrowDownToLine size={16} />Return Book
              </button>
              <button onClick={() => setPage('users')}>
                <Users size={16} />Manage Users
              </button>
              <button onClick={() => setPage('suggestions')}>
                <Lightbulb size={16} />Suggestions
              </button>
            </div>
          </Panel>
        </>
        }
          {page === 'catalogue' && <>
            <div className="prototype-page-title">
              <h1>Manage Catalogue</h1>
              <button className="prototype-primary" onClick={() => setBooks(current => [...current, { id: `BK-${String(current.length + 1).padStart(3, '0')}`, title: 'New Catalogue Record', author: 'Pending metadata', copies: 0 }])}>
                <Plus size={16} /> Add Book
              </button>
            </div>
            <Panel title="Catalogue">
              <div className="prototype-search">
                <Search size={17} /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search books, authors, ISBN…" />
              </div>
              <table className="prototype-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Author</th>
                    <th>Copies</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>{filtered.map(book =>
                  <tr key={book.id}>
                    <td>{book.id}</td>
                    <td><b>{book.title}</b></td>
                    <td>{book.author}</td>
                    <td>{book.copies}</td>
                    <td>
                      <button onClick={() => setBooks(current => current.filter(x => x.id !== book.id))}>Remove</button>
                    </td>
                  </tr>
                )}</tbody>
              </table>
            </Panel>
          </>}
          {page === 'issue' &&
            <RequestQueue requests={loanRequests} loading={queueLoading} error={queueError} message={queueMessage} actionId={queueActionId} onRefresh={refreshQueue} onReview={handleReview} onIssue={handleIssue} />
          }
          {page === 'return' &&
            <FormPanel title="Return Book" label="Book ID / Accession Number" button="Return Book" />
          }
          {page === 'suggestions' &&
            <Panel title="Acquisition Demand">
              <div className="prototype-suggestion-row">
                <span>Artificial Intelligence: A Modern Approach</span>
                <b>15 votes</b>
              </div>
              <div className="prototype-suggestion-row">
                <span>Hands-On Machine Learning</span>
                <b>12 votes</b>
              </div>
              <div className="prototype-suggestion-row">
                <span>Clean Code</span>
                <b>10 votes</b>
              </div>
            </Panel>}
          {page === 'users' &&
            <Panel title="User Management">
              <LibrarianUsers token={token} />
            </Panel>}
        </section>
      </main>
    </div>);
}
function Stat({ value, label }) {
  return (
    <div className="prototype-stat">
      <b>{value}</b>
      <small>{label}</small>
    </div>);
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

function FormPanel({ title, label, second, button }) {
  return (
    <Panel title={title}>
      <div className="prototype-form">
        <label>
          {label}
          <input />
        </label>
        {second &&
          <label>
            {second}
            <input />
          </label>
        }
        <button className="prototype-primary">{button}</button>
      </div>
    </Panel>);
}
