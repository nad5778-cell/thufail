import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPicSummary } from "../api/client";

const REFRESH_INTERVAL_MS = 30_000;

export default function PicSummaryPage() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await getPicSummary();
        if (!cancelled) {
          setRows(data);
          setError(null);
          setLastUpdated(new Date());
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (error) return <p style={{ color: "crimson" }}>Failed to load PIC summary: {error}</p>;

  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div>
      <p style={{ color: "#666" }}>
        {lastUpdated ? `Last updated ${lastUpdated.toLocaleTimeString()} (auto-refreshes every 30s)` : "Loading…"}
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col} style={cellStyle}>{col}</th>
            ))}
            <th style={cellStyle}></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.pic_code}>
              {columns.map((col) => (
                <td key={col} style={cellStyle}>{String(row[col])}</td>
              ))}
              <td style={cellStyle}>
                <Link to={`/pic/${encodeURIComponent(row.pic_code)}`}>View records →</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const cellStyle = {
  border: "1px solid #ddd",
  padding: "8px 12px",
  textAlign: "left",
};
