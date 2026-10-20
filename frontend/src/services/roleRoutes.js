const PORTAL_ROUTES = Object.freeze({
  STUDENT: 'student',
  FACULTY: 'teacher',
  DEPARTMENT: 'department',
  LIBRARIAN: 'librarian',
});

const ROLE_ALIASES = Object.freeze({
  TEACHER: 'FACULTY',
  FACULTY_TEACHER: 'FACULTY',
  DEPT: 'DEPARTMENT',
});

export function normalizePortalRole(value) {
  const key = String(value ?? '').trim().toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  return ROLE_ALIASES[key] || key;
}

export function isPortalRole(value) {
  return Object.hasOwn(PORTAL_ROUTES, normalizePortalRole(value));
}

export function getDashboardRoute(value) {
  return PORTAL_ROUTES[normalizePortalRole(value)] || null;
}
