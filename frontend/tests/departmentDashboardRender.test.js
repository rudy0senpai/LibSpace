import assert from 'node:assert/strict';
import test from 'node:test';
import { build } from 'esbuild';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const testRequire = createRequire(import.meta.url);

test('department dashboard renders its real shell and loading state during server rendering', async () => {
  const result = await build({
    stdin: {
      contents: `
        import React from 'react';
        import { renderToStaticMarkup } from 'react-dom/server';
        import { AuthProvider } from './src/context/AuthContext.jsx';
        import DepartmentDashboard from './src/pages/department/DepartmentDashboard.jsx';
        export function renderDepartment() {
          return renderToStaticMarkup(React.createElement(AuthProvider, null, React.createElement(DepartmentDashboard)));
        }
      `,
      resolveDir: frontendRoot,
      sourcefile: 'department-render-probe.jsx',
      loader: 'jsx',
    },
    bundle: true,
    write: false,
    format: 'cjs',
    platform: 'node',
    external: ['react', 'react/*', 'react-dom/server', 'recharts'],
    define: { 'import.meta.env.VITE_API_URL': '"http://localhost:5001"', 'import.meta.env.DEV': 'false' },
    jsx: 'automatic',
  });
  const loaded = { exports: {} };
  new Function('require', 'module', 'exports', result.outputFiles[0].text)(testRequire, loaded, loaded.exports);
  const html = loaded.exports.renderDepartment();
  assert.match(html, /Department Dashboard/);
  assert.match(html, /Quick Filters/);
  assert.match(html, /Loading department analytics/);
});
