import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getTicketStats } from "../services/tickets";

const STATUS_LABELS = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getTicketStats()
      .then(setStats)
      .catch(() => setError("Could not load the dashboard stats."));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p>Loading dashboard...</p>;

  const total = Object.values(stats).reduce((sum, n) => sum + n, 0);

  return (
    <div className="page-form">
      <Link to="/tickets" className="back-link">
        &larr; Volver a mis tickets
      </Link>
      <h1>Dashboard</h1>
      <p className="help">
        {total} ticket{total !== 1 ? "s" : ""} en total, a tu alcance.
      </p>

      <div className="stats-grid">
        {Object.entries(STATUS_LABELS).map(([key, label]) => (
          <div key={key} className={`stat-card stat-card--${key}`}>
            <span className="stat-number">{stats[key] ?? 0}</span>
            <span className="stat-label">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
