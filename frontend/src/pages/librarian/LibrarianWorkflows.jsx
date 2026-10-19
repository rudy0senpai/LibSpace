import { useCallback, useEffect, useState } from 'react';
import { addCatalogueCopy, createCatalogueBook, getLibrarianCatalogue, getLibrarianLoans, getLibrarianSuggestions, returnLibrarianLoan, reviewLibrarianSuggestion, updateCatalogueBook } from '../../services/api';
import BookCoverCard from '../../components/catalogue/BookCoverCard';

export default function LibrarianWorkflows({ page, onChanged }) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('');
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [pageNo, setPageNo] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selected, setSelected] = useState(null);
  const [copyTarget, setCopyTarget] = useState(null);
  const [form, setForm] = useState({ title: '', isbn: '', authors: '', description: '', publication_year: '', publisher: '', category: '' });
  const [copyForm, setCopyForm] = useState({ accession_number: '', barcode: '', rack: '', shelf: '' });

  const load = useCallback(async (nextPage = pageNo) => {
    setLoading(true); setError('');
    try {
      let result;
      if (page === 'catalogue') {
        result = await getLibrarianCatalogue({ q: query, page: nextPage, per_page: 20 });
        setData(result.data?.items || []); setTotal(result.data?.total || 0); setPageNo(nextPage);
      } else if (page === 'return') {
        result = await getLibrarianLoans({ q: query, status }); setData(result.data || []);
      } else {
        result = await getLibrarianSuggestions({ q: query, status }); setData(result.data?.items || []);
      }
    } catch (err) { setError(err.message || 'Unable to load records.'); }
    finally { setLoading(false); }
  }, [page, query, status, pageNo]);
  useEffect(() => { load(1); }, [page]);

  async function saveBook(event) {
    event.preventDefault(); setError(''); setMessage('');
    const payload = { ...form, authors: form.authors.split(',').map(value => value.trim()).filter(Boolean), publication_year: form.publication_year ? Number(form.publication_year) : null };
    try {
      if (selected) await updateCatalogueBook(selected.id, payload);
      else await createCatalogueBook(payload);
      setMessage(selected ? 'Book details saved.' : 'Book added to catalogue.'); setSelected(null); setForm({ title: '', isbn: '', authors: '', description: '', publication_year: '', publisher: '', category: '' }); await load(1); onChanged?.();
    } catch (err) { setError(err.message || 'Unable to save book.'); }
  }
  function editBook(book) { setCopyTarget(null); setSelected(book); setForm({ title: book.title, isbn: book.isbn || '', authors: book.authors.join(', '), description: book.description || '', publication_year: book.publication_year || '', publisher: book.publisher || '', category: book.category || '' }); }
  async function saveCopy(event) {
    event.preventDefault();
    try { await addCatalogueCopy(copyTarget.id, copyForm); setMessage('Copy added and available.'); setCopyForm({ accession_number: '', barcode: '', rack: '', shelf: '' }); setCopyTarget(null); await load(1); onChanged?.(); }
    catch (err) { setError(err.message || 'Unable to add copy.'); }
  }
  async function returnBook(loan) {
    if (!window.confirm(`Record the return of “${loan.book_title}” from ${loan.borrower}?`)) return;
    try { await returnLibrarianLoan(loan.id); setMessage('Return recorded; copy is available again.'); await load(1); onChanged?.(); }
    catch (err) { setError(err.message || 'Unable to record return.'); }
  }
  async function review(item, nextStatus) {
    try { await reviewLibrarianSuggestion(item.id, nextStatus); setMessage(`Suggestion marked ${nextStatus.toLowerCase().replaceAll('_', ' ')}.`); await load(1); }
    catch (err) { setError(err.message || 'Unable to review suggestion.'); }
  }
  const title = page === 'catalogue' ? 'Manage Catalogue' : page === 'return' ? 'Return Books' : 'Suggestion Review';
  return <section className="librarian-workflows" aria-labelledby="workflow-title">
    <h2 id="workflow-title">{title}</h2>
    {message && <p role="status" className="notice success">{message}</p>}
    {error && <p role="alert" className="notice error">{error} <button type="button" onClick={() => load(1)}>Retry</button></p>}
    <div className="prototype-search"><input aria-label={`Search ${title}`} value={query} onChange={e => setQuery(e.target.value)} placeholder={page === 'catalogue' ? 'Search title, author, ISBN' : page === 'return' ? 'Search borrower, user ID, or title' : 'Search suggestion title'} /><button type="button" onClick={() => load(1)} disabled={loading}>{loading ? 'Loading…' : 'Search'}</button>
      {page !== 'catalogue' && <select aria-label="Status filter" value={status} onChange={e => setStatus(e.target.value)}><option value="">{page === 'return' ? 'All statuses' : 'All suggestion statuses'}</option>{(page === 'return' ? ['ACTIVE', 'OVERDUE', 'RETURNED'] : ['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'ORDERED', 'AVAILABLE']).map(s => <option key={s}>{s}</option>)}</select>}
    </div>
    {page === 'catalogue' && <>
      <form className="prototype-suggest librarian-book-form" onSubmit={saveBook}>
        <input aria-label="Book title" placeholder="Title (required)" required value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
        <input aria-label="ISBN" placeholder="ISBN-10 or ISBN-13" value={form.isbn} onChange={e => setForm({ ...form, isbn: e.target.value })} />
        <input aria-label="Authors" placeholder="Authors, comma separated" value={form.authors} onChange={e => setForm({ ...form, authors: e.target.value })} />
        <input aria-label="Publication year" placeholder="Publication year" type="number" min="1400" max="2100" value={form.publication_year} onChange={e => setForm({ ...form, publication_year: e.target.value })} />
        <input aria-label="Publisher" placeholder="Publisher" value={form.publisher} onChange={e => setForm({ ...form, publisher: e.target.value })} />
        <input aria-label="Category" placeholder="Category / subject" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} />
        <textarea aria-label="Book description" placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
        <button type="submit">{selected ? 'Save changes' : 'Add book'}</button>{selected && <button type="button" onClick={() => { setSelected(null); setForm({ title: '', isbn: '', authors: '', description: '', publication_year: '', publisher: '', category: '' }); }}>Cancel edit</button>}
      </form>
    </>}
    {loading && data.length === 0 && <p role="status">Loading records…</p>}
    {!loading && !error && data.length === 0 && <p role="status">No matching records.</p>}
    <div className="librarian-record-list">{data.map(item => page === 'catalogue' ? <div className="librarian-catalogue-record" key={item.id}>
      <BookCoverCard
        key={item.id}
        book={{
          ...item,
          author: item.authors.join(', '),
          total: item.copies.length,
          available: item.copies.filter(copy => copy.status === 'AVAILABLE').length,
          rack: item.copies[0]?.rack || '',
          shelf: item.copies[0]?.shelf || '',
        }}
        actions={<>
          <button type="button" onClick={() => editBook(item)}>Edit metadata</button>
          <button type="button" onClick={() => { setSelected(null); setCopyTarget(item); }}>Manage copies</button>
        </>}
      />
      {copyTarget?.id === item.id && <form className="prototype-suggest" onSubmit={saveCopy}><input required placeholder="Accession number" value={copyForm.accession_number} onChange={e => setCopyForm({ ...copyForm, accession_number: e.target.value })} /><input required placeholder="Barcode" value={copyForm.barcode} onChange={e => setCopyForm({ ...copyForm, barcode: e.target.value })} /><input required placeholder="Rack" value={copyForm.rack} onChange={e => setCopyForm({ ...copyForm, rack: e.target.value })} /><input required placeholder="Shelf" value={copyForm.shelf} onChange={e => setCopyForm({ ...copyForm, shelf: e.target.value })} /><button>Add copy</button></form>}
    </div> : page === 'return' ? <article className="prototype-panel" key={item.id}><h3>{item.book_title}</h3><p>Borrower: {item.borrower} · ID: {item.user_id}</p><p>Issued {new Date(item.issued_at).toLocaleDateString()} · Due {new Date(item.due_at).toLocaleDateString()} · <b>{item.status}</b></p><p>Copy {item.accession_number}</p>{['BORROWED', 'OVERDUE'].includes(item.status) && <button type="button" onClick={() => returnBook(item)}>Record return</button>}</article> : <article className="prototype-panel" key={item.id}><h3>{item.title}</h3><p>{item.author || 'Author not recorded'} · {item.requester} ({item.requester_role}) · {item.votes} votes</p><p>Submitted {new Date(item.submitted_at).toLocaleDateString()} · Status: {item.status}</p><label>Review status <select value={item.status} onChange={e => review(item, e.target.value)}>{['SUBMITTED','UNDER_REVIEW','APPROVED','REJECTED','ORDERED','AVAILABLE'].map(s => <option key={s}>{s}</option>)}</select></label></article>)}</div>
    {page === 'catalogue' && total > 20 && <div className="prototype-action-grid"><button disabled={pageNo <= 1 || loading} onClick={() => load(pageNo - 1)}>Previous</button><span>Page {pageNo} · {total} books</span><button disabled={pageNo * 20 >= total || loading} onClick={() => load(pageNo + 1)}>Next</button></div>}
  </section>;
}
