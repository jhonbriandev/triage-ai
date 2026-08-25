# Plan Maestro — Triage IA

> Documento vivo del proyecto. Se actualiza en este mismo archivo a medida que avanza el desarrollo — no se duplica en versiones nuevas.

## 1. Resumen del proyecto

- **Nombre:** Triage IA
- **Objetivo:** Sistema de triage de tickets de soporte con sugerencias generadas por IA (categoría, prioridad, resumen y respuesta inicial sugerida para el cliente)
- **Propósito personal:** Tercer proyecto de portafolio en el camino hacia desarrollador Django + React profesional
- **Estructura del repositorio:** Monorepo (`backend/` + `frontend/`)

## 2. Stack tecnológico

**Backend**
- Django + Django REST Framework
- PostgreSQL (conexión vía `DATABASE_URL`)
- `django-environ` para variables de entorno
- `djangorestframework-simplejwt` para autenticación JWT
- `google-genai` (SDK oficial de Google) para la integración con Gemini

**IA**
- Proveedor: Google Gemini, vía la API gratuita de Google AI Studio
- Modelo actual: `gemini-3.6-flash` (ver bitácora del día 4 — se migró desde `gemini-2.5-flash`, descontinuado por Google para cuentas nuevas)

**Frontend** (pendiente de iniciar)
- React (Vite) — correrá en `localhost:5173`

**Entornos de desarrollo**
- Backend: `localhost:8000`
- Frontend: `localhost:5173` (cuando inicie)

## 3. Cómo levantar el proyecto en una máquina nueva

Esta sección existe porque ya nos tocó resolver esto una vez (entorno virtual no seleccionado, `.env` sin la clave de Gemini) — queda documentado para no perder tiempo de nuevo.

1. Clonar el repositorio y crear un entorno virtual dentro de `backend/` (`python -m venv venv`)
2. Activar el entorno virtual y correr `pip install -r requirements.txt`
3. En VS Code: `Ctrl+Shift+P` → **"Python: Select Interpreter"** → elegir el intérprete dentro de `venv/Scripts/python.exe` (Windows). Si aparece marcado como **"Global"**, el editor no está viendo tus paquetes instalados.
4. Crear el archivo `.env` en la raíz de `backend/` (no se sube a git — confirmar que está en `.gitignore`) con, como mínimo:
   ```
   DATABASE_URL=postgres://usuario:password@localhost:5432/nombre_bd
   GEMINI_API_KEY=tu-clave-de-Google-AI-Studio
   ```
5. Correr las migraciones: `python manage.py migrate`
6. Levantar el servidor: `python manage.py runserver`

## 4. Bitácora de avance

### Día 1 — Fundaciones del backend
- Proyecto Django con estructura `config` (settings separado del proyecto raíz)
- App `tickets` creada
- Conexión a PostgreSQL vía `DATABASE_URL`
- 4 modelos: `Categoria`, `Ticket`, `Comentario`, `SugerenciaIA`
- Panel de administración configurado

### Día 2 — Usuarios, roles y permisos
- App `users` con modelo `Perfil` (relación `OneToOneField` con el `User` de Django + señal para auto-creación)
- Serializers con `read_only_fields` y campos de solo lectura vía `source=`
- 3 clases de permisos basadas en rol: `PermisoTicket`, `PermisoComentario`, `PermisoCategoria`

### Día 3 — Autenticación JWT y ViewSets
- Autenticación JWT vía `djangorestframework-simplejwt`
- 3 `ModelViewSet` con `get_queryset()` filtrado por rol y `perform_create()` que fuerza la propiedad del recurso
- Rutas de todos los CRUD registradas bajo `/api/` con `DefaultRouter`

### Día 4 — Integración con IA (Gemini)
- `tickets/services.py`: función `generate_suggestion_ia(ticket)` que arma un prompt con título y descripción del ticket, y llama a Gemini pidiendo una respuesta en JSON estructurado (`response_mime_type='application/json'`)
- El JSON se parsea con `json.loads()` y se mapea directo a los 4 campos de `SugerenciaIA`
- `TicketViewSet.perform_create` actualizado para llamar a este servicio automáticamente al crear un ticket, generando la sugerencia enlazada
- `GEMINI_API_KEY` gestionada vía `.env`
- `SessionAuthentication` sumada a `DEFAULT_AUTHENTICATION_CLASSES`, **solo para poder probar cómodamente desde la API navegable de DRF** en desarrollo — JWT sigue siendo el método real que usará el frontend
- Ruta `path('api-auth/', include('rest_framework.urls'))` agregada para que el botón de login aparezca en la API navegable
- **Corrección de modelo:** `gemini-2.5-flash` fue descontinuado por Google para cuentas nuevas → migrado a `gemini-3.6-flash` (modelo estable/GA recomendado por Google, sin cambios en el resto del código)
- **Hallazgo:** la llamada síncrona a Gemini tarda 3-5+ segundos (ver sección 7) — motiva el manejo de errores/timeout del día 5

## 5. Decisiones de diseño y su razón

| Decisión | Por qué |
|---|---|
| Filtrado por rol en `get_queryset()`, propiedad forzada en `perform_create()` | Separa "qué puedo ver" de "qué puedo crear/de quién es" — cada método tiene una sola responsabilidad |
| Llamada a Gemini de forma síncrona (sin Celery) | A la escala de un portafolio, la simplicidad importa más que la escalabilidad; Celery queda documentado como tema avanzado fuera de alcance |
| `SugerenciaIA` sin su propio endpoint de creación | Es un objeto que se genera como consecuencia de crear un ticket, no algo que un usuario deba poder inventar por su cuenta vía POST |
| `SugerenciaIA` se expondrá anidada dentro del serializer de `Ticket` (decidido, pendiente de implementar) | Patrón más simple para principiantes; refleja la relación real — la sugerencia pertenece al ticket, no vive de forma independiente |
| `SessionAuthentication` sumada solo como conveniencia de desarrollo | Permite probar visualmente en el navegador sin debilitar la autenticación real (JWT) que usará el frontend |

## 6. Referencia de endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/token/` | Obtener par de tokens JWT (`access` + `refresh`) |
| GET / POST | `/api/tickets/` | Listar / crear tickets (crea la sugerencia de IA automáticamente) |
| GET / PUT / DELETE | `/api/tickets/{id}/` | Detalle, edición y borrado de un ticket |
| GET / POST | `/api/categorias/` | Listar / crear categorías |
| GET / POST | `/api/comentarios/` | Listar / crear comentarios |
| GET | `/api-auth/login/` | Login por sesión (solo para la API navegable, no lo usa el frontend) |

*(Pendiente confirmar el nombre exacto de las rutas de categorías/comentarios contra tu `urls.py` real)*

## 7. Lecciones aprendidas / troubleshooting

- **VS Code marca `from google.genai import types` en amarillo:** casi siempre porque el intérprete seleccionado apunta al Python global en vez del `venv` del proyecto (ver sección 3).
- **401 en `/api/tickets/`:** esperado sin token — hay que loguearse primero en `/api/token/` y mandar el `access` token en el header `Authorization: Bearer <token>`.
- **Modelos de Gemini se descontinúan con el tiempo:** revisar la [página de deprecaciones de Gemini](https://ai.google.dev/gemini-api/docs/deprecations) si un modelo empieza a devolver 404 inesperadamente.
- **Llamada síncrona a Gemini tarda 3-5+ segundos:** esperado — incluye viaje de ida, generación del modelo, y viaje de vuelta. Se atiende parcialmente en el día 5 (timeout); la solución completa (asíncrona) sería Celery, fuera de alcance de este proyecto.

## 8. Pendientes / Roadmap

- [ ] Serializer anidado de `SugerenciaIA` dentro de `TicketSerializer` (decisión tomada, falta implementar)
- [ ] **Día 5:** Manejo de errores para la llamada a Gemini (incluye timeout, dado que la llamada síncrona puede tardar varios segundos)
- [ ] **Día 6:** Tests automatizados con mocks para el servicio de IA
- [ ] Frontend en React (Vite) — no iniciado
- [ ] *(Fuera de alcance, solo como referencia conceptual)* Celery para llamadas asíncronas a la IA

---
*Última actualización: día 4 — integración con Gemini + corrección de modelo descontinuado + autenticación para pruebas en el navegador.*
