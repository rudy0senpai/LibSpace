import { BookOpen, Check, ChevronRight } from 'lucide-react';

const roleNames = { STUDENT: 'Student', FACULTY: 'Faculty / Teacher', DEPARTMENT: 'Department', LIBRARIAN: 'Librarian', ADMIN: 'Administrator' };

export default function DashboardSidebar({ role, items, activeItem, onNavigate, extra, mobileOpen, onMobileClose }) {
  return (
    <aside id="dashboard-sidebar" className={`dashboard-sidebar${mobileOpen ? ' mobile-open' : ' mobile-closed'}`} aria-label={`${roleNames[role] || role} navigation`}>
      <div className="dashboard-brand">
        <span className="dashboard-brand-mark"><BookOpen size={21} /></span>
        <span><b>MITRC <i>LibSphere</i></b><small>Library · Discovery · Community</small></span>
        <button type="button" className="dashboard-sidebar-close" onClick={onMobileClose} aria-label="Close navigation"><ChevronRight size={18} /></button>
      </div>
      <div className="dashboard-role-chip">{roleNames[role] || role}</div>
      <nav className="dashboard-nav" aria-label="Dashboard pages">
        {items.map(item => {
          const Icon = item.icon;
          return <button
            key={item.id}
            type="button"
            className={`dashboard-nav-item${activeItem === item.id ? ' active' : ''}${item.disabled ? ' unavailable' : ''}`}
            onClick={() => !item.disabled && onNavigate(item.id)}
            disabled={Boolean(item.disabled)}
            title={item.disabled ? item.reason || `${item.label} is unavailable` : undefined}
            aria-current={activeItem === item.id ? 'page' : undefined}
            aria-label={item.disabled ? `${item.label}, unavailable` : item.label}
          >
            {Icon && <Icon size={17} aria-hidden="true" />}
            <span>{item.label}</span>
            {activeItem === item.id && <Check className="dashboard-nav-check" size={14} aria-hidden="true" />}
            {item.disabled && <small>Unavailable</small>}
          </button>;
        })}
      </nav>
      {extra && <div className="dashboard-sidebar-extra">{extra}</div>}
      <footer className="dashboard-sidebar-footer"><span className="dashboard-status-dot" />Local library portal <small>MITRC · Alwar</small></footer>
    </aside>
  );
}
