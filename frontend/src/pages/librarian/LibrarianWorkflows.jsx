import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { addCatalogueCopy, createCatalogueBook, getCatalogueAvailability, getLibrarianCatalogue, getLibrarianLoans, getLibrarianSuggestions, returnLibrarianLoan, reviewLibrarianSuggestion, updateCatalogueAvailability, updateCatalogueBook } from '../../services/api';
import BookCoverCard from '../../components/catalogue/BookCoverCard';
import { ReturnLoanCard, SuggestionReviewCard } from '../../components/librarian/LibrarianWorkflowCards';

const emptyBookForm = () => ({ title: '', isbn: '', authors: '', description: '', publication_year: '', edition: '', language: 'English', publisher: '', departments: '', category: '', cover_image_ref: '', source_metadata: {} });
const statusLabel = value => String(value || 'UNKNOWN').replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());

const validIsbn = value => {
  const isbn = String(value || '').replace(/[-\s]/g, '').toUpperCase();
  if (!isbn) return true;
  if (/^\d{9}[\dX]$/.test(isbn)) return [...isbn].reduce((sum, char, i) => sum + (10 - i) * (char === 'X' ? 10 : Number(char)), 0) % 11 === 0;
  return /^\d{13}$/.test(isbn) && [...isbn].reduce((sum, char, i) => sum + Number(char) * (i % 2 ? 3 : 1), 0) % 10 === 0;
};

function WorkflowModal({ title, labelledBy, children, onClose }) {
  const dialogRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement;
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialogRef.current?.focus();
    const onKeyDown = event => {
      if (event.key === 'Escape') { event.preventDefault(); onCloseRef.current(); }
      if (event.key === 'Tab' && dialogRef.current) {
        const items = [...dialogRef.current.querySelectorAll('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex="0"]')];
        if (!items.length) return;
        const first = items[0], last = items.at(-1), active = document.activeElement;
        if (event.shiftKey && (active === first || active === dialogRef.current || !dialogRef.current.contains(active))) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && (active === last || active === dialogRef.current || !dialogRef.current.contains(active))) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => { document.body.style.overflow = oldOverflow; document.removeEventListener('keydown', onKeyDown); previous?.focus?.(); };
  }, []);
  const theme = document.querySelector('.dashboard-app')?.getAttribute('data-theme') === 'night' ? 'night' : 'light';
  return createPortal(<div className="catalogue-modal-backdrop" data-theme={theme} onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}><section className="catalogue-modal" role="dialog" aria-modal="true" aria-labelledby={labelledBy} tabIndex={-1} ref={dialogRef}><header className="catalogue-modal__header"><h2 id={labelledBy}>{title}</h2><button type="button" className="catalogue-modal__close" aria-label="Close dialog" onClick={onClose}>×</button></header>{children}</section></div>, document.body);
}

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
  const [createOpen, setCreateOpen] = useState(false);
  const [copyTarget, setCopyTarget] = useState(null);
  const [form, setForm] = useState(emptyBookForm);
  const [savedForm, setSavedForm] = useState(null);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [returningId, setReturningId] = useState('');
  const [reviewingId, setReviewingId] = useState('');
  const [availability, setAvailability] = useState(null);
  const [availabilityChoice, setAvailabilityChoice] = useState(true);
  const [availabilityReason, setAvailabilityReason] = useState('');
  const [availabilityError, setAvailabilityError] = useState('');
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [copyForm, setCopyForm] = useState({ accession_number: '', barcode: '', rack: '', shelf: '' });

  const load = useCallback(async (nextPage = pageNo) => {
    setLoading(true); setError('');
    try {
      let result;
      if (page === 'catalogue') {
        result = await getLibrarianCatalogue({ q: query, page: nextPage, per_page: 20 });
        setData(result.data?.items || []); setTotal(result.data?.total || 0);
      } else if (page === 'return') {
        result = await getLibrarianLoans({ q: query, status, page: nextPage, per_page: 20 });
        setData(result.data?.items || []); setTotal(result.data?.total || 0);
      } else {
        result = await getLibrarianSuggestions({ q: query, status, page: nextPage, per_page: 20 });
        setData(result.data?.items || []); setTotal(result.data?.total || 0);
      }
      setPageNo(nextPage);
    } catch (err) { setError(err.message || 'Unable to load records.'); }
    finally { setLoading(false); }
  }, [page, query, status, pageNo]);
  useEffect(() => { load(1); }, [page]);

  function closeBookModal(force = false) {
    const dirty = JSON.stringify(form) !== JSON.stringify(savedForm);
    if (!force && dirty && !window.confirm('Discard unsaved changes?')) return;
    setSelected(null); setCreateOpen(false); setForm(emptyBookForm()); setSavedForm(null); setFormError('');
  }
  function editBook(book) {
    setCopyTarget(null); setCreateOpen(false); setSelected(book);
    const value = { title: book.title || '', isbn: book.isbn || '', authors: (book.authors || []).join(', '), description: book.description || '', publication_year: book.publication_year || '', edition: book.edition || '', language: book.language || 'English', publisher: book.publisher || '', departments: (book.departments || []).map(item => item.name).join(', '), category: book.category || '', cover_image_ref: book.cover_image_ref || '', source_metadata: book.source_metadata || {} };
    setForm(value); setSavedForm(value); setFormError('');
  }
  function openCreate() { const value = emptyBookForm(); setSelected(null); setCreateOpen(true); setForm(value); setSavedForm(value); setFormError(''); }
  async function saveBook(event) {
    event.preventDefault(); setFormError('');
    if (!form.title.trim()) { setFormError('Book title is required.'); return; }
    if (form.isbn && !validIsbn(form.isbn)) { setFormError('Enter a valid ISBN-10 or ISBN-13 checksum.'); return; }
    setSaving(true);
    const payload = { ...form, authors: form.authors.split(',').map(value => value.trim()).filter(Boolean), departments: form.departments.split(',').map(value => value.trim()).filter(Boolean), publication_year: form.publication_year ? Number(form.publication_year) : null };
    try {
      if (selected) {
        const result = await updateCatalogueBook(selected.id, payload);
        setData(previous => previous.map(book => book.id === selected.id ? { ...book, ...result.data } : book)); setMessage('Book metadata saved.');
      } else { await createCatalogueBook(payload); setMessage('Book added to catalogue.'); await load(1); }
      closeBookModal(true); onChanged?.();
    } catch (err) { setFormError(err.message || 'Unable to save book metadata.'); }
    finally { setSaving(false); }
  }
  async function openAvailability(book) {
    setAvailabilityError(''); setAvailabilityLoading(true); setAvailability({ book, summary: null });
    try { const result = await getCatalogueAvailability(book.id); const summary = result.data; setAvailability({ book, summary }); setAvailabilityChoice(summary.available_copies > 0); setAvailabilityReason(''); }
    catch (err) { setAvailabilityError(err.message || 'Unable to load availability.'); }
    finally { setAvailabilityLoading(false); }
  }
  function closeAvailability(force = false) {
    const dirty = Boolean(availability?.summary) && (availabilityChoice !== (availability.summary.available_copies > 0) || availabilityReason.trim() !== '');
    if (!force && dirty && !window.confirm('Discard unsaved availability changes?')) return;
    setAvailability(null); setAvailabilityError(''); setAvailabilityReason('');
  }
  async function saveAvailability(event) {
    event.preventDefault(); if (!availability) return;
    setAvailabilityLoading(true); setAvailabilityError('');
    try {
      const result = await updateCatalogueAvailability(availability.book.id, { available: availabilityChoice, reason: availabilityReason });
      const summary = result.data;
      setData(previous => previous.map(book => book.id === availability.book.id ? { ...book, copies: (summary.copy_states || []).map(copy => ({ ...copy })) } : book));
      setMessage(`Availability updated for “${summary.title}”.`); onChanged?.(); closeAvailability(true);
    } catch (err) { setAvailabilityError(err.message || 'Unable to update availability.'); }
    finally { setAvailabilityLoading(false); }
  }
  async function saveCopy(event) {
    event.preventDefault();
    try { await addCatalogueCopy(copyTarget.id, copyForm); setMessage('Copy added and available.'); setCopyForm({ accession_number: '', barcode: '', rack: '', shelf: '' }); setCopyTarget(null); await load(1); onChanged?.(); }
    catch (err) { setError(err.message || 'Unable to add copy.'); }
  }
  async function returnBook(loan) {
    const prompt = `Record return for “${loan.book_title}” from ${loan.borrower} (${loan.user_id}), copy ${loan.accession_number}?`;
    if (!window.confirm(prompt)) return;
    setReturningId(loan.id); setError(''); setMessage('');
    try {
      await returnLibrarianLoan(loan.id);
      setMessage(`Return recorded for “${loan.book_title}”.`);
      await load(1);
      onChanged?.();
    } catch (err) {
      setError(err.message || 'Unable to record return.');
    } finally {
      setReturningId('');
    }
  }
  async function review(item, nextStatus) {
    if (!nextStatus || reviewingId) return;
    setReviewingId(item.id); setError(''); setMessage('');
    try {
      const result = await reviewLibrarianSuggestion(item.id, nextStatus);
      const saved = result.data || result;
      setData(previous => previous.map(row => row.id === item.id ? { ...row, status: saved.status || nextStatus } : row));
      setMessage(`Suggestion marked ${String(saved.status || nextStatus).toLowerCase().replaceAll('_', ' ')}.`);
      onChanged?.();
    } catch (err) {
      setError(err.message || 'Unable to review suggestion.');
    } finally {
      setReviewingId('');
    }
  }
  const title = page === 'catalogue' ? 'Manage Catalogue' : page === 'return' ? 'Return Books' : 'Suggestion Review';
  return <section className="librarian-workflows" aria-labelledby="workflow-title">
    <h2 id="workflow-title">{title}</h2>
    {message && <p role="status" className="notice success">{message}</p>}
    {error && <p role="alert" className="notice error">{error} <button type="button" onClick={() => load(1)}>Retry</button></p>}
    <div className="prototype-search"><input aria-label={`Search ${title}`} value={query} onChange={e => setQuery(e.target.value)} placeholder={page === 'catalogue' ? 'Search title, author, ISBN' : page === 'return' ? 'Search borrower, user ID, or title' : 'Search suggestion title, author, or requester'} /><button type="button" onClick={() => load(1)} disabled={loading}>{loading ? 'Loading…' : 'Search'}</button>
      {page === 'catalogue' && <button type="button" onClick={openCreate}>Add book</button>}
      {page !== 'catalogue' && <select aria-label="Status filter" value={status} onChange={e => setStatus(e.target.value)}><option value="">{page === 'return' ? 'All statuses' : 'All suggestion statuses'}</option>{(page === 'return' ? ['ACTIVE', 'OVERDUE', 'REQUESTED', 'APPROVED', 'BORROWED', 'RETURNED', 'REJECTED', 'CANCELLED', 'LOST', 'DAMAGED'] : ['SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'DUPLICATE', 'ORDERED', 'AVAILABLE', 'ALREADY_AVAILABLE']).map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}</select>}
    </div>
    {loading && data.length === 0 && <p role="status">Loading records…</p>}
    {!loading && !error && data.length === 0 && <p role="status">No matching records.</p>}
    <div className="librarian-record-list">{data.map(item => page === 'catalogue' ? <div className="librarian-catalogue-record" key={item.id}>
      <BookCoverCard
        key={item.id}
        book={{ ...item, author: (item.authors || []).join(', '), description: item.description || 'No description available.', total: (item.copies || []).length, available: (item.copies || []).filter(copy => copy.status === 'AVAILABLE').length, rack: item.copies?.[0]?.rack || '', shelf: item.copies?.[0]?.shelf || '' }}
        actions={<>
          <button type="button" onClick={() => editBook(item)}>Edit metadata</button>
          <button type="button" onClick={() => openAvailability(item)}>Manage availability</button>
          <button type="button" onClick={() => { setSelected(null); setCopyTarget(item); }}>Manage copies</button>
        </>}
      />
      {copyTarget?.id === item.id && <form className="prototype-suggest" onSubmit={saveCopy}><input required placeholder="Accession number" value={copyForm.accession_number} onChange={e => setCopyForm({ ...copyForm, accession_number: e.target.value })} /><input required placeholder="Barcode" value={copyForm.barcode} onChange={e => setCopyForm({ ...copyForm, barcode: e.target.value })} /><input required placeholder="Rack" value={copyForm.rack} onChange={e => setCopyForm({ ...copyForm, rack: e.target.value })} /><input required placeholder="Shelf" value={copyForm.shelf} onChange={e => setCopyForm({ ...copyForm, shelf: e.target.value })} /><button>Add copy</button></form>}
    </div> : page === 'return' ? <ReturnLoanCard key={item.id} loan={item} busy={Boolean(returningId)} returning={returningId === item.id} onReturn={() => returnBook(item)} /> : <SuggestionReviewCard key={item.id} item={item} busy={Boolean(reviewingId)} reviewing={reviewingId === item.id} onReview={review} />)}</div>
    {total > 20 && <nav className="librarian-workflow-pagination" aria-label={`${title} pagination`}><button type="button" disabled={pageNo <= 1 || loading} onClick={() => load(pageNo - 1)}>Previous</button><span>Page {pageNo} of {Math.ceil(total / 20)} · {total} {page === 'catalogue' ? 'books' : page === 'return' ? 'loans' : 'suggestions'}</span><button type="button" disabled={pageNo * 20 >= total || loading} onClick={() => load(pageNo + 1)}>Next</button></nav>}
    {(selected || createOpen) && <WorkflowModal title={selected ? 'Edit Book Metadata' : 'Add a Book'} labelledBy="book-metadata-title" onClose={() => closeBookModal()}>
      <form className="catalogue-modal__form" onSubmit={saveBook}><div className="catalogue-modal__body">
        {formError && <p className="catalogue-modal__error" role="alert">{formError}</p>}
        <fieldset><legend>Bibliographic details</legend><div className="catalogue-modal__grid">
          <label>Book title *<input required maxLength="300" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></label>
          <label>Author(s)<input value={form.authors} onChange={e => setForm({ ...form, authors: e.target.value })} placeholder="Comma-separated" /></label>
          <label>ISBN<input value={form.isbn} onChange={e => setForm({ ...form, isbn: e.target.value })} /></label>
          <label>Publisher<input value={form.publisher} onChange={e => setForm({ ...form, publisher: e.target.value })} /></label>
          <label>Publication year<input type="number" min="1400" max="2100" value={form.publication_year} onChange={e => setForm({ ...form, publication_year: e.target.value })} /></label>
          <label>Edition<input maxLength="80" value={form.edition} onChange={e => setForm({ ...form, edition: e.target.value })} /></label>
          <label>Language<input maxLength="80" value={form.language} onChange={e => setForm({ ...form, language: e.target.value })} /></label>
          <label>Programme / department<input value={form.departments} onChange={e => setForm({ ...form, departments: e.target.value })} placeholder="Comma-separated names or codes" /></label>
          <label>Subject area / category<input value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} /></label>
          <label className="catalogue-modal__wide">Cover URL<input type="url" value={form.cover_image_ref} onChange={e => setForm({ ...form, cover_image_ref: e.target.value })} placeholder="https://…" /></label>
          <label className="catalogue-modal__wide">Description<textarea rows="4" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="No description available." /></label>
        </div></fieldset>
        {selected && Object.keys(form.source_metadata || {}).length > 0 && <details className="catalogue-source-metadata"><summary>Source metadata (optional)</summary><pre>{JSON.stringify(form.source_metadata, null, 2)}</pre></details>}
      </div><footer className="catalogue-modal__footer"><button type="button" onClick={() => closeBookModal()}>Cancel</button><button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button></footer></form>
    </WorkflowModal>}
    {availability && <WorkflowModal title="Manage Book Availability" labelledBy="availability-modal-title" onClose={() => closeAvailability()}>
      <form className="catalogue-modal__form" onSubmit={saveAvailability}><div className="catalogue-modal__body">
        {availabilityError && <p className="catalogue-modal__error" role="alert">{availabilityError}</p>}
        <h3>{availability.book.title}</h3><p>ISBN: {availability.book.isbn || 'Not recorded'}</p>
        {availabilityLoading && <p role="status">Loading availability…</p>}
        {availability.summary && <dl className="availability-summary"><div><dt>Total physical copies</dt><dd>{availability.summary.total_copies}</dd></div><div><dt>Available copies</dt><dd>{availability.summary.available_copies}</dd></div><div><dt>Borrowed copies</dt><dd>{availability.summary.borrowed_copies}</dd></div><div><dt>Reserved copies</dt><dd>{availability.summary.reserved_copies}</dd></div><div><dt>Active reservations</dt><dd>{availability.summary.active_reservations ?? 0}</dd></div><div><dt>Catalogue status</dt><dd>{availability.summary.availability_status === 'AVAILABLE' ? 'Available' : 'Not available'}</dd></div></dl>}
        <label className="availability-choice">Availability status<select value={availabilityChoice ? 'available' : 'unavailable'} onChange={e => setAvailabilityChoice(e.target.value === 'available')}><option value="available" disabled={availability.summary?.available_copies === 0 && availability.summary?.held_copies === 0}>Available</option><option value="unavailable">Unavailable</option></select></label>
        {!availabilityChoice && <label>Reason (optional)<textarea rows="3" maxLength="300" value={availabilityReason} onChange={e => setAvailabilityReason(e.target.value)} placeholder="Why are the available copies temporarily unavailable?" /></label>}
        {availability.summary?.total_copies === 0 && <p>No physical copies exist. <button type="button" onClick={() => { const target = availability.book; closeAvailability(true); setCopyTarget(target); }}>Manage copies to add one before marking available.</button></p>}
      </div><footer className="catalogue-modal__footer"><button type="button" onClick={() => closeAvailability()}>Cancel</button><button type="submit" disabled={availabilityLoading}>{availabilityLoading ? 'Saving…' : 'Save availability'}</button></footer></form>
    </WorkflowModal>}
  </section>;
}
