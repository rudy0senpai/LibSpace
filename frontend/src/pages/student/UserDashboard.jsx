import { useMemo, useRef, useState, useEffect } from 'react';
import { BookOpen, Bell, Lightbulb, LogOut, Search, Table2, ArrowUp, Plus, Loader2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { searchBooks, getMyLoans, getMySuggestions, createSuggestion, voteSuggestion, getCategories, requestBook, cancelMyLoan } from '../../services/api';
import RequestedBooks from './RequestedBooks';
import VirtualBookGrid from './VirtualBookGrid';

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
  const [loansLoading, setLoansLoading] = useState(true);
  const [loanError, setLoanError] = useState('');
  const [requestingBookId, setRequestingBookId] = useState('');
  const [cancellingId, setCancellingId] = useState('');
  const [votingIds, setVotingIds] = useState(() => new Set());
  const [categoryFilter, setCategoryFilter] = useState('');
  const [availabilityFilter, setAvailabilityFilter] = useState('');
  const [searchPage, setSearchPage] = useState(1);
  const [searchTotal, setSearchTotal] = useState(0);
  const searchSequence = useRef(0);
  const activeBookIds = useMemo(() => new Set(loans.filter(loan => ['REQUESTED', 'APPROVED', 'BORROWED', 'OVERDUE'].includes(loan.status)).map(loan => loan.book_id)), [loans]);
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
    setLoansLoading(true);
    setLoanError('');
    try {
      const res = await getMyLoans();
      setLoans(res.data || []);
      setBooks(res.data || []);
    } catch (e) {
      setLoanError(e.message || 'Failed to load your requested books.');
    } finally {
      setLoansLoading(false);
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

  async function handleSearch(append = false) {
    const pageToLoad = append ? searchPage + 1 : 1;
    const sequence = ++searchSequence.current;
    setLoading(true);
    setError('');
    try {
      const res = await searchBooks({
        q: query, page: pageToLoad, per_page: 24,
        category_id: categoryFilter || undefined,
        availability: availabilityFilter || undefined,
      });
      if (sequence !== searchSequence.current) return;
      const items = res.data?.items || [];
      setSearchResults(current => append ? [...current, ...items] : items);
      setSearchPage(pageToLoad);
      setSearchTotal(res.data?.total || 0);
    } catch (e) {
      if (sequence !== searchSequence.current) return;
      setError('Search failed: ' + e.message);
      if (!append) setSearchResults([]);
    } finally {
      if (sequence === searchSequence.current) setLoading(false);
    }
  }

  async function handleSuggest(e) {
    e.preventDefault();
    if (!suggestion.trim() || !user) return;
    try {
      const created = await createSuggestion({ title: suggestion.trim(), justification: `Suggested by ${user?.role === 'FACULTY' ? 'faculty' : 'student'}`, reason: 'COURSE_REQUIREMENT' });
      if (created.data?.id) await voteSuggestion(created.data.id);
      setSuggestion('');
      await loadMySuggestions();
    } catch (e) {
      setError('Failed to submit suggestion: ' + e.message);
    }
  }

  async function handleVote(suggestionId) {
    const current = suggestions.find(item => item.id === suggestionId);
    if (!current || current.voted_by_me || votingIds.has(suggestionId)) return;
    setVotingIds(previous => new Set(previous).add(suggestionId));
    setSuggestions(previous => previous.map(item => item.id === suggestionId
      ? { ...item, votes: item.votes + 1, voted_by_me: true }
      : item));
    try {
      const result = await voteSuggestion(suggestionId);
      setSuggestions(previous => previous.map(item => item.id === suggestionId
        ? { ...item, votes: result.data.vote_count, voted_by_me: result.data.voted }
        : item));
    } catch (e) {
      await loadMySuggestions();
      setError('Vote failed: ' + e.message);
    } finally {
      setVotingIds(previous => {
        const next = new Set(previous);
        next.delete(suggestionId);
        return next;
      });
    }
  }

  async function handleBookRequest(book) {
    setRequestingBookId(book.id);
    setError('');
    try {
      await requestBook(String(book.id));
      await loadMyLoans();
    } catch (e) {
      setError(e.message || 'Unable to submit the borrowing request.');
    } finally {
      setRequestingBookId('');
    }
  }

  async function handleCancel(loanId) {
    setCancellingId(loanId);
    setLoanError('');
    try {
      await cancelMyLoan(loanId);
      await loadMyLoans();
    } catch (e) {
      setLoanError(e.message || 'Unable to cancel this request.');
    } finally {
      setCancellingId('');
    }
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
                <Stat value={loans.filter(l => l.status === 'REQUESTED' || l.status === 'APPROVED').length} label="Requests" />
                <Stat value={loans.filter(l => l.status === 'BORROWED' || l.status === 'OVERDUE').length} label="Active loans" />
                <Stat value={loans.filter(l => l.status === 'OVERDUE').length} label="Overdue" />
                <Stat value={suggestions.length} label="Suggestions" />
              </div>
              <div className="prototype-two-col">
                <Panel title="Currently Borrowed">
                  {loans.filter(loan => loan.status === 'BORROWED' || loan.status === 'OVERDUE').length === 0 ? (
                    <p className="prototype-muted">No books currently borrowed</p>
                  ) : (
                    loans.filter(loan => loan.status === 'BORROWED' || loan.status === 'OVERDUE').map(loan => (
                      <BookRow key={loan.id} loan={loan} />
                    ))
                  )}
                </Panel>
                <Panel title="Recommended for You">
                  <div className="prototype-recommend">
                    <small>Recommendations are not available yet.</small>
                  </div>
                </Panel>
              </div>
              <RequestedBooks loans={loans} loading={loansLoading} error={loanError} onRetry={loadMyLoans} onCancel={handleCancel} cancellingId={cancellingId} />
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
                  aria-label="Search books, authors or ISBN"
                />
                <select aria-label="Filter by category" value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
                  <option value="">All categories</option>
                  {categories.map(category => <option key={category.id} value={category.id}>{category.name}</option>)}
                </select>
                <select aria-label="Filter by availability" value={availabilityFilter} onChange={e => setAvailabilityFilter(e.target.value)}>
                  <option value="">Any availability</option>
                  <option value="available">Available now</option>
                  <option value="unavailable">Unavailable</option>
                </select>
                <button onClick={() => handleSearch(false)} disabled={loading}>
                  {loading ? <Loader2 size={16} className="spin" /> : 'Search'}
                </button>
              </div>
              {error && <div className="notice error" role="alert">{error}</div>}
              {searchResults.length > 0 && <p className="prototype-muted">Showing {searchResults.length} of {searchTotal} matching books.</p>}
              {searchResults.length > 0 && <VirtualBookGrid items={searchResults} renderItem={(book, index, total) => (
                <div className="prototype-book-card" role="listitem" aria-posinset={index + 1} aria-setsize={total} key={book.id}>
                  <b>{book.title}</b>
                  <small>{book.author}</small>
                  <span className={book.available > 0 ? 'available' : 'unavailable'}>
                    {book.available > 0 ? `Available ${book.available}/${book.total}` : 'Not Available'}
                  </span>
                  <small>Rack: {book.rack}</small>
                  <button disabled={requestingBookId === book.id || activeBookIds.has(String(book.id)) || book.available <= 0} onClick={() => handleBookRequest(book)}>
                    {requestingBookId === book.id ? 'Submitting…' : activeBookIds.has(String(book.id)) ? 'Already requested' : book.available <= 0 ? 'Unavailable' : 'Request Book'}
                  </button>
                </div>
              )} />}
              {searchResults.length === 0 && !loading && (
                <p className="prototype-muted">{searchTotal ? 'No books on this page.' : 'Search the catalogue to see matching books.'}</p>
              )}
              {searchResults.length < searchTotal && <button type="button" onClick={() => handleSearch(true)} disabled={loading}>
                {loading ? 'Loading…' : 'Load more books'}
              </button>}
            </>
          )}

          {page === 'mybooks' && (
            <>
              <h1>My Books</h1>
              <RequestedBooks loans={loans} loading={loansLoading} error={loanError} onRetry={loadMyLoans} onCancel={handleCancel} cancellingId={cancellingId} />
              <Panel title="Currently Borrowed">
                {loans.filter(loan => loan.status === 'BORROWED' || loan.status === 'OVERDUE').length === 0 ? (
                  <p className="prototype-muted">No books currently borrowed</p>
                ) : (
                  loans.filter(loan => loan.status === 'BORROWED' || loan.status === 'OVERDUE').map(loan => (
                    <BookRow key={loan.id} loan={loan} />
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
                    <button
                      type="button"
                      className={item.voted_by_me ? 'suggestion-vote voted' : 'suggestion-vote'}
                      aria-pressed={item.voted_by_me}
                      disabled={item.voted_by_me || votingIds.has(item.id)}
                      onClick={() => handleVote(item.id)}
                    >
                      {votingIds.has(item.id) ? <Loader2 size={16} className="spin" /> : <ArrowUp size={16} />}
                      <b>{item.voted_by_me ? 'Voted' : 'Vote'} · {item.votes}</b>
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

function BookRow({ loan }) {
  const dueDate = loan.due_at ? new Date(loan.due_at) : null;
  const isOverdue = loan.status === 'OVERDUE';
  const isDueSoon = dueDate && !isOverdue && (dueDate - new Date()) < 3 * 24 * 60 * 60 * 1000;
  return (
    <div className="prototype-book-row">
      <div>
        <b>{loan.book_title}</b>
        <small>{loan.book_author}</small>
      </div>
      <span>{loan.rack} / {loan.shelf}</span>
      <em className={isOverdue ? 'due' : isDueSoon ? 'due-soon' : 'on-time'}>
        {isOverdue ? 'Overdue' : dueDate ? isDueSoon ? 'Due Soon' : 'On Time' : loan.status}
      </em>
    </div>
  );
}
