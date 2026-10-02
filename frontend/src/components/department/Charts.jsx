import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar, PieChart, Pie, Cell, Legend } from 'recharts';
const palette = ['#3567e8', '#7c5cff', '#24b6d9', '#20b486', '#f3b33d', '#f07b45', '#ef4c7a'];
export function BorrowingTrend({ data = [] }) {
    return
    <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
            <XAxis dataKey="month" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="total_loans" stroke="#3567e8" strokeWidth={3} dot={{ r: 4 }} />
        </LineChart>
    </ResponsiveContainer>;
}
export function CategoryBars({ data = [] }) {
    return
    <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
            <XAxis type="number" allowDecimals={false} />
            <YAxis type="category" dataKey="category_name" width={105} />
            <Tooltip />
            <Bar dataKey="borrow_count" radius={[0, 5, 5, 0]}>
                {
                    data.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)
                }
            </Bar>
        </BarChart>
    </ResponsiveContainer>;
}
export function StudentFaculty({ data = [] }) {
    return
    <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
            <XAxis dataKey="period" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Bar dataKey="students" fill="#3567e8" radius={[4, 4, 0, 0]} />
            <Bar dataKey="faculty" fill="#7c5cff" radius={[4, 4, 0, 0]} />
        </BarChart>
    </ResponsiveContainer>;
}
export function CopyStatus({ data = [] }) {
    return
    <ResponsiveContainer width="100%" height={250}>
        <PieChart>
            <Pie data={data} dataKey="count" nameKey="status" innerRadius={62} outerRadius={92} paddingAngle={2}>
                {
                    data.map((_, i) => <Cell key={i} fill={palette[i % palette.length]} />)
                }
            </Pie>
            <Tooltip />
            <Legend />
        </PieChart>
    </ResponsiveContainer>;
}
export function SuggestionBars({ data = [] }) {
    return
    <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
            <XAxis dataKey="category_name" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="suggestion_count" fill="#7c5cff" radius={[5, 5, 0, 0]} />
        </BarChart>
    </ResponsiveContainer>;
}
export function Utilization({ data = [] }) {
    return
    <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e8edf5" />
            <XAxis dataKey="period" />
            <YAxis unit="%" />
            <Tooltip formatter={(v) => [`${v}%`, 'Utilization']} />
            <Line type="monotone" dataKey="utilization_rate" stroke="#20b486" strokeWidth={3} />
        </LineChart>
    </ResponsiveContainer>;
}
