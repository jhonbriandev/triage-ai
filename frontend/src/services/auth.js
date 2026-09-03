// Única capa que habla con el backend de autenticación y con
// localStorage. No sabe nada de React — por eso puede usarse tanto
// dentro de componentes como en archivos planos (ej. api.js).
import api from "./api";

// Lee el "cuerpo" (payload) de un JWT sin librerías externas.
// Un JWT es cabecera.cuerpo.firma; el cuerpo viene en Base64 y
// atob() lo convierte a texto plano.
function decodeToken(token) {
  try {
    const payloadBase64 = token.split(".")[1];
    const payloadJson = atob(payloadBase64);
    return JSON.parse(payloadJson);
  } catch {
    return null; // token roto o mal formado: mejor null que romper la app
  }
}

// LOGIN: pide un par de tokens al backend y los guarda.
// Sin try/catch a propósito (igual que register): si /token/ falla,
// el error sube tal cual al componente que llamó a login(), y ahí
// se decide qué mostrar (ver Login.jsx).
export async function login(username, password) {
  const { data } = await api.post("/token/", { username, password });
  // SimpleJWT responde con { access, refresh }
  localStorage.setItem("access_token", data.access); // corta duración, va en cada petición
  localStorage.setItem("refresh_token", data.refresh); // larga duración, solo para renovar el access
  return data;
}

// REGISTER: crea un usuario nuevo. NO inicia sesión sola — después
// de esto, el flujo normal es redirigir a /login.
export async function register(username, password, email) {
  const { data } = await api.post("users/register/", {
    username,
    password,
    email,
  });
  return data;
}

// LOGOUT: borra los tokens guardados en el navegador. No avisa al
// backend — con JWT, el backend no "sabe" ni le importa que cerraste
// sesión; solo dejas de tener el pase.
//
// También existe un logout() en AuthContext.jsx: ese ENVUELVE a este
// y además hace setUser(null) para que React actualice la pantalla.
// Este de aquí es el único que puede usarse fuera de componentes.
export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// isAuthenticated: ¿hay un token guardado? (sin decodificarlo)
// REEMPLAZADO POR USEAUTH, NO SE USA
//
// export function isAuthenticated() {
//   return Boolean(localStorage.getItem("access_token"));
// }

// Única función que decodifica el token y arma el objeto de usuario.
// getActualRole() y AuthContext (getCurrentUser) se apoyan en esta.
export function getCurrentUser() {
  const token = localStorage.getItem("access_token");
  if (!token) return null;

  const payload = decodeToken(token);
  if (!payload) return null;

  return { username: payload.username, role: payload.role };
}

// Atajo para código FUERA de componentes React (donde no se puede
// usar useAuth()). Dentro de un componente, preferir useAuth().
export function getActualRole() {
  return getCurrentUser()?.role ?? null;
}
