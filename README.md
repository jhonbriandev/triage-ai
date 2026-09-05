[![Tests](https://github.com/jhonbriandev/triage-ai/actions/workflows/tests.yml/badge.svg)](https://github.com/jhonbriandev/triage-ai/actions/workflows/tests.yml)

# Triage IA

Sistema de soporte técnico que usa IA (Google Gemini) para clasificar automáticamente cada ticket que un cliente reporta — categoría, prioridad, un resumen y una respuesta inicial sugerida — para que el agente que lo atienda ya llegue con contexto, en vez de partir de cero.

Construido como proyecto de portafolio: Django REST Framework en el backend, React en el frontend, autenticación JWT con permisos diferenciados por rol, y una integración real con un modelo de IA externo, con manejo de errores de verdad (el sistema sigue funcionando aunque la IA falle).

## Capturas y demo

Demo en vivo: https://triage-ai-beta.vercel.app/dashboard

![alt text](image.png)

Vista principal, lista de tickets con roles para Administrador, agente o cliente.

![alt text](image-1.png)

Detalle del ticket creado, clasificacion de prioridad , estado y categoria

![alt text](image-2.png)

Detalle del ticket creado, sugerencia de la inteligencia artificial sobre la prioridad, estado y categoria

![alt text](image-3.png)

Dashboard interactivo para todo los roles, clasificacion y filtrado segun el estado

## Stack tecnológico

Backend: Django · Django REST Framework · Simple JWT · PostgreSQL · google-genai (Gemini) · pytest + factory_boy

Frontend: React (Vite) · React Router · React Hook Form · Axios · jwt-decode

Infraestructura: Railway (backend + base de datos) · Vercel (frontend)

Cuando un cliente crea un ticket, el backend responde de inmediato con el ticket ya creado y, en la misma petición, llama a Gemini para generar una sugerencia de clasificación. Si la IA falla por cualquier motivo (sin conexión, límite de peticiones, respuesta inválida), el ticket se conserva igual — la sugerencia simplemente queda pendiente, y un agente puede clasificarlo a mano.

![Arquitectura del sistema](docs/architecture.svg)

## Funcionalidades principales

- **3 roles con permisos diferenciados:** cliente (crea tickets, ve y comenta solo los suyos), agente (ve y gestiona los que tiene asignados), admin (ve todo, gestiona categorías).
- **Clasificación automática por IA:** cada ticket nuevo recibe una sugerencia de categoría, prioridad, resumen y respuesta inicial — visible solo para agentes/admin, nunca para el cliente que lo creó.
- **Autenticación JWT** con renovación automática de sesión (el usuario nunca tiene que volver a loguearse solo porque el token venció mientras usaba la app).
- **Dashboard con métricas** de tickets por estado, respetando el mismo alcance por rol que el resto de la app.
- **Manejo de errores real** en la integración con IA: la creación de un ticket nunca falla por un problema del lado de la IA.

---

## Decisiones técnicas destacadas

Algunas elecciones de diseño que vale la pena explicar, no solo mostrar:

- **La categoría del ticket es opcional al crearlo.** El cliente que reporta un problema no tiene por qué saber en qué categoría técnica encaja — para eso está la IA. La categoría se completa después (por la sugerencia de la IA, confirmada por un agente, o a mano).
- **Los campos de la sugerencia de IA son texto libre, no relaciones ni listas cerradas.** Lo que devuelve un modelo de lenguaje no es 100% predecible; forzarlo a encajar en una lista rígida podría romper la app si la IA responde algo ligeramente distinto a lo esperado. Se guarda tal cual, y es un humano quien decide si aplicarlo a los campos reales del ticket (que sí son controlados).
- **La IA nunca puede tumbar la creación de un ticket.** La llamada a Gemini está aislada en su propia capa de manejo de errores (tipo de excepción propio, timeout, validación de la respuesta) — si falla, se registra el error y el ticket se crea de todas formas, sin sugerencia.
- **Los `on_delete` de cada relación se eligieron caso por caso**, no por defecto: `PROTECT` donde se protege un historial (no perder los tickets de un cliente si su cuenta se borra), `CASCADE` donde el registro hijo no tiene sentido sin su padre (un comentario sin su ticket), `SET_NULL` donde la relación es opcional (un ticket sin agente asignado vuelve a quedar "sin asignar", no se bloquea ni se borra nada).
- **Asignación de tickets**, los tickets se crean sin agente asignado. Solo el rol admin puede asignar un ticket a un agente específico. Los agentes no pueden auto-asignarse tickets ni ver tickets que no les fueron asignados.

---

## Instalación local

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # y completa tus valores reales
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env           # y completa tu VITE_API_URL
npm run dev
```

Con ambos corriendo, abre `http://localhost:5173`.

---

## Variables de entorno

**`backend/.env`**

| Variable               | Descripción                                                                                    |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| `SECRET_KEY`           | Clave interna de Django. Django genera una automáticamente al crear el proyecto.               |
| `DEBUG`                | `True` en desarrollo, **`False` siempre en producción**.                                       |
| `DATABASE_URL`         | Cadena de conexión a PostgreSQL (formato `postgres://usuario:password@host:puerto/nombre_bd`). |
| `GEMINI_API_KEY`       | Tu clave de la API de Gemini, desde [Google AI Studio](https://aistudio.google.com).           |
| `ALLOWED_HOSTS`        | Dominios permitidos, separados por coma (en producción: tu dominio real).                      |
| `CORS_ALLOWED_ORIGINS` | Orígenes del frontend permitidos, separados por coma.                                          |

**`frontend/.env`**

| Variable       | Descripción                                                    |
| -------------- | -------------------------------------------------------------- |
| `VITE_API_URL` | URL base de la API (ej. `http://127.0.0.1:8000/api` en local). |

---
