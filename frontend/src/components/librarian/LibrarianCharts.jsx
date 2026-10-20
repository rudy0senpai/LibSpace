import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { AlertTriangle, ArrowRight, BookOpen, Clock, ThumbsUp } from 'lucide-react';

export const CHART_PALETTE = [
  '#d97706', // warm amber
  '#0284c7', // sky blue
  '#059669', // emerald
  '#7c3aed', // violet
  '#dc2626', // crimson
  '#0d9488', // teal
  '#ea580c', // orange
  '#d946ef', // fuchsia
];

const tooltipStyle = {
  backgroundColor: 'var(--chart-tooltip-bg, rgba(25, 22, 18, 0.95))',
  borderColor: 'var(--chart-tooltip-border, rgba(255, 255, 255, 0.2))',
  borderRadius: '8px',
  color: 'var(--chart-tooltip-text, #f5efe5)',
  fontSize: '12px',
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
  padding: '8px 12px',
};

const axisTick = {
  fill: 'var(--chart-text, #8c8273)',
  fontSize: 11,
};

export function LibrarianBorrowingTrendChart({ data = [] }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <div className="librarian-chart-empty">No borrowing activity recorded in the selected period.</div>;
  }

  return (
    <div className="librarian-chart-wrap" aria-label="Borrowing activity over time chart">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, rgba(255,255,255,0.12))" />
          <XAxis dataKey="label" tick={axisTick} stroke="var(--chart-grid, rgba(255,255,255,0.12))" />
          <YAxis allowDecimals={false} tick={axisTick} stroke="var(--chart-grid, rgba(255,255,255,0.12))" />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => [`${value} loan${value === 1 ? '' : 's'}`, 'Loans']}
            labelStyle={{ fontWeight: 700, marginBottom: 4 }}
          />
          <Line
            type="monotone"
            dataKey="borrow_count"
            stroke="var(--dashboard-accent, #d97706)"
            strokeWidth={3}
            dot={{ r: 4, fill: 'var(--dashboard-accent, #d97706)' }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LibrarianCopyStatusChart({ data = [] }) {
  const filtered = (data || []).filter(item => Number(item.count) > 0);
  if (!filtered.length) {
    return <div className="librarian-chart-empty">No physical copies registered in the catalogue.</div>;
  }

  const formatStatus = (status) =>
    String(status || 'UNKNOWN')
      .replaceAll('_', ' ')
      .toLowerCase()
      .replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="librarian-chart-wrap" aria-label="Physical copy status distribution chart">
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={filtered}
            dataKey="count"
            nameKey="status"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={3}
          >
            {filtered.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={CHART_PALETTE[index % CHART_PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, name) => [`${value} copies`, formatStatus(name)]}
          />
          <Legend
            formatter={formatStatus}
            wrapperStyle={{ fontSize: '11px', color: 'var(--chart-text, #8c8273)' }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LibrarianTopBorrowedChart({ data = [] }) {
  if (!Array.isArray(data) || data.length === 0) {
    return <div className="librarian-chart-empty">No circulation loans recorded for this range.</div>;
  }

  return (
    <div className="librarian-chart-wrap" aria-label="Most borrowed books chart">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 20, left: 10, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, rgba(255,255,255,0.12))" />
          <XAxis type="number" allowDecimals={false} tick={axisTick} stroke="var(--chart-grid, rgba(255,255,255,0.12))" />
          <YAxis
            type="category"
            dataKey="title"
            width={120}
            tick={axisTick}
            stroke="var(--chart-grid, rgba(255,255,255,0.12))"
            tickFormatter={(val) => (val.length > 18 ? `${val.slice(0, 16)}…` : val)}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(val) => [`${val} borrow${val === 1 ? '' : 's'}`, 'Total loans']}
          />
          <Bar dataKey="borrow_count" radius={[0, 6, 6, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LibrarianSuggestionStatusChart({ data = [] }) {
  const filtered = (data || []).filter(item => Number(item.count) > 0);
  if (!filtered.length) {
    return <div className="librarian-chart-empty">No book suggestions submitted in this period.</div>;
  }

  const formatStatus = (s) =>
    String(s || 'UNKNOWN')
      .replaceAll('_', ' ')
      .toLowerCase()
      .replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="librarian-chart-wrap" aria-label="Suggestion statuses distribution">
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={filtered} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, rgba(255,255,255,0.12))" />
          <XAxis
            dataKey="status"
            tick={axisTick}
            stroke="var(--chart-grid, rgba(255,255,255,0.12))"
            tickFormatter={formatStatus}
          />
          <YAxis allowDecimals={false} tick={axisTick} stroke="var(--chart-grid, rgba(255,255,255,0.12))" />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, name, item) => [`${value} suggestions`, formatStatus(item?.payload?.status)]}
          />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {filtered.map((_, i) => (
              <Cell key={i} fill={CHART_PALETTE[(i + 2) % CHART_PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LibrarianOverdueList({ loans = [], onGoToReturn }) {
  if (!Array.isArray(loans) || loans.length === 0) {
    return (
      <div className="librarian-empty-card">
        <Clock size={24} aria-hidden="true" />
        <p>No overdue loans requiring immediate attention. Great job!</p>
      </div>
    );
  }

  return (
    <div className="librarian-overdue-list-wrap">
      <div className="librarian-overdue-list">
        {loans.map(loan => (
          <div key={loan.id} className="librarian-overdue-item">
            <div className="overdue-item-main">
              <strong className="overdue-item-title" title={loan.book_title}>
                {loan.book_title}
              </strong>
              <div className="overdue-item-meta">
                <span>Borrower: <b>{loan.borrower}</b> ({loan.user_id})</span>
                <span>Copy: <code>{loan.accession_number}</code></span>
                <span className="overdue-date-alert">
                  <AlertTriangle size={12} aria-hidden="true" />
                  Due {new Date(loan.due_at).toLocaleDateString('en-IN', { dateStyle: 'medium' })}
                </span>
              </div>
            </div>
            <button
              type="button"
              className="librarian-table-action-btn"
              onClick={() => onGoToReturn?.(loan)}
              title={`Open return workflow for ${loan.book_title}`}
            >
              Process return <ArrowRight size={13} aria-hidden="true" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LibrarianTopSuggestionsList({ suggestions = [], onGoToSuggestions }) {
  if (!Array.isArray(suggestions) || suggestions.length === 0) {
    return <div className="librarian-chart-empty">No book suggestions submitted in this period.</div>;
  }

  const formatStatus = (s) =>
    String(s || 'UNKNOWN')
      .replaceAll('_', ' ')
      .toLowerCase()
      .replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="librarian-ranked-list">
      {suggestions.map((item, idx) => (
        <div key={item.id} className="librarian-ranked-item">
          <span className="ranked-index">#{idx + 1}</span>
          <div className="ranked-info">
            <strong className="ranked-title" title={item.title}>{item.title}</strong>
            <span className={`status-pill pill-${String(item.status).toLowerCase()}`}>
              {formatStatus(item.status)}
            </span>
          </div>
          <div className="ranked-votes" title={`${item.vote_count} votes`}>
            <ThumbsUp size={13} aria-hidden="true" />
            <b>{item.vote_count}</b>
          </div>
        </div>
      ))}
      <div className="ranked-footer-action">
        <button type="button" className="librarian-link-action" onClick={onGoToSuggestions}>
          View all suggestions & review <ArrowRight size={13} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
