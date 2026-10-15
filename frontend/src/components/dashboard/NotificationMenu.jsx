import { useEffect, useRef, useState } from 'react';
import { Bell, ChevronDown } from 'lucide-react';

export default function NotificationMenu({ role }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = event => { if (event.key === 'Escape') setOpen(false); };
    const closeOutside = event => { if (!rootRef.current?.contains(event.target)) setOpen(false); };
    document.addEventListener('keydown', closeOnEscape);
    document.addEventListener('pointerdown', closeOutside);
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      document.removeEventListener('pointerdown', closeOutside);
    };
  }, [open]);
  return (
    <div className="dashboard-menu-wrap" ref={rootRef}>
      <button type="button" className="dashboard-icon-button" aria-label="Notification status" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(value => !value)}>
        <Bell size={18} /><ChevronDown size={13} />
      </button>
      {open && <section className="dashboard-popover dashboard-notification-popover" role="dialog" aria-label="Notification status">
        <b>Notifications</b>
        <p>The {role.toLowerCase()} notification feed is not connected yet. No live notification list is available.</p>
        <button type="button" onClick={() => setOpen(false)}>Close</button>
      </section>}
    </div>
  );
}
