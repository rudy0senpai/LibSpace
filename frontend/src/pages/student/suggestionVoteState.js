function updateSuggestion(items, suggestionId, update) {
  return items.map(item => item.id === suggestionId ? update(item) : item);
}

export function optimisticallyToggleSuggestionVote(items, suggestionId) {
  return updateSuggestion(items, suggestionId, item => {
    const voted = !item.voted_by_me;
    return { ...item, voted_by_me: voted, votes: Math.max(0, Number(item.votes || 0) + (voted ? 1 : -1)) };
  });
}

export function applySuggestionVoteResponse(items, suggestionId, result) {
  return updateSuggestion(items, suggestionId, item => ({
    ...item,
    voted_by_me: Boolean(result?.voted),
    votes: Math.max(0, Number(result?.vote_count || 0)),
  }));
}

export function restoreSuggestionVote(items, suggestionId, previous) {
  return updateSuggestion(items, suggestionId, item => ({ ...item, ...previous }));
}
