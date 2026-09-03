import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function PrivateRoute({ children, permittedRoles }) {
  const { user } = useAuth();

  // Sin sesión: directo al login.
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Con sesión, pero rol no permitido para esta ruta puntual.
  if (permittedRoles && !permittedRoles.includes(user.role)) {
    return <Navigate to="/tickets" replace />;
  }

  return children;
}
