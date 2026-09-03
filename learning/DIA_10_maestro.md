# Día 10 — Triage IA: gestión de tickets sin sugerencia + permisos de creación

## Contexto del día

Al revisar la lógica de negocio surgieron dos preguntas:

1. Un agente o admin que recibe un ticket **sin sugerencia de IA** (falló la generación, o aún no llegó) solo tenía en pantalla el campo de comentarios — no había forma de asignar prioridad ni categoría.
2. ¿Un agente debería poder **crear** tickets? Se decidió que **no** — solo cliente y admin.

Este documento recopila todos los cambios hechos para resolver ambos problemas.

---

## 1. `DetailTicket.jsx` — separar la gestión del ticket de la sugerencia de IA

### Problema original

El único formulario para editar categoría/prioridad (`formApply`) vivía **dentro** del bloque `{ticket.suggestion_ai && (...)}`. Si la IA no generaba sugerencia, ese `<form>` completo no se renderizaba, y el agente se quedaba sin forma de gestionar el ticket.

### Solución

- Se creó un `useForm()` **independiente** llamado `manageForm`, en una tarjeta ("Gestionar ticket") que se muestra siempre que `canManage` es verdadero — **sin depender de `ticket.suggestion_ai`**.
- `manageForm` se precarga con los **valores reales del ticket** (`dataTicket.status`, `dataTicket.priority`, `dataTicket.category`) al cargar la página, no con la sugerencia.
- La tarjeta de sugerencia de IA pasó de ser "la única puerta de entrada" a ser un **ayudante opcional**, con un botón `useSuggestedValues` que:
  1. Busca en `categories` la categoría cuyo `name` coincide con el nombre sugerido por la IA (la IA da un nombre de texto; el `<select>` necesita el `id`).
  2. Copia esos valores al formulario de gestión con `manageForm.setValue(...)`.
  3. **No guarda nada todavía** — solo rellena los campos. El agente puede corregirlos manualmente y recién guarda con el botón "Guardar cambios" (`onManageSubmit` → `updateTicket`).
- `onManageSubmit` ahora también envía `status` al backend (antes solo mandaba `category` y `priority`), porque se agregó un `<select>` de estado al formulario de gestión.

**Por qué se diseñó así:** separar "copiar la sugerencia" de "guardar" evita que un clic aplique cambios sin revisión — el mismo patrón que usan formularios con autocompletado (la sugerencia rellena, la persona confirma).

### Bug encontrado en el camino: error 400 al guardar

El `<select>` de prioridad en `manageForm` usaba valores en inglés (`low`, `medium`, `high`, `urgent`) mientras el backend (Django `choices`) esperaba español (`baja`, `media`, `alta`, `urgente`). El texto visible era igual en ambos, pero el `value` real (lo que viaja al backend) no coincidía → 400 Bad Request.

**Lección general:** ante un error 400 de Axios, revisar siempre la pestaña **Network → Response** del navegador — el backend casi siempre explica qué campo rechazó y por qué.

---

## 2. `ListTickets.jsx` — categoría no se mostraba cuando sí existía

### Problema

```jsx
{!ticket.category_name && (
  <span className="label label--pending">Sin categorizar</span>
)}
```

Solo existía el caso "sin categoría" (`!ticket.category_name`). Nunca se escribió el `<span>` para cuando la categoría sí existe — no es que se ocultara, simplemente no estaba programado.

### Solución recomendada

Usar un solo elemento con el operador `??` (nullish coalescing), en vez de dos condicionales `&&` separadas que hay que mantener sincronizadas:

```jsx
<span className={`label ${!ticket.category_name ? "label--pending" : ""}`}>
  {ticket.category_name ?? "Sin categorizar"}
</span>
```

---

## 3. Decisión de negocio: ¿quién puede crear tickets?

Se comparó con la lógica típica de sistemas de soporte (Zendesk, Freshdesk, Jira Service Desk):

- **Cliente**: crea tickets (flujo normal, self-service).
- **Agente**: normalmente no crea tickets propios desde cero (aunque en otros sistemas sí puede hacerlo en nombre de un cliente o para tickets internos — **no es el caso de este proyecto**).
- **Admin**: acceso total, incluyendo creación.

**Decisión tomada para este proyecto:** el agente **no** puede crear tickets. El admin sí.

**Nota pendiente de revisar más adelante:** cuando el admin crea un ticket, `perform_create` lo guarda con `customer = admin` (el admin queda como "cliente" de su propio ticket). Por ahora se deja así; si se quisiera que el admin cree un ticket a nombre de otro cliente, habría que agregar un campo al formulario y al serializer.

### 3.1. Backend — `permissions.py` (`PermissionTicket`)

`has_object_permission` no aplica para la creación (`POST`), porque en ese momento el objeto todavía no existe — DRF solo llama a `has_permission` antes de crear. Ahí es donde se agregó la regla:

```python
def has_permission(self, request, view):
    if not (request.user and request.user.is_authenticated):
        return False

    # Un agente no puede CREAR tickets (POST); el resto de acciones
    # (listar, ver detalle, actualizar) se filtran aparte en
    # has_object_permission / get_queryset.
    if request.method == 'POST' and request.user.profile.role == 'agent':
        return False

    return True
```

Devolver `False` hace que DRF responda `403 Forbidden` antes de llegar a `perform_create` — esta es la protección real, independiente de lo que muestre o no el frontend.

### 3.2. Frontend — ocultar el botón (experiencia de usuario, no seguridad real)

En `ListTickets.jsx`, condicionar el botón "+ Nuevo ticket" igual que ya se hace con el botón "Categorías" (visible solo para admin):

```jsx
{role !== "agent" && (
  <Link to="/tickets/new">
    <button>+ Nuevo ticket</button>
  </Link>
)}
```

### 3.3. Frontend — proteger la ruta `/tickets/new`

`PrivateRoute` ya soportaba un prop `permittedRoles` sin usarlo en esta ruta. Falta declararlo donde se define la ruta (archivo de rutas, ej. `App.jsx`):

```jsx
<Route
  path="/tickets/new"
  element={
    <PrivateRoute permittedRoles={["customer", "admin"]}>
      <NewTicket />
    </PrivateRoute>
  }
/>
```

Si el rol actual no está en `permittedRoles`, `PrivateRoute` redirige a `/tickets`. Así, aunque el agente escriba la URL directamente, no accede al formulario.

**Pendiente:** revisar si otras rutas (`/tickets/:id`, `/admin/categories`, etc.) también necesitan `permittedRoles` explícito.

---

## Resumen de archivos tocados en el día 10

| Archivo | Cambio |
|---|---|
| `DetailTicket.jsx` (frontend) | Formulario de gestión independiente de la sugerencia IA; corrección de valores `priority` (español) |
| `ListTickets.jsx` (frontend) | Mostrar nombre de categoría cuando existe |
| `permissions.py` (backend, `PermissionTicket`) | Bloquear `POST` de tickets para rol `agent` |
| `views.py` (backend, `TicketViewSet`) | Sin cambios de código; se revisó `perform_create` y `get_queryset` para confirmar el comportamiento por rol |
| Archivo de rutas (frontend, pendiente de aplicar) | Agregar `permittedRoles={["customer", "admin"]}` a la ruta `/tickets/new` |

## Pendientes que quedan fuera del día 10 (registrados para no perderlos)

- Revisar si el admin debería poder crear un ticket a nombre de otro cliente (requeriría campo extra en formulario + serializer).
- Confirmar `permittedRoles` en el resto de rutas protegidas.
- Bug ya conocido (no de hoy): la sesión no expira al cerrar la pestaña/ventana.
- Bug ya conocido (no de hoy): error 404 en Vercel al volver a la lista tras editar un ticket.
