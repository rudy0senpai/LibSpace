import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

export const palette = [
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

const gridStroke = 'var(--chart-grid, rgba(255,255,255,0.12))';

export function BorrowingTrend({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis dataKey="month" tick={axisTick} stroke={gridStroke} />
        <YAxis allowDecimals={false} tick={axisTick} stroke={gridStroke} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v} loans`, 'Total loans']} />
        <Line
          type="monotone"
          dataKey="total_loans"
          stroke="var(--dashboard-accent, #d97706)"
          strokeWidth={3}
          dot={{ r: 4, fill: 'var(--dashboard-accent, #d97706)' }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function CategoryBars({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20, top: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis type="number" allowDecimals={false} tick={axisTick} stroke={gridStroke} />
        <YAxis
          type="category"
          dataKey="category_name"
          width={110}
          tick={axisTick}
          stroke={gridStroke}
          tickFormatter={(v) => (v.length > 16 ? `${v.slice(0, 14)}…` : v)}
        />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v} borrowed`, 'Loans']} />
        <Bar dataKey="borrow_count" radius={[0, 5, 5, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function StudentFaculty({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis dataKey="period" tick={axisTick} stroke={gridStroke} />
        <YAxis allowDecimals={false} tick={axisTick} stroke={gridStroke} />
        <Tooltip contentStyle={tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: '11px', color: 'var(--chart-text, #8c8273)' }} />
        <Bar dataKey="students" name="Students" fill="var(--dashboard-accent, #d97706)" radius={[4, 4, 0, 0]} />
        <Bar dataKey="faculty" name="Faculty" fill="var(--chart-accent-secondary, #2b7a78)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CopyStatus({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="status"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={3}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={palette[i % palette.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={tooltipStyle}
          formatter={(v, name) => [`${v} copies`, String(name).replaceAll('_', ' ')]}
        />
        <Legend
          formatter={(v) => String(v).replaceAll('_', ' ')}
          wrapperStyle={{ fontSize: '11px', color: 'var(--chart-text, #8c8273)' }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function SuggestionBars({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis dataKey="category_name" tick={axisTick} stroke={gridStroke} />
        <YAxis allowDecimals={false} tick={axisTick} stroke={gridStroke} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v} suggestions`, 'Demand']} />
        <Bar dataKey="suggestion_count" fill="var(--dashboard-accent, #d97706)" radius={[5, 5, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function Utilization({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={data} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
        <XAxis dataKey="period" tick={axisTick} stroke={gridStroke} />
        <YAxis unit="%" tick={axisTick} stroke={gridStroke} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, 'Utilization']} />
        <Line
          type="monotone"
          dataKey="utilization_rate"
          stroke="var(--chart-accent-secondary, #2b7a78)"
          strokeWidth={3}
          dot={{ r: 4, fill: 'var(--chart-accent-secondary, #2b7a78)' }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
