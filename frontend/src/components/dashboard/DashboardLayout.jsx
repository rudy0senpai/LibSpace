import { useEffect, useState } from 'react';
import DashboardSidebar from './DashboardSidebar';
import DashboardHeader from './DashboardHeader';

const STORAGE_KEY = 'libsphere_dashboard_theme';

function readTheme() {
  try { return localStorage.getItem(STORAGE_KEY) === 'night' ? 'night' : 'warm'; }
  catch { return 'warm'; }
}

export default function DashboardLayout({
  user, role, title, subtitle, navItems, activeItem, onNavigate, onLogout,
  sidebarContent, onOpenCatalogue, onOpenUsers, children,
}) {
  const [theme, setTheme] = useState(readTheme);
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, theme); } catch { /* Storage may be unavailable. */ }
  }, [theme]);
  useEffect(() => {
    if (!mobileOpen) return undefined;
    const closeOnEscape = event => { if (event.key === 'Escape') setMobileOpen(false); };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [mobileOpen]);

  function navigate(itemId) {
    const item = navItems.find(navItem => navItem.id === itemId);
    if (!item || item.disabled) return;
    onNavigate?.(itemId);
    setMobileOpen(false);
  }

  return (
    <div className="dashboard-app" data-theme={theme}>
      <div className="dashboard-wallpaper" aria-hidden="true" />
      <DashboardSidebar role={role} items={navItems} activeItem={activeItem} onNavigate={navigate} extra={sidebarContent} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <div className="dashboard-main">
        <DashboardHeader
          role={role} user={user} title={title} subtitle={subtitle} theme={theme}
          onThemeChange={() => setTheme(value => value === 'warm' ? 'night' : 'warm')}
          onLogout={onLogout} onMenuClick={() => setMobileOpen(value => !value)} menuOpen={mobileOpen}
          onOpenCatalogue={onOpenCatalogue} onOpenUsers={onOpenUsers}
        />
        <div className="dashboard-content" id="dashboard-main-content">{children}</div>
      </div>
      {mobileOpen && <button type="button" className="dashboard-sidebar-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    </div>
  );
}
