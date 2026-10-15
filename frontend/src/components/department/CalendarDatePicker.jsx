import { useEffect, useMemo, useRef, useState } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, X } from 'lucide-react';

const monthNames = Array.from({ length: 12 }, (_, month) =>
  new Intl.DateTimeFormat('en', { month: 'long' }).format(new Date(2020, month, 1)),
);

function dateKey(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function parseDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return null;
  const [year, month, day] = value.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day ? date : null;
}

function displayDate(value) {
  const date = parseDate(value);
  return date ? new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }).format(date) : 'Not set';
}

export default function CalendarDatePicker({ id, label, value, onChange, minDate, maxDate }) {
  const [open, setOpen] = useState(false);
  const [viewMonth, setViewMonth] = useState(() => {
    const initial = parseDate(value) || new Date();
    return new Date(initial.getFullYear(), initial.getMonth(), 1);
  });
  const triggerRef = useRef(null);
  const year = viewMonth.getFullYear();
  const month = viewMonth.getMonth();
  const years = useMemo(() => {
    const currentYear = new Date().getFullYear();
    return Array.from({ length: currentYear + 11 - 1980 }, (_, index) => 1980 + index);
  }, []);
  const days = useMemo(() => {
    const offset = new Date(year, month, 1).getDay();
    return Array.from({ length: 42 }, (_, index) => new Date(year, month, index - offset + 1));
  }, [year, month]);

  useEffect(() => {
    const selected = parseDate(value);
    if (selected) setViewMonth(new Date(selected.getFullYear(), selected.getMonth(), 1));
  }, [value]);

  function moveMonth(amount) {
    setViewMonth(current => new Date(current.getFullYear(), current.getMonth() + amount, 1));
  }

  function selectDate(date) {
    onChange(dateKey(date));
    setOpen(false);
    triggerRef.current?.focus();
  }

  function clearDate() {
    onChange('');
    setOpen(false);
    triggerRef.current?.focus();
  }

  return (
    <div className="calendar-picker">
      <button
        ref={triggerRef}
        type="button"
        id={`${id}-trigger`}
        className="calendar-trigger"
        aria-label={`${label}: ${displayDate(value)}. Open calendar.`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={`${id}-calendar`}
        onClick={() => {
          if (!open) {
            const selected = parseDate(value) || new Date();
            setViewMonth(new Date(selected.getFullYear(), selected.getMonth(), 1));
          }
          setOpen(current => !current);
        }}
      >
        <CalendarDays size={16} aria-hidden="true" />
        <span className="calendar-trigger-text">
          <span className="calendar-label">{label}</span>
          <span className="calendar-value">{displayDate(value)}</span>
        </span>
      </button>
      {open && (
        <div
          className="calendar-popover"
          id={`${id}-calendar`}
          role="dialog"
          aria-label={`${label} date calendar`}
          onKeyDown={event => { if (event.key === 'Escape') { setOpen(false); triggerRef.current?.focus(); } }}
        >
          <div className="calendar-header">
            <button type="button" aria-label="Previous month" onClick={() => moveMonth(-1)}><ChevronLeft size={17} /></button>
            <label>
              <span className="sr-only">Month</span>
              <select value={month} onChange={event => setViewMonth(new Date(year, Number(event.target.value), 1))}>
                {monthNames.map((name, index) => <option key={name} value={index}>{name}</option>)}
              </select>
            </label>
            <label>
              <span className="sr-only">Year</span>
              <select value={year} onChange={event => setViewMonth(new Date(Number(event.target.value), month, 1))}>
                {years.map(item => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <button type="button" aria-label="Next month" onClick={() => moveMonth(1)}><ChevronRight size={17} /></button>
          </div>
          <div className="calendar-weekdays" aria-hidden="true">
            {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => <span key={day}>{day}</span>)}
          </div>
          <div className="calendar-days" role="group" aria-label={`${monthNames[month]} ${year}`}>
            {days.map(day => {
              const key = dateKey(day);
              const outsideMonth = day.getMonth() !== month;
              const disabled = (minDate && key < minDate) || (maxDate && key > maxDate);
              return (
                <button
                  type="button"
                  key={key}
                  className={`calendar-day${outsideMonth ? ' outside-month' : ''}${value === key ? ' selected' : ''}`}
                  aria-label={new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(day)}
                  aria-pressed={value === key}
                  disabled={Boolean(disabled)}
                  onClick={() => selectDate(day)}
                >
                  {day.getDate()}
                </button>
              );
            })}
          </div>
          <div className="calendar-footer">
            <button type="button" className="calendar-clear" onClick={clearDate}><X size={14} />Clear date</button>
            <button type="button" onClick={() => { setOpen(false); triggerRef.current?.focus(); }}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}
