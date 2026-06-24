import { Routes, Route, Link } from "react-router-dom";
import PicSummaryPage from "./pages/PicSummaryPage";
import PicDetailPage from "./pages/PicDetailPage";
import PicAnomaliesPage from "./pages/PicAnomaliesPage";

export default function App() {
  return (
    <div style={{ fontFamily: "sans-serif", margin: "0 auto", maxWidth: 1100, padding: 24 }}>
      <header style={{ marginBottom: 24 }}>
        <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
          <h1>PIC Data Portal</h1>
        </Link>
      </header>
      <Routes>
        <Route path="/" element={<PicSummaryPage />} />
        <Route path="/pic/:picCode" element={<PicDetailPage />} />
        <Route path="/pic/:picCode/anomalies" element={<PicAnomaliesPage />} />
      </Routes>
    </div>
  );
}
