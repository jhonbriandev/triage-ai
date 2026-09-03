import { createContext, useContext, useState } from "react";
import { getCurrentUser, logout as logoutService } from "../services/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Se lee el token UNA vez al cargar la app. Así, si recargan la página
  // (F5) estando logueados, no "olvidan" quién es el usuario.
  const [user, setUser] = useState(() => getCurrentUser());

  function refreshUser() {
    // Se llama DESPUÉS de que services/auth.js ya guardó el token nuevo.
    // Esta función solo actualiza lo que la interfaz muestra.
    setUser(getCurrentUser());
  }

  function logout() {
    logoutService(); // borra los tokens de localStorage
    setUser(null); // limpia lo que se muestra en pantalla
  }

  return (
    <AuthContext.Provider value={{ user, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Custom hook: evita repetir useContext(AuthContext) en cada componente.
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return context;
}
