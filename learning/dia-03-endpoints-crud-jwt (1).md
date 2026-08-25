# Día 3 — Endpoints CRUD + Autenticación JWT

**Proyecto:** Sistema de triage de tickets con sugerencias de IA (Django + React)
**Tema del día:** Conectar los modelos/serializers/permisos (Días 1 y 2) a URLs reales, protegidas con JWT.

---

## 🎯 Objetivo del día
Que el frontend (React) pueda hacer login y consumir un CRUD real de tickets/comentarios/categorías, respetando los roles cliente/agente/admin.

## ✅ Checklist completado

- [x] `djangorestframework-simplejwt` instalado y configurado como autenticación por defecto
- [x] Endpoints de login (`/api/token/`) y refresh (`/api/token/refresh/`)
- [x] `CategoriaViewSet`, `TicketViewSet`, `ComentarioViewSet` con `ModelViewSet`
- [x] `get_queryset()` filtrando cada listado según el rol (la pieza que el Día 2 dejó pendiente)
- [x] `perform_create` forzando `cliente`/`autor` desde el usuario real, y validando que un cliente no pueda comentar en tickets ajenos
- [x] Router conectando los 3 recursos a `/api/` con las 5 acciones CRUD de cada uno
- [x] Probado con los 3 roles por HTTP real: login, listado filtrado, creación, y bloqueo de accesos indebidos (403/404/401 según el caso)

---

## 🧩 Nomenclaturas y símbolos importantes (Python / Django / React)

Guía de referencia de todos los patrones de nombres que se cruzan en el proyecto, para no confundirlos entre sí — cada uno significa algo distinto aunque se parezcan visualmente.

### Puntos y guiones bajos dentro de Python/Django

**1. `.` (punto) — entrar a un objeto que ya tienes cargado**
- `comentario.ticket.agente_asignado` funciona porque `comentario` ya es un objeto real en memoria. El punto simplemente "entra" a un atributo tras otro.

**2. `__` dentro de un queryset (`filter`, `exclude`, `annotate`...) — cruzar relaciones o comparar**
- `ticket__agente_asignado=user` → cruza de `Comentario` a `Ticket` para comparar un campo, **antes** de traer nada de la base de datos. Django lo traduce a un `JOIN` de SQL.
- El mismo `__` también sirve para comparaciones (*lookups*): `titulo__icontains='urgente'`, `__gte`, `__lt`, `__isnull`. Se pueden encadenar: `ticket__agente_asignado__isnull=True`.
- **Por qué no un punto:** dentro de `filter(...)` lo que escribes son *argumentos con nombre*, y Python solo permite letras, números y guion bajo en esos nombres — un punto ahí es directamente un `SyntaxError`.
- **Analogía:** el punto es tener el ticket de papel en la mano y leerlo. `__` es una instrucción escrita a un archivista para que busque entre cajones (tablas) relacionados.

**3. `_id` como sufijo de una ForeignKey — el número, sin el objeto completo**
- `ticket.agente_asignado_id` trae solo el ID (sin consulta extra a la base de datos), a diferencia de `ticket.agente_asignado` (objeto completo, puede disparar una consulta extra). Django crea este atributo automáticamente por cada `ForeignKey` que definas — no lo escribes tú.
- Se usa cuando solo necesitas **comparar números** (`ticket.agente_asignado_id == user.id`), evitando un viaje innecesario a buscar el objeto completo.

**4. `__init__`, `__str__` — métodos "mágicos" (dunder methods), ¡no confundir con el `__` de las consultas!**
- Cuando ves guion bajo doble **al inicio Y al final** de un nombre, es otra cosa totalmente distinta: son métodos reservados que el propio Python llama automáticamente en momentos especiales. El más común en tus modelos:
  ```python
  class Ticket(models.Model):
      titulo = models.CharField(max_length=200)
      # ...
      def __str__(self):
          return self.titulo
  ```
  `__str__` le dice a Django cómo mostrar el objeto como texto — sin esto, en el admin verías `Ticket object (1)`; con esto, ves el título real. Si tu modelo `Ticket` ya tiene esto desde el Día 1, es justo esta la razón.
- **Regla para no confundirte:** `__` en medio de un nombre dentro de un `filter()` = "cruza/compara". `__` rodeando un nombre de método (`__algo__`) = método especial del lenguaje. Se ven parecidos, significan cosas completamente distintas.

**5. `_variable` (un solo guion bajo al inicio) — "uso interno", por convención**
- Verás esto ocasionalmente (ej: `_helper`, `_cache`). Python no lo bloquea de verdad, es solo una señal para otros programadores: "esto es un detalle interno, no lo uses desde afuera de este archivo/clase". Menos común que necesites escribir esto tú mismo por ahora — pero sí lo vas a leer en librerías de terceros.

### Estilo de nombres (mayúsculas/minúsculas)

**6. `snake_case` vs `PascalCase` (CamelCase) — la convención estándar de Python/Django**
- **Clases** → `PascalCase` (cada palabra empieza en mayúscula, sin guiones): `TicketViewSet`, `ComentarioSerializer`, `PermisoTicket`.
- **Todo lo demás** (variables, funciones, métodos, campos de modelo) → `snake_case` (minúsculas, palabras separadas por guion bajo): `agente_asignado`, `get_queryset`, `perform_create`.
- No es capricho: es la [guía de estilo oficial de Python (PEP 8)](https://peps.python.org/pep-0008/), y casi toda la comunidad Django la sigue — seguirla hace que tu código se vea "profesional" a simple vista para cualquiera que lo revise (por ejemplo, un reclutador viendo tu repo).

**7. `MAYÚSCULAS_CON_GUION_BAJO` — constantes**
- Valores que no deberían cambiar en tiempo de ejecución, ej. `ESTADOS_TICKET = ['abierto', 'cerrado', 'en_progreso']` en algún lugar de configuración. No es una regla forzada por Python, pero es una convención muy respetada.

### Cruzando la frontera Django → React

**8. `snake_case` (Python) vs `camelCase` (JavaScript) — el JSON no se traduce solo**
- En Python/Django todo es `snake_case` (`agente_asignado`). En JavaScript/React la convención normal es `camelCase` (`agenteAsignado`).
- Por defecto, DRF **no traduce** nada: el JSON que le llega a React va a traer las claves tal cual las nombraste en el serializer, en `snake_case` (`{"agente_asignado": 3, "titulo": "..."}`).
- **La forma más común para principiantes:** dejarlo así, en `snake_case` de punta a punta, y simplemente acceder en React como `ticket.agente_asignado` (aunque "se vea raro" en JS). Es la opción más simple y con menos piezas que pueden fallar. La alternativa —agregar una librería que convierta automáticamente `snake_case` ↔ `camelCase` en cada petición— existe y algunos equipos la usan, pero es una capa extra de configuración que no vale la pena mientras estás construyendo el proyecto; se puede agregar después si hace falta.

### Específico de tu modelo (relaciones repetidas)

**9. `related_name` — cuando dos ForeignKey apuntan al mismo modelo**
- Tu `Ticket` tiene **dos** relaciones hacia el mismo modelo de usuario: `cliente` y `agente_asignado`. Cuando dos `ForeignKey` en el mismo modelo apuntan al mismo modelo relacionado, Django necesita un `related_name` distinto en cada una para saber cómo acceder "en reversa" (desde un usuario hacia sus tickets), por ejemplo:
  ```python
  cliente = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tickets_como_cliente')
  agente_asignado = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tickets_asignados')
  ```
  Esto te permitiría luego hacer `usuario.tickets_asignados.all()`. Si ya migraste sin errores en el Día 1, es señal de que ya está bien resuelto — solo vale la pena que sepas identificar el nombre por si lo necesitas más adelante (por ejemplo, para un endpoint tipo "mis tickets asignados").

---

## 🐛 Errores encontrados
_Ninguno registrado en la sesión de hoy — si aparece alguno al reproducir el código, se agrega aquí con: mensaje de error, causa y solución._

---

## 📌 Buenas prácticas aplicadas hoy (para el README público más adelante)

- **Bloqueado por defecto:** `IsAuthenticated` como permiso global; solo se abre lo que se decide explícitamente.
- **Separación de responsabilidades:** el filtrado por rol vive en `get_queryset()` (qué se puede *ver*), la protección de escritura vive en las clases de permisos (Día 2) y en `perform_create` (qué se puede *crear/tocar*).
- **Nunca confiar en el cliente:** aunque el frontend mande `"cliente": 5` o un `ticket` ajeno en el JSON, el backend siempre revalida contra `request.user` antes de guardar.
- **DRY con Router + ModelViewSet:** 3 líneas de `register()` reemplazan ~15 rutas escritas a mano para los 3 recursos.

---

## ⏭️ Siguiente paso
**Día 4** — pendiente de definir (continuar roadmap).
