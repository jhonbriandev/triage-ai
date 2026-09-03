import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Traduce el código interno del rol a un texto más humano para mostrar.
const NAME_ROLE = {
  customer: "Cliente",
  agent: "Agente",
  admin: "Administrador",
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const salir = () => {
    logout();
    navigate("/login");
  };

  // Sin usuario logueado (pantallas de login/registro) no se muestra navbar.
  if (!user) return null;

  return (
    <nav className="navbar">
      <Link to="/tickets" className="navbar-brand">
        🎫 Triage IA
      </Link>

      <div className="navbar-links">
        <Link to="/tickets">Tickets</Link>
        {user.role !== "agent" && <Link to="/tickets/new">+ Nuevo</Link>}
        {user.role === "admin" && (
          <Link to="/admin/categories">Categorías</Link>
        )}
        <Link to="/dashboard">Dashboard</Link>
      </div>

      <div className="navbar-user">
        <span className="navbar-username">{user.username}</span>
        <span className={`role-badge role-badge--${user.role}`}>
          {NAME_ROLE[user.role] ?? user.role}
        </span>
        <button className="button-danger" onClick={salir}>
          Salir
        </button>
      </div>
    </nav>
  );
}
