# Día 7 — Triage IA: Frontend con React, Axios y Autenticación JWT

> Proyecto: Triage IA (sistema de tickets de soporte con sugerencias de IA)
> Stack de este día: React (Vite) + Axios + JWT + react-hook-form + react-router-dom

---

## 🎯 Objetivo del día

Conectar el frontend con el backend de forma segura y automática, usando Axios en
lugar de `fetch`, y dejar funcionando el flujo completo: **login → guardado de
tokens → petición protegida → renovación automática de token → logout**.

---

## 📚 Conceptos nuevos aprendidos

### 1. Axios vs Fetch — ¿por qué cambiamos?

`fetch` es como pedir un taxi por teléfono: en cada llamada hay que repetir
todos los datos (incluyendo el "pase" de autenticación). `Axios` es como una
app de taxi donde ya guardaste tus datos: cada viaje los usa automáticamente.

| Con `fetch` había que... | Con `Axios` esto se resuelve así |
|---|---|
| Escribir `JSON.stringify()` a mano | Axios convierte el objeto a JSON solo |
| Poner `Content-Type` en cada petición | Ya viene por defecto |
| Revisar `if (!response.ok)` a mano | Axios lanza un error automático → se usa `try/catch` |
| Poner el token JWT en cada petición | Un **interceptor** lo agrega solo, una sola vez configurado |
| Leer la respuesta con `await response.json()` | Los datos ya vienen listos en `response.data` |

**Por qué es la opción más común para principiantes en proyectos con JWT:**
porque olvidar poner el token en una sola petición (con `fetch`) es un error
frecuente y difícil de detectar. Centralizarlo en un interceptor elimina ese
riesgo por completo. Es el estándar de facto en proyectos Django + React con
autenticación por token.

### 2. `.then()` vs `async/await`

- `.then()` es como notas pegadas una sobre otra: "cuando llegue esto, haz
  esto, y luego esto otro..." — legible al inicio, pero difícil de seguir si
  se encadenan muchos pasos.
- `async/await` permite leer el código de arriba hacia abajo, como una receta
  normal, incluso si hay pasos que "esperan" una respuesta.

**Decisión del proyecto:** usar siempre `async/await` + `try/catch`, evitando
`.then()` / `.catch()` / `.finally()` encadenados.

**Excepción encontrada:** `useEffect` de React **no acepta una función `async`
directamente** como argumento. La solución estándar (y la usada en este
proyecto) es declarar una función `async` **dentro** del `useEffect` y
llamarla de inmediato:

```javascript
useEffect(() => {
  async function cargarDatos() {
    try {
      const data = await miServicio();
      setEstado(data);
    } catch {
      // manejo de error
    } finally {
      setLoading(false);
    }
  }
  cargarDatos();
}, []);
```

### 3. Interceptores de Axios

Un interceptor es un "guardia" que revisa cada petición o respuesta antes de
que continúe su camino:

- **Interceptor de request** (puerta de salida): antes de que la petición
  salga, revisa si hay un token guardado y lo agrega al header
  `Authorization`.
- **Interceptor de response** (puerta de entrada): revisa cada respuesta que
  llega. Si el backend responde `401` (token vencido) y aún no se ha
  reintentado, intenta renovar el token con el `refresh_token` y reintenta la
  petición original. Si el refresh también falla, borra los tokens y redirige
  a `/login`.

Analogía completa: **check-in del aeropuerto** (interceptor de request, te
grapa el pasaporte al boleto) + **aduana de llegada** (interceptor de
response: si tu pasaporte venció, primero intenta renovarlo antes de
rechazarte).

---

## 🗂️ Arquitectura de servicios (`frontend/src/services/`)

### `api.js` — instancia de Axios + interceptores

```javascript
import axios from "axios";

// Instancia personalizada de Axios: ya trae la URL base configurada,
// así el resto del proyecto no repite "http://localhost:8000/api" en cada llamada.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL, // viene del .env, cambia solo eso en producción
});

// INTERCEPTOR DE REQUEST: antes de CADA petición, agrega el token si existe.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// INTERCEPTOR DE RESPONSE: si una petición falla con 401, intenta renovar
// el token UNA sola vez con el refresh_token, y reintenta la petición original.
api.interceptors.response.use(
  (response) => response, // si todo salió bien, no hace nada extra

  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // evita bucles infinitos de reintento

      try {
        const refreshToken = localStorage.getItem("refresh_token");

        // OJO: se usa "axios" (el original), NO "api", para no volver a pasar
        // por estos mismos interceptores en esta llamada puntual.
        const { data } = await axios.post(
          `${import.meta.env.VITE_API_URL}/token/refresh/`,
          { refresh: refreshToken },
        );

        localStorage.setItem("access_token", data.access);
        originalRequest.headers.Authorization = `Bearer ${data.access}`;
        return api(originalRequest); // reintenta la petición original, ya con token nuevo

      } catch (renewError) {
        // Ni renovando funcionó: cerramos sesión localmente
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        return Promise.reject(renewError);
      }
    }

    return Promise.reject(error); // cualquier otro error sigue su curso normal
  },
);

export default api;
```

### `auth.js` — login, registro, logout, chequeo de sesión

```javascript
import api from "./api";

// Pide un par de tokens (access + refresh) al backend y los guarda.
export async function login(username, password) {
  const { data } = await api.post("/token/", { username, password });
  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);
  return data;
}

// Crea un usuario nuevo. NO guarda tokens: el registro no inicia sesión sola.
export async function register(username, password, email) {
  const { data } = await api.post("/register/", { username, password, email });
  return data;
}

// "Cierra sesión" borrando los tokens locales (el backend no se entera).
export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// Revisa si HAY un token guardado (no si sigue siendo válido).
export function isAuthenticated() {
  return Boolean(localStorage.getItem("access_token"));
}
```

> Nota de diseño: `login`/`register` no llevan `try/catch` aquí a propósito.
> Este archivo solo "habla" con el backend; es el **componente** que lo llama
> (el formulario) quien decide qué hacer si algo falla.

### `tickets.js` — llamadas relacionadas a tickets

```javascript
import api from "./api";

// Trae la lista de tickets del usuario logueado.
// No hace falta poner el token a mano: el interceptor de "api" ya lo agrega.
export async function getTickets() {
  const { data } = await api.get("/tickets/");
  return data;
}
```

> **Cambio de nombre:** la versión original se llamaba `toListTickets`, un
> nombre poco común en JS/React. La convención más usada para funciones que
> **obtienen** datos es `get...` o `fetch...` (`getTickets`, `fetchTickets`).
> Facilita que cualquiera (o un reclutador revisando el repo) entienda de
> inmediato qué hace la función sin leer su cuerpo.

---

## 🧩 Componentes construidos

### `ListTickets.jsx`

```javascript
import { useEffect, useState } from "react";
import { getTickets } from "../services/tickets";
import { logout } from "../services/auth";
import { useNavigate } from "react-router-dom";

export default function ListTickets() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    // useEffect no acepta un callback async directo, así que declaramos
    // la función async adentro y la llamamos de inmediato.
    async function cargarTickets() {
      try {
        const data = await getTickets();
        setTickets(data);
      } catch {
        setError("No se pudieron cargar los tickets.");
      } finally {
        setLoading(false); // se ejecuta siempre, haya éxito o error
      }
    }
    cargarTickets();
  }, []); // [] = ejecutar solo una vez, al montar el componente

  const exit = () => {
    logout();
    navigate("/login");
  };

  if (loading) return <p>Cargando tickets...</p>;

  return (
    <div className="page-list">
      <header>
        <h1>Mis tickets</h1>
        <button onClick={exit}>Cerrar sesión</button>
      </header>

      {error && <p className="error">{error}</p>}
      {!error && tickets.length === 0 && <p>Todavía no tienes tickets.</p>}

      <ul>
        {tickets.map((ticket) => (
          <li key={ticket.id} className={`ticket ticket--${ticket.priority}`}>
            <strong>{ticket.title}</strong>
            <span className="label">{ticket.status_display}</span>
            <span className="label">{ticket.priority_display}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### `Login.jsx`

```javascript
import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { login } from "../services/auth";

export default function Login() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();
  const [errorServidor, setErrorServidor] = useState("");
  const navigate = useNavigate();

  const onSubmit = async (data) => {
    setErrorServidor("");
    try {
      await login(data.username, data.password);
      navigate("/tickets");
    } catch (error) {
      // Mensaje genérico a propósito: no revela si el usuario existe o no,
      // solo si la contraseña está mal (buena práctica de seguridad).
      setErrorServidor("Usuario o contraseña incorrectos.");
    }
  };

  return (
    <div className="page-auth">
      <form onSubmit={handleSubmit(onSubmit)}>
        <h1>Iniciar sesión</h1>

        <div className="field">
          <label htmlFor="username">Usuario</label>
          <input
            id="username"
            {...register("username", { required: "El usuario es obligatorio" })}
          />
          {errors.username && <span className="error">{errors.username.message}</span>}
        </div>

        <div className="field">
          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            type="password"
            {...register("password", { required: "La contraseña es obligatoria" })}
          />
          {errors.password && <span className="error">{errors.password.message}</span>}
        </div>

        {errorServidor && <p className="error">{errorServidor}</p>}

        <button type="submit">Entrar</button>
        <p>¿No tienes cuenta? <Link to="/register">Regístrate</Link></p>
      </form>
    </div>
  );
}
```

**Dos tipos de error, dos mecanismos distintos:**
- `errors.username` / `errors.password` → validación del **formulario**
  (campo vacío), la maneja `react-hook-form` antes de tocar el backend.
- `errorServidor` → error que viene del **backend** (credenciales
  incorrectas), manejado con `useState` dentro del `catch`.

### `PrivateRoute.jsx`

```javascript
import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../services/auth";

// Guardia de puerta: envuelve una página y decide si el usuario puede
// entrar o si lo manda al login.
export default function PrivateRoute({ children }) {
  if (!isAuthenticated()) {
    // "replace" evita que con el botón "atrás" del navegador se pueda
    // volver a caer en la página protegida sin sesión.
    return <Navigate to="/login" replace />;
  }
  return children;
}
```

**Alternativa que existe (para conocimiento futuro):** en React Router v6
también es común usar `<Outlet />` con rutas anidadas en vez de envolver
`children`. Para un principiante, la versión con `children` (la que usamos
aquí) es más fácil de entender porque se ve como un componente normal; la
versión con `Outlet` es más "idiomática" de v6 pero exige entender rutas
anidadas primero. No es necesario cambiarla ahora.

---

## 🐞 Fallas encontradas y corregidas

| Falla | Dónde | Corrección |
|---|---|---|
| Uso de `.then()/.catch()/.finally()` encadenados, contra la regla de usar solo `async/await` | `ListTickets.jsx` | Se movió la carga de datos a una función `async` interna declarada dentro del `useEffect` |
| Nombre de función poco convencional (`toListTickets`) | `tickets.js` | Renombrado a `getTickets`, siguiendo la convención `get.../fetch...` para funciones que obtienen datos |

---

## 💡 Mejoras sugeridas (no bloqueantes, para tener en cuenta más adelante)

- `isAuthenticated()` solo verifica que exista un token, no que siga siendo
  válido. Es suficiente por ahora porque el interceptor de `api.js` cubre la
  renovación/expiración real; no requiere cambio inmediato.
- Cuando el proyecto crezca, considerar extraer el manejo de errores de
  `login`/`register` a mensajes más específicos (usuario ya existe, email
  inválido, etc.) usando el detalle que devuelve `error.response.data`.

---

## 📖 Glosario rápido del día

- **Interceptor:** función que se ejecuta automáticamente antes o después de
  cada petición/respuesta de Axios, sin que tengas que llamarla a mano.
- **Access token:** pase de corta duración usado en cada petición protegida.
- **Refresh token:** pase de larga duración, usado solo para pedir un access
  token nuevo cuando el actual vence.
- **`localStorage`:** almacenamiento del navegador que persiste aunque
  recargues la página (a diferencia de una variable normal de JS).
- **401 (Unauthorized):** código HTTP que el backend usa para decir "tu
  identificación ya no es válida".

---

## ✅ Checklist Día 7

- [x] Entender por qué Axios reemplaza a `fetch` en este proyecto
- [x] Entender la diferencia entre `.then()` y `async/await`, y la excepción
      de `useEffect`
- [x] Revisar y comentar `api.js` (interceptores de request y response)
- [x] Revisar y comentar `auth.js` y `tickets.js`
- [x] Corregir `ListTickets.jsx` para usar `async/await` dentro de `useEffect`
- [x] Revisar `Login.jsx` (ya alineado al estilo del proyecto)
- [x] Revisar y comentar `PrivateRoute.jsx`

---

## 🔜 Próximos pasos (Día 8)

- Conectar el resto de páginas pendientes al backend real usando este mismo
  patrón de servicios + `async/await`.
- Revisar el componente `Registro` con la misma lógica de `Login`.
- Retomar la colección de Postman construida en el Día 5 para validar
  endpoints en paralelo al frontend.
