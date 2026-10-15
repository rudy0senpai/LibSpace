import { useEffect, useRef, useState } from 'react';
import { Search, X, LoaderCircle, BookOpen, UsersRound } from 'lucide-react';
import { searchBooks, getLibrarianUsers } from '../../services/api';

export default function GlobalSearch({ role, onOpenCatalogue, onOpenUsers }) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState({ books: [], users: [] });
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResult({ books: [], users: [] });
      setError('');
      setLoading(false);
      return undefined;
    }
    let current = true;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError('');
      try {
        const [bookResponse, userResponse] = await Promise.all([
          searchBooks({ q: trimmed, page: 1, per_page: 6 }),
          role === 'LIBRARIAN'
            ? getLibrarianUsers({ q: trimmed, page: 1, per_page: 5, sort: 'name' })
            : Promise.resolve({ data: { items: [] } }),
        ]);
        if (current) setResult({ books: bookResponse.data?.items || [], users: userResponse.data?.items || [] });
      } catch (requestError) {
        if (current) setError(requestError.message || 'Search is unavailable.');
      } finally {
        if (current) setLoading(false);
      }
    }, 240);
    return () => { current = false; window.clearTimeout(timer); };
  }, [query, role, retry]);

  useEffect(() => {
    const onPointerDown = event => { if (!rootRef.current?.contains(event.target)) setOpen(false); };
    const onKeyDown = event => { if (event.key === 'Escape') setOpen(false); };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, []);

  const hasResults = result.books.length > 0 || result.users.length > 0;
  return (
    <div className="global-search" ref={rootRef}>
      <Search size={17} aria-hidden="true" />
      <input
        type="search"
        value={query}
        onFocus={() => setOpen(true)}
        onChange={event => { setQuery(event.target.value); setSelected(null); setOpen(true); }}
        onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); setOpen(true); } }}
        aria-label={role === 'LIBRARIAN' ? 'Search books and users' : 'Search books'}
        aria-expanded={open && query.trim().length >= 2}
        aria-controls="global-search-results"
        placeholder={role === 'LIBRARIAN' ? 'Search books or users…' : 'Search books…'}
      />
      {query && <button type="button" className="global-search-clear" aria-label="Clear search" onClick={() => { setQuery(''); setSelected(null); setOpen(true); }}><X size={15} /></button>}
      {open && query.trim().length >= 2 && (
        <div className="global-search-popover" id="global-search-results" role="region" aria-label="Search results" aria-busy={loading}>
          {loading && <p className="dashboard-search-status" role="status"><LoaderCircle size={15} className="dashboard-spin" /> Searching…</p>}
          {error && <div className="dashboard-search-error" role="alert">{error}<button type="button" onClick={() => setRetry(value => value + 1)}>Retry</button></div>}
          {!loading && !error && !hasResults && <p className="dashboard-search-status">No matching books{role === 'LIBRARIAN' ? ' or users' : ''}.</p>}
          {result.books.length > 0 && <>
            <div className="dashboard-search-heading"><BookOpen size={14} /> Books</div>
            {result.books.map(book => <button type="button" className="dashboard-search-result" key={book.id} onClick={() => setSelected({ type: 'book', item: book })}>
              <span><b>{book.title}</b><small>{book.author || 'Author unavailable'} · {book.category}</small></span>
              <em>{book.available > 0 ? `${book.available} available` : 'Unavailable'}</em>
            </button>)}
          </>}
          {result.users.length > 0 && <>
            <div className="dashboard-search-heading"><UsersRound size={14} /> Users</div>
            {result.users.map(account => <button type="button" className="dashboard-search-result" key={`${account.role}:${account.user_id || account.name}`} onClick={() => setSelected({ type: 'user', item: account })}>
              <span><b>{account.name}</b><small>{account.user_id || 'No user ID'} · {account.role}</small></span>
              <em>{account.department?.code || '—'}</em>
            </button>)}
          </>}
          {selected && <div className="dashboard-search-detail" aria-live="polite">
            {selected.type === 'book' ? <>
              <b>{selected.item.title}</b><span>{selected.item.author || 'Author unavailable'} · {selected.item.isbn || 'No ISBN listed'}</span>
              <small>{selected.item.available} of {selected.item.total} copies available · Rack {selected.item.rack || 'not listed'}</small>
              {onOpenCatalogue && <button type="button" onClick={() => { onOpenCatalogue(selected.item.title); setOpen(false); }}>Open catalogue results</button>}
            </> : <>
              <b>{selected.item.name}</b><span>{selected.item.user_id} · {selected.item.role}</span>
              <small>{selected.item.department?.name || 'No department'} · {selected.item.is_active ? 'Enabled account' : 'Disabled account'}</small>
              {onOpenUsers && <button type="button" onClick={() => { onOpenUsers(selected.item.user_id || selected.item.name); setOpen(false); }}>Open user management</button>}
            </>}
          </div>}
        </div>
      )}
    </div>
  );
}
