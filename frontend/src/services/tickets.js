import api from "./api";

// --------------------------------------------
// toListTickets: trae la lista de tickets del usuario logueado
// --------------------------------------------
export async function toListTickets() {
  const { data } = await api.get("/tickets/");
  // No necesitamos poner el token a mano aquí: el interceptor de "api"
  // (Bloque 2 de api.js) ya lo agrega automáticamente a esta petición.
  return data;
}
