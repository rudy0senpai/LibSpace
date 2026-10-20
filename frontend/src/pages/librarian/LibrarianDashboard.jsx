import { useEffect, useState, useCallback } from 'react';
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  BookOpen,
  Calendar,
  CheckCircle2,
  Clock,
  Filter,
  Layers,
  LayoutDashboard,
  Lightbulb,
  LogOut,
  RefreshCw,
  Search,
  Users,
} from 'lucide-react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import { useAuth } from '../../context/AuthContext';
import { getLibrarianDashboard } from '../../services/reportService';
import { getLibrarianLoanRequests, reviewLoanRequest, issueApprovedLoan } from '../../services/api';
import LibrarianUsers from './LibrarianUsers';
import LibrarianWorkflows from './LibrarianWorkflows';
import {
  LibrarianBorrowingTrendChart,
  LibrarianCopyStatusChart,
  LibrarianTopBorrowedChart,
  LibrarianSuggestionStatusChart,
  LibrarianOverdueList,
  LibrarianTopSuggestionsList,
} from '../../components/librarian/LibrarianCharts';

const defaultDateRange = () => {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 180);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
};

export default function LibrarianDashboard() {
  const { user, token, signOut } = useAuth();
  const [page, setPage] = useState('dashboard');
  const [userSearch, setUserSearch] = useState('');
  const [dashboard, setDashboard] = useState(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState('');
  const [dateRange, setDateRange] = useState(defaultDateRange);
  const [activePreset, setActivePreset] = useState('180d');

  const [loanRequests, setLoanRequests] = useState([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState('');
  const [queueActionId, setQueueActionId] = useState('');
  const [queueMessage, setQueueMessage] = useState('');

  const loadDashboardData = useCallback(async (startVal, endVal) => {
    if (!token) return;
    setDashboardLoading(true);
    setDashboardError('');
    try {
      const params = {};
      if (startVal) params.start_date = startVal;
      if (endVal) params.end_date = endVal;
      const data = await getLibrarianDashboard(token, params);
      setDashboard(data);
    } catch (err) {
      setDashboardError(err.message || 'Unable to load library analytics.');
    } finally {
      setDashboardLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadDashboardData(dateRange.start, dateRange.end);
  }, [loadDashboardData, dateRange.start, dateRange.end]);

  const refreshQueue = useCallback(async () => {
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
  }, []);

  useEffect(() => {
    if (!token) return;
    refreshQueue();
  }, [token, refreshQueue]);

  const summary = dashboard?.summary;
  const formatCount = value => (value == null ? '—' : new Intl.NumberFormat('en-IN').format(value));

  function applyPreset(days, label) {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - days);
    const newStart = start.toISOString().slice(0, 10);
    const newEnd = end.toISOString().slice(0, 10);
    setDateRange({ start: newStart, end: newEnd });
    setActivePreset(label);
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

  const nav = [
    ['dashboard', LayoutDashboard, 'Dashboard'],
    ['catalogue', BookOpen, 'Manage Catalogue'],
    ['issue', ArrowUpFromLine, 'Borrowing Requests'],
    ['return', ArrowDownToLine, 'Return Books'],
    ['suggestions', Lightbulb, 'Suggestions'],
    ['users', Users, 'Users'],
  ];
  const navItems = nav.map(([id, icon, label]) => ({ id, icon, label }));
  const pageTitle =
    {
      dashboard: 'Librarian Dashboard',
      catalogue: 'Manage Catalogue',
      issue: 'Borrowing Requests',
      return: 'Return Books',
      suggestions: 'Suggestions',
      users: 'User Management',
    }[page] || 'Librarian Dashboard';

  return (
    <DashboardLayout
      user={user}
      role="LIBRARIAN"
      title={pageTitle}
      subtitle="Central library administration and live analytics"
      navItems={navItems}
      activeItem={page}
      onNavigate={setPage}
      onLogout={signOut}
      onOpenUsers={value => {
        setUserSearch(value || '');
        setPage('users');
      }}
    >
      <div className="prototype-shell librarian-shell">
        <aside className="prototype-sidebar librarian-sidebar">
          <div className="prototype-brand">
            <b>
              MITRC <span>LibSphere</span>
            </b>
            <small>Library Administration</small>
          </div>
          {nav.map(([key, Icon, label]) => (
            <button
              key={key}
              className={`prototype-nav ${page === key ? 'active' : ''}`}
              onClick={() => setPage(key)}
            >
              <Icon size={17} />
              {label}
            </button>
          ))}
          <div className="prototype-divider" />
          <button className="prototype-nav" onClick={signOut}>
            <LogOut size={17} />Logout
          </button>
          <div className="prototype-user">
            <div className="prototype-avatar">{(user?.name || 'L')[0]}</div>
            <div>
              <b>{user?.name || 'Librarian'}</b>
              <small>LIBRARIAN · MITRC</small>
            </div>
          </div>
        </aside>

        <main className="prototype-main">
          <header className="prototype-header">
            <div>
              <b>{pageTitle}</b>
              <small>Live circulation & catalogue management</small>
            </div>
            <span>{new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}</span>
          </header>

          <section className="prototype-content">
            {page === 'dashboard' && (
              <>
                <div className="librarian-dashboard-header-row">
                  <div>
                    <h1 className="librarian-page-title">Library Control Center</h1>
                    <p className="prototype-muted">
                      {dashboardError ||
                        (dashboard?.meta?.source
                          ? `Live database analytics from ${dashboard.meta.source}. Range: ${dashboard.meta.start_date} to ${dashboard.meta.end_date}.`
                          : 'Loading library metrics from the database…')}
                    </p>
                  </div>

                  <div className="librarian-date-filter-box" aria-label="Dashboard activity date range">
                    <div className="librarian-preset-buttons">
                      <button
                        type="button"
                        className={`preset-btn ${activePreset === '30d' ? 'active' : ''}`}
                        onClick={() => applyPreset(30, '30d')}
                      >
                        30D
                      </button>
                      <button
                        type="button"
                        className={`preset-btn ${activePreset === '90d' ? 'active' : ''}`}
                        onClick={() => applyPreset(90, '90d')}
                      >
                        90D
                      </button>
                      <button
                        type="button"
                        className={`preset-btn ${activePreset === '180d' ? 'active' : ''}`}
                        onClick={() => applyPreset(180, '180d')}
                      >
                        6M
                      </button>
                      <button
                        type="button"
                        className={`preset-btn ${activePreset === '365d' ? 'active' : ''}`}
                        onClick={() => applyPreset(365, '365d')}
                      >
                        1Y
                      </button>
                    </div>

                    <div className="librarian-custom-dates">
                      <input
                        type="date"
                        aria-label="Start date"
                        value={dateRange.start}
                        onChange={e => {
                          setDateRange(prev => ({ ...prev, start: e.target.value }));
                          setActivePreset('custom');
                        }}
                      />
                      <span>to</span>
                      <input
                        type="date"
                        aria-label="End date"
                        value={dateRange.end}
                        onChange={e => {
                          setDateRange(prev => ({ ...prev, end: e.target.value }));
                          setActivePreset('custom');
                        }}
                      />
                      <button
                        type="button"
                        className="refresh-btn"
                        disabled={dashboardLoading}
                        onClick={() => loadDashboardData(dateRange.start, dateRange.end)}
                        title="Reload metrics"
                      >
                        <RefreshCw size={14} className={dashboardLoading ? 'spin' : ''} />
                      </button>
                    </div>
                  </div>
                </div>

                {dashboardError && (
                  <div className="notice error" role="alert">
                    {dashboardError}
                    <button
                      type="button"
                      onClick={() => loadDashboardData(dateRange.start, dateRange.end)}
                    >
                      Retry
                    </button>
                  </div>
                )}

                {/* KPI Summary Cards */}
                <div className="prototype-stats seven-stats" aria-label="Library key performance indicators">
                  <Stat
                    value={formatCount(summary?.total_books)}
                    label="Distinct Titles"
                    sub="Catalogue records"
                    tone="blue"
                    onActivate={() => setPage('catalogue')}
                  />
                  <Stat
                    value={formatCount(summary?.total_copies)}
                    label="Physical Copies"
                    sub="Total inventory"
                    tone="teal"
                    onActivate={() => setPage('catalogue')}
                  />
                  <Stat
                    value={formatCount(summary?.available_copies)}
                    label="Available Copies"
                    sub="On shelves"
                    tone="green"
                    onActivate={() => setPage('catalogue')}
                  />
                  <Stat
                    value={formatCount(summary?.borrowed_copies)}
                    label="Currently Borrowed"
                    sub="In circulation"
                    tone="amber"
                    onActivate={() => setPage('return')}
                  />
                  <Stat
                    value={formatCount(summary?.overdue_loans)}
                    label="Overdue Loans"
                    sub="Require action"
                    tone="red"
                    highlight={Number(summary?.overdue_loans) > 0}
                    onActivate={() => setPage('return')}
                  />
                  <Stat
                    value={formatCount(summary?.pending_borrowing_requests)}
                    label="Borrow Requests"
                    sub="Awaiting review"
                    tone="purple"
                    onActivate={() => setPage('issue')}
                  />
                  <Stat
                    value={formatCount(summary?.pending_suggestions)}
                    label="Pending Suggestions"
                    sub="Under review"
                    tone="orange"
                    onActivate={() => setPage('suggestions')}
                  />
                </div>

                {/* Row 1: Borrowing Activity Trend + Copy Status Distribution */}
                <div className="librarian-dashboard-grid two-one">
                  <Panel title={`Borrowing Activity Over Time (${dashboard?.meta?.bucket || 'monthly'} view)`}>
                    <LibrarianBorrowingTrendChart data={dashboard?.borrowing_trend || []} />
                  </Panel>
                  <Panel title="Physical Copy Status Distribution">
                    <LibrarianCopyStatusChart data={dashboard?.copy_status_distribution || []} />
                  </Panel>
                </div>

                {/* Row 2: Most Borrowed Books + Overdue Loans Attention List */}
                <div className="librarian-dashboard-grid one-one">
                  <Panel title="Most Borrowed Titles">
                    <LibrarianTopBorrowedChart data={dashboard?.top_borrowed_books || []} />
                  </Panel>
                  <Panel
                    title={`Overdue Loans Requiring Attention (${formatCount(summary?.overdue_loans)})`}
                    headerAction={
                      <button
                        type="button"
                        className="panel-header-btn"
                        onClick={() => setPage('return')}
                      >
                        All returns
                      </button>
                    }
                  >
                    <LibrarianOverdueList
                      loans={dashboard?.overdue_loans || []}
                      onGoToReturn={() => setPage('return')}
                    />
                  </Panel>
                </div>

                {/* Row 3: Suggestion Analytics (Statuses & Most Voted) */}
                <div className="librarian-dashboard-grid one-one">
                  <Panel title="Acquisition Suggestions by Review Status">
                    <LibrarianSuggestionStatusChart data={dashboard?.suggestion_status_distribution || []} />
                  </Panel>
                  <Panel
                    title="Most Voted Book Suggestions"
                    headerAction={
                      <button
                        type="button"
                        className="panel-header-btn"
                        onClick={() => setPage('suggestions')}
                      >
                        All suggestions
                      </button>
                    }
                  >
                    <LibrarianTopSuggestionsList
                      suggestions={dashboard?.top_suggestions || []}
                      onGoToSuggestions={() => setPage('suggestions')}
                    />
                  </Panel>
                </div>

                {/* Quick Navigation Panel */}
                <Panel title="Quick Management Workflows">
                  <div className="prototype-action-grid">
                    <button type="button" onClick={() => setPage('catalogue')}>
                      <BookOpen size={16} /> Manage Catalogue
                    </button>
                    <button type="button" onClick={() => setPage('issue')}>
                      <ArrowUpFromLine size={16} /> Borrowing Requests ({loanRequests.length})
                    </button>
                    <button type="button" onClick={() => setPage('return')}>
                      <ArrowDownToLine size={16} /> Return Books & Overdues
                    </button>
                    <button type="button" onClick={() => setPage('suggestions')}>
                      <Lightbulb size={16} /> Review Suggestions
                    </button>
                    <button type="button" onClick={() => setPage('users')}>
                      <Users size={16} /> User Management
                    </button>
                  </div>
                </Panel>
              </>
            )}

            {page === 'catalogue' && (
              <LibrarianWorkflows page="catalogue" onChanged={() => loadDashboardData(dateRange.start, dateRange.end)} />
            )}

            {page === 'issue' && (
              <RequestQueue
                requests={loanRequests}
                loading={queueLoading}
                error={queueError}
                message={queueMessage}
                actionId={queueActionId}
                onRefresh={refreshQueue}
                onReview={handleReview}
                onIssue={handleIssue}
              />
            )}

            {page === 'return' && (
              <LibrarianWorkflows page="return" onChanged={() => loadDashboardData(dateRange.start, dateRange.end)} />
            )}

            {page === 'suggestions' && (
              <LibrarianWorkflows page="suggestions" onChanged={() => loadDashboardData(dateRange.start, dateRange.end)} />
            )}

            {page === 'users' && (
              <Panel title="User Management">
                <LibrarianUsers token={token} initialSearch={userSearch} />
              </Panel>
            )}
          </section>
        </main>
      </div>
    </DashboardLayout>
  );
}

function Stat({ value, label, sub, tone = 'blue', highlight = false, onActivate }) {
  return (
    <button
      type="button"
      className={`prototype-stat librarian-stat-card tone-${tone}${highlight ? ' is-highlighted' : ''}`}
      onClick={onActivate}
      aria-label={`${label}: ${value}. ${sub || ''}. Click to open.`}
    >
      <b className="stat-value">{value}</b>
      <span className="stat-label">{label}</span>
      {sub && <small className="stat-sub">{sub}</small>}
    </button>
  );
}

function Panel({ title, headerAction, children }) {
  return (
    <section className="prototype-panel librarian-panel">
      <div className="prototype-panel-head">
        <b>{title}</b>
        {headerAction}
      </div>
      <div className="prototype-panel-body">{children}</div>
    </section>
  );
}

function RequestQueue({
  requests,
  loading,
  error,
  message,
  actionId,
  onRefresh,
  onReview,
  onIssue,
}) {
  return (
    <Panel title="Borrowing Requests">
      <div className="prototype-page-title">
        <p className="prototype-muted">
          Review incoming student and faculty book requests. Approved copies remain reserved until issued.
        </p>
        <button type="button" onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>
      {message && <div className="notice success" role="status">{message}</div>}
      {error && (
        <div className="notice error" role="alert">
          {error} <button type="button" onClick={onRefresh}>Retry</button>
        </div>
      )}
      {loading && requests.length === 0 && <p className="prototype-muted">Loading requests…</p>}
      {!loading && !error && requests.length === 0 && (
        <p className="prototype-muted">No pending borrowing requests at this time.</p>
      )}
      {requests.map(request => (
        <article className="prototype-book-row" key={request.id}>
          <div>
            <b>{request.book_title}</b>
            <small>
              {request.book_author} · {request.requester_name} ({request.requester_role}) · {request.requester_id}
            </small>
            <small>
              Submitted{' '}
              {request.request_submitted_at
                ? new Date(request.request_submitted_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
                : '—'}
            </small>
          </div>
          <span className={`loan-status loan-status-${request.status.toLowerCase()}`}>
            {request.status}
          </span>
          {request.status === 'REQUESTED' && (
            <div className="loan-actions">
              <button
                type="button"
                disabled={actionId === request.id}
                onClick={() => onReview(request.id, 'APPROVED')}
              >
                Approve
              </button>
              <button
                type="button"
                disabled={actionId === request.id}
                onClick={() => onReview(request.id, 'REJECTED')}
              >
                Reject
              </button>
            </div>
          )}
          {request.status === 'APPROVED' && (
            <button
              type="button"
              disabled={actionId === request.id}
              onClick={() => onIssue(request.id)}
            >
              {actionId === request.id ? 'Issuing…' : 'Issue book'}
            </button>
          )}
        </article>
      ))}
    </Panel>
  );
}
