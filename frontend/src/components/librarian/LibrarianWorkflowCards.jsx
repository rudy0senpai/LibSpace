import { useState } from 'react';
import { AlertTriangle, Book, Calendar, CheckCircle2, Clock, RotateCcw, ThumbsUp, User } from 'lucide-react';

const ALL_SUGGESTION_STATUSES = [
  'SUBMITTED',
  'UNDER_REVIEW',
  'APPROVED',
  'ORDERED',
  'AVAILABLE',
  'REJECTED',
  'DUPLICATE',
  'ALREADY_AVAILABLE',
];
const ACTIVE_LOAN_STATUSES = new Set(['BORROWED', 'OVERDUE']);

const label = value =>
  String(value || 'UNKNOWN')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(/\b\w/g, letter => letter.toUpperCase());

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

export function StatusBadge({ status, kind = 'loan' }) {
  const text = label(status);
  const isOverdue = status === 'OVERDUE';
  return (
    <span
      className={`librarian-status-badge librarian-status-badge--${kind} librarian-status-badge--${classToken(status)}${isOverdue ? ' is-overdue' : ''}`}
      aria-label={`Status: ${text}`}
    >
      {isOverdue && <AlertTriangle size={12} className="librarian-badge-icon" aria-hidden="true" />}
      {status === 'RETURNED' && <CheckCircle2 size={12} className="librarian-badge-icon" aria-hidden="true" />}
      {text}
    </span>
  );
}

export function ReturnLoanCard({ loan, busy, returning, onReturn }) {
  const [confirming, setConfirming] = useState(false);
  const active = ACTIVE_LOAN_STATUSES.has(loan.status);
  const isOverdue = loan.status === 'OVERDUE';
  const isReturned = loan.status === 'RETURNED';

  return (
    <article
      className={`librarian-return-card librarian-record-card${isOverdue ? ' is-overdue' : ''}${isReturned ? ' is-returned' : ''}`}
      aria-labelledby={`loan-${loan.id}-title`}
    >
      <header className="librarian-record-card__header">
        <div className="librarian-return-card__thumb-wrap">
          {loan.cover_image_ref ? (
            <img
              className="librarian-return-card__cover"
              src={loan.cover_image_ref}
              alt=""
              loading="lazy"
              onError={event => {
                event.currentTarget.style.display = 'none';
                if (event.currentTarget.nextSibling) {
                  event.currentTarget.nextSibling.style.display = 'flex';
                }
              }}
            />
          ) : null}
          <div
            className="librarian-return-card__cover-fallback"
            style={{ display: loan.cover_image_ref ? 'none' : 'flex' }}
            aria-hidden="true"
          >
            <Book size={20} />
          </div>
        </div>

        <div className="librarian-record-card__heading">
          <h3 id={`loan-${loan.id}-title`} title={loan.book_title}>
            {loan.book_title || 'Untitled book'}
          </h3>
          <p className="librarian-record-card__copy">
            Copy identifier: <strong className="accession-code">{loan.accession_number || '—'}</strong>
          </p>
        </div>
        <StatusBadge status={loan.status} />
      </header>

      {isOverdue && (
        <div className="librarian-overdue-callout" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <span>
            <strong>Overdue notice:</strong> {dueMessage(loan)}. Follow up with the borrower.
          </span>
        </div>
      )}

      <div className="librarian-record-card__details">
        <section className="librarian-detail-group" aria-label="Borrower details">
          <h4><User size={13} aria-hidden="true" /> Borrower</h4>
          <dl>
            <div>
              <dt>Display name</dt>
              <dd title={loan.borrower}>{loan.borrower || '—'}</dd>
            </div>
            <div>
              <dt>Login ID</dt>
              <dd title={loan.user_id} className="user-id-code">{loan.user_id || '—'}</dd>
            </div>
          </dl>
        </section>

        <section className="librarian-detail-group" aria-label="Loan dates">
          <h4><Calendar size={13} aria-hidden="true" /> Schedule</h4>
          <dl>
            <div>
              <dt>Issued</dt>
              <dd>{formattedDate(loan.issued_at)}</dd>
            </div>
            <div>
              <dt>Due date</dt>
              <dd>{formattedDate(loan.due_at)}</dd>
            </div>
          </dl>
        </section>
      </div>

      <footer className="librarian-record-card__footer">
        <div className={`librarian-due-state${isOverdue ? ' is-overdue' : ''}`} aria-live="polite">
          <Clock size={13} aria-hidden="true" />
          <span>{dueMessage(loan)}</span>
        </div>

        {active ? (
          confirming ? (
            <div className="librarian-confirm-group" role="group" aria-label="Confirm return action">
              <span className="librarian-confirm-prompt">Confirm return?</span>
              <button
                type="button"
                className="librarian-confirm-action"
                disabled={busy || returning}
                onClick={() => {
                  setConfirming(false);
                  onReturn?.();
                }}
              >
                {returning ? 'Recording…' : 'Yes, return'}
              </button>
              <button
                type="button"
                className="librarian-cancel-action"
                disabled={busy || returning}
                onClick={() => setConfirming(false)}
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="librarian-primary-action"
              disabled={busy || returning}
              onClick={() => setConfirming(true)}
              aria-label={`Record return for ${loan.book_title || 'book'}, copy ${loan.accession_number || ''}`}
            >
              <RotateCcw size={14} aria-hidden="true" />
              {returning ? 'Recording return…' : 'Record return'}
            </button>
          )
        ) : (
          <span className="librarian-record-card__no-action">
            {isReturned ? 'Returned' : 'No return action available'}
          </span>
        )}
      </footer>
    </article>
  );
}

export function SuggestionReviewCard({ item, busy, reviewing, onReview }) {
  const statusId = `suggestion-${item.id}-review-status`;
  const savedDate = formattedDate(item.submitted_at || item.created_at);

  return (
    <article
      className="librarian-suggestion-card librarian-record-card"
      aria-labelledby={`suggestion-${item.id}-title`}
    >
      <header className="librarian-record-card__header librarian-suggestion-card__header">
        <div className="librarian-record-card__heading">
          <h3 id={`suggestion-${item.id}-title`} title={item.title}>
            {item.title || 'Untitled suggestion'}
          </h3>
          <p className="librarian-suggestion-card__author" title={item.author}>
            By <strong>{item.author || 'Author not recorded'}</strong>
          </p>
        </div>
        <StatusBadge status={item.status} kind="suggestion" />
      </header>

      <div className="librarian-suggestion-card__meta">
        <div className="librarian-meta-cell">
          <span className="meta-label">Requester</span>
          <strong className="meta-value" title={item.requester}>{item.requester || '—'}</strong>
          <small className="meta-sub">{label(item.requester_role)}</small>
        </div>
        <div className="librarian-meta-cell">
          <span className="meta-label">Department / Programme</span>
          <strong className="meta-value" title={item.department || ''}>{item.department || 'Not recorded'}</strong>
        </div>
        <div className="librarian-meta-cell">
          <span className="meta-label">Submitted</span>
          <strong className="meta-value">{savedDate}</strong>
        </div>
        <div
          className="librarian-vote-count"
          aria-label={`${Number(item.votes) || 0} votes`}
        >
          <ThumbsUp size={15} aria-hidden="true" />
          <div className="vote-num-group">
            <strong>{Number(item.votes) || 0}</strong>
            <span>votes</span>
          </div>
        </div>
      </div>

      {item.reason && (
        <div className="librarian-suggestion-card__reason">
          <h4>Reason for request</h4>
          <p title={item.reason}>{item.reason}</p>
        </div>
      )}

      <footer className="librarian-suggestion-card__footer">
        <div className="librarian-status-selector-wrap">
          <label htmlFor={statusId}>Review status</label>
          <select
            id={statusId}
            aria-label={`Review status for ${item.title}`}
            value={item.status || ''}
            disabled={busy || reviewing}
            onChange={event => {
              const nextStatus = event.target.value;
              if (nextStatus && nextStatus !== item.status) {
                onReview(item, nextStatus);
              }
            }}
          >
            {ALL_SUGGESTION_STATUSES.map(s => (
              <option key={s} value={s}>
                {label(s)}
              </option>
            ))}
          </select>
        </div>
        {reviewing && (
          <span className="librarian-saving-status" role="status" aria-live="polite">
            Saving changes…
          </span>
        )}
      </footer>
    </article>
  );
}
