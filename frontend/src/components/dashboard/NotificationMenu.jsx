import { useEffect, useRef, useState } from 'react';
import { Bell, ChevronDown } from 'lucide-react';
import { getMyNotifications, markMyNotificationRead } from '../../services/api';

export default function NotificationMenu({ role }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
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
  async function load() {
    setLoading(true); setError('');
    try { const result = await getMyNotifications(); setItems(result.data?.items || []); setUnread(result.data?.unread || 0); }
    catch (err) { setError(err.message || 'Unable to load notifications.'); }
    finally { setLoading(false); }
  }
  async function toggle() {
    const next = !open; setOpen(next);
    if (next) await load();
  }
  async function markRead(id) {
    try {
      await markMyNotificationRead(id);
      setItems(current => current.map(item => item.id === id ? { ...item, is_read: true } : item));
      setUnread(current => Math.max(0, current - 1));
    } catch (err) { setError(err.message || 'Unable to update notification.'); }
  }
  return (
    <div className="dashboard-menu-wrap" ref={rootRef}>
      <button type="button" className="dashboard-icon-button" aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`} aria-haspopup="dialog" aria-expanded={open} onClick={toggle}>
        <Bell size={18} />{unread > 0 && <span className="notification-count" aria-label={`${unread} unread`}>{unread}</span>}<ChevronDown size={13} />
      </button>
      {open && <section className="dashboard-popover dashboard-notification-popover" role="dialog" aria-label={`${role.toLowerCase()} notifications`}>
        <div className="notification-popover-head"><b>Notifications</b><button type="button" onClick={load} disabled={loading}>{loading ? 'Refreshing…' : 'Refresh'}</button></div>
        {error && <p role="alert">{error} <button type="button" onClick={load}>Retry</button></p>}
        {loading && items.length === 0 && <p role="status">Loading notifications…</p>}
        {!loading && !error && items.length === 0 && <p role="status">You’re all caught up. No notifications yet.</p>}
        <ul className="notification-list">{items.map(item => <li key={item.id} className={item.is_read ? '' : 'unread'}>
          <div><b>{item.title}</b><p>{item.message}</p><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString()}</time></div>
          {!item.is_read && <button type="button" onClick={() => markRead(item.id)}>Mark read</button>}
        </li>)}</ul>
      </section>}
    </div>
  );
}
