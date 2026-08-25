import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../services/auth";

// PrivateRoute es un "guardia de puerta": envuelve una página y decide
// si el usuario puede entrar, o si lo manda de vuelta al login.
// "children" es lo que pongas ADENTRO de <PrivateRoute>...</PrivateRoute>
// cuando definas tus rutas (por ejemplo, <ListTickets />).
export default function PrivateRoute({ children }) {
  if (!isAuthenticated()) {
    // Si no hay token guardado, ni siquiera intentamos mostrar la página.
    // "replace" evita que el usuario pueda darle "atrás" en el navegador
    // y volver a caer en la página protegida sin estar logueado.
    return <Navigate to="/login" replace />;
  }

  // Si sí hay token, mostramos el contenido real de la ruta.
  return children;
}
