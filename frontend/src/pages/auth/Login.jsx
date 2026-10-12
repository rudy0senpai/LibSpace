import { useState } from 'react';
import { BookOpen, ChevronDown, Contact, LoaderCircle, UserRound, UsersRound } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const ROLES = [
  ['STUDENT', 'Student'],
  ['FACULTY', 'Teacher'],
  ['DEPARTMENT', 'Department'],
  ['LIBRARIAN', 'Librarian'],
];
const TEST_AUTH_MODE = import.meta.env.VITE_AUTH_MODE === 'testing';

export default function Login() {
  const { signIn, restoreError } = useAuth();
  const [name, setName] = useState('');
  const [userId, setUserId] = useState('');
  const [role, setRole] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});

  async function submit(event) {
    event.preventDefault();
    const errors = {
      name: name.trim() ? '' : 'Enter your name.',
      userId: userId.trim() ? '' : 'Enter your user ID.',
      role: role ? '' : 'Select your role.',
    };
    setFieldErrors(errors);
    if (Object.values(errors).some(Boolean)) return;

    setBusy(true);
    setError('');
    try {
      const credentials = { name: name.trim(), user_id: userId.trim(), role };
      const session = await signIn(credentials);
      const authenticatedRole = session.user.role;
      const destination = {
        STUDENT: 'student',
        FACULTY: 'teacher',
        DEPARTMENT: 'department',
        LIBRARIAN: 'librarian',
      }[authenticatedRole];
      window.location.hash = `#/${destination}`;
    } catch (err) {
      setError(err.message || 'Unable to log in. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-mark"><BookOpen aria-hidden="true" /></div>
        <h1 id="login-title">LibSphere</h1>
        <p className="login-subtitle">Login to access your account</p>
        {TEST_AUTH_MODE ? (
          <form onSubmit={submit} noValidate>
            <>
              <label className="login-field" htmlFor="login-name">User Name
                <span className={`login-control ${fieldErrors.name ? 'invalid' : ''}`}>
                  <UserRound aria-hidden="true" />
                  <input id="login-name" type="text" autoComplete="name" placeholder="Enter your name" value={name} onChange={e => { setName(e.target.value); setFieldErrors(current => ({ ...current, name: '' })); }} aria-invalid={Boolean(fieldErrors.name)} aria-describedby={fieldErrors.name ? 'login-name-error' : undefined} />
                </span>
                {fieldErrors.name && <small id="login-name-error" className="login-field-error">{fieldErrors.name}</small>}
              </label>
              <label className="login-field" htmlFor="login-user-id">User ID
                <span className={`login-control ${fieldErrors.userId ? 'invalid' : ''}`}>
                  <Contact aria-hidden="true" />
                  <input id="login-user-id" type="text" autoComplete="username" placeholder="Enter your ID (Roll No. / Teacher ID / etc.)" value={userId} onChange={e => { setUserId(e.target.value); setFieldErrors(current => ({ ...current, userId: '' })); }} aria-invalid={Boolean(fieldErrors.userId)} aria-describedby={fieldErrors.userId ? 'login-id-error' : undefined} />
                </span>
                {fieldErrors.userId && <small id="login-id-error" className="login-field-error">{fieldErrors.userId}</small>}
              </label>
              <label className="login-field" htmlFor="login-role">User Role
                <span className={`login-control login-select ${fieldErrors.role ? 'invalid' : ''}`}>
                  <UsersRound aria-hidden="true" />
                  <select id="login-role" value={role} onChange={e => { setRole(e.target.value); setFieldErrors(current => ({ ...current, role: '' })); }} aria-invalid={Boolean(fieldErrors.role)} aria-describedby={fieldErrors.role ? 'login-role-error' : undefined}>
                    <option value="">Select your role</option>
                    {ROLES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                  <ChevronDown aria-hidden="true" />
                </span>
                {fieldErrors.role && <small id="login-role-error" className="login-field-error">{fieldErrors.role}</small>}
              </label>
            </>
            {restoreError && <div className="login-error" role="alert">Saved session could not be checked: {restoreError}</div>}
            {error && <div className="login-error" role="alert">{error}</div>}
            <button className="login-submit" type="submit" disabled={busy}>
              {busy ? <><LoaderCircle className="login-spinner" size={18} />Logging in…</> : 'Login'}
            </button>
          </form>
        ) : (
          <div className="login-error" role="status">Login is available only in explicit local testing mode.</div>
        )}
      </section>
    </main>
  );
}
