import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getPicRecords } from "../api/client";

const PAGE_SIZE = 50;

export default function PicDetailPage() {
  const { picCode } = useParams();
  const [rows, setRows] = useState([]);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getPicRecords(picCode, { limit: PAGE_SIZE, offset })
      .then((data) => {
        if (!cancelled) setRows(data.rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [picCode, offset]);

  if (error) return <p style={{ color: "crimson" }}>Failed to load records: {error}</p>;

  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];

  return (
    <div>
      <p><Link to="/">← Back to summary</Link></p>
      <h2>Records for PIC {picCode}</h2>
      <p><Link to={`/pic/${encodeURIComponent(picCode)}/anomalies`}>Run NATIONAL_IDENTITY anomaly check →</Link></p>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col} style={cellStyle}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col} style={cellStyle}>{String(row[col])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
        <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
          Previous
        </button>
        <button disabled={rows.length < PAGE_SIZE} onClick={() => setOffset(offset + PAGE_SIZE)}>
          Next
        </button>
      </div>
    </div>
  );
}

const cellStyle = {
  border: "1px solid #ddd",
  padding: "8px 12px",
  textAlign: "left",
};
