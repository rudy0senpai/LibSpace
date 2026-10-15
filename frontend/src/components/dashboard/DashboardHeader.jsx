import { useEffect, useState } from 'react';
import { LayoutDashboard, Moon, Sun, Menu } from 'lucide-react';
import GlobalSearch from './GlobalSearch';
import NotificationMenu from './NotificationMenu';
import ProfileMenu from './ProfileMenu';

export default function DashboardHeader({ role, user, title, subtitle, theme, onThemeChange, onLogout, onMenuClick, menuOpen, onOpenCatalogue, onOpenUsers }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(timer);
  }, []);
  const locale = typeof navigator !== 'undefined' ? navigator.language : undefined;
  const dateTime = new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(now);
  const ThemeIcon = theme === 'warm' ? Moon : Sun;
  const themeAction = theme === 'warm' ? 'Switch to night theme' : 'Switch to warm theme';
  return (
    <header className="dashboard-header">
      <button type="button" className="dashboard-mobile-toggle" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} aria-controls="dashboard-sidebar" onClick={onMenuClick}><Menu size={20} /></button>
      <div className="dashboard-header-title"><div className="dashboard-header-brand"><LayoutDashboard size={17} /><span>LibSphere</span></div><b>{title}</b><small>{subtitle}</small></div>
      <GlobalSearch role={role} onOpenCatalogue={onOpenCatalogue} onOpenUsers={onOpenUsers} />
      <time className="dashboard-clock" dateTime={now.toISOString()}>{dateTime}</time>
      <button type="button" className="dashboard-icon-button dashboard-theme-toggle" onClick={onThemeChange} aria-label={themeAction} title={themeAction} aria-pressed={theme === 'night'}><ThemeIcon size={18} /><span>{theme === 'warm' ? 'Warm' : 'Night'}</span></button>
      <NotificationMenu role={role} />
      <ProfileMenu user={user} onLogout={onLogout} />
    </header>
  );
}
