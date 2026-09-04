import api from "./api";

// --------------------------------------------
// toListTickets: trae la lista de tickets del usuario logueado
// --------------------------------------------
export async function toListTickets(status) {
  // No necesitamos poner el token a mano aquí: el interceptor de "api"
  // (Bloque 2 de api.js) ya lo agrega automáticamente a esta petición.
  // "params" le dice a axios: agrega esto como parte de la URL,
  // en forma de "?clave=valor". Si no hay status, mandamos un
  // objeto vacío y la URL queda igual que antes (sin filtro).
  const { data } = await api.get("/tickets/", {
    params: status ? { status } : {},
  });
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

export async function getTicketStats() {
  const { data } = await api.get("/tickets/stats/");
  return data;
}

// --------------------------------------------
// listAgents: trae la lista de agentes disponibles
// (el backend ya restringe esto a solo admin; aquí solo
// hacemos la petición, no hace falta validar el rol aquí)
// --------------------------------------------
export async function listAgents() {
  const { data } = await api.get("/tickets/agents/");
  return data;
}

// --------------------------------------------
// assignTicket: asigna (o quita) un agente de un ticket puntual
// --------------------------------------------
export async function assignTicket(id, agentId) {
  // Apunta a la acción especial /assign/ del backend, NO al
  // endpoint general de update (por eso no reusamos updateTicket).
  const { data } = await api.patch(`/tickets/${id}/assign/`, {
    assigned_agent: agentId,
  });
  return data;
}
