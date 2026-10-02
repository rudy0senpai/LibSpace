import { useMemo, useState } from 'react';
import { BookOpen, Bell, Lightbulb, LogOut, Search, Table2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const catalog = [
  { title: 'Clean Code', author: 'Robert C. Martin', avail: 3, total: 5, rack: 'CS-A-04' },
  { title: 'Deep Learning', author: 'Ian Goodfellow, Yoshua Bengio, Aaron Courville', avail: 2, total: 2, rack: 'AI-B-01' },
  { title: 'Computer Networks', author: 'Andrew S. Tanenbaum, David J. Wetherall', avail: 5, total: 7, rack: 'CS-A-11' },
  { title: 'Database System Concepts', author: 'Abraham Silberschatz, Henry F. Korth', avail: 4, total: 6, rack: 'CS-C-03' },
  { title: 'Python Crash Course', author: 'Eric Matthes', avail: 0, total: 3, rack: 'CS-B-02' },
];

export default function UserDashboard() {
  const { user, signOut } = useAuth();
  const [page, setPage] = useState('dashboard');
  const [query, setQuery] = useState('');
  const [suggestion, setSuggestion] = useState('');
  const [suggestions, setSuggestions] = useState([{ title: 'System Design Interview', votes: 12 }, { title: 'AI for Everyone', votes: 7 }]);
  const [books, setBooks] = useState([
    { id: 1, title: 'Clean Code', date: '2026-10-08', status: 'On time', rack: 'CS-A-04' },
    { id: 2, title: 'Computer Networks', date: '2026-10-03', status: 'Due soon', rack: 'CS-A-11' },
    { id: 3, title: 'Machine Learning', date: '2026-10-10', status: 'On time', rack: 'AI-A-02' },
  ]);
  const filtered = useMemo(() => catalog.filter(book => `${book.title} ${book.author}`.toLowerCase().includes(query.toLowerCase())), [query]);
  const firstName = user?.name?.split(' ')[0] || 'Student';

  const nav = [['dashboard', Table2, 'Dashboard'], ['search', Search, 'Search Books'], ['mybooks', BookOpen, 'My Books'], ['suggestions', Lightbulb, 'Suggestions'], ['notifications', Bell, 'Notifications']];
  return <div className="prototype-shell">
    <aside className="prototype-sidebar"><div className="prototype-brand"><b>MITRC <span>LibSphere</span></b><small>Library Management</small></div>{nav.map(([key, Icon, label]) => <button key={key} className={`prototype-nav ${page === key ? 'active' : ''}`} onClick={() => setPage(key)}><Icon size={17} />{label}{key === 'mybooks' && <em>{books.length}</em>}</button>)}<div className="prototype-divider"/><button className="prototype-nav" onClick={signOut}><LogOut size={17}/>Logout</button><div className="prototype-user"><div className="prototype-avatar">{firstName[0]}</div><div><b>{user?.name}</b><small>{user?.role || 'STUDENT'} · MITRC Alwar</small></div></div></aside>
    <main className="prototype-main"><header className="prototype-header"><div><b>{page === 'dashboard' ? 'Student Dashboard' : page === 'search' ? 'Search Catalogue' : page === 'mybooks' ? 'My Books' : page === 'suggestions' ? 'Community Suggestions' : 'Notifications'}</b><small>Personalized library activity</small></div><span>{new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}</span></header>
      <section className="prototype-content">
        {page === 'dashboard' && <><h1>Good evening, {firstName}</h1><p className="prototype-muted">Here’s your library activity at a glance.</p><div className="prototype-stats"><Stat value={books.length} label="Borrowed"/><Stat value="1" label="Due Soon"/><Stat value="0" label="Overdue"/><Stat value="2" label="Reservations"/></div><div className="prototype-two-col"><Panel title="Currently Borrowed">{books.map(book => <BookRow key={book.id} book={book} onReturn={() => setBooks(current => current.filter(x => x.id !== book.id))}/>)}</Panel><Panel title="Recommended for you"><div className="prototype-recommend">Hands-On Machine Learning <small>87% match</small></div><div className="prototype-recommend">Database System Concepts <small>81% match</small></div></Panel></div></>}
        {page === 'search' && <><h1>Discover Books</h1><div className="prototype-search"><Search size={17}/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search books, authors, ISBN…"/></div><div className="prototype-book-grid">{filtered.map(book => <div className="prototype-book-card" key={book.title}><b>{book.title}</b><small>{book.author}</small><span className={book.avail ? 'available' : 'unavailable'}>{book.avail ? `Available ${book.avail}/${book.total}` : 'Not Available'}</span><small>{book.rack}</small><button onClick={() => alert(`Request sent for: ${book.title}`)}>Request Book</button></div>)}</div></>}
        {page === 'mybooks' && <><h1>My Books</h1><Panel title="Current Loans">{books.map(book => <BookRow key={book.id} book={book} onReturn={() => setBooks(current => current.filter(x => x.id !== book.id))}/>)}</Panel></>}
        {page === 'suggestions' && <><h1>Suggest a Book 💡</h1><p className="prototype-muted">Community voted — supported suggestions can be reviewed by the library.</p><Panel title="Book suggestion"><div className="prototype-suggest"><input value={suggestion} onChange={e => setSuggestion(e.target.value)} placeholder="Enter book title…"/><button onClick={() => { if (!suggestion.trim()) return; setSuggestions([{ title: suggestion.trim(), votes: 1 }, ...suggestions]); setSuggestion(''); }}>Suggest + Vote</button></div>{suggestions.map(item => <div className="prototype-suggestion-row" key={item.title}><span>{item.title}</span><b>▲ {item.votes}</b></div>)}</Panel></>}
        {page === 'notifications' && <><h1>Notifications</h1><Panel title="Recent notifications"><div className="notice warning">⚠ Computer Networks is due soon.</div><div className="notice success">✓ Your request for Clean Code was approved.</div></Panel></>}
      </section>
    </main>
  </div>;
}
function Stat({ value, label }) { return <div className="prototype-stat"><b>{value}</b><small>{label}</small></div>; }
function Panel({ title, children }) { return <section className="prototype-panel"><div className="prototype-panel-head"><b>{title}</b></div><div className="prototype-panel-body">{children}</div></section>; }
function BookRow({ book, onReturn }) { return <div className="prototype-book-row"><div><b>{book.title}</b><small>{book.rack}</small></div><span>{book.date}</span><em className={book.status === 'Due soon' ? 'due' : 'on-time'}>{book.status}</em><button onClick={onReturn}>Return</button></div>; }
