import { Loader2, RotateCw, XCircle } from 'lucide-react';

const statusLabel = {
  REQUESTED: 'Awaiting approval',
  APPROVED: 'Approved — awaiting issue',
  BORROWED: 'Currently borrowed',
  OVERDUE: 'Overdue',
  REJECTED: 'Rejected',
  CANCELLED: 'Cancelled',
  RETURNED: 'Returned',
};

export default function RequestedBooks({ loans, loading, error, onRetry, onCancel, cancellingId }) {
  return (
    <section className="prototype-panel">
      <div className="prototype-panel-head">
        <b>Requested Books</b>
        <button type="button" onClick={onRetry} aria-label="Refresh requested books" disabled={loading}>
          {loading ? <Loader2 size={15} className="spin" /> : <RotateCw size={15} />}
        </button>
      </div>
      <div className="prototype-panel-body" aria-live="polite">
        {loading && loans.length === 0 && <p className="prototype-muted">Loading your requests…</p>}
        {error && <div className="notice error" role="alert">{error} <button type="button" onClick={onRetry}>Retry</button></div>}
        {!loading && !error && loans.length === 0 && (
          <p className="prototype-muted">No requests or loan history yet. Browse the catalogue to request a book.</p>
        )}
        {loans.map(loan => {
          const canCancel = loan.status === 'REQUESTED' || loan.status === 'APPROVED';
          return (
            <article className="prototype-book-row" key={loan.id}>
              <div>
                <b>{loan.book_title}</b>
                <small>{loan.book_author || 'Author information unavailable'}</small>
                <small>Requested: {loan.request_submitted_at ? new Date(loan.request_submitted_at).toLocaleDateString() : '—'}</small>
                {loan.issued_at && <small>Issued: {new Date(loan.issued_at).toLocaleDateString()}</small>}
                {loan.due_at && <small>Due: {new Date(loan.due_at).toLocaleDateString()}</small>}
              </div>
              <span className={`loan-status loan-status-${loan.status.toLowerCase()}`}>{statusLabel[loan.status] || loan.status}</span>
              {canCancel && <button type="button" disabled={cancellingId === loan.id} onClick={() => onCancel(loan.id)}>
                {cancellingId === loan.id ? <Loader2 size={15} className="spin" /> : <><XCircle size={15} /> Cancel</>}
              </button>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
