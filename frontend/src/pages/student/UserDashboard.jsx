import { useMemo, useState, useEffect } from 'react';
import { BookOpen, Bell, Lightbulb, LogOut, Search, Table2, ArrowUp, Plus, Loader2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { searchBooks, getMyLoans, getMySuggestions, createSuggestion, voteSuggestion, getCategories } from '../../services/api';

export default function UserDashboard() {
  const { user, signOut } = useAuth();
  const [page, setPage] = useState('dashboard');
  const [query, setQuery] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [books, setBooks] = useState([]);
  const [loans, setLoans] = useState([]);
  const [categories, setCategories] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const firstName = user?.name?.split(' ')[0] || 'Student';

  // Load initial data
  useEffect(() => {
    loadCategories();
    loadMyLoans();
    loadMySuggestions();
  }, []);

  async function loadCategories() {
    try {
      const res = await getCategories();
      setCategories(res.data || []);
    } catch (e) {
      console.error('Failed to load categories', e);
    }
  }

  async function loadMyLoans() {
    try {
      const res = await getMyLoans();
      setLoans(res.data || []);
      setBooks(res.data || []);
    } catch (e) {
      setError('Failed to load loans');
    }
  }

  async function loadMySuggestions() {
    try {
      const res = await getMySuggestions();
      setSuggestions(res.data || []);
    } catch (e) {
      setError('Failed to load suggestions');
    }
  }

  async function handleSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await searchBooks({ q: query });
      setSearchResults(res.data?.items || []);
    } catch (e) {
      setError('Search failed: ' + e.message);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSuggest(e) {
    e.preventDefault();
    if (!suggestion.trim() || !user) return;
    try {
      await createSuggestion({ title: suggestion.trim(), justification: `Suggested by ${user?.role === 'FACULTY' ? 'faculty' : 'student'}`, reason: 'COURSE_REQUIREMENT' });
      setSuggestion('');
      await loadMySuggestions();
    } catch (e) {
      setError('Failed to submit suggestion: ' + e.message);
    }
  }

  async function handleVote(suggestionId) {
    try {
      const res = await voteSuggestion(suggestionId);
      if (res.data?.voted) {
        setSuggestions(prev => prev.map(s => s.id === suggestionId ? { ...s, votes: s.votes + 1 } : s));
      } else {
        setSuggestions(prev => prev.map(s => s.id === suggestionId ? { ...s, votes: s.votes - 1 } : s));
      }
    } catch (e) {
      setError('Vote failed: ' + e.message);
    }
  }

  async function handleReturn(loanId) {
    // For demo purposes - in real app would call return endpoint
    setLoans(prev => prev.filter(l => l.id !== loanId));
    setBooks(prev => prev.filter(b => b.id !== loanId));
  }

  const nav = [
    ['dashboard', Table2, 'Dashboard'],
    ['search', Search, 'Search Books'],
    ['mybooks', BookOpen, 'My Books'],
    ['suggestions', Lightbulb, 'Suggestions'],
    ['notifications', Bell, 'Notifications'],
  ];

  return (
    <div className="prototype-shell">
      <aside className="prototype-sidebar">
        <div className="prototype-brand">
          <b>MITRC <span>LibSphere</span></b>
          <small>Library Management</small>
        </div>
        {nav.map(([key, Icon, label]) => (
          <button key={key} className={`prototype-nav ${page === key ? 'active' : ''}`} onClick={() => setPage(key)}>
            <Icon size={17} />{label}
            {key === 'mybooks' && <em>{loans.length}</em>}
          </button>
        ))}
        <div className="prototype-divider" />
        <button className="prototype-nav" onClick={signOut}><LogOut size={17} />Logout</button>
        <div className="prototype-user">
          <div className="prototype-avatar">{firstName[0]}</div>
          <div>
            <b>{user?.name}</b>
            <small>{user?.role || 'STUDENT'} · MITRC Alwar</small>
          </div>
        </div>
      </aside>
      <main className="prototype-main">
        <header className="prototype-header">
          <div>
            <b>
              {page === 'dashboard' ? (user?.role === 'FACULTY' ? 'Teacher Dashboard' : 'Student Dashboard') :
               page === 'search' ? 'Search Catalogue' :
               page === 'mybooks' ? 'My Books' :
               page === 'suggestions' ? 'Community Suggestions' : 'Notifications'}
            </b>
            <small>Personalized library activity</small>
          </div>
          <span>{new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}</span>
        </header>
        <section className="prototype-content">
          {error && <div className="notice error">{error}</div>}

          {page === 'dashboard' && (
            <>
              <h1>Good evening, {firstName}</h1>
              <p className="prototype-muted">Here's your library activity at a glance.</p>
              <div className="prototype-stats">
                <Stat value={loans.length} label="Borrowed" />
                <Stat value={loans.filter(l => l.status === 'BORROWED' || l.status === 'OVERDUE').length} label="Active" />
                <Stat value={loans.filter(l => l.status === 'OVERDUE').length} label="Overdue" />
                <Stat value={suggestions.length} label="Suggestions" />
              </div>
              <div className="prototype-two-col">
                <Panel title="Currently Borrowed">
                  {loans.length === 0 ? (
                    <p className="prototype-muted">No active loans</p>
                  ) : (
                    loans.map(loan => (
                      <BookRow key={loan.id} loan={loan} onReturn={() => handleReturn(loan.id)} />
                    ))
                  )}
                </Panel>
                <Panel title="Recommended for You">
                  <div className="prototype-recommend">
                    <small>Connect to backend for AI recommendations</small>
                  </div>
                </Panel>
              </div>
            </>
          )}

          {page === 'search' && (
            <>
              <h1>Discover Books</h1>
              <div className="prototype-search">
                <Search size={17} />
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="Search books, authors, ISBN…"
                />
                <button onClick={handleSearch} disabled={loading}>
                  {loading ? <Loader2 size={16} className="spin" /> : 'Search'}
                </button>
              </div>
              <div className="prototype-book-grid">
                {searchResults.map(book => (
                  <div className="prototype-book-card" key={book.id}>
                    <b>{book.title}</b>
                    <small>{book.author}</small>
                    <span className={book.available > 0 ? 'available' : 'unavailable'}>
                      {book.available > 0 ? `Available ${book.available}/${book.total}` : 'Not Available'}
                    </span>
                    <small>Rack: {book.rack}</small>
                    <button onClick={() => alert(`Request sent for: ${book.title}`)}>Request Book</button>
                  </div>
                ))}
                {searchResults.length === 0 && query && !loading && (
                  <p className="prototype-muted">No books found matching "{query}"</p>
                )}
              </div>
            </>
          )}

          {page === 'mybooks' && (
            <>
              <h1>My Books</h1>
              <Panel title="Current Loans">
                {loans.length === 0 ? (
                  <p className="prototype-muted">No books currently borrowed</p>
                ) : (
                  loans.map(loan => (
                    <BookRow key={loan.id} loan={loan} onReturn={() => handleReturn(loan.id)} />
                  ))
                )}
              </Panel>
            </>
          )}

          {page === 'suggestions' && (
            <>
              <h1>Suggest a Book 💡</h1>
              <p className="prototype-muted">Community voted — supported suggestions are reviewed by the library.</p>
              <Panel title="Book suggestion">
                <form onSubmit={handleSuggest} className="prototype-suggest">
                  <input
                    value={suggestion}
                    onChange={e => setSuggestion(e.target.value)}
                    placeholder="Enter book title…"
                    required
                  />
                  <button type="submit"><Plus size={16} /> Suggest + Vote</button>
                </form>
                {suggestions.map(item => (
                  <div className="prototype-suggestion-row" key={item.id}>
                    <span>{item.title}</span>
                    <button onClick={() => handleVote(item.id)}>
                      <ArrowUp size={16} /> <b>{item.votes}</b>
                    </button>
                  </div>
                ))}
                {suggestions.length === 0 && <p className="prototype-muted">No suggestions yet</p>}
              </Panel>
            </>
          )}

          {page === 'notifications' && (
            <>
              <h1>Notifications</h1>
              <Panel title="Recent notifications">
                <div className="notice warning">⚠ Your books may be due soon</div>
                <div className="notice success">✓ Request processed</div>
              </Panel>
            </>
          )}
        </section>
      </main>
    </div>
  );
}

function Stat({ value, label }) {
  return (
    <div className="prototype-stat">
      <b>{value}</b>
      <small>{label}</small>
    </div>
  );
}

function Panel({ title, children }) {
  return (
    <section className="prototype-panel">
      <div className="prototype-panel-head"><b>{title}</b></div>
      <div className="prototype-panel-body">{children}</div>
    </section>
  );
}

function BookRow({ loan, onReturn }) {
  const dueDate = new Date(loan.due_at);
  const isOverdue = loan.status === 'OVERDUE';
  const isDueSoon = !isOverdue && (dueDate - new Date()) < 3 * 24 * 60 * 60 * 1000;
  return (
    <div className="prototype-book-row">
      <div>
        <b>{loan.book_title}</b>
        <small>{loan.book_author}</small>
      </div>
      <span>{loan.rack} / {loan.shelf}</span>
      <em className={isOverdue ? 'due' : isDueSoon ? 'due-soon' : 'on-time'}>
        {isOverdue ? 'Overdue' : isDueSoon ? 'Due Soon' : 'On Time'}
      </em>
      <button onClick={onReturn}>Return</button>
    </div>
  );
}
