import { useEffect, useMemo, useRef, useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react';
import { lookupBookCover } from '../../services/api';
import { lookupBookMetadata } from '../../services/metadataService';

const display = value => value == null || value === '' ? 'Not listed' : value;
export const getCoverCandidates = (book, metadata) => [...new Set([
  book?.cover_image_ref,
  metadata?.cover_url,
].filter(Boolean))];
const yearFrom = value => {
  const match = String(value || '').match(/\b(1[4-9]\d{2}|20\d{2}|2100)\b/);
  return match?.[0] || '';
};

export default function BookCoverCard({ book, actions = null, position, setSize, expanded: expandedProp, onExpandedChange }) {
  const cardRef = useRef(null);
  const [localExpanded, setLocalExpanded] = useState(false);
  const expanded = typeof expandedProp === 'boolean' ? expandedProp : localExpanded;
  const [inViewport, setInViewport] = useState(false);
  const [coverIndex, setCoverIndex] = useState(0);
  const [metadata, setMetadata] = useState(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const requestedISBN = useRef('');
  const title = book.title || 'Untitled book';
  const isbn = book.isbn || '';

  useEffect(() => {
    const element = cardRef.current;
    if (!element) return undefined;
    if (typeof IntersectionObserver === 'undefined') {
      setInViewport(true);
      return undefined;
    }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setInViewport(true);
        observer.disconnect();
      }
    }, { rootMargin: '240px' });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const requestKey = isbn || book.id;
    if (!inViewport || !requestKey || (book.cover_image_ref && coverIndex === 0) || requestedISBN.current === requestKey) return undefined;
    requestedISBN.current = requestKey;
    let active = true;
    setMetadataLoading(true);
    const metadataPromise = isbn ? lookupBookMetadata(isbn) : Promise.resolve(null);
    const coverPromise = lookupBookCover(book.id).catch(() => null);
    Promise.all([metadataPromise, coverPromise]).then(([details, coverResult]) => {
      if (!active) return;
      const cover = coverResult?.data;
      setMetadata({
        ...(details || {}),
        cover_url: cover?.cover_url || null,
        attribution: cover?.source ? `Cover source: ${cover.source.replaceAll('_', ' ')}.` : details?.attribution,
      });
    }).finally(() => {
      if (active) setMetadataLoading(false);
    });
    return () => { active = false; };
  }, [book.cover_image_ref, book.id, coverIndex, inViewport, isbn]);

  const coverSources = useMemo(() => getCoverCandidates(book, metadata), [book.cover_image_ref, metadata]);
  const coverUrl = coverSources[coverIndex] || '';
  const authors = book.author || metadata?.authors?.join(', ') || '';
  const publisher = book.publisher || metadata?.publisher || '';
  const year = book.publication_year || yearFrom(metadata?.published_date);
  const category = book.category || metadata?.categories?.[0] || 'Uncategorized';
  const description = book.description || metadata?.description || '';
  const toggleExpanded = () => {
    const next = !expanded;
    if (typeof expandedProp !== 'boolean') setLocalExpanded(next);
    onExpandedChange?.(next);
  };
  const handleToggleKeyDown = event => {
    if ((event.key === 'Enter' || event.key === ' ') && !event.repeat) {
      event.preventDefault();
      toggleExpanded();
    }
  };
  const statusClass = Number(book.available) > 0 ? 'available' : 'unavailable';
  const detailId = `book-card-details-${String(book.id || title).replace(/[^a-zA-Z0-9_-]/g, '-')}`;

  return (
    <article className={`book-cover-card${expanded ? ' is-expanded' : ''}`} ref={cardRef} role={position == null ? undefined : 'listitem'} aria-posinset={position} aria-setsize={setSize} aria-label={title}>
      <header className="book-cover-card__header">
        <h3>{title}</h3>
        <button
          type="button"
          className="book-cover-card__toggle"
          aria-label={`${expanded ? 'Collapse' : 'Expand'} details for ${title}`}
          aria-expanded={expanded}
          aria-controls={detailId}
          onKeyDown={handleToggleKeyDown}
          onClick={toggleExpanded}
        >
          {expanded ? <ChevronUp size={18} aria-hidden="true" /> : <ChevronDown size={18} aria-hidden="true" />}
        </button>
      </header>
      <div className="book-cover-card__visual">
        <div className="book-cover-card__image-frame">
          {coverUrl ? (
            <img
              src={coverUrl}
              alt={`Cover of ${title}`}
              loading="lazy"
              decoding="async"
              onError={() => setCoverIndex(index => index + 1)}
            />
          ) : (
            <div className="book-cover-card__placeholder" role="img" aria-label={`No cover available for ${title}`}>
              <BookOpen size={28} aria-hidden="true" />
              <span>{metadataLoading ? 'Finding cover…' : 'Cover unavailable'}</span>
            </div>
          )}
        </div>
        <div className="book-cover-card__subject" title={category}><span>{category}</span></div>
      </div>
      <div className="book-cover-card__status">
        <span className={`book-cover-card__availability ${statusClass}`}>
          {Number(book.available) > 0 ? `${book.available} available` : 'Not available'}
        </span>
        <span>{book.total ?? 0} total copies</span>
      </div>
      <div
        id={detailId}
        className="book-cover-card__details"
        aria-hidden={!expanded}
        {...(expanded ? {} : { inert: '' })}
      >
        <div className="book-cover-card__details-inner">
          <dl>
            <div><dt>Author</dt><dd>{display(authors)}</dd></div>
            <div><dt>ISBN</dt><dd>{display(isbn)}</dd></div>
            <div><dt>Publisher / year</dt><dd>{[publisher, year].filter(Boolean).join(' · ') || 'Not listed'}</dd></div>
            <div><dt>Location</dt><dd>{[book.rack, book.shelf].filter(Boolean).join(' · ') || 'Not listed'}</dd></div>
          </dl>
          <p className="book-cover-card__description">{description || (metadataLoading ? 'Checking publisher metadata…' : 'No description available.')}</p>
          {metadata?.attribution && <small className="book-cover-card__attribution">{metadata.attribution}</small>}
          {actions && <div className="book-cover-card__actions">{actions}</div>}
        </div>
      </div>
    </article>
  );
}
