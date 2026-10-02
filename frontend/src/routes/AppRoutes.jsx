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
  const { user } = useAuth();
  const [route, setRoute] = useState(routeFromHash);

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener('hashchange', onHash);
    if (!window.location.hash) window.location.hash = user ? '#/' : '#/login';
    return () => window.removeEventListener('hashchange', onHash);
  }, [user]);

  if (route === 'login') return <Login />;
  if (!user) return <Login />;

  if (route === 'department' || (!route && user.role === 'DEPARTMENT')) {
    return <ProtectedRoute><RoleRoute roles={['DEPARTMENT', 'ADMIN', 'LIBRARIAN']}><DepartmentDashboard /></RoleRoute></ProtectedRoute>;
  }
  if (route === 'librarian' || (!route && user.role === 'LIBRARIAN')) {
    return <ProtectedRoute><RoleRoute roles={['LIBRARIAN', 'ADMIN']}><LibrarianDashboard /></RoleRoute></ProtectedRoute>;
  }
  if (route === 'student' || route === 'user' || (!route && ['STUDENT', 'FACULTY'].includes(user.role))) {
    return <ProtectedRoute><RoleRoute roles={['STUDENT', 'FACULTY']}><UserDashboard /></RoleRoute></ProtectedRoute>;
  }
  if (route === 'admin' || user.role === 'ADMIN') {
    return <ProtectedRoute><RoleRoute roles={['ADMIN']}><DepartmentDashboard /></RoleRoute></ProtectedRoute>;
  }

  window.location.hash = '#/';
  return null;
}
