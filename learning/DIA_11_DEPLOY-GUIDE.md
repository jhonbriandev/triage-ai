# Guía Maestra de Deploy — Proyecto Triage de Tickets con IA

> Documento de referencia con todo lo aprendido durante el deploy del proyecto full stack (Django + DRF + React) en **Railway** (backend) y **Vercel** (frontend). Pensado para consultarlo en futuros deploys, o si el proyecto necesita redeploy desde cero.

---

## 1. Arquitectura del deploy

```
┌─────────────────────┐         ┌──────────────────────┐
│   FRONTEND (React)  │  HTTPS  │   BACKEND (Django)    │
│   Vercel             │ ──────► │   Railway              │
│   triage-ai-beta     │  API    │   triage-ai-production │
│   .vercel.app        │ ◄────── │   -9205.up.railway.app │
└─────────────────────┘  CORS   └──────────┬────────────┘
                                            │
                                            │ Private Networking
                                            ▼
                                 ┌──────────────────────┐
                                 │   PostgreSQL          │
                                 │   (Railway, mismo     │
                                 │   proyecto)            │
                                 └──────────────────────┘
```

**Regla de oro que aprendimos:** backend y base de datos deben vivir en el **mismo proyecto de Railway** (no solo tener nombres parecidos) para que la red privada interna (`*.railway.internal`) pueda conectarlos. Si están en proyectos distintos, ese nombre interno nunca se resuelve, sin importar qué tan bien esté escrita la referencia de la variable.

---

## 2. Backend en Railway

### 2.1 Stack y estructura

- Django + DRF + JWT + PostgreSQL, dentro de la carpeta `backend/` del monorepo.
- El repo tiene esta forma:
  ```
  ./
  ├── backend/     ← Django vive aquí
  ├── frontend/    ← React vive aquí
  ├── learning/
  └── README.md
  ```

### 2.2 Configuración del servicio en Railway

**Root Directory:** hay que indicarle explícitamente a Railway que use la carpeta `backend/` como raíz del servicio (Settings → Source → Root Directory = `backend`). Si no se hace esto, Railway analiza el repo completo, no encuentra pistas de qué framework usar, y falla con `Railpack could not determine how to build the app`.

### 2.3 Procfile (comando de arranque)

Ubicado en `backend/Procfile`:

```
web: python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --forwarded-allow-ips '*'
```

**Qué hace cada parte, y por qué:**

| Parte | Qué hace | Por qué |
|---|---|---|
| `python manage.py migrate --noinput` | Aplica las migraciones pendientes a la base de datos | Se corre primero: la app no debe levantar el servidor si la base de datos no está al día |
| `python manage.py collectstatic --noinput` | Junta todos los archivos estáticos (CSS, JS del admin, etc.) en un solo lugar | Necesario en producción; Django no sirve estáticos "al vuelo" como en desarrollo |
| `gunicorn config.wsgi` | Levanta el servidor de producción (gunicorn), apuntando al archivo `wsgi.py` de Django | `manage.py runserver` no está pensado para producción; gunicorn sí |
| `--bind 0.0.0.0:$PORT` | Hace que el servidor escuche en todas las interfaces de red (`0.0.0.0`), en el puerto que Railway asigna dinámicamente (`$PORT`) | Sin esto, gunicorn escucha por defecto en `127.0.0.1:8000` (solo accesible "desde adentro"), y Railway no puede enrutar tráfico externo hacia ahí |
| `--forwarded-allow-ips '*'` | Le dice a gunicorn que confíe en los headers de proxy que le manda Railway | Railway actúa como proxy intermedio; sin esto gunicorn podría no reconocer bien la IP real del cliente |

⚠️ **Nunca "quemar" (fijar) el número de puerto a mano.** `$PORT` es dinámico y puede cambiar entre deploys — la app siempre debe leerlo de la variable de entorno, no asumir un número fijo.

### 2.4 Variables de entorno necesarias en Railway

| Variable | Obligatoria | Ejemplo de valor | Notas |
|---|---|---|---|
| `SECRET_KEY` | Sí | cadena aleatoria larga | Generar con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`. Nunca debe estar hardcodeada en el código ni subida a GitHub |
| `DATABASE_URL` | Sí | `${{Postgres.DATABASE_URL}}` | **Debe ser una referencia** (`${{NombreServicio.DATABASE_URL}}`), no el texto plano pegado a mano. El nombre debe coincidir EXACTAMENTE (mayúsculas incluidas) con el nombre del servicio de Postgres en Railway |
| `ALLOWED_HOSTS` | Sí | `triage-ai-production-9205.up.railway.app` | **Sin** `https://` — solo el dominio (netloc). Si falta o está mal, Django tira `DisallowedHost` |
| `CORS_ALLOWED_ORIGINS` | Sí | `https://triage-ai-beta.vercel.app` | **Con** `https://` — a diferencia de `ALLOWED_HOSTS`. Múltiples orígenes se separan por coma sin espacios |
| `PORT` | Recomendado fijarlo | `8080` | Fijar un valor constante evita tener que reconfigurar manualmente el "target port" en Networking cada vez que Railway asigna uno distinto |
| `GEMINI_API_KEY` | Para la función de IA | tu clave | Tiene `default=''` en el código, así que no rompe el deploy si falta, pero sin ella no funciona la clasificación/sugerencia con IA |
| `DEBUG` | Opcional | `False` | Por defecto ya es `False`; en producción nunca debe estar en `True` (expone tracebacks detallados al público) |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Opcional | — | Solo necesarias si el proyecto envía correos (recuperación de contraseña, notificaciones) |

**Diferencia clave a recordar:** `ALLOWED_HOSTS` = solo dominio, sin esquema. `CORS_ALLOWED_ORIGINS` = URL completa, con `https://`. Confundir estas dos fue la causa de varios errores durante el deploy.

### 2.5 Networking (dominio público)

En Railway → Settings → Networking, al generar el dominio (`Generate Domain`), Railway pide también un **puerto de destino** (target port). Este campo:

- **No se actualiza solo** si `$PORT` cambia.
- Debe coincidir siempre con el puerto real donde gunicorn queda escuchando (visible en los logs: `Listening at: http://0.0.0.0:XXXX`).
- Por eso conviene fijar `PORT` como variable de entorno constante (ver tabla arriba) — así este campo de Networking nunca queda desactualizado.

---

## 3. Errores del backend que aparecieron (y su causa raíz)

Documentados en orden cronológico, porque cada uno enseña algo distinto:

### 3.1 `Railpack could not determine how to build the app`
- **Causa:** Root Directory apuntando a la raíz del repo en vez de `backend/`.
- **Fix:** Settings → Source → Root Directory = `backend`.

### 3.2 `Script start.sh not found`
- **Causa:** Railway esperaba un método de arranque y no encontró ninguno.
- **Fix:** crear `Procfile` (más simple que `start.sh`: no requiere permisos de ejecución y es reconocido automáticamente).

### 3.3 `KeyError: 'SECRET_KEY'` / `ImproperlyConfigured: Set the SECRET_KEY environment variable`
- **Causa:** falta la variable `SECRET_KEY` en Railway.
- **Fix:** generarla y agregarla en Variables.

### 3.4 `SystemCheckError ... CORS_ALLOWED_ORIGINS is missing scheme or netloc`
- **Causa:** el valor de `CORS_ALLOWED_ORIGINS` no tenía `https://` al inicio.
- **Fix:** agregar el esquema completo.

### 3.5 `could not translate host name "postgres.railway.internal" to address`
- **Causa raíz real (tardó varios intentos en aparecer):** el backend y la base de datos estaban en **proyectos distintos** de Railway (`alert-forgiveness` vs `splendid-reprieve`). El nombre interno `*.railway.internal` solo funciona dentro del mismo proyecto.
- **Causas intermedias también corregidas en el camino:**
  - `DATABASE_URL` pegado como texto plano en vez de referencia `${{...}}`.
  - Nombre del servicio mal escrito en la referencia (sensible a mayúsculas/minúsculas).
- **Fix definitivo:** crear el servicio PostgreSQL dentro del mismo proyecto que el backend, y usar la referencia automática que Railway genera al vincularlos.

### 3.6 `502 Bad Gateway`
- **Causa:** desajuste entre el puerto real donde escuchaba gunicorn (`8080`, asignado dinámicamente por `$PORT`) y el "target port" configurado manualmente en Networking (`8000`, un valor puesto a mano sin saber cuál usar realmente).
- **Fix:** actualizar el target port en Networking para que coincida, y fijar `PORT` como variable constante para que no vuelva a desalinearse.

### 3.7 `django.core.exceptions.DisallowedHost`
- **Causa:** `ALLOWED_HOSTS` no tenía el dominio de Railway correctamente configurado (se había perdido/sobrescrito en medio de otros cambios de variables).
- **Fix:** confirmar que `ALLOWED_HOSTS=triage-ai-production-9205.up.railway.app` (sin `https://`).
- **Lección:** un error 400 sin cuerpo JSON y con `Content-Type: text/html` es señal de que el problema es de Django/Railway a nivel de infraestructura, no de validación de datos del serializer — hay que revisar los logs del servidor, no solo la respuesta en el navegador.

---

## 4. Frontend en Vercel

### 4.1 Configuración del proyecto

- **Root Directory:** `frontend/` (Vercel detecta Vite automáticamente).
- **Variables de entorno:** con prefijo `VITE_`, ya que Vite solo expone al navegador las variables que empiezan con ese prefijo.

### 4.2 Variable `VITE_API_URL`

```
VITE_API_URL=https://triage-ai-production-9205.up.railway.app/api
```

**Errores que se dieron aquí:**

1. **Duplicar el nombre dentro del valor:** el campo "Value" quedó como `VITE_API_URL=https://...` en vez de solo `https://...` (el nombre ya va en el campo "Name", separado). Esto generaba una URL rota.
2. **Guardarla como tipo "Secret":** Vercel marcó advertencia porque toda variable `VITE_*` se incluye en el código que llega al navegador — no puede ser privada por diseño. Debe guardarse como **Config**, no como **Secret**.
   - Importante: **una vez guardada como Secret, no se puede convertir a Config** — hay que borrarla y crearla de nuevo con el tipo correcto desde el inicio.
3. **Faltaba el esquema `https://`:** sin él, axios interpreta la URL como una ruta relativa dentro del propio dominio de Vercel, generando URLs absurdas tipo `vercel.app/railway.app/...`.

**Regla clave:** las variables `VITE_*` se incrustan en el código **durante el build**, no se leen en tiempo real. Cualquier cambio en su valor requiere un **Redeploy** manual desde la pestaña Deployments — guardar la variable sola no alcanza.

### 4.3 Uso en el código (cliente axios)

```javascript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});
```
Correcto tal cual está — el problema nunca estuvo en el código, sino en el valor configurado en Vercel.

### 4.4 Error 404 en rutas de React Router (SPA)

**Síntoma:** al navegar dentro de la app (ej. volver a la lista tras editar un ticket), Vercel devuelve `404: NOT_FOUND`.

**Causa:** el proyecto es una SPA (Single Page Application) — solo existe un `index.html` real; todas las demás "páginas" las genera React Router en el navegador. Cuando el navegador pide directamente una ruta como `/tickets/5`, Vercel busca un archivo físico con ese nombre, no lo encuentra, y da 404.

**Fix:** crear `frontend/vercel.json`:
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```
Esto le dice a Vercel: para cualquier ruta que no sea un archivo real, sirve siempre `index.html` y deja que React Router decida qué mostrar.

---

## 5. Checklist rápido para el próximo deploy (o si hay que rehacerlo)

**Backend (Railway):**
- [ ] Root Directory = `backend`
- [ ] `Procfile` con `--bind 0.0.0.0:$PORT`
- [ ] Variables: `SECRET_KEY`, `DATABASE_URL` (referencia, mismo proyecto que Postgres), `ALLOWED_HOSTS` (sin https), `CORS_ALLOWED_ORIGINS` (con https), `PORT` fijo, `GEMINI_API_KEY`
- [ ] Backend y PostgreSQL en el **mismo proyecto** de Railway
- [ ] Target port en Networking = mismo valor que `PORT`

**Frontend (Vercel):**
- [ ] Root Directory = `frontend`
- [ ] `VITE_API_URL` como tipo **Config** (no Secret), con `https://` completo, sin duplicar el nombre en el valor
- [ ] `frontend/vercel.json` con el rewrite a `index.html`
- [ ] Redeploy manual después de cualquier cambio de variable `VITE_*`

---

## 6. Pendientes / bugs conocidos (no relacionados al deploy en sí)

- **Sesión no expira:** la sesión no se cierra al cerrar la pestaña/ventana del navegador, y parece no tener expiración — ocurre tanto en local como en producción. Pendiente de revisar la configuración de JWT / tiempo de vida de tokens.

---

## 7. Glosario rápido (para repasar conceptos usados en este proceso)

| Término | Explicación simple |
|---|---|
| **Root Directory** | La carpeta dentro del repo que la plataforma debe tratar como "la raíz" del proyecto a desplegar |
| **Procfile** | Archivo de texto simple que le dice a la plataforma qué comando ejecutar para arrancar la app |
| **Variable de entorno** | Un dato de configuración (clave, URL, etc.) que vive fuera del código, inyectado por la plataforma al arrancar la app |
| **`$PORT`** | Variable de entorno dinámica que la plataforma asigna; la app debe leerla, nunca asumir un número fijo |
| **CORS** | Mecanismo del navegador que controla qué dominios externos pueden hacer peticiones a tu API |
| **`ALLOWED_HOSTS`** | Lista de dominios que Django acepta como destino válido de una petición (sin esquema) |
| **Red privada / `*.railway.internal`** | Canal de comunicación interno entre servicios de un mismo proyecto de Railway, no accesible desde internet |
| **SPA (Single Page Application)** | App donde solo hay un HTML real; la navegación entre "páginas" ocurre en el navegador vía JavaScript (React Router), no recargando el servidor |
| **Rewrite (Vercel)** | Regla que redirige internamente una petición a otro archivo, sin cambiar la URL visible en el navegador |
