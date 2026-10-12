import { AuthProvider } from './context/AuthContext';
import DepartmentDashboard from './pages/department/DepartmentDashboard';
import AppRoutes from './routes/AppRoutes';

export default function App() {
  return (
  <AuthProvider>
    <AppRoutes />
  </AuthProvider>);
}
