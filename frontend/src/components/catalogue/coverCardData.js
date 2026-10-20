export const getCoverCandidates = (book, metadata) => [...new Set([
  book?.cover_image_ref,
  metadata?.cover_url,
].filter(Boolean))];

export const nextCoverIndex = (current, candidateCount) =>
  Math.min(Math.max(0, current + 1), Math.max(0, candidateCount));

export const coverLookupKey = (isbn, bookId, candidateIndex) =>
  `${isbn || bookId || ''}:${candidateIndex > 0 ? 'image-failed' : 'initial'}`;

export const visibleBookDescription = value => {
  if (typeof value !== 'string') return '';
  const description = value.trim();
  if (/^\[?\s*academic csv provenance\s*:/i.test(description)) return '';
  return description;
};
