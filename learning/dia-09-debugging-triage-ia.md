# Día 9 — Sesión de debugging: rutas por rol, sugerencias de IA y reintentos

Este documento recopila todos los bugs encontrados y corregidos durante la
continuación del Día 9 (rutas privadas por rol, tarjeta de sugerencia de IA,
y confiabilidad de las llamadas a Gemini). Para cada uno: el síntoma, cómo
lo diagnosticamos, la causa real, y la lección para el futuro.

---

## 1. Gemini respondía con `503 Service Unavailable` y tickets sin sugerencia

### Síntoma
4 tickets se crearon sin sugerencia de IA. El manejo de errores ya existente
(`ErrorGenerationIA`) funcionaba bien y sí dejaba rastro en los logs — el
problema no era manejo de errores, era falta de reintentos.

### Diagnóstico
Revisar los logs de Django mostró el patrón real:
```
Ticket #26 → 503 Service Unavailable ("high demand")
Ticket #27 → 503 Service Unavailable ("high demand")
Ticket #28 → 503 Service Unavailable ("high demand")
Ticket #29 → Timeout
```
3 de 4 fallos eran el **mismo motivo**: saturación temporal de Gemini, no un
error de nuestro código.

### Causa
Un `503` de una API externa suele ser temporal ("inténtalo más tarde"). No
teníamos ningún mecanismo de reintento — el primer fallo se aceptaba como
definitivo.

### Solución: reintentos con backoff exponencial
```python
import time

def generate_suggestion_ia(ticket, max_intentos=3):
    for intento in range(max_intentos):
        try:
            client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=15000),
            )
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type='application/json'),
            )
            break  # éxito, salir del bucle de reintentos

        except errors.APIError as exc:
            es_temporal = getattr(exc, 'code', None) in (503, 429)
            if es_temporal and intento < max_intentos - 1:
                espera = 2 ** intento  # 1s, 2s, 4s
                logger.warning('Gemini saturado (intento %s/%s) para ticket #%s, reintentando en %ss',
                               intento + 1, max_intentos, ticket.pk, espera)
                time.sleep(espera)
                continue
            logger.warning('Gemini respondió con un error para el ticket #%s: %s', ticket.pk, exc)
            raise ErrorGenerationIA(f'La API de Gemini respondió con un error: {exc}') from exc

        except Exception as exc:
            logger.warning('Fallo inesperado llamando a Gemini para el ticket #%s: %s', ticket.pk, exc)
            raise ErrorGenerationIA(f'No se pudo contactar a la IA: {exc}') from exc
    # ... sigue el parseo de JSON y validaciones, sin cambios
```

**Verificado:** tras el cambio, una petición que antes hubiera fallado con
503 llegó a `200 OK` (con reintento silencioso de por medio).

### Lección
- Un error de una API externa no siempre es "mi código está mal" — revisar
  el código de estado y el mensaje antes de asumir la causa.
- Solo reintentar errores **temporales** (503, 429). Reintentar un JSON mal
  formado o campos faltantes no cambia el resultado — eso hay que arreglarlo
  en el prompt, no con reintentos.
- Los logs bien estructurados (`logger.warning` con el motivo exacto) son lo
  que permitió diagnosticar esto en minutos en vez de adivinar.

### Pendiente evaluado y descartado por ahora
Mover la llamada a Gemini a un hilo en segundo plano (`threading.Thread`)
para no bloquear al usuario. Se decidió posponerlo: con datos reales, el
timeout fue solo 1 de 4 casos — los reintentos atacan el 75% de los fallos
observados con mucho menos esfuerzo. Queda como mejora futura si after de
los reintentos siguen quedando tickets sin sugerencia.

---

## 2. El rol y el username no llegaban al frontend (`undefined`)

### Síntoma
`rol`/`role` y `username` leídos del JWT decodificado daban `undefined`.

### Causa
`TokenObtainPairView` (el de fábrica de SimpleJWT) **no incluye campos
personalizados** en el token — solo lo mínimo (`user_id`, `exp`, etc.). El
campo `role` del modelo de usuario nunca se agregó al payload del JWT.

### Solución
Serializer y vista personalizados que heredan del original y agregan los
campos extra al token:
```python
# users/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class TokenObtenerConRolSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.profile.role
        token['username'] = user.username
        return token
```
```python
# users/views.py
class TokenObtenerConRolView(TokenObtainPairView):
    serializer_class = TokenObtenerConRolSerializer
```
```python
# config/urls.py — reemplazar el TokenObtainPairView genérico
path('api/token/', TokenObtenerConRolView.as_view(), name='token_obtain_pair'),
```

### Lección
- Un JWT solo trae lo que el backend metió explícitamente — no es magia, es
  texto plano codificado en Base64 (no encriptado, solo firmado).
- Patrón reutilizable: heredar la vista/serializer original y solo
  sobreescribir `get_token` es más simple y seguro que reescribir todo desde
  cero.
- Después de cambiar qué trae el token, hay que **volver a iniciar sesión**
  — el token viejo ya guardado en `localStorage` no se actualiza solo (es
  una "foto" del momento del login).

---

## 3. Desajustes de nombres entre backend (inglés) y frontend (español)

Este patrón se repitió varias veces a lo largo de la sesión — vale la pena
documentarlo como una categoría propia de bug, no solo casos sueltos.

| Dónde | Se esperaba | Backend enviaba | Efecto |
|---|---|---|---|
| Lectura de rol | `data.rol` | `data.role` | `undefined` silencioso |
| `getActualRol()` | `data.rol` | el token traía `role` | `undefined` silencioso |
| Precarga de categoría en sugerencia IA | `c.nombre` | `c.name` | `TypeError` (`.toLowerCase()` sobre `undefined`) — truena el `try` y dispara el `catch` genérico |
| `<select>` de categorías en la tarjeta de IA | `categorias` (variable) | el estado se llamaba `categories` | variable inexistente, rompe el render |

### Lección central
- Cuando un valor viene del backend, **el nombre del campo lo decide el
  backend** (el modelo/serializer de Django) — el frontend debe usar
  exactamente ese nombre, no traducirlo.
- Mezclar inglés (nombres de campos) y español (nombres de variables locales)
  en el mismo proyecto es la fuente número uno de estos bugs. La forma más
  simple de evitarlos como principiante: usar el mismo idioma en ambos lados,
  o revisar el serializer cada vez que se lee un campo nuevo en el frontend.
- Un acceso a propiedad inexistente (`obj.campoQueNoExiste`) en JavaScript
  **no truena** — da `undefined` silenciosamente. El error real aparece
  recién cuando se intenta *operar* sobre ese `undefined` (ej.
  `.toLowerCase()`), y en ese punto el error puede caer en un `catch`
  genérico que oculta la causa real detrás de un mensaje de error que no
  tiene nada que ver (ej. "no se pudo cargar el ticket", cuando en realidad
  el ticket sí cargó bien).
- Cuando un `catch` genérico muestra un mensaje que no cuadra con lo que
  Network muestra (todo en 200), sospechar de un error de JavaScript
  *después* de recibir los datos, no de la petición en sí.

---

## 4. La condición para mostrar la tarjeta de sugerencia de IA no existía (`puedeGestionar`/`canManage`)

### Síntoma
El JSX usaba una variable (`puedeGestionar`, luego renombrada `canManage`)
que nunca se había declarado en el componente.

### Solución
```jsx
const role = getActualRole();
const canManage = role === "agent" || role === "admin";
```

### Lección
Cuando un documento de referencia (una guía, un resumen de sesión anterior)
*usa* una variable dando por hecho que ya existe, no siempre significa que
esté declarada en el código real — puede venir de un paso previo que no
quedó documentado. Ante la duda, buscar (`Ctrl+F`) en el archivo real antes
de asumir.

---

## 5. `DetailTicket.jsx` — múltiples bugs de estructura

Se encontraron varios problemas acumulados en el mismo componente:

1. **Bloque de código suelto fuera de cualquier función** (un
   `if (canManage) { await ... }` pegado entre los imports y el
   `export default function`). Esto es inválido en JavaScript: un `await`
   fuera de una función `async`, usando variables (`canManage`,
   `setCategorias`, `datosTicket`) que no existían en ese punto del archivo.
   → Se eliminó de ahí y se reubicó dentro de `loadAll`, después de que el
   ticket ya llegó del backend (la precarga de categoría/prioridad sugerida
   necesita los datos del ticket, así que no puede ejecutarse antes).

2. **`const { role } = getActualRole();`** — destructuring incorrecto. La
   función devuelve el rol directo (un string), no un objeto `{ role }`.
   → Corregido a `const role = getActualRole();`.

3. **Faltaba `useState` para `categories`** — se usaba `categories.map(...)`
   sin haberlo declarado como estado.
   → `const [categories, setCategories] = useState([]);`

4. **Faltaba un segundo `useForm()`** — el JSX usaba `formApply.register(...)`
   y `formApply.handleSubmit(...)` para un formulario que nunca se declaró
   (aparte del formulario de comentarios, que sí usaba el primer `useForm()`).
   → `const formApply = useForm();`

5. **`setValue` usado sin haberlo sacado del `useForm()`** — había que
   agregarlo al destructuring del primer formulario:
   ```jsx
   const { register, handleSubmit, reset, setValue, formState: { errors } } = useForm();
   ```

6. **`applySuggestion` llamaba a una función no importada** (`actualizarTicket`,
   cuando la función real en el proyecto se llama `updateTicket`), y
   reutilizaba el nombre `loading` (ya usado por el estado de carga de la
   página) para una variable local distinta, lo cual es válido en JavaScript
   pero confuso.
   → Se importó `updateTicket` correctamente y se renombró la variable local
   a `updated` para evitar la confusión con el estado `loading`.

### Lección
Cuando un componente crece por partes (agregado en distintas sesiones), es
fácil que una pieza (un `useForm`, un `useState`, un import) quede sin
declarar mientras el JSX o la lógica ya la referencian. Revisar el
componente de arriba a abajo, confirmando que **toda variable usada tenga
una declaración visible**, es más confiable que depurar síntoma por síntoma.

---

## 6. `Register.jsx` — colisión de nombres entre `react-hook-form` y la API

### Síntoma
El formulario de registro no llamaba realmente al backend.

### Causa
```jsx
const { register, handleSubmit, formState: { errors } } = useForm();
// ...
await register(data.username, data.password, data.email); // ❌
```
`register` de react-hook-form sirve para **conectar un campo del
formulario**, no para enviar datos al servidor. Como nunca se importó la
función real (`register` de `services/auth.js`), JavaScript usaba la única
`register` disponible: la de react-hook-form. No servía para lo que se
esperaba.

### Solución
```jsx
import { register as registerUser } from "../services/auth";
// ...
await registerUser(data.username, data.password, data.email);
```
Además, faltaba el campo de `<input>` para `email` en el formulario — se
enviaba `data.email` pero nunca existió el campo correspondiente.

### Lección
Cuando dos cosas necesitan el mismo nombre lógico (`register` de un hook de
formularios vs. `register` de una función de autenticación), usar un alias
en el import (`import { x as y }`) evita que una tape a la otra en
silencio.

---

## 7. `PermissionCategory` no se aplicaba — error de tipeo en el atributo

### Síntoma
Cualquier usuario autenticado podía crear, editar y borrar categorías,
aunque `PermissionCategory` ya tenía la lógica correcta escrita (solo admin
puede escribir).

### Causa
```python
class CategoryViewSet(viewsets.ModelViewSet):
    permission_class = [PermissionCategory]   # ❌ falta la "s"
```
DRF busca específicamente `permission_classes` (plural). Al no encontrarlo,
usa el permiso por defecto del proyecto — que en este caso era
`IsAuthenticated` a secas, sin restricción de rol.

### Solución
```python
permission_classes = [PermissionCategory]   # ✅
```

### Lección
Un atributo mal escrito en DRF (o en Django en general) casi nunca lanza un
error — Python simplemente lo trata como una variable nueva sin efecto.
Esto hace que estos bugs sean silenciosos y difíciles de notar sin revisar
el nombre exacto contra la documentación.

---

## 8. Ruta de gestión de categorías no coincidía entre el link y la `<Route>`

### Síntoma
El botón "Categorías" en la lista de tickets llevaba a una URL que no
coincidía con ninguna ruta declarada.

### Causa
```jsx
// El link:
<Link to="/manage-categories">

// La ruta declarada:
<Route path="admin/categories" ... />   // sin "/" inicial, nombre distinto
```

### Solución
Unificar ambos — se ajustó la `<Route>` para que coincidiera con el link ya
existente:
```jsx
<Route
  path="/manage-categories"
  element={
    <PrivateRoute permittedRoles={["admin"]}>
      <ManageCategories />
    </PrivateRoute>
  }
/>
```

### Lección
`PrivateRoute` con `permittedRoles` protege bien la ruta **solo si se le
pasa el prop** al envolver la ruta — sin él, deja pasar a cualquier usuario
autenticado. Además, la protección del frontend es solo para la
experiencia (ocultar botones/pantallas); la barrera real siempre es el
permiso del backend (`PermissionCategory`, punto 7).

---

## 9. Condición de carrera al renovar el token con varias peticiones en paralelo

### Síntoma
Un agente con un ticket asignado lo veía en la lista, pero al entrar al
detalle recibía el error genérico "No se pudo cargar este ticket". En
Network, todas las peticiones (`tickets/25`, `commentaries`, `categories`)
terminaban en `200 OK` — el error no era de backend ni de permisos.

### Descartado en el camino
- Se sospechó primero de rotación de refresh tokens (`ROTATE_REFRESH_TOKENS`)
  — descartado al revisar `settings.py`: no había ninguna sección
  `SIMPLE_JWT`, por lo que se usan los valores por defecto (rotación
  desactivada).
- Se sospechó de una condición de carrera con múltiples refrescos de token
  simultáneos (varias peticiones en paralelo, cada una disparando su propio
  POST a `/token/refresh/`) — plausible en general y se dejó como mejora de
  todas formas, pero no fue la causa de este síntoma puntual.

### Causa real (ver punto 3)
Un error de JavaScript (`c.nombre` en vez de `c.name`, y `categorias` en vez
de `categories`) dentro del bloque `try` de `loadAll()`, que hacía caer la
ejecución en el `catch` genérico — mostrando el mensaje de error a pesar de
que las peticiones de red sí habían tenido éxito.

### Mejora aplicada de todas formas: refresh de token compartido
Aunque no fue la causa de este bug puntual, se identificó que el
interceptor de `api.js` no protege contra múltiples refrescos simultáneos
si varias peticiones en paralelo reciben `401` al mismo tiempo. Se preparó
esta mejora para `api.js`:
```javascript
let refreshEnCurso = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        if (!refreshEnCurso) {
          refreshEnCurso = axios
            .post(`${import.meta.env.VITE_API_URL}/token/refresh/`, {
              refresh: localStorage.getItem("refresh_token"),
            })
            .then(({ data }) => {
              localStorage.setItem("access_token", data.access);
              if (data.refresh) {
                localStorage.setItem("refresh_token", data.refresh);
              }
              return data.access;
            })
            .finally(() => { refreshEnCurso = null; });
        }
        const nuevoAccessToken = await refreshEnCurso;
        originalRequest.headers.Authorization = `Bearer ${nuevoAccessToken}`;
        return api(originalRequest);
      } catch (renewError) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = "/login";
        return Promise.reject(renewError);
      }
    }
    return Promise.reject(error);
  },
);
```

### Lección — la más importante de la sesión
**No asumir la causa antes de tener evidencia directa.** Se recorrieron
varias hipótesis razonables (permisos de backend, rotación de tokens,
condición de carrera) antes de llegar a la causa real, que era un simple
desajuste de nombres de campo. El método que sí funcionó:
1. Revisar el código de estado exacto en Network (no solo "falló").
2. Confirmar con "Preserve log" si el error ocurre antes o después de una
   redirección.
3. Ante Network en 200 pero un error visible en pantalla, sospechar de
   JavaScript que corre *después* de recibir los datos, no de la red.
4. Leer el componente línea por línea buscando nombres de variables que no
   coincidan con lo que el backend realmente envía.

---

## Checklist del Día 9 (continuación)

- ✅ Reintentos con backoff exponencial para errores temporales de Gemini (503/429)
- ✅ Rol y username agregados al JWT vía serializer personalizado
- ✅ `canManage` (antes `puedeGestionar`) declarado correctamente en `DetailTicket.jsx`
- ✅ Estructura de `DetailTicket.jsx` corregida (bloque huérfano, `useForm` faltante, imports, nombres de variables)
- ✅ `Register.jsx` corregido (colisión de nombres `register`, campo de email agregado)
- ✅ `PermissionCategory` aplicándose de verdad (`permission_classes`, con "s")
- ✅ Ruta de gestión de categorías unificada entre link y `<Route>`
- ✅ Bug de "ticket no carga" resuelto (desajuste `c.nombre`/`c.name` y `categorias`/`categories`)
- ✅ Interceptor de refresh de token protegido contra refrescos simultáneos duplicados
