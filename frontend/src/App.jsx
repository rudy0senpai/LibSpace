import { AuthProvider } from './context/AuthContext';
import AppRoutes from './routes/AppRoutes';
import RenderErrorBoundary from './components/dashboard/RenderErrorBoundary';

export default function App() {
  return (
    <AuthProvider>
      <RenderErrorBoundary>
        <AppRoutes />
      </RenderErrorBoundary>
    </AuthProvider>
  );
}
