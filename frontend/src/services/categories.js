import api from "./api";

// toListCategories: trae TODAS las categorías disponibles.
// La usa CreateTicket.jsx para llenar el <select> con opciones.
// No recibe parámetros porque no filtramos nada: queremos la lista
// completa, sin importar quién esté logueado.
export async function toListCategories() {
  const { data } = await api.get("/categories/");
  return data;
}

export async function createCategory(name) {
  const { data } = await api.post("/categories/", { name });
  return data;
}

export async function deleteCategory(id) {
  await api.delete(`/categories/${id}/`);
}
