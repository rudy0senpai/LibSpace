import assert from 'node:assert/strict';
import test from 'node:test';
import { normalizeDepartmentDashboardResponse } from '../src/components/department/departmentDashboardData.js';

test('department dashboard accepts empty and incomplete API payloads without inventing metrics', () => {
  const normalized = normalizeDepartmentDashboardResponse({ scope: { name: 'CSE' }, summary: { department_books: 0 } });
  assert.equal(normalized.scope.name, 'CSE');
  assert.equal(normalized.summary.department_books, 0);
  assert.equal(normalized.summary.available_copies, undefined);
  for (const key of ['categories', 'borrowing_trend', 'borrowing_by_category', 'student_vs_faculty', 'book_utilization', 'copy_status', 'suggestion_demand', 'top_books', 'recent_suggestions']) {
    assert.deepEqual(normalized[key], []);
  }
  assert.deepEqual(normalized.suggestions.items, []);
});

test('malformed nullable list/object fields become safe empty collections', () => {
  const normalized = normalizeDepartmentDashboardResponse({
    summary: null, comparisons: [], categories: {}, borrowing_trend: [null, 3], top_books: null,
    suggestions: { items: null }, recent_suggestions: 'not a list',
  });
  assert.deepEqual(normalized.summary, {});
  assert.deepEqual(normalized.comparisons, {});
  assert.deepEqual(normalized.categories, []);
  assert.deepEqual(normalized.borrowing_trend, []);
  assert.deepEqual(normalized.top_books, []);
  assert.deepEqual(normalized.suggestions.items, []);
  assert.deepEqual(normalized.recent_suggestions, []);
});
