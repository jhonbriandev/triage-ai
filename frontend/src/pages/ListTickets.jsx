import { useEffect, useState } from "react";
import { toListTickets } from "../services/tickets";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const STATUS_LABELS = {
  abierto: "Abierto",
  en_progreso: "En progreso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
};

export default function ListTickets() {
  // Tres estados típicos para cualquier pantalla que carga datos de una API:
  const [tickets, setTickets] = useState([]); // los datos en sí
  const [loading, setLoading] = useState(true); // ¿todavía estamos esperando la respuesta?
  const [error, setError] = useState(""); // mensaje de error, si algo falló
  const { user } = useAuth();

  // BLOQUE NUEVO: leer la URL actual
  // useSearchParams funciona como useState, pero en vez de guardar
  // el valor en memoria, lo lee y lo escribe directamente en la URL
  // del navegador (todo lo que viene después del "?").
  const [searchParams] = useSearchParams();
  const status = searchParams.get("status"); // null si no hay filtro

  useEffect(() => {
    // Función async interna (ver explicación arriba): useEffect no
    // acepta un callback async directo, así que la declaramos aquí y
    // la invocamos de inmediato.
    async function loadTickets() {
      setLoading(true); // se reactiva cada vez que cambia el filtro
      try {
        const data = await toListTickets(status);
        // Pasamos los valores de toListTickets a setTickets
        setTickets(data);
      } catch {
        setError("No se pudieron cargar los tickets.");
      } finally {
        // "finally" se ejecuta SIEMPRE, haya éxito o error;
        // por eso es el lugar ideal para apagar el "loading".
        setLoading(false);
      }
    }

    loadTickets();
  }, [status]); // AHORA depende de "status": si cambia, se vuelve a pedir

  // Mientras carga, no mostramos nada más que este mensaje
  if (loading) return <p>Cargando tickets...</p>;

  // Para depurar, para saber el rol y el usuario
  // Previamente agregada la funcion en la view de Django
  // console.log("rol actual:", role);
  // console.log("usuario completo:", username);
  return (
    <div className="page-list">
      <header>
        <h1>
          {status
            ? `Tickets: ${STATUS_LABELS[status] ?? status}`
            : "Mis tickets"}
        </h1>
        {/* Si hay un filtro activo, mostramos un link para quitarlo */}
        {status && <Link to="/tickets">Ver todos</Link>}
      </header>

      {error && <p className="error">{error}</p>}
      {!error && tickets.length === 0 && <p>Todavía no tienes tickets.</p>}

      <ul>
        {tickets.map((ticket) => (
          // "key" es obligatorio en listas de React: le ayuda a identificar
          // qué elemento cambió, sin tener que redibujar toda la lista.
          <li key={ticket.id} className="ticket">
            <Link to={`/tickets/${ticket.id}`}>
              <strong>{ticket.title}</strong>

              <span className={`label label--status-${ticket.status}`}>
                {ticket.status_display}
              </span>

              <span className={`label label--priority-${ticket.priority}`}>
                {ticket.priority_display}
              </span>

              <span
                className={`label ${!ticket.category_name ? "label--pending" : ""}`}
              >
                {ticket.category_name ?? "Sin categorizar"}
              </span>
              {(user?.role === "admin" || user?.role === "agent") && (
                <span className="label label--owner">
                  👤 {ticket.customer_username}
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
