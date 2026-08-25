import { useEffect, useState } from "react";
import { toListTickets } from "../services/tickets";
import { logout } from "../services/auth";
import { useNavigate } from "react-router-dom";

export default function ListTickets() {
  // Tres estados típicos para cualquier pantalla que carga datos de una API:
  const [tickets, setTickets] = useState([]); // los datos en sí
  const [loading, setLoading] = useState(true); // ¿todavía estamos esperando la respuesta?
  const [error, setError] = useState(""); // mensaje de error, si algo falló
  const navigate = useNavigate();

  useEffect(() => {
    // Función async interna (ver explicación arriba): useEffect no
    // acepta un callback async directo, así que la declaramos aquí y
    // la invocamos de inmediato.
    async function cargarTickets() {
      try {
        const data = await toListTickets();
        setTickets(data);
      } catch {
        setError("No se pudieron cargar los tickets.");
      } finally {
        // "finally" se ejecuta SIEMPRE, haya éxito o error;
        // por eso es el lugar ideal para apagar el "loading".
        setLoading(false);
      }
    }

    cargarTickets();
  }, []); // [] = "ejecuta esto solo una vez, cuando el componente aparece en pantalla"

  const exit = () => {
    logout(); // borra los tokens del localStorage
    navigate("/login"); // redirige al login (sin recargar toda la página)
  };

  // Mientras carga, no mostramos nada más que este mensaje
  if (loading) return <p>Cargando tickets...</p>;

  return (
    <div className="page-list">
      <header>
        <h1>Mis tickets</h1>
        <button onClick={exit}>Cerrar sesión</button>
      </header>

      {error && <p className="error">{error}</p>}
      {!error && tickets.length === 0 && <p>Todavía no tienes tickets.</p>}

      <ul>
        {tickets.map((ticket) => (
          // "key" es obligatorio en listas de React: le ayuda a identificar
          // qué elemento cambió, sin tener que redibujar toda la lista.
          <li key={ticket.id} className={`ticket ticket--${ticket.priority}`}>
            <strong>{ticket.title}</strong>
            <span className="label">{ticket.status_display}</span>
            <span className="label">{ticket.priority_display}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
