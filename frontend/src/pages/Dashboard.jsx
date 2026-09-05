import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { getTicketStats } from "../services/tickets";

const STATUS_LABELS = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

// Igual que STATUS_LABELS pero para prioridad: la clave es el valor
// que manda el backend (baja/media/alta/urgente) y el valor es lo
// que se muestra al usuario.
const PRIORITY_LABELS = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  urgente: "Urgente",
};

// Apuntamos a las mismas variables CSS que ya usan
// las etiquetas de prioridad (label--priority-*). Así el pie chart
// queda visualmente consistente con el resto de la app, y si cambias
// el color en el CSS, el gráfico se actualiza solo.
const PRIORITY_COLORS = {
  baja: "var(--color-priority-baja)",
  media: "var(--color-priority-media)",
  alta: "var(--color-priority-alta)",
  urgente: "var(--color-priority-urgente)",
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

  // Antes esto era Object.values(stats).reduce(...), pero ahora
  // "stats" trae también la clave "priority", que es un objeto y no
  // un número. Sumarla junto a los demás valores rompería la cuenta
  // (terminaría en NaN). Por eso ahora sumamos explícitamente solo
  // las claves de estado, usando STATUS_LABELS como lista de "cuáles
  // claves sí son conteos de estado".
  const total = Object.keys(STATUS_LABELS).reduce(
    (sum, key) => sum + (stats[key] ?? 0),
    0,
  );

  // Recharts no entiende un objeto tipo {baja: 3, media: 5, ...};
  // necesita un array de objetos con "name" (lo que se muestra) y
  // "value" (el número). Por eso convertimos aquí. También guardamos
  // "key" para poder buscar el color correcto de cada porción.
  const priorityData = Object.entries(PRIORITY_LABELS).map(([key, label]) => ({
    key,
    name: label,
    value: stats.priority?.[key] ?? 0,
  }));

  // Si no hay ningún ticket clasificado todavía, no tiene sentido
  // dibujar un círculo vacío: mostramos un mensaje en su lugar.
  const totalPriority = priorityData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="page-form">
      <Link to="/tickets" className="back-link">
        &larr; Volver a mis tickets
      </Link>
      <h1>Dashboard</h1>
      <h3>Clasificacion por Estado</h3>
      <p className="help">
        {total} ticket{total !== 1 ? "s" : ""} en total, a tu alcance.
      </p>

      <div className="stats-grid">
        {Object.entries(STATUS_LABELS).map(([key, label]) => (
          <Link
            key={key}
            to={`/tickets?status=${key}`}
            className={`stat-card stat-card--${key} stat-card-link`}
          >
            <span className="stat-number">{stats[key] ?? 0}</span>
            <span className="stat-label">{label}</span>
          </Link>
        ))}
      </div>

      <h3>Clasificacion por Prioridad</h3>

      {totalPriority === 0 ? (
        <p className="help">Aún no hay tickets clasificados por prioridad.</p>
      ) : (
        <div className="chart-card">
          {/* ResponsiveContainer hace que el gráfico se adapte al ancho
              del contenedor padre en vez de tener un tamaño fijo en
              píxeles. Es la forma más común de usar Recharts para que
              el gráfico se vea bien tanto en celular como en desktop. */}
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={priorityData}
                dataKey="value" // qué número dibuja cada porción
                nameKey="name" // qué texto se muestra (leyenda/tooltip)
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ name, value }) => `${name}: ${value}`}
              >
                {/* Un <Cell> por cada porción, así cada una toma su
                    propio color en vez de que todas compartan uno solo. */}
                {priorityData.map((entry) => (
                  <Cell key={entry.key} fill={PRIORITY_COLORS[entry.key]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
