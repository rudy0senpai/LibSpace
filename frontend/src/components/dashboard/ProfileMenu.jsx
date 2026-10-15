import { useEffect, useRef } from 'react';
import { ChevronDown, LogOut, UserRound } from 'lucide-react';

const roleNames = { STUDENT: 'Student', FACULTY: 'Faculty / Teacher', DEPARTMENT: 'Department', LIBRARIAN: 'Librarian', ADMIN: 'Administrator' };

function initials(name) {
  return (name || 'LibSphere User').trim().split(/\s+/).slice(0, 2).map(part => part[0]?.toUpperCase() || '').join('');
}

export default function ProfileMenu({ user, onLogout }) {
  const ref = useRef(null);
  useEffect(() => {
    const closeOutside = event => { if (!ref.current?.contains(event.target)) ref.current?.removeAttribute('open'); };
    const closeOnEscape = event => { if (event.key === 'Escape') ref.current?.removeAttribute('open'); };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, []);
  return (
    <details className="dashboard-profile-menu" ref={ref}>
      <summary aria-label={`Account menu for ${user?.name || 'account'}`}>
        <span className="dashboard-avatar" aria-hidden="true">{initials(user?.name)}</span>
        <span className="dashboard-profile-label"><b>{user?.name || 'Account'}</b><small>{roleNames[user?.role] || user?.role}</small></span>
        <ChevronDown size={15} aria-hidden="true" />
      </summary>
      <div className="dashboard-popover dashboard-profile-popover">
        <div className="dashboard-profile-summary"><UserRound size={17} /><span><b>{user?.name || 'Authenticated user'}</b><small>{roleNames[user?.role] || user?.role}</small></span></div>
        <button type="button" className="dashboard-logout" onClick={onLogout}><LogOut size={16} />Sign out</button>
      </div>
    </details>
  );
}
