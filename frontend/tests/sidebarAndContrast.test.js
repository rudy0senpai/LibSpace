import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const student = readFileSync(resolve('src/pages/student/UserDashboard.jsx'), 'utf8');
const department = readFileSync(resolve('src/pages/department/DepartmentDashboard.jsx'), 'utf8');
const librarian = readFileSync(resolve('src/pages/librarian/LibrarianDashboard.jsx'), 'utf8');
const css = readFileSync(resolve('src/styles/dashboard-glass.css'), 'utf8');

function luminance(hex) {
  const channels = [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16) / 255);
  const linear = channels.map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}
function contrast(a, b) {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (high + 0.05) / (low + 0.05);
}

 test('Notifications is absent from student/faculty, department, and librarian sidebar navigation', () => {
  const departmentSidebar = department.match(/<aside className="sidebar">([\s\S]*?)<\/aside>/)?.[1] || '';
  assert.doesNotMatch(student, /notifications|Notifications|<Bell\b/);
  assert.doesNotMatch(departmentSidebar, /Notifications|<Bell\b/);
  assert.doesNotMatch(librarian, /notifications|Notifications/);
});

test('primary book-action labels meet WCAG AA contrast in light and night themes', () => {
  const light = css.match(/--dashboard-button-bg:\s*(#[0-9a-f]{6})[\s\S]*?--dashboard-button-ink:\s*(#[0-9a-f]{6})/i);
  const night = css.match(/\.dashboard-app\[data-theme="night"\][\s\S]*?--dashboard-button-bg:\s*(#[0-9a-f]{6})[\s\S]*?--dashboard-button-ink:\s*(#[0-9a-f]{6})/i);
  assert.ok(light && night, 'both theme button tokens are explicitly defined');
  assert.ok(contrast(light[2], light[1]) >= 4.5);
  assert.ok(contrast(night[2], night[1]) >= 4.5);
  assert.match(css, /\.book-cover-card__actions button:focus-visible/);
  assert.match(css, /\.book-cover-card__actions button:disabled/);
});
