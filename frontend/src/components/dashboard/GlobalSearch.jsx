import { useEffect, useRef, useState } from 'react';
import { Search, X, LoaderCircle, BookOpen, UsersRound } from 'lucide-react';
import { searchBooks, getLibrarianUsers, lookupBookCover } from '../../services/api';
import { lookupBookMetadata } from '../../services/metadataService';

export default function GlobalSearch({ role, onOpenCatalogue, onOpenUsers }) {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState({ books: [], users: [] });
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [metadata, setMetadata] = useState(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [coverStage, setCoverStage] = useState(0);
  const rootRef = useRef(null);

  useEffect(() => {
    const book = selected?.type === 'book' ? selected.item : null;
    if (!book || (book.cover_image_ref && coverStage === 0) || coverStage > 0) { setMetadata(null); return undefined; }
    let current = true;
    setMetadataLoading(true);
    const detailsPromise = book.isbn ? lookupBookMetadata(book.isbn) : Promise.resolve(null);
    const coverPromise = book.id ? lookupBookCover(book.id).catch(() => null) : Promise.resolve(null);
    Promise.all([detailsPromise, coverPromise]).then(([details, coverResult]) => {
      if (current) setMetadata({ ...(details || {}), cover_url: coverResult?.data?.cover_url || null, source: coverResult?.data?.source || null });
    }).finally(() => { if (current) setMetadataLoading(false); });
    return () => { current = false; };
  }, [coverStage, selected]);

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResult({ books: [], users: [] });
      setError('');
      setLoading(false);
      setActiveIndex(-1);
      return undefined;
    }
    let current = true;
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError('');
      setResult({ books: [], users: [] });
      setSelected(null);
      setActiveIndex(-1);
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
  const selectableResults = [
    ...result.books.map(item => ({ type: 'book', item })),
    ...result.users.map(item => ({ type: 'user', item })),
  ];
  const selectResult = index => {
    const entry = selectableResults[index];
    if (entry) {
      setCoverStage(0);
      setSelected(entry);
      setActiveIndex(index);
    }
  };
  const selectedBook = selected?.type === 'book' ? selected.item : null;
  const selectedCover = selectedBook
    ? coverStage === 0 ? selectedBook.cover_image_ref || metadata?.cover_url : ''
    : '';
  return (
    <div className="global-search" ref={rootRef}>
      <Search size={17} aria-hidden="true" />
      <input
        type="search"
        value={query}
        onFocus={() => setOpen(true)}
        onChange={event => { setQuery(event.target.value); setSelected(null); setActiveIndex(-1); setResult({ books: [], users: [] }); setOpen(true); }}
        onKeyDown={event => {
          if (event.key === 'ArrowDown' && selectableResults.length) {
            event.preventDefault();
            setOpen(true);
            setActiveIndex(index => Math.min(index + 1, selectableResults.length - 1));
          } else if (event.key === 'ArrowUp' && selectableResults.length) {
            event.preventDefault();
            setActiveIndex(index => Math.max(index - 1, 0));
          } else if (event.key === 'Enter') {
            event.preventDefault();
            if (activeIndex >= 0) selectResult(activeIndex);
            else setOpen(true);
          }
        }}
        aria-label={role === 'LIBRARIAN' ? 'Search books and users' : 'Search books'}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open && query.trim().length >= 2}
        aria-controls="global-search-options"
        aria-activedescendant={activeIndex >= 0 ? `global-search-option-${activeIndex}` : undefined}
        placeholder={role === 'LIBRARIAN' ? 'Search books or users…' : 'Search books…'}
      />
      {query && <button type="button" className="global-search-clear" aria-label="Clear search" onClick={() => { setQuery(''); setSelected(null); setOpen(true); }}><X size={15} /></button>}
      {open && query.trim().length >= 2 && (
        <div className="global-search-popover" id="global-search-results" role="region" aria-label="Search results" aria-busy={loading}>
          {loading && <p className="dashboard-search-status" role="status"><LoaderCircle size={15} className="dashboard-spin" /> Searching…</p>}
          {error && <div className="dashboard-search-error" role="alert">{error}<button type="button" onClick={() => setRetry(value => value + 1)}>Retry</button></div>}
          {!loading && !error && !hasResults && <p className="dashboard-search-status">No matching books{role === 'LIBRARIAN' ? ' or users' : ''}.</p>}
          <div className="global-search-options" id="global-search-options" role="listbox" aria-label="Catalogue results">
            {result.books.length > 0 && <div role="group" aria-label="Books">
              <div className="dashboard-search-heading"><BookOpen size={14} /> Books</div>
              {result.books.map((book, index) => <div role="option" aria-selected={activeIndex === index} id={`global-search-option-${index}`} tabIndex={-1} className={`dashboard-search-result${activeIndex === index ? ' active' : ''}`} key={book.id} onMouseEnter={() => setActiveIndex(index)} onClick={() => selectResult(index)}>
                <span><b>{book.title}</b><small>{book.author || 'Author unavailable'} · {book.category}</small></span>
                <em>{book.available > 0 ? `${book.available} available` : 'Unavailable'}</em>
              </div>)}
            </div>}
            {result.users.length > 0 && <div role="group" aria-label="Users">
              <div className="dashboard-search-heading"><UsersRound size={14} /> Users</div>
              {result.users.map((account, index) => {
                const optionIndex = result.books.length + index;
                return <div role="option" aria-selected={activeIndex === optionIndex} id={`global-search-option-${optionIndex}`} tabIndex={-1} className={`dashboard-search-result${activeIndex === optionIndex ? ' active' : ''}`} key={`${account.role}:${account.user_id || account.name}`} onMouseEnter={() => setActiveIndex(optionIndex)} onClick={() => selectResult(optionIndex)}>
                  <span><b>{account.name}</b><small>{account.user_id || 'No user ID'} · {account.role}</small></span>
                  <em>{account.department?.code || '—'}</em>
                </div>;
              })}
            </div>}
          </div>
          {selected && <div className="dashboard-search-detail" aria-live="polite">
            {selected.type === 'book' ? <>
              {selectedCover ? <img src={selectedCover} alt={`Cover of ${selected.item.title}`} className="dashboard-book-cover" loading="lazy" onError={() => setCoverStage(stage => stage === 0 ? 1 : 2)} /> : <div className="dashboard-book-cover-placeholder" role="img" aria-label={`No cover available for ${selected.item.title}`}><BookOpen size={22} /><span>{metadataLoading ? 'Checking cover…' : 'Cover unavailable'}</span></div>}
              <b>{selected.item.title}</b><span>{selected.item.author || metadata?.authors?.join(', ') || 'Author unavailable'} · {selected.item.isbn || 'No ISBN listed'}</span>
              <small>{selected.item.available} of {selected.item.total} copies available · Rack {selected.item.rack || 'not listed'}</small>
              {(metadataLoading || selected.item.description || metadata?.description) && <small>{metadataLoading ? 'Checking publisher metadata…' : selected.item.description || metadata.description}</small>}
              {metadata?.attribution && <small>{metadata.attribution}</small>}
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
