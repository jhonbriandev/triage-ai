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
export async function getTicket(id) {
  const { data } = await api.get(`/tickets/${id}/`);
  return data;
}

export async function createTicket({ title, description, category }) {
  const { data } = await api.post("/tickets/", {
    title,
    description,
    category,
  });
  return data;
}

export async function updateTicket(id, changes) {
  const { data } = await api.patch(`/tickets/${id}/`, changes);
  return data;
}
