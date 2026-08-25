import api from "./api";
// Importamos nuestra instancia de axios ya configurada (con baseURL e interceptores)

// --------------------------------------------
// LOGIN: pide un par de tokens al backend
// --------------------------------------------
export async function login(username, password) {
  const { data } = await api.post("/token/", { username, password });
  // El backend (con SimpleJWT) responde con { access, refresh }

  localStorage.setItem("access_token", data.access); // token de corta duración, para cada petición
  localStorage.setItem("refresh_token", data.refresh); // token de larga duración, para renovar el access

  return data; // por si el componente que llama a login() quiere usar algo más de la respuesta
}

// --------------------------------------------
// REGISTER: crea un usuario nuevo (sin loguearlo automáticamente)
// --------------------------------------------
export async function register(username, password, email) {
  const { data } = await api.post("/register/", { username, password, email });
  return data;
  // Nota: aquí NO guardamos tokens, porque este endpoint solo crea el usuario,
  // no inicia sesión. Por eso después del registro normalmente rediriges a /login.
}

// --------------------------------------------
// LOGOUT: "cierra sesión" borrando los tokens guardados
// --------------------------------------------
export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  // Ojo: esto NO avisa al backend, solo borra el pase de acceso en el navegador.
  // Con JWT, el backend no "sabe" ni le importa que cerraste sesión;
  // simplemente ya no tienes token para demostrar quién eres.
}

// --------------------------------------------
// isAuthenticated: ¿el usuario tiene un token guardado?
// --------------------------------------------
export function isAuthenticated() {
  return Boolean(localStorage.getItem("access_token"));
  // Boolean(string) → true si hay texto, false si es null/vacío.
  // OJO: esto solo revisa que EXISTA un token, no si sigue siendo válido
  // (eso lo verifica el backend cuando lo usas; si venció, entra el
  // interceptor de response que ya vimos).
}
