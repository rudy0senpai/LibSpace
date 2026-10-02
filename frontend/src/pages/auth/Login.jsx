import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';

const DEMOS = {
  DEPARTMENT: { email: 'priya.sharma@mitrc.ac.in', password: 'LibSphere@2026' },
  STUDENT: { email: 'aarav.mehta@mitrc.ac.in', password: 'LibSphere@2026' },
  LIBRARIAN: { email: 'suresh.kumar@mitrc.ac.in', password: 'LibSphere@2026' },
};

export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState(DEMOS.DEPARTMENT.email);
  const [password, setPassword] = useState(DEMOS.DEPARTMENT.password);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const session = await signIn(email.trim(), password);
      const role = session.user.role;
      window.location.hash = role === 'DEPARTMENT' ? '#/department' : role === 'LIBRARIAN' ? '#/librarian' : role === 'ADMIN' ? '#/admin' : '#/student';
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  function useDemo(role) {
    setEmail(DEMOS[role].email); setPassword(DEMOS[role].password); setError('');
  }

  return (
    <div className="prototype-login">
      <div className="prototype-login-card">
        <div className="prototype-logo">MITRC <span>LibSphere</span></div>
        <p className="prototype-muted">Library Management & Discovery Portal</p>
        <h1>Sign in to your library account</h1>
        <form onSubmit={submit}>
          <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>
          <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
          <button className="prototype-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign In'}</button>
        </form>
        {error && <div className="prototype-error">{error}</div>}
        <div className="demo-row">
          <button onClick={() => useDemo('STUDENT')}>Student demo</button>
          <button onClick={() => useDemo('DEPARTMENT')}>Department demo</button>
          <button onClick={() => useDemo('LIBRARIAN')}>Librarian demo</button>
        </div>
        <small>Prototype name: <b>LibSpace</b> · Website/project name: <b>LibSphere</b></small>
      </div>
    </div>);
}
