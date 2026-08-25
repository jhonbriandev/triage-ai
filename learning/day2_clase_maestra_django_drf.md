# Clase maestra: Django REST Framework — Serializers y Permisos

Documento de referencia con todo lo trabajado en esta sesión: qué
aprendimos, qué corregimos, y las "reglas mentales" para seguir
avanzando. Pensado para volver a leerlo cuando algo se te olvide.

---

## 1. El problema de fondo: un modelo guarda IDs, no texto legible

Cuando defines algo así en un modelo:

```python
customer = models.ForeignKey(User, on_delete=models.CASCADE)
status = models.CharField(max_length=1, choices=STATUS_CHOICES)
```

La base de datos, por dentro, guarda:

- `customer` → un número (el ID de un User)
- `status` → un código corto (ej: `'O'`)

Pero cuando el frontend recibe el JSON de la API, casi nunca quiere
ver `customer: 5` o `status: "O"`. Quiere ver `"oldstarz"` y
`"Abierto"`. Todo lo que aprendimos hoy resuelve ese "traductor" entre
lo que guarda la base de datos y lo que necesita mostrar la interfaz.

Analogía: piensa en el modelo como el archivo interno de una empresa,
donde a cada empleado y cliente se le identifica por un número de
legajo. El serializer es la recepcionista que, cuando alguien
pregunta, traduce esos números a nombres reales.

---

## 2. Serializers: los 4 tipos de campo que usamos

| Tipo | Ejemplo | Qué hace |
|---|---|---|
| Campo del modelo | `'customer'` | Muestra el ID tal cual está guardado |
| Campo relacionado (`source`) | `category_name` con `source='category.name'` | "Viaja" a otro modelo relacionado y trae un dato suyo |
| Choices (`get_<campo>_display`) | `status_display` con `source='get_status_display'` | Traduce un código interno (`'O'`) a su texto visible (`"Abierto"`) |
| Campo calculado | `SerializerMethodField` + `get_<nombre>()` | Un valor que se calcula con código propio, no viene directo de un campo |

### 2.1 `source`: cómo "viajar" a otro modelo

```python
category_name = serializers.CharField(source='category.name', read_only=True)
```

Se lee de derecha a izquierda del punto: "desde el ticket, ve a su
`category`, y de ahí trae `name`". Es exactamente lo mismo que en
Python harías con `ticket.category.name`.

```
TICKET
  │
  ├── category ──▶ Category ──▶ name
  ├── customer ──▶ User     ──▶ username
  └── assigned_agent ──▶ User ──▶ username
```

### 2.2 `get_<campo>_display()`: el traductor de choices

Cuando un campo del modelo tiene `choices=`, Django genera
**automáticamente** un método `get_<nombre_del_campo>_display()`.
No lo escribes tú; ya viene incluido.

```python
status_display = serializers.CharField(source='get_status_display', read_only=True)
```

- Internamente: `status = 'O'`
- Display: `"Abierto"`

### 2.3 `read_only_fields`: lo que se muestra pero no se puede editar

```python
read_only_fields = ['customer', 'created_at']
```

Significa: estos campos aparecen en la respuesta (el cliente los
puede leer), pero si el cliente intenta mandarlos en un POST/PUT/PATCH,
DRF los ignora. Es una forma de proteger datos que no deberían
depender de lo que mande el usuario (por ejemplo, la fecha de
creación, o quién es el dueño del ticket).

Atajo que vimos en `SuggestionAiSerializer`:

```python
read_only_fields = fields
```

Esto dice "TODOS los campos son de solo lectura", útil cuando un
serializer entero es de solo lectura (por ejemplo, contenido generado
por IA que el cliente nunca debería poder modificar a mano).

### 2.4 Error que corregimos

Habías escrito `userneme` en vez de `username` en un `source`. Es un
recordatorio de que estas cadenas de texto (`source='algo.otro'`) no
las valida el editor — si el nombre del atributo está mal escrito,
DRF simplemente no encuentra el dato y falla en silencio o con un
error confuso. Conviene revisar estos strings con cuidado.

---

## 3. Permisos personalizados en DRF

### 3.1 `request`: el "sobre" de la petición

`request` es el objeto que representa la petición HTTP entrante.
Los dos datos que más usamos de él:

- `request.user` → quién está haciendo la petición (el usuario logueado)
- `request.method` → qué está tratando de hacer (`'GET'`, `'POST'`, `'PATCH'`, etc.)

### 3.2 `permissions.SAFE_METHODS`

Es una tupla fija que trae DRF:

```python
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')
```

Son los métodos que **solo leen**, no modifican nada. Por eso:

```python
if request.method in permissions.SAFE_METHODS:
```

se lee como: "¿esta petición es de solo lectura?"

### 3.3 `has_permission` vs `has_object_permission`

- **`has_permission(self, request, view)`**: primer filtro, general.
  Se ejecuta antes de saber sobre qué objeto puntual se está actuando.
  En este proyecto casi siempre solo comprobamos: "¿está autenticado?"
- **`has_object_permission(self, request, view, obj)`**: filtro fino,
  ya con el objeto concreto (`obj`) en la mano — por ejemplo, un
  ticket puntual. Aquí es donde comparamos roles e IDs.

DRF llama primero a `has_permission()`. Si pasa, y la vista opera
sobre un objeto específico, llama también a `has_object_permission()`.

### 3.4 El sufijo `_id`: de dónde sale y por qué usarlo

No lo escribiste tú en el modelo. Es una convención automática de
Django: cada vez que declaras una relación (`ForeignKey`,
`OneToOneField`), Django crea, además del atributo con el objeto
completo, una columna con el sufijo `_id` que guarda solo el número.

```python
assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

Te da automáticamente dos formas de acceder al dato:

```python
ticket.assigned_agent      # objeto User completo -> <User: pedro>
ticket.assigned_agent_id   # solo su ID -> 7
```

Comparar por `_id` es una comparación simple entre dos números:

```python
obj.assigned_agent_id == request.user.id
# 7 == 7 -> True
```

Es equivalente, en resultado, a comparar los objetos completos:

```python
obj.assigned_agent == request.user
```

pero trabajar con IDs suele ser más directo quieres solo verificar
"¿es la misma persona?", sin necesitar el objeto completo.

### 3.5 Mapa mental de los tres permisos que armamos

```
                    PETICIÓN
                       │
                       ▼
                 request.user
                       │
                       ▼
                     Profile
                       │
                       ▼
                      rol
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
        admin        agent       customer
          │            │            │
          ▼            ▼            ▼
        TODO       ticket         ticket
                   asignado       propio
                                  │
                              solo lectura
```

- **`PermissionTicket`**: decide quién puede ver/editar un ticket puntual.
- **`PermissionCommentary`**: un comentario "hereda" el permiso de su ticket
  (`ticket = obj.ticket`, y de ahí se aplican las mismas reglas).
- **`PermissionCategory`**: cualquiera autenticado puede leer categorías;
  solo el admin puede crearlas/editarlas/borrarlas.

---

## 4. Errores que encontramos y corregimos

| Error | Corrección |
|---|---|
| `userneme` en un `source` | `username` |
| Confusión entre `has_permission` y `has_object_permission` | Aclarado: general vs. específico por objeto |
| Duda sobre si `_id` había que crearlo | Aclarado: lo genera Django automáticamente al declarar un `ForeignKey` |

---

## 5. Reglas mentales para seguir avanzando

1. Si necesitas mostrar un dato de OTRO modelo relacionado → usa
   `source='relacion.campo'`.
2. Si el modelo tiene `choices=` y quieres el texto legible → usa
   `source='get_<campo>_display'`.
3. Si un campo no debe poder editarse desde afuera → agrégalo a
   `read_only_fields`.
4. Si un serializer entero es de solo lectura → `read_only_fields = fields`.
5. Para permisos por objeto puntual → `has_object_permission`, no
   `has_permission`.
6. Para comparar "¿es el mismo usuario?" en un permiso → compara por
   `_id` (más simple, mismo resultado que comparar objetos completos).
7. Para distinguir lectura de escritura en un permiso → revisa
   `request.method in permissions.SAFE_METHODS`.

---

## 6. Archivos generados en esta sesión

- `serializers_comentado.py`
- `permissions_comentado.py`
- Este documento: `clase_maestra_django_drf.md`
