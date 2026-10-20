import assert from 'node:assert/strict';
import test from 'node:test';
import { getDashboardRoute, isPortalRole, normalizePortalRole } from '../src/services/roleRoutes.js';

test('department role formatting always resolves to the department dashboard', () => {
  for (const role of ['DEPARTMENT', 'department', ' Department ', 'DePaRtMeNt']) {
    assert.equal(normalizePortalRole(role), 'DEPARTMENT');
    assert.equal(getDashboardRoute(role), 'department');
  }
});

test('teacher aliases normalize to faculty without changing other role routes', () => {
  assert.equal(normalizePortalRole('Faculty / Teacher'), 'FACULTY');
  assert.equal(getDashboardRoute('teacher'), 'teacher');
  assert.equal(getDashboardRoute('student'), 'student');
  assert.equal(getDashboardRoute('librarian'), 'librarian');
  assert.equal(isPortalRole('department'), true);
  assert.equal(isPortalRole('unknown-role'), false);
  assert.equal(getDashboardRoute('unknown-role'), null);
});
