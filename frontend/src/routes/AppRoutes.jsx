import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Login from '../pages/auth/Login';
import UserDashboard from '../pages/student/UserDashboard';
import LibrarianDashboard from '../pages/librarian/LibrarianDashboard';
import DepartmentDashboard from '../pages/department/DepartmentDashboard';
import ProtectedRoute from './ProtectedRoute';
import RoleRoute from './RoleRoute';

function routeFromHash() {
  return window.location.hash.replace(/^#\/?/, '') || '';
}

export default function AppRoutes() {
  const { user, ready } = useAuth();
  const [route, setRoute] = useState(routeFromHash);

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', onHash);
    if (!window.location.hash) window.location.hash = user ? '#/' : '#/login';
    return () => window.removeEventListener('hashchange', onHash);
  }, [user]);

  if (!ready) return <div className="auth-loading" role="status">Checking saved session…</div>;
  if (route === 'login' && !user) return <Login />;
  if (!user) return <Login />;

  const destination = {
    DEPARTMENT: 'department',
    LIBRARIAN: 'librarian',
    STUDENT: 'student',
    FACULTY: 'teacher',
  }[user.role];

  if (!destination) {
    window.location.hash = '#/login';
    return <Login />;
  }

  if (route !== destination && !(destination === 'student' && route === 'user')) {
    window.location.hash = `#/${destination}`;
    return null;
  }

  const page = destination === 'department' ? <DepartmentDashboard />
    : destination === 'librarian' ? <LibrarianDashboard />
      : <UserDashboard />;

  return <ProtectedRoute><RoleRoute roles={[user.role]}>{page}</RoleRoute></ProtectedRoute>;
}
