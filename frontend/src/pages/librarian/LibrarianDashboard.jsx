import { useMemo, useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, BookOpen, LayoutDashboard, Lightbulb, LogOut, Plus, Search, Users } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const booksSeed = [
  { id: 'BK-001', title: 'Clean Code', author: 'Robert C. Martin', copies: 5 },
  { id: 'BK-002', title: 'Deep Learning', author: 'Ian Goodfellow', copies: 2 },
  { id: 'BK-003', title: 'Computer Networks', author: 'Andrew S. Tanenbaum', copies: 7 },
  { id: 'BK-004', title: 'Database System Concepts', author: 'Abraham Silberschatz', copies: 6 },
];

export default function LibrarianDashboard() {
  const { user, signOut } = useAuth();
  const [page, setPage] = useState('dashboard');
  const [query, setQuery] = useState('');
  const [books, setBooks] = useState(booksSeed);
  const filtered = useMemo(() => books.filter(book => `${book.id} ${book.title} ${book.author}`.toLowerCase().includes(query.toLowerCase())), [books, query]);
  const nav = [['dashboard', LayoutDashboard, 'Dashboard'], ['catalogue', BookOpen, 'Manage Catalogue'], ['issue', ArrowUpFromLine, 'Issue Book'], ['return', ArrowDownToLine, 'Return Books'], ['suggestions', Lightbulb, 'Suggestions'], ['users', Users, 'Users']];
  return <div className="prototype-shell librarian-shell">
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
          <b>{page === 'dashboard' ? 'Librarian Dashboard' : page === 'catalogue' ? 'Manage Catalogue' : page === 'issue' ? 'Issue Book' : page === 'return' ? 'Return Books' : page === 'suggestions' ? 'Acquisition Demand' : 'Users'}</b>
          <small>Library control center</small>
        </div>
        <span>
          {new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}
        </span>
      </header>
      <section className="prototype-content">{page === 'dashboard' && <>
        <h1>Library Control Center</h1>
        <p className="prototype-muted">Core library operations and activity.</p>
        <div className="prototype-stats six">
          <Stat value="—" label="Total Books" />
          <Stat value="—" label="Total Copies" />
          <Stat value="—" label="Available" />
          <Stat value="—" label="Borrowed" />
          <Stat value="—" label="Overdue" />
          <Stat value="—" label="Suggestion Votes" />
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
          <FormPanel title="Issue Book" label="Student ID" second="Book ID / ISBN" button="Issue Now" />
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
            <p className="prototype-muted">User management is available to authorized librarians/admins. Connect this view to the users API when that endpoint is implemented.</p>
          </Panel>}
      </section>
    </main>
  </div>
}
function Stat({ value, label }) {
  return <div className="prototype-stat">
    <b>{value}</b>
    <small>{label}</small>
  </div>;
}
function Panel({ title, children }) {
  return <section className="prototype-panel">
    <div className="prototype-panel-head">
      <b>{title}</b>
    </div>
    <div className="prototype-panel-body">
      {children}
    </div>
  </section>;
}
function FormPanel({ title, label, second, button }) {
  return <Panel title={title}>
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
  </Panel>;
}
