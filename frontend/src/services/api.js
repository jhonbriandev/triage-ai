import axios from "axios";

// ============================================
// BLOQUE 1: Instancia personalizada de Axios
// ============================================
// En vez de usar "axios" a secas en cada componente, creamos una versión
// propia ("api") que ya trae configurada la URL base del backend.
// Así, en el resto del proyecto solo escribimos api.get("/tickets/")
// en vez de repetir "http://localhost:8000/api/tickets/" en cada archivo.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  // VITE_API_URL viene de tu archivo .env (ej: VITE_API_URL=http://localhost:8000/api)
  // Esto es importante para producción: cuando despliegues el proyecto,
  // solo cambias esa variable de entorno, no el código.
});

// ============================================
// BLOQUE 2: Interceptor de REQUEST (antes de salir)
// ============================================
// Piensa en esto como un guardia de seguridad parado en la puerta de salida.
// Antes de que CUALQUIER petición salga hacia el backend, este guardia
// revisa: "¿este usuario tiene su pase (token) guardado?" Si lo tiene,
// se lo pega en el header Authorization automáticamente.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  // localStorage es como un cajón del navegador donde guardamos datos
  // que sobreviven aunque recargues la página (a diferencia de una
  // variable normal de JavaScript, que se borra al refrescar).
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    // "Bearer" es solo una palabra estándar que dice "lo que sigue es un token".
  }
  return config; // siempre debemos devolver la config, o la petición no sale
});

// ============================================
// BLOQUE 3: Interceptor de RESPONSE (al recibir la respuesta)
// ============================================
// Este es el "guardia" pero en la puerta de ENTRADA: revisa cada respuesta
// que llega del backend. Recibe dos funciones:
// - la primera se ejecuta si todo salió bien (response) => response
// - la segunda se ejecuta si algo falló (async (error) => {...})
api.interceptors.response.use(
  (response) => response, // si la respuesta es exitosa, no hacemos nada, la dejamos pasar tal cual

  async (error) => {
    // Guardamos la petición original que falló, para poder reintentarla después
    const originalRequest = error.config;

    // --------------------------------------------
    // Sub-bloque 3.1: ¿Es un error 401 (token vencido)
    // y no lo hemos intentado renovar todavía?
    // --------------------------------------------
    // "401" es el código HTTP que el backend usa para decir
    // "tu identificación ya no es válida" (token expirado).
    // originalRequest._retry es una bandera que nosotros mismos ponemos,
    // para asegurarnos de que esto se intente SOLO UNA VEZ por petición
    // (si no, y el refresh también falla, entraríamos en un bucle infinito).
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // --------------------------------------------
        // Sub-bloque 3.2: Intentamos renovar el access_token
        // --------------------------------------------
        const refreshToken = localStorage.getItem("refresh_token");

        // OJO: aquí usamos "axios" (el original), NO "api".
        // Esto es a propósito: si usáramos "api", esta petición
        // pasaría de nuevo por el interceptor de request (Bloque 2)
        // y por el de response (este mismo), generando confusión o loops.
        // Usamos axios "limpio" para esta única llamada especial.
        const { data } = await axios.post(
          `${import.meta.env.VITE_API_URL}/token/refresh/`,
          { refresh: refreshToken },
        );

        // Si el refresh funcionó, guardamos el nuevo access_token
        localStorage.setItem("access_token", data.access);

        // Actualizamos el header de la petición ORIGINAL que había fallado,
        // con el token nuevo...
        originalRequest.headers.Authorization = `Bearer ${data.access}`;

        // ...y la reintentamos, como si nunca hubiera fallado.
        // El usuario ni se entera de que hubo un problema en el camino.
        return api(originalRequest);
      } catch (renewError) {
        // --------------------------------------------
        // Sub-bloque 3.3: El refresh_token también venció o es inválido
        // --------------------------------------------
        // Si ni siquiera renovando el token funciona, ya no hay nada que
        // hacer: cerramos la sesión localmente y mandamos al usuario
        // de vuelta al login.
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        return Promise.reject(renewError);
      }
    }

    // Si el error NO era un 401, o ya lo habíamos reintentado antes,
    // simplemente dejamos que el error siga su curso normal
    // (para que el try/catch de tu componente lo capture).
    return Promise.reject(error);
  },
);

export default api;
