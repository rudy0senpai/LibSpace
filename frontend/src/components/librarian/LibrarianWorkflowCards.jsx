const REVIEWABLE_STATUSES = ['UNDER_REVIEW', 'APPROVED', 'REJECTED', 'ORDERED', 'AVAILABLE'];
const ACTIVE_LOAN_STATUSES = new Set(['BORROWED', 'OVERDUE']);
const label = value => String(value || 'UNKNOWN').replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());
const classToken = value => String(value || 'unknown').toLowerCase().replace(/[^a-z0-9_-]+/g, '-');
const formattedDate = value => {
  const parsed = value ? new Date(value) : null;
  return parsed && !Number.isNaN(parsed.getTime())
    ? new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(parsed)
    : '—';
};

function dueMessage(loan) {
  if (!ACTIVE_LOAN_STATUSES.has(loan.status)) return label(loan.status);
  const due = new Date(loan.due_at);
  if (Number.isNaN(due.getTime())) return 'Due date unavailable';
  const difference = due.getTime() - Date.now();
  if (Math.abs(difference) < 86400000 && difference >= 0) return 'Due today';
  const days = Math.ceil(Math.abs(difference) / 86400000);
  return difference < 0 ? `${days} day${days === 1 ? '' : 's'} overdue` : `Due in ${days} day${days === 1 ? '' : 's'}`;
}

function StatusBadge({ status, kind = 'loan' }) {
  const text = label(status);
  return <span className={`librarian-status-badge librarian-status-badge--${kind} librarian-status-badge--${classToken(status)}`} aria-label={`Status: ${text}`}>{text}</span>;
}

export function ReturnLoanCard({ loan, busy, returning, onReturn }) {
  const active = ACTIVE_LOAN_STATUSES.has(loan.status);
  return (
    <article className={`librarian-return-card librarian-record-card${loan.status === 'OVERDUE' ? ' is-overdue' : ''}`} aria-labelledby={`loan-${loan.id}-title`}>
      <header className="librarian-record-card__header">
        {loan.cover_image_ref && <img className="librarian-return-card__cover" src={loan.cover_image_ref} alt="" loading="lazy" onError={event => { event.currentTarget.hidden = true; }} />}
        <div className="librarian-record-card__heading">
          <h3 id={`loan-${loan.id}-title`} title={loan.book_title}>{loan.book_title || 'Untitled book'}</h3>
          <p className="librarian-record-card__copy">Copy <strong>{loan.accession_number || '—'}</strong></p>
        </div>
        <StatusBadge status={loan.status} />
      </header>
      {loan.status === 'OVERDUE' && <p className="librarian-overdue-callout"><strong>Overdue:</strong> {dueMessage(loan)}. Follow up with the borrower.</p>}
      <div className="librarian-record-card__details">
        <section aria-label="Borrower details">
          <h4>Borrower</h4>
          <dl>
            <div><dt>Name</dt><dd title={loan.borrower}>{loan.borrower || '—'}</dd></div>
            <div><dt>User ID</dt><dd title={loan.user_id}>{loan.user_id || '—'}</dd></div>
          </dl>
        </section>
        <section aria-label="Loan dates">
          <h4>Loan dates</h4>
          <dl>
            <div><dt>Issued</dt><dd>{formattedDate(loan.issued_at)}</dd></div>
            <div><dt>Due</dt><dd>{formattedDate(loan.due_at)}</dd></div>
          </dl>
        </section>
      </div>
      <footer className="librarian-record-card__footer">
        <span className={`librarian-due-state${loan.status === 'OVERDUE' ? ' is-overdue' : ''}`} aria-live="polite">{dueMessage(loan)}</span>
        {active
          ? <button type="button" className="librarian-primary-action" disabled={busy} onClick={onReturn}>{returning ? 'Recording return…' : 'Record return'}</button>
          : <span className="librarian-record-card__no-action">No active return action</span>}
      </footer>
    </article>
  );
}

export function SuggestionReviewCard({ item, busy, reviewing, onReview }) {
  const statusId = `suggestion-${item.id}-review-status`;
  const savedDate = formattedDate(item.submitted_at);
  return (
    <article className="librarian-suggestion-card librarian-record-card" aria-labelledby={`suggestion-${item.id}-title`}>
      <header className="librarian-record-card__header librarian-suggestion-card__header">
        <div className="librarian-record-card__heading">
          <h3 id={`suggestion-${item.id}-title`} title={item.title}>{item.title || 'Untitled suggestion'}</h3>
          <p className="librarian-suggestion-card__author">{item.author || 'Author not recorded'}</p>
        </div>
        <StatusBadge status={item.status} kind="suggestion" />
      </header>
      <div className="librarian-suggestion-card__meta">
        <div><span>Requester</span><strong title={item.requester}>{item.requester || '—'}</strong><small>{label(item.requester_role)}</small></div>
        <div><span>Department / programme</span><strong title={item.department || ''}>{item.department || 'Not recorded'}</strong></div>
        <div><span>Submitted</span><strong>{savedDate}</strong></div>
        <div className="librarian-vote-count" aria-label={`${Number(item.votes) || 0} votes`}><strong>{Number(item.votes) || 0}</strong><span>Votes</span></div>
      </div>
      {item.reason && <div className="librarian-suggestion-card__reason"><h4>Reason</h4><p title={item.reason}>{item.reason}</p></div>}
      <footer className="librarian-suggestion-card__footer">
        <label htmlFor={statusId}>Change review status</label>
        <select id={statusId} aria-label={`Review status for ${item.title}`} value="" disabled={busy} onChange={event => onReview(item, event.target.value)}>
          <option value="">Choose a supported status…</option>
          {REVIEWABLE_STATUSES.map(status => <option key={status} value={status}>{label(status)}</option>)}
        </select>
        {reviewing && <span className="librarian-saving-status" role="status">Saving review status…</span>}
      </footer>
    </article>
  );
}
