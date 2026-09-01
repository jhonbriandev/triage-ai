import api from "./api";

// toListCommentaries: trae solo los comentarios de UN ticket
// específico, no todos los comentarios de todos los tickets.
//
// { params: { ticket: ticketId } } es la forma en que Axios arma
// automáticamente el ?ticket=5 al final de la URL (query param),
// sin que tengas que construir el string a mano con template literals.
// Es equivalente a llamar a: /commentaries/?ticket=5
export async function toListCommentaries(ticketId) {
  const { data } = await api.get("/commentaries/", {
    params: { ticket: ticketId },
  });
  return data;
}

// createCommentary: envía un comentario nuevo.
// Recibimos un objeto { ticket, text } y lo desestructuramos en los
// parámetros de la función para dejar explícito qué datos exige el
// backend, en vez de recibir un objeto genérico sin nombre.
export async function createCommentary({ ticket, text }) {
  const { data } = await api.post("/commentaries/", { ticket, text });
  return data;
}
