# Día 11 — Identidad de usuario, Navbar y colores (cierre)

> Este documento es el **cierre** del Día 11: código final, fallos
> encontrados en el camino y decisiones tomadas. El documento de propuesta
> (`dia-11-identidad-usuario-navbar-estilos.md`) fue el punto de partida
> usado *durante* el día para ir construyendo esto; este es el resultado.
> Cada bloque de código está marcado como **✅ confirmado** (ya visto en el
> código real que compartieron) o **🔲 propuesto** (recomendado, pero no
> confirmado todavía contra el archivo real).

---

## 🎯 Objetivo cumplido

- Mostrar nombre + rol del usuario logueado, en el Navbar.
- Decidir no usar sidebar (pocas secciones de navegación).
- Mostrar el dueño del ticket en la lista, solo para admin/agente.
- Colores por prioridad y estado.
- Consolidar cómo se lee la sesión en toda la app: **una sola fuente de
  verdad** — `useAuth()` dentro de componentes, `services/auth.js`
  directamente solo fuera de ellos (interceptores, utilidades).

---

## 🗺️ Mapa final de archivos

```
services/auth.js         habla con el backend + decodifica el JWT
        ↓
context/AuthContext.jsx   guarda el usuario decodificado en memoria de React
        ↓
useAuth()                 lo que TODO componente usa para leer sesión
        ↓
   ┌────┼──────────┬──────────────┐
Navbar  ListTickets  DetailTicket   PrivateRoute (🔲 pendiente confirmar)
```

`isAuthenticated()` ya no aparece en el mapa: se confirmó que no tenía
ningún consumidor real en el proyecto y se eliminó de `services/auth.js`.

---

## 🐞 Fallos encontrados y corregidos (bitácora del día)

| # | Falla | Dónde | Corrección |
|---|---|---|---|
| 1 | `getUsername()` devolvía el objeto `{username, role}` completo, pese a su nombre | `services/auth.js` | Renombrada a `getCurrentUser()`; `getActualRole()` ahora la reutiliza en vez de decodificar el token dos veces |
| 2 | El método `login` del Context no hacía login (no llamaba al backend, solo releía el token) — nombre engañoso | `context/AuthContext.jsx` | Renombrado a `refreshUser()` |
| 3 | `exit()` llamaba a `logout()` sin haberlo importado — código muerto con un bug latente (hubiera roto la app si alguien lo conectaba a un botón) | `ListTickets.jsx` | Eliminada, junto con el `useNavigate` que ya no se usaba en el archivo |
| 4 | `console.log` de depuración de rol/usuario quedaron en el código final | `ListTickets.jsx` | Eliminados |
| 5 | `login()` tenía un `try/catch` que rompía la coherencia con `register()` (la decisión ya documentada en el Día 7 era que ninguno de los dos lo llevara) | `services/auth.js` | Se quitó el `try/catch` de `login()` |
| 6 | `isAuthenticated()` sin ningún consumidor real en el proyecto | `services/auth.js` | Confirmado huérfano y eliminado |
| 7 | `DetailTicket.jsx` seguía leyendo el rol con `getActualRole()` directo, en vez de `useAuth()` — rompía la regla de "una sola fuente de verdad" dentro de componentes | `DetailTicket.jsx` | Reemplazado por `useAuth()` |

---

## 🌐 Idiomas — ya confirmado (antes decía "a verificar")

El `<select>` real de `DetailTicket.jsx` confirma que `status` viaja en
español, igual que `priority`:

| Campo | Idioma | Valores confirmados |
|---|---|---|
| `role` | Inglés | `customer`, `agent`, `admin` |
| `priority` | Español | `baja`, `media`, `alta`, `urgente` |
| `status` | Español | `abierto`, `en_progreso`, `resuelto`, `cerrado` |

Esto confirma que los badges de color (`label--status-abierto`, etc.)
propuestos en el CSS ya usan los nombres correctos.

---

## 🗂️ Código final

### `services/auth.js` — ✅ confirmado

```javascript
// Única capa que habla con el backend de autenticación y con
// localStorage. No sabe nada de React — por eso puede usarse tanto
// dentro de componentes como en archivos planos (ej. api.js).
import api from "./api";

// Lee el "cuerpo" (payload) de un JWT sin librerías externas.
function decodeToken(token) {
  try {
    const payloadBase64 = token.split(".")[1];
    const payloadJson = atob(payloadBase64);
    return JSON.parse(payloadJson);
  } catch {
    return null;
  }
}

// LOGIN: pide tokens al backend y los guarda. Sin try/catch a propósito
// (igual que register): el componente que llama decide qué hacer si falla.
export async function login(username, password) {
  const { data } = await api.post("/token/", { username, password });
  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);
  return data;
}

// REGISTER: crea un usuario nuevo. NO inicia sesión sola.
export async function register(username, password, email) {
  const { data } = await api.post("users/register/", { username, password, email });
  return data;
}

// LOGOUT: borra los tokens del navegador. No avisa al backend.
// El logout() de AuthContext ENVUELVE a este y además hace setUser(null).
export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// Decodifica el token y arma el objeto de usuario. getActualRole() se
// apoya en esta para no repetir la lógica de decodificación.
export function getCurrentUser() {
  const token = localStorage.getItem("access_token");
  if (!token) return null;

  const payload = decodeToken(token);
  if (!payload) return null;

  return { username: payload.username, role: payload.role };
}

// Atajo para código FUERA de componentes React (donde no se puede usar
// useAuth()). Dentro de un componente, siempre preferir useAuth().
export function getActualRole() {
  return getCurrentUser()?.role ?? null;
}
```

### `context/AuthContext.jsx` — ✅ confirmado

```jsx
import { createContext, useContext, useState } from "react";
import { getCurrentUser, logout as logoutService } from "../services/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getCurrentUser());

  // Vuelve a leer el token y actualiza lo que la app muestra.
  // NO llama al backend — eso ya lo hizo services/auth.js antes.
  function refreshUser() {
    setUser(getCurrentUser());
  }

  function logout() {
    logoutService();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return context;
}
```

### `components/Navbar.jsx` — ✅ confirmado

```jsx
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAME_ROLE = {
  customer: "Cliente",
  agent: "Agente",
  admin: "Administrador",
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const salir = () => {
    logout();
    navigate("/login");
  };

  if (!user) return null; // no hay navbar en pantallas de login/registro

  return (
    <nav className="navbar">
      <Link to="/tickets" className="navbar-brand">🎫 Triage IA</Link>

      <div className="navbar-links">
        <Link to="/tickets">Tickets</Link>
        {user.role !== "agent" && <Link to="/tickets/new">+ Nuevo</Link>}
        {user.role === "admin" && <Link to="/admin/categories">Categorías</Link>}
        <Link to="/dashboard">Dashboard</Link>
      </div>

      <div className="navbar-user">
        <span className="navbar-username">{user.username}</span>
        <span className={`role-badge role-badge--${user.role}`}>
          {NAME_ROLE[user.role] ?? user.role}
        </span>
        <button className="button-danger" onClick={salir}>Salir</button>
      </div>
    </nav>
  );
}
```

### `Login.jsx` — ✅ confirmado

```jsx
import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { login as loginService } from "../services/auth";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const [errorServidor, setErrorServidor] = useState("");
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const onSubmit = async (data) => {
    setErrorServidor("");
    try {
      await loginService(data.username, data.password);
      refreshUser(); // avisa al Context: "ya hay usuario logueado"
      navigate("/tickets");
    } catch (error) {
      setErrorServidor("Usuario o contraseña incorrectos.");
    }
  };

  return (
    <div className="page-auth">
      <form onSubmit={handleSubmit(onSubmit)}>
        <h1>Iniciar sesión</h1>
        <div className="field">
          <label htmlFor="username">Usuario</label>
          <input id="username" {...register("username", { required: "El usuario es obligatorio" })} />
          {errors.username && <span className="error">{errors.username.message}</span>}
        </div>
        <div className="field">
          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" {...register("password", { required: "La contraseña es obligatoria" })} />
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

### `Register.jsx` — ✅ confirmado, sin cambios necesarios

```jsx
import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { register as registerUser } from "../services/auth";

export default function Register() {
  const { register, handleSubmit, formState: { errors } } = useForm();
  const [errorServidor, setErrorServidor] = useState("");
  const navigate = useNavigate();

  const onSubmit = async (data) => {
    setErrorServidor("");
    try {
      await registerUser(data.username, data.password, data.email);
      navigate("/login");
    } catch (error) {
      const dataError = error.response?.data;
      const firstError = dataError ? Object.values(dataError)[0]?.[0] : null;
      setErrorServidor(firstError || "No se pudo completar el registro.");
    }
  };

  return (
    <div className="page-auth">
      <form onSubmit={handleSubmit(onSubmit)}>
        <h1>Regístrate</h1>
        <div className="field">
          <label htmlFor="username">Usuario</label>
          <input id="username" {...register("username", { required: "El usuario es obligatorio" })} />
          {errors.username && <span className="error">{errors.username.message}</span>}
        </div>
        <div className="field">
          <label htmlFor="password">Contraseña</label>
          <input id="password" type="password" {...register("password", { required: "La contraseña es obligatoria", minLength: { value: 8, message: "Mínimo 8 caracteres" } })} />
          {errors.password && <span className="error">{errors.password.message}</span>}
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" {...register("email", { required: "El email es obligatorio" })} />
          {errors.email && <span className="error">{errors.email.message}</span>}
        </div>
        {errorServidor && <p className="error">{errorServidor}</p>}
        <button type="submit">Registrar</button>
        <p>¿Tienes cuenta? <Link to="/login">Inicia Sesión</Link></p>
      </form>
    </div>
  );
}
```

**Por qué no necesita `useAuth()`:** este archivo nunca lee ni depende de
la sesión — solo crea un usuario nuevo y redirige a `/login`. Es
justamente la decisión ya documentada en el Día 7: *"el registro no inicia
sesión sola"*. Forzar un `useAuth()` aquí sería agregar una dependencia que
el componente no necesita — la regla de "una sola fuente de verdad" también
significa no usar el Context donde no hace falta.

### `ListTickets.jsx` — ✅ confirmado

```jsx
import { useEffect, useState } from "react";
import { toListTickets } from "../services/tickets";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ListTickets() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { user } = useAuth();

  useEffect(() => {
    async function loadTickets() {
      try {
        const data = await toListTickets();
        setTickets(data);
      } catch {
        setError("No se pudieron cargar los tickets.");
      } finally {
        setLoading(false);
      }
    }
    loadTickets();
  }, []);

  if (loading) return <p>Cargando tickets...</p>;

  return (
    <div className="page-list">
      <header>
        <h1>Mis tickets</h1>
      </header>

      {error && <p className="error">{error}</p>}
      {!error && tickets.length === 0 && <p>Todavía no tienes tickets.</p>}

      <ul>
        {tickets.map((ticket) => (
          <li key={ticket.id} className="ticket">
            <Link to={`/tickets/${ticket.id}`}>
              <strong>{ticket.title}</strong>
              <span className={`label label--status-${ticket.status}`}>{ticket.status_display}</span>
              <span className={`label label--priority-${ticket.priority}`}>{ticket.priority_display}</span>
              <span className={`label ${!ticket.category_name ? "label--pending" : ""}`}>
                {ticket.category_name ?? "Sin categorizar"}
              </span>
              {(user?.role === "admin" || user?.role === "agent") && (
                <span className="label label--owner">👤 {ticket.customer_username}</span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### `DetailTicket.jsx` — ✅ actualizado hoy (`getActualRole` → `useAuth`)

```jsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { getTicket, updateTicket } from "../services/tickets";
import { toListCommentaries, createCommentary } from "../services/commentaries";
import { useAuth } from "../context/AuthContext";
import { toListCategories } from "../services/categories";

export default function DetailTicket() {
  const { id } = useParams();
  const { user } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [commentaries, setCommentaries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const canManage = user?.role === "agent" || user?.role === "admin";

  const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm();

  // Formulario de gestión (estado/prioridad/categoría): SIEMPRE disponible
  // para agente/admin, exista o no una sugerencia de IA.
  const manageForm = useForm();

  const loadAll = async () => {
    try {
      const [dataTicket, dataCommentaries] = await Promise.all([
        getTicket(id),
        toListCommentaries(id),
      ]);
      setTicket(dataTicket);
      setCommentaries(dataCommentaries);

      if (canManage) {
        const cats = await toListCategories();
        setCategories(cats);
        // Precarga con los valores ACTUALES del ticket, no con la sugerencia.
        manageForm.setValue("status", dataTicket.status);
        manageForm.setValue("priority", dataTicket.priority);
        manageForm.setValue("category", dataTicket.category ?? "");
      }
    } catch {
      setError("No se pudo cargar este ticket (¿existe y es tuyo?).");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onSubmitCommentary = async (data) => {
    await createCommentary({ ticket: id, text: data.text });
    reset();
    setCommentaries(await toListCommentaries(id));
  };

  const useSuggestionAnswer = () => {
    setValue("text", ticket.suggestion_ai.suggestion_answer);
  };

  // Copia los valores SUGERIDOS al formulario de gestión, sin guardarlos
  // todavía — el agente los revisa antes de enviar.
  const useSuggestedValues = () => {
    const suggestion = ticket.suggestion_ai;
    const match = categories.find(
      (c) => c.name.toLowerCase() === suggestion.suggestion_category.toLowerCase(),
    );
    manageForm.setValue("category", match?.id ?? "");
    manageForm.setValue("priority", suggestion.suggestion_priority);
  };

  const onManageSubmit = async (data) => {
    const updated = await updateTicket(id, {
      status: data.status,
      priority: data.priority,
      category: data.category || null,
    });
    setTicket({ ...updated, suggestion_ai: ticket.suggestion_ai });
  };

  if (loading) return <p>Cargando...</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <div className="page-detail">
      <Link to="/tickets">&larr; Volver a mis tickets</Link>

      <h1>{ticket.title}</h1>
      <div className="labels">
        <span className="label">{ticket.status_display}</span>
        <span className="label">{ticket.priority_display}</span>
        <span className="label">{ticket.category_name ?? "Sin categorizar"}</span>
      </div>
      <p>{ticket.description}</p>
      <p className="meta">
        Creado por {ticket.customer_username} · {new Date(ticket.created_at).toLocaleString()}
      </p>

      {canManage && (
        <div className="card-manage">
          <h2>Gestionar ticket</h2>
          <form onSubmit={manageForm.handleSubmit(onManageSubmit)} className="form-manage">
            <div className="field">
              <label>Estado</label>
              <select {...manageForm.register("status")}>
                <option value="abierto">Abierto</option>
                <option value="en_progreso">En progreso</option>
                <option value="resuelto">Resuelto</option>
                <option value="cerrado">Cerrado</option>
              </select>
            </div>
            <div className="field">
              <label>Prioridad</label>
              <select {...manageForm.register("priority")}>
                <option value="baja">Baja</option>
                <option value="media">Media</option>
                <option value="alta">Alta</option>
                <option value="urgente">Urgente</option>
              </select>
            </div>
            <div className="field">
              <label>Categoría</label>
              <select {...manageForm.register("category")}>
                <option value="">Sin categoría</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <button type="submit">Guardar cambios</button>
          </form>
        </div>
      )}

      {canManage && ticket.suggestion_ai && (
        <div className="card-ai">
          <h2>Sugerencia de la IA</h2>
          <p><strong>Categoría sugerida:</strong> {ticket.suggestion_ai.suggestion_category}</p>
          <p><strong>Prioridad sugerida:</strong> {ticket.suggestion_ai.suggestion_priority}</p>
          <p><strong>Resumen:</strong> {ticket.suggestion_ai.generated_summary}</p>
          <p><strong>Respuesta sugerida:</strong> {ticket.suggestion_ai.suggestion_answer}</p>
          <div className="ai-actions">
            <button type="button" onClick={useSuggestedValues}>Usar estos valores en "Gestionar ticket"</button>
            <button type="button" onClick={useSuggestionAnswer}>Usar esta respuesta como comentario</button>
          </div>
        </div>
      )}

      <h2>Comentarios</h2>
      <ul className="list-commentaries">
        {commentaries.length === 0 && <p>Todavía no hay comentarios.</p>}
        {commentaries.map((c) => (
          <li key={c.id}><strong>{c.author_username}:</strong> {c.text}</li>
        ))}
      </ul>

      <form onSubmit={handleSubmit(onSubmitCommentary)} className="form-commentary">
        <textarea rows={3} placeholder="Escribe un comentario..." {...register("text", { required: "Escribe algo antes de enviar" })} />
        {errors.text && <span className="error">{errors.text.message}</span>}
        <button type="submit">Comentar</button>
      </form>
    </div>
  );
}
```

**Único cambio real:** el import de `getActualRole` se cambió por
`useAuth`, y `role`/`canManage` ahora se calculan desde `user?.role`. Todo
lo demás del archivo (formularios, sugerencia de IA, comentarios) queda
exactamente igual — no se tocó lógica de negocio, solo la fuente de la
sesión.

---

## 🔲 Pendiente de confirmar (no verificado contra archivo real)

### `PrivateRoute.jsx`

Nunca se compartió el archivo real durante este día. La versión
recomendada sigue siendo esta, construida sobre el Día 7 y el Día 10:

```jsx
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function PrivateRoute({ children, permittedRoles }) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (permittedRoles && !permittedRoles.includes(user.role)) {
    return <Navigate to="/tickets" replace />;
  }

  return children;
}
```

⚠️ Queda pendiente para el próximo día: compartir el archivo real y
confirmar si ya usa `useAuth()` o si todavía depende de
`isAuthenticated()`/`getActualRole()` — que ya no existen en `auth.js` tal
como quedó hoy, así que si `PrivateRoute.jsx` real todavía los importa,
**va a romperse** (`isAuthenticated is not a function` o similar). Esta es
la primera cosa a revisar en la próxima sesión.

### `components/Footer.jsx`, estructura de `App.jsx` y CSS

Propuestos en el documento de trabajo del día, pero nunca confirmados
contra el código real (el usuario no los compartió de vuelta). Se dejan
como referencia rápida por si aún no se aplicaron:

```jsx
// components/Footer.jsx
export default function Footer() {
  return (
    <footer className="footer">
      <p>Triage IA — Proyecto final Full Stack · {new Date().getFullYear()}</p>
    </footer>
  );
}
```

```jsx
// App.jsx — estructura general
<div className="app-shell">
  <Navbar />
  <main className="app-main">
    <Routes>{/* rutas existentes, sin cambios */}</Routes>
  </main>
  <Footer />
</div>
```

```css
:root {
  --color-priority-baja: #16a34a;
  --color-priority-media: #f59e0b;
  --color-priority-alta: #ea580c;
  --color-priority-urgente: #dc2626;
  --color-status-abierto: #2563eb;
  --color-status-en_progreso: #f59e0b;
  --color-status-resuelto: #16a34a;
  --color-status-cerrado: #6b7280;
  --color-role-customer: #2563eb;
  --color-role-agent: #7c3aed;
  --color-role-admin: #dc2626;
}
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
.app-main { flex: 1; }
.navbar { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; padding: 1rem 1.5rem; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.navbar-brand { font-weight: 700; font-size: 1.1rem; color: #1a1a1a; text-decoration: none; }
.navbar-links { display: flex; gap: 1rem; flex-wrap: wrap; }
.navbar-links a { color: #444; text-decoration: none; font-size: 0.95rem; }
.navbar-links a:hover { color: #2563eb; }
.navbar-user { display: flex; align-items: center; gap: 0.6rem; }
.navbar-username { font-weight: 600; font-size: 0.9rem; }
.role-badge { font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 999px; color: white; text-transform: uppercase; letter-spacing: 0.03em; }
.role-badge--customer { background: var(--color-role-customer); }
.role-badge--agent { background: var(--color-role-agent); }
.role-badge--admin { background: var(--color-role-admin); }
.footer { text-align: center; padding: 1.5rem; color: #888; font-size: 0.85rem; }
.label--priority-baja { background: var(--color-priority-baja); color: white; }
.label--priority-media { background: var(--color-priority-media); color: white; }
.label--priority-alta { background: var(--color-priority-alta); color: white; }
.label--priority-urgente { background: var(--color-priority-urgente); color: white; font-weight: 700; }
.label--status-abierto { background: var(--color-status-abierto); color: white; }
.label--status-en_progreso { background: var(--color-status-en_progreso); color: white; }
.label--status-resuelto { background: var(--color-status-resuelto); color: white; }
.label--status-cerrado { background: var(--color-status-cerrado); color: #f0f0f0; }
.label--owner { background: #eef2ff; color: #3730a3; }
.ticket { transition: box-shadow 0.15s ease, transform 0.15s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.ticket:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.1); transform: translateY(-1px); }
```

---

## 📖 Glosario del día (recopilado)

- **Context API:** comparte datos con cualquier componente sin pasarlos a
  mano de padre a hijo.
- **Custom hook (`useAuth`):** empaqueta `useContext` bajo un nombre simple.
- **Payload de un JWT:** la parte de en medio del token, en texto plano
  codificado en Base64 (no encriptado).
- **Código huérfano:** una función exportada que ningún otro archivo
  importa — es señal de que se puede simplificar o borrar (caso de
  `isAuthenticated()`).
- **Una sola fuente de verdad:** un mismo dato (el usuario logueado) se lee
  siempre por el mismo camino (`useAuth()` en componentes), para que nunca
  haya dos copias que se puedan desincronizar.

---

## ✅ Checklist Día 11 — cerrado

- [x] `getUsername()` → `getCurrentUser()`; `getActualRole()` reutilizándola
- [x] Context: `login` → `refreshUser`; `Login.jsx` actualizado
- [x] `ListTickets.jsx` limpio (sin lectura directa del token, sin `console.log`, sin `exit()`)
- [x] `login()` sin `try/catch`, coherente con `register()`
- [x] `isAuthenticated()` confirmado huérfano y eliminado
- [x] `DetailTicket.jsx` usando `useAuth()` en vez de `getActualRole()`
- [x] `Register.jsx` revisado — confirmado que no necesita `useAuth()`
- [x] Confirmado: `status` y `priority` viajan en español
- [ ] `PrivateRoute.jsx` — pendiente, no compartido (ver riesgo arriba: puede romperse por los imports eliminados)
- [ ] `Footer.jsx`, estructura de `App.jsx` y CSS — propuestos, no confirmados contra el proyecto real

## 🔜 Pendientes para el Día 12

1. **Prioridad alta:** revisar `PrivateRoute.jsx` real — riesgo de que
   siga importando `isAuthenticated()`/`getActualRole()` de una forma que
   ya no exista o haya cambiado.
2. Confirmar si `Footer.jsx`, la estructura de `App.jsx` y el CSS
   propuesto ya se aplicaron.
3. Pendientes ya conocidos de días anteriores: sesión que no expira al
   cerrar la pestaña; 404 en Vercel al volver a la lista tras editar un
   ticket; refresh de token que podría perder `role`/`username` (SimpleJWT
   no re-ejecuta `get_token` personalizado al renovar).
