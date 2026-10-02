import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { session } = useAuth();
  if (!session) {
    window.location.hash = '#/login';
    return null;
  }
  return children;
}
