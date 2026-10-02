import { useAuth } from '../context/AuthContext';

export default function RoleRoute({ roles, children }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) {
    window.location.hash = '#/';
    return null;
  }
  return children;
}
