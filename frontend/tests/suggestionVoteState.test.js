import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { optimisticallyToggleSuggestionVote, applySuggestionVoteResponse, restoreSuggestionVote } from '../src/pages/student/suggestionVoteState.js';

const initial = [
  { id: 's-1', votes: 4, voted_by_me: false, title: 'Book A' },
  { id: 's-2', votes: 2, voted_by_me: true, title: 'Book B' },
];

test('optimistic vote and unvote update only the selected suggestion count and active state', () => {
  const voted = optimisticallyToggleSuggestionVote(initial, 's-1');
  assert.deepEqual(voted[0], { ...initial[0], votes: 5, voted_by_me: true });
  assert.deepEqual(voted[1], initial[1]);
  const unvoted = optimisticallyToggleSuggestionVote(voted, 's-1');
  assert.deepEqual(unvoted[0], initial[0]);
});

test('server response reconciles optimistic state and rollback restores the exact previous row', () => {
  const optimistic = optimisticallyToggleSuggestionVote(initial, 's-1');
  const reconciled = applySuggestionVoteResponse(optimistic, 's-1', { voted: false, vote_count: 8 });
  assert.deepEqual(reconciled[0], { ...initial[0], votes: 8, voted_by_me: false });
  assert.deepEqual(restoreSuggestionVote(optimistic, 's-1', initial[0])[0], initial[0]);
});

test('suggestion component fetches per-session state and leaves active vote control clickable for unvoting', () => {
  const source = readFileSync(resolve('src/pages/student/UserDashboard.jsx'), 'utf8');
  assert.match(source, /loadMySuggestions\(\);/);
  assert.match(source, /\}, \[user\?\.id\]\);/);
  assert.match(source, /voted_by_me/);
  assert.match(source, /disabled=\{votingIds\.has\(item\.id\)\}/);
  assert.match(source, /item\.voted_by_me\s*\?\s*'Unvote'/);
  assert.match(source, /setError\(`Vote failed:/);
});
