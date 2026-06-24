import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getNationalIdentityAnomalies, getNationalIdentityAnomaliesDownloadUrl } from "../api/client";

export default function PicAnomaliesPage() {
  const { picCode } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getNationalIdentityAnomalies(picCode)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [picCode]);

  if (error) return <p style={{ color: "crimson" }}>Failed to load anomalies: {error}</p>;
  if (!data) return <p>Analyzing NATIONAL_IDENTITY records…</p>;

  const columns = data.rows.length > 0 ? Object.keys(data.rows[0]) : [];

  return (
    <div>
      <p><Link to={`/pic/${encodeURIComponent(picCode)}`}>← Back to PIC records</Link></p>
      <h2>NATIONAL_IDENTITY Anomalies — PIC {picCode}</h2>
      <p>
        {data.anomaly_count} anomalies out of {data.total} records (
        {data.total ? ((data.anomaly_count / data.total) * 100).toFixed(1) : 0}%)
        {" — "}
        <a href={getNationalIdentityAnomaliesDownloadUrl(picCode)}>Download Excel dashboard</a>
      </p>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col} style={cellStyle}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, i) => (
            <tr key={i} style={row.is_anomaly ? anomalyRowStyle : undefined}>
              {columns.map((col) => (
                <td key={col} style={cellStyle}>{String(row[col])}</td>
              ))}
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

const anomalyRowStyle = {
  backgroundColor: "#fdebeb",
  color: "#c00000",
};
