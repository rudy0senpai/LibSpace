import { useMemo, useState } from 'react';
import { Bell, BookOpen, CalendarDays, ChartNoAxesCombined, ChevronDown, Clock3, FileDown, Filter, Layers3, Lightbulb, Menu, RefreshCw, Search, Users } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useDepartmentDashboard } from '../../hooks/useDepartmentDashboard';
import { BorrowingTrend, CategoryBars, StudentFaculty, CopyStatus, SuggestionBars, Utilization } from '../../components/department/Charts';

export default function DepartmentDashboard() {
  const { user, token, signOut } = useAuth();
  const [start, setStart] = useState('2026-04-01');
  const [end, setEnd] = useState('2026-10-01');
  const [category, setCategory] = useState('');
  const [userType, setUserType] = useState('');
  const [suggestionStatus, setSuggestionStatus] = useState('');
  const [search, setSearch] = useState('');
  const params = useMemo(() => ({ start_date: start, end_date: end, category_id: category, user_type: userType, suggestion_status: suggestionStatus, search }), [start, end, category, userType, suggestionStatus, search]);
  const { data, loading, error, reload } = useDepartmentDashboard(token, params);
  const s = data?.summary || {};
  const c = data?.comparisons || {};
  const fmt = value => new Intl.NumberFormat('en-IN').format(value ?? 0);
  return (
  <div className="app-shell">
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-title">MITRC
          <span>LibSphere</span>
        </div>
        <div className="brand-sub">Library Management & Discovery Portal</div>
      </div>
      <nav>
        <a className="nav active"><Layers3 />Dashboard</a>
        <a className="nav"><Search />Book Search</a>
        <a className="nav"><Lightbulb />Suggestions</a>
        <a className="nav"><ChartNoAxesCombined />Reports</a>
        <a className="nav"><Bell />Notifications</a>
        <a className="nav"><Users />Profile</a>
      </nav>
      <div className="quick">
        <div className="quick-title">
          <Filter />Quick Filters
        </div>
        <label>Department</label>
        <div className="select locked">
          {data?.scope?.name || 'Loading department…'}
          <ChevronDown size={15} />
        </div>
        <label>Category</label>
        <select value={category} onChange={e => setCategory(e.target.value)}>
          <option value="">All Categories</option>
          {(data?.borrowing_by_category || []).map(x =>
            <option key={x.category_id || x.category_name} value={x.category_id}>{x.category_name}</option>)}
        </select>
        <label>User Type</label>
        <select value={userType} onChange={e => setUserType(e.target.value)}>
          <option value="">All Users</option>
          <option value="STUDENT">Students</option>
          <option value="FACULTY">Faculty</option>
        </select>
        <label>Suggestion Status</label>
        <select value={suggestionStatus} onChange={e => setSuggestionStatus(e.target.value)}>
          <option value="">All Statuses</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="APPROVED">Approved</option>
          <option value="ORDERED">Ordered</option>
        </select>
        <button className="filter-btn" onClick={reload}>
          <Filter size={16} />Apply Filters
        </button>
      </div>
      <div className="sidebar-footer">A smarter library<br />for a brighter tomorrow<br /><br /><b>MITRC</b><br />Modern Institute of Technology and Research Centre<br />Alwar, Rajasthan</div>
    </aside>
    <main className="main">
      <header className="topbar">
        <button className="mobile-menu">
          <Menu />
        </button>
        <div className="searchbox">
          <Search size={18} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search suggestions, books…" />
        </div>
        <Bell />
        <div className="profile">
          <div className="avatar">{(user?.name || 'DP').split(' ').map(x => x[0]).join('').slice(0, 2)}</div>
          <div><b>{user?.name}</b>
            <small>Department Head</small>
            <small>{data?.scope?.name || 'Department'}</small>
          </div>
          <button onClick={signOut} title="Logout">↪</button>
        </div>
      </header>
      <div className="content">
        <div className="title-row">
          <div>
            <h1>Department Dashboard</h1>
            <div className="department-name">{data?.scope?.name || 'Department'} <ChevronDown size={16} />
            </div>
          </div>
          <div className="actions">
            <div className="date-range">
              <CalendarDays size={16} />
              <input type="date" value={start} onChange={e => setStart(e.target.value)} />
              <span>→</span>
              <input type="date" value={end} onChange={e => setEnd(e.target.value)} />
            </div>
            <button className="report-btn" onClick={() => window.print()}>
              <FileDown size={17} />Generate Report
            </button>
          </div>
        </div>{error ?
          <div className="error-banner">
            <span>{error}</span>
            <button onClick={reload}><RefreshCw size={15} />Retry</button>
          </div> : loading ?
            <div className="loading">Loading department analytics from PostgreSQL…</div> : data ? <>
              <div className="kpis">
                <Card icon={<BookOpen />} title="Department Books" value={fmt(s.department_books)} change={c.department_books_change} tone="blue" />
                <Card icon={<BookOpen />} title="Available Copies" value={fmt(s.available_copies)} change={c.available_copies_change} tone="green" />
                <Card icon={<Layers3 />} title="Currently Borrowed" value={fmt(s.currently_borrowed)} change={c.currently_borrowed_change} tone="purple" />
                <Card icon={<Clock3 />} title="Overdue Books" value={fmt(s.overdue_books)} change={c.overdue_books_change} tone="red" />
                <Card icon={<Users />} title="Active Students" value={fmt(s.active_students)} change={c.active_students_change} tone="cyan" />
                <Card icon={<Users />} title="Active Faculty" value={fmt(s.active_faculty)} change={c.active_faculty_change} tone="orange" />
                <Card icon={<Lightbulb />} title="Pending Suggestions" value={fmt(s.pending_suggestions)} change={c.pending_suggestions_change} tone="violet" />
              </div>
              <div className="grid-3">
                <Panel title="Monthly Borrowing Trend">
                  <BorrowingTrend data={data.borrowing_trend} />
                </Panel>
                <Panel title="Borrowing by Category">
                  <CategoryBars data={data.borrowing_by_category} />
                </Panel>
                <Panel title="Student vs Faculty Borrowing">
                  <StudentFaculty data={data.student_vs_faculty} />
                </Panel>
                <Panel title="Department Book Utilization">
                  <Utilization data={data.book_utilization} />
                </Panel>
                <Panel title="Book Copy Status">
                  <CopyStatus data={data.copy_status} />
                </Panel>
                <Panel title="Suggestion Demand by Category">
                  <SuggestionBars data={data.suggestion_demand} />
                </Panel>
              </div>
              <div className="bottom-grid">
                <Panel title="Book Suggestions" wide>
                  <SuggestionTable rows={data.suggestions} />
                </Panel>
                <div className="side-stack">
                  <Panel title="Top Suggested Books">
                    <ol className="rank-list">{data.top_books.map((x, i) =>
                      <li key={`${x.title}-${i}`}>
                        <span className="rank">{i + 1}</span>
                        <span>{x.title}</span>
                        <b>{x.vote_count} votes</b>
                      </li>)}
                    </ol>
                  </Panel>
                  <Panel title="Recent Suggestions">
                    <ul className="recent">{data.recent_suggestions.map(x =>
                      <li key={x.id}>
                        <div>
                          <b>{x.title}</b>
                          <small>
                            {x.requester_type} · {new Date(x.created_at).toLocaleDateString('en-IN')}
                          </small>
                        </div>
                        <span>{x.votes} votes</span>
                      </li>)}
                    </ul>
                  </Panel>
                </div>
              </div>
            </> :
              <div className="loading">No dashboard data returned.</div>}
      </div>
    </main>
  </div>);
}
function Card({ icon, title, value, change, tone }) {
  return (
  <div className={`kpi ${tone}`}>
    <div className="kpi-icon">{icon}</div>
    <div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-title">{title}</div>
      {change !== null && change !== undefined ?
        <div className={`change ${change >= 0 ? 'up' : 'down'}`}>{change >= 0 ? '↑' : '↓'}
          {Math.abs(change)}% vs previous period</div> :
        <div className="change muted">Insufficient historical data</div>}
    </div>
  </div>);
}
function Panel({ title, children, wide = false }) {
  return (
  <section className={`panel ${wide ? 'wide' : ''}`}>
    <div className="panel-head">
      <h3>{title}</h3>
    </div>
    <div className="panel-body">{children}</div>
  </section>);
}
function SuggestionTable({ rows }) {
  return rows.length === 0 ?
    <div className="empty">No book suggestions yet.</div> :
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Book Title</th>
            <th>Requester</th>
            <th>Type</th>
            <th>Department</th>
            <th>Reason</th>
            <th>Votes</th>
            <th>Status</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((x, i) => <tr key={x.id}><td>{i + 1}
          </td>
            <td>
              <b>{x.title}</b>
              {x.author && <small>{x.author}</small>}
            </td>
            <td>{x.requester}</td>
            <td>
              <span className={`tag ${String(x.requester_type).toLowerCase()}`}>
                {x.requester_type}
              </span>
            </td>
            <td>
              {x.department}</td><td>{String(x.reason || '').replaceAll('_', ' ')}
            </td>
            <td>👍 {x.votes}</td>
            <td>
              <span className={`status ${String(x.status).toLowerCase()}`}>
                {String(x.status).replaceAll('_', ' ')}
              </span>
            </td>
            <td>
              {new Date(x.created_at).toLocaleDateString('en-IN')}
            </td>
          </tr>)}
        </tbody>
      </table>
    </div>;
}
