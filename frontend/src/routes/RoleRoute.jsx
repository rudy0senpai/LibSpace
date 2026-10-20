import { useAuth } from '../context/AuthContext';
import { normalizePortalRole } from '../services/roleRoutes';

export default function RoleRoute({ roles, children }) {
  const { user } = useAuth();
  if (!user || !roles.map(normalizePortalRole).includes(normalizePortalRole(user.role))) {
    window.location.hash = '#/';
    return null;
  }
  return children;
}
