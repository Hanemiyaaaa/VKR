import { useEffect, useState } from 'react';

export default function DataTable({ rows }) {
    const [columns, setColumns] = useState([]);

    useEffect(() => {
        if (rows && rows.length > 0) {
            const first = rows[0];
            const cols = Object.keys(first).filter(k => !k.startsWith('_') && k !== '__v');
            setColumns(cols);
        } else {
            setColumns([]);
        }
    }, [rows]);

    if (!rows || rows.length === 0) {
        return <div>Нет данных</div>;
    }

    return (
        <div className="table-container">
            <table className="data-table">
                <thead>
                    <tr>
                        {columns.map(col => <th key={col}>{col}</th>)}
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row, idx) => (
                        <tr key={idx}>
                            {columns.map(col => <td key={col}>{row[col] !== null && row[col] !== undefined ? String(row[col]) : '—'}</td>)}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}