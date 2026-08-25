# Día 6 — Tests y Mocks

## Objetivo del día

En esta sesión trabajamos principalmente con:

- Tests de modelos Django.
- Tests de endpoints con Django REST Framework.
- `APIClient`.
- `force_authenticate`.
- Factories para crear datos de prueba.
- `Mock`, `MagicMock` y `patch`.
- Pruebas de errores de servicios externos.
- Pruebas de permisos y aislamiento entre usuarios.
- Relaciones Django con `PROTECT`, `SET_NULL` y `CASCADE`.

La idea principal que debemos conservar es:

> **Factory crea datos reales de prueba. Mock simula comportamientos o dependencias.**

---

# 1. Qué aprendimos sobre las Factories

Las factories permiten crear objetos reales rápidamente en la base de datos de testing.

Ejemplos:

```python
user = UserFactory()
ticket = TicketFactory()
category = CategoryFactory()
agent = AgentFactory()
commentary = CommentaryFactory(ticket=ticket)
```

Una factory no es simplemente un objeto temporal falso. Cuando usamos `@pytest.mark.django_db`, estamos creando registros reales dentro de la base de datos de pruebas.

Esto permite probar comportamiento real de Django:

```python
ticket.delete()
ticket.refresh_from_db()
```

o relaciones:

```python
Commentary.objects.filter(ticket_id=ticket_id)
```

## Regla mental

```text
Factory
   ↓
Crea datos reales de prueba
   ↓
User / Ticket / Category / Commentary
```

---

# 2. Qué aprendimos sobre APIClient

`APIClient` pertenece a Django REST Framework y permite simular peticiones HTTP contra nuestra API.

Por ejemplo:

```python
client = APIClient()

response = client.get('/api/tickets/')
```

No necesitamos levantar el servidor ni utilizar Postman.

Podemos simular:

```python
client.get(...)
client.post(...)
client.patch(...)
client.delete(...)
```

## Autenticación

También aprendimos:

```python
client.force_authenticate(user=user)
```

Esto permite que la siguiente petición se comporte como si hubiera sido realizada por ese usuario.

Ejemplo:

```python
customer = UserFactory()

client.force_authenticate(user=customer)

response = client.get('/api/tickets/')
```

La idea es:

```text
UserFactory()
    ↓
Usuario real de prueba

force_authenticate()
    ↓
Simula que ese usuario está autenticado

APIClient
    ↓
Simula la petición HTTP
```

---

# 3. Tests de modelos

En los tests de modelos comprobamos comportamiento propio de Django y de nuestros modelos.

## `__str__`

Ejemplo:

```python
def test_str_return_name(self):
    category = CategoryFactory(name='Bugs')
    assert str(category) == 'Bugs'
```

Estamos comprobando que la representación textual del objeto sea la esperada.

No estamos probando la base de datos de forma compleja; estamos probando comportamiento del modelo.

---

# 4. Relaciones `PROTECT`, `SET_NULL` y `CASCADE`

Esta fue una parte especialmente importante.

## PROTECT

Si una categoría tiene tickets:

```text
Category
   ↓
Ticket
```

y la relación utiliza:

```python
on_delete=models.PROTECT
```

no podemos eliminar la categoría mientras existan tickets relacionados.

El test:

```python
with pytest.raises(ProtectedError):
    category.delete()
```

comprueba precisamente ese comportamiento.

### Idea

```text
Category
   ↓
Tiene Tickets
   ↓
Intentamos eliminar Category
   ↓
ProtectedError
```

---

## SET_NULL

Para un agente asignado:

```text
Agent
   ↓
Ticket
```

si la relación usa:

```python
on_delete=models.SET_NULL
```

al eliminar el agente:

```text
Agent eliminado
      ↓
Ticket permanece
      ↓
assigned_agent = None
```

Por eso el test utiliza:

```python
agent.delete()
ticket.refresh_from_db()

assert ticket.assigned_agent is None
```

### ¿Por qué `refresh_from_db()`?

Porque queremos volver a consultar el objeto desde la base de datos después de realizar un cambio.

Sin él podríamos estar observando el estado que tenía el objeto en memoria antes de eliminar el agente.

---

## CASCADE

Para comentarios:

```text
Ticket
 ├── Commentary
 ├── Commentary
 └── Commentary
```

si utilizamos:

```python
on_delete=models.CASCADE
```

al eliminar el ticket también se eliminan sus comentarios.

El test:

```python
ticket.delete()

assert Commentary.objects.filter(
    ticket_id=ticket_id
).count() == 0
```

comprueba que no quedaron comentarios asociados.

---

# 5. Tests de permisos

También trabajamos con reglas de negocio.

Por ejemplo:

```python
def test_customer_only_see_his_tickets(self, api_client):
    customer1 = UserFactory()
    customer2 = UserFactory()

    own_ticket = TicketFactory(customer=customer1)
    TicketFactory(customer=customer2)

    api_client.force_authenticate(user=customer1)

    response = api_client.get('/api/tickets/')

    assert response.status_code == 200

    ids = [ticket['id'] for ticket in response.data]

    assert ids == [own_ticket.id]
```

Este test no solamente comprueba que `/api/tickets/` responde.

Comprueba una regla:

> Un cliente solamente puede ver sus propios tickets.

Eso es mucho más importante que comprobar únicamente `status_code == 200`.

---

# 6. 401, 403 y 404

Durante los tests vimos tres códigos especialmente importantes.

## 401 — No autenticado

```python
response = api_client.get('/api/tickets/')

assert response.status_code == 401
```

Significa:

> El usuario no está autenticado.

---

## 403 — Autenticado pero sin permiso

Ejemplo:

```python
api_client.force_authenticate(user=customer)

response = api_client.patch(...)

assert response.status_code == 403
```

El usuario existe y está autenticado, pero no puede realizar esa acción.

---

## 404 — Recurso no disponible para ese usuario

Por ejemplo:

```python
response = api_client.get(
    f'/api/tickets/{stranger_ticket.id}/'
)

assert response.status_code == 404
```

Aquí la API puede estar ocultando la existencia del recurso.

Esto puede ser una decisión de seguridad:

> Para este usuario, el ticket se comporta como si no existiera.

No debemos asumir automáticamente que `404` significa que el objeto realmente no existe en la base de datos.

---

# 7. El problema que encontramos con el 400 y el 403

Tuvimos un caso muy útil:

El test esperaba:

```python
assert response.status_code == 403
```

pero recibíamos:

```text
400 Bad Request
```

La razón estaba relacionada con el serializer.

Nuestro modelo `Commentary` tenía:

```python
ticket
author
text
created_at
```

pero el request enviaba:

```python
{
    'ticket': stranger_ticket.id,
    'text': 'Intento colarme',
}
```

y `author` estaba siendo tratado como campo obligatorio.

La idea correcta para este diseño es que el cliente no decida quién es el autor.

El servidor debería utilizar:

```python
serializer.save(author=self.request.user)
```

y el serializer debería tratar `author` como de solo lectura:

```python
read_only_fields = ['author']
```

## Lección

Cuando un test de permisos devuelve `400` en lugar de `403`, no debemos asumir inmediatamente que el permiso está mal.

Primero debemos comprobar:

1. ¿El request tiene todos los datos válidos?
2. ¿El serializer acepta esos datos?
3. ¿La creación llega realmente a la lógica de permisos?
4. ¿La vista está devolviendo el código esperado?

El flujo conceptual es:

```text
Request
   ↓
Validación del serializer
   ↓
¿Datos válidos?
   ├── NO → 400
   │
   └── SÍ
        ↓
    Permisos / lógica
        ↓
       403
```

---

# 8. El problema con las importaciones

También encontramos un problema con:

```python
from .factories import ...
```

que produjo:

```text
ImportError: attempted relative import with no known parent package
```

Después apareció:

```text
ModuleNotFoundError:
No module named 'tickets.tests.factories';
'tickets.tests' is not a package
```

La solución conceptual fue revisar la estructura del proyecto y asegurarnos de que `tests` fuera reconocido como paquete cuando usamos:

```python
from tickets.tests.factories import ...
```

Una estructura esperada puede ser:

```text
tickets/
├── __init__.py
├── models.py
└── tests/
    ├── __init__.py
    ├── factories.py
    └── test_models.py
```

### Lección

Antes de cambiar imports al azar, hay que mirar el error y la estructura real del proyecto.

---

# 9. MOCK — La parte más importante del día

Aquí apareció un concepto nuevo.

## ¿Qué problema resuelve un Mock?

Imaginemos que nuestro servicio utiliza una API externa de IA:

```python
client = genai.Client(...)
response = client.models.generate_content(...)
```

Si hacemos un test normal, podríamos terminar llamando a la IA real.

Eso es mala idea para un test unitario porque:

- Puede ser lento.
- Puede costar dinero.
- Puede fallar por problemas de Internet.
- Puede depender de un servicio externo.
- Puede devolver resultados variables.
- Hace que los tests sean menos predecibles.

Aquí entra el Mock.

---

# 10. La diferencia fundamental

## Factory

Una factory dice:

> Necesito un objeto real para mi prueba.

```python
ticket = TicketFactory()
```

Tenemos un `Ticket` real en la base de datos de testing.

## Mock

Un Mock dice:

> No quiero ejecutar esta dependencia real. Quiero controlar qué hace.

Por ejemplo:

```text
API de IA real
     ↓
    NO

Mock de la API
     ↓
    SÍ
```

Podemos decidir exactamente qué devuelve o qué error produce.

---

# 11. `patch`

Usamos:

```python
with patch('tickets.services.genai.Client') as MockClient:
```

La idea es:

> Durante este bloque de código, sustituye temporalmente `genai.Client` por un Mock.

Conceptualmente:

```text
Antes:

tickets.services.genai.Client
        ↓
Cliente real de GenAI


Durante patch:

tickets.services.genai.Client
        ↓
MockClient
```

Cuando termina el `with`, el objeto original vuelve a estar disponible.

Por eso `patch` es temporal.

---

# 12. `return_value`

Esta línea puede parecer complicada:

```python
MockClient.return_value.models.generate_content.return_value = response_mock(json_valido)
```

Podemos leerla paso a paso.

Primero:

```python
MockClient
```

es nuestro cliente falso.

Cuando hacemos:

```python
MockClient()
```

obtenemos:

```python
MockClient.return_value
```

Ese objeto tiene:

```python
.models
```

y después:

```python
.generate_content()
```

Y queremos decidir qué devuelve esa llamada.

Por eso:

```python
generate_content.return_value
```

significa:

> Cuando se ejecute `generate_content()`, devuelve esto.

Entonces:

```python
MockClient.return_value.models.generate_content.return_value = ...
```

significa:

> Cuando el código llame a `generate_content()`, devuelve exactamente la respuesta falsa que hemos preparado.

---

# 13. ¿Por qué existe `response_mock()`?

Tenemos:

```python
def response_mock(texto):
    r = MagicMock()
    r.text = texto
    return r
```

Esto existe porque nuestro servicio probablemente utiliza algo como:

```python
response.text
```

No necesitamos reproducir toda la respuesta real de GenAI.

Solamente necesitamos crear un objeto que tenga la propiedad que nuestro código utiliza:

```python
response.text
```

Por eso:

```python
r = MagicMock()
r.text = texto
```

es suficiente para este test.

## Idea importante

No estamos simulando toda la IA.

Estamos simulando solamente la parte de la respuesta que nuestro código necesita.

---

# 14. `MagicMock` frente a `Mock`

`MagicMock` es una versión más completa de `Mock` que facilita la simulación de objetos y atributos.

En nuestro caso:

```python
r = MagicMock()
r.text = texto
```

nos permite crear rápidamente un objeto que se comporta como una respuesta.

Para este proyecto no necesitamos memorizar todavía todas las diferencias entre `Mock` y `MagicMock`.

La idea práctica es:

```text
Mock / MagicMock
        ↓
Objeto controlado por el test
```

---

# 15. `return_value` frente a `side_effect`

Esta diferencia es MUY importante.

## `return_value`

Usamos:

```python
MockClient.return_value.models.generate_content.return_value = response_mock(json_valido)
```

cuando queremos decir:

> La llamada funciona y devuelve este resultado.

Ejemplo:

```text
generate_content()
       ↓
JSON válido
```

---

## `side_effect`

Usamos:

```python
MockClient.return_value.models.generate_content.side_effect = (
    Exception('fallo de red')
)
```

cuando queremos decir:

> Cuando llamen a esta función, provoca este error.

Ejemplo:

```text
generate_content()
       ↓
Exception
       ↓
ErrorGenerationIA
```

### Regla mental

```text
return_value
    ↓
"devuelve esto"


side_effect
    ↓
"haz que ocurra esto"
```

---

# 16. Nuestros tres escenarios de IA

Los tests del servicio de IA están muy bien divididos.

## Camino feliz

```python
response_mock(json_valido)
```

La IA devuelve una respuesta correcta.

Comprobamos:

```python
assert results['suggestion_priority'] == 'alta'
```

---

## Error externo

```python
generate_content.side_effect = Exception(...)
```

Simulamos que la API no responde.

Esperamos:

```python
with pytest.raises(ErrorGenerationIA):
```

Esto comprueba que nuestro servicio transforma un error externo en nuestro propio error de aplicación.

---

## Respuesta inválida

La IA responde, pero devuelve:

```json
{
    "suggestion_priority": "SUPER URGENTE"
}
```

La API no falló técnicamente.

El problema es que los datos recibidos son inválidos.

Esperamos igualmente:

```python
with pytest.raises(ErrorGenerationIA):
```

Esto prueba una diferencia importante:

```text
Error técnico
    ↓
API no responde


Error de contenido
    ↓
API responde algo que nuestra aplicación no acepta
```

Ambos casos deben estar controlados.

---

# 17. Mock de una IA durante la creación de tickets

Otro test comprueba:

```text
Crear Ticket
     ↓
Intentar usar IA
     ↓
IA falla
     ↓
Ticket se crea igualmente
     ↓
has_suggestion_ia = False
```

El Mock provoca el fallo:

```python
MockClient.return_value.models.generate_content.side_effect = (
    Exception('la IA no responde')
)
```

Después comprobamos:

```python
assert response.status_code == 201
assert response.data['has_suggestion_ia'] is False
```

Este test es especialmente valioso porque prueba una regla de negocio:

> La IA es una funcionalidad complementaria; si falla, la creación del ticket no debe fallar.

---

# 18. Buenas prácticas que aplicamos

## 1. Tests pequeños

Cada test intenta comprobar una regla concreta.

Ejemplos:

```text
cliente solo ve sus tickets
admin ve todos
usuario no autenticado recibe 401
cliente no puede modificar estado
agente asignado puede modificarlo
```

Esto facilita descubrir qué parte se rompe.

---

## 2. Nombres descriptivos

Aunque algunos nombres todavía pueden mejorar gramaticalmente, la intención es clara.

Un buen test debería poder leerse casi como una frase:

```python
test_customer_cannot_see_stranger_ticket
```

permite entender inmediatamente la regla.

---

## 3. Usamos Factories

En lugar de construir manualmente:

```python
User.objects.create(...)
Ticket.objects.create(...)
```

usamos:

```python
UserFactory()
TicketFactory()
```

Esto reduce repetición y hace los tests más legibles.

---

## 4. Usamos `APIClient`

No necesitamos Postman ni un servidor real.

Podemos probar:

```python
api_client.get(...)
api_client.post(...)
api_client.patch(...)
```

directamente desde pytest.

---

## 5. Probamos casos positivos y negativos

No solamente comprobamos que algo funciona.

También comprobamos:

```text
Funciona
No funciona
No autenticado
Sin permisos
Datos inválidos
Dependencia externa caída
```

Esto hace los tests mucho más útiles.

---

## 6. Mockeamos dependencias externas

La IA es un excelente ejemplo.

No queremos que nuestro test dependa de:

```text
Internet
   ↓
API externa
   ↓
Google / GenAI
```

Queremos:

```text
Test
 ↓
Mock
 ↓
Respuesta controlada
```

---

# 19. Fallas de operación que debemos vigilar

No nos interesa solamente que el código tenga buena sintaxis.

También debemos preguntarnos si el test realmente está probando lo que creemos.

## Falla 1 — Un test de permisos que devuelve 400

Esto nos pasó.

Esperábamos:

```python
403
```

pero recibíamos:

```python
400
```

La enseñanza:

> Antes de probar permisos, debemos asegurarnos de que el request sea válido.

---

## Falla 2 — No garantizar quién es el dueño del ticket

Un test como:

```python
customer = UserFactory()
stranger_ticket = TicketFactory()
```

puede ser menos explícito que:

```python
customer = UserFactory()
stranger = UserFactory()
stranger_ticket = TicketFactory(customer=stranger)
```

La segunda versión deja claro que el ticket pertenece a otra persona.

Los tests deben preparar sus datos de manera explícita.

---

## Falla 3 — Confundir nombres de campos

Durante la sesión aparecieron diferencias como:

```text
customer / cliente
assigned_agent / agente_asignado
status / estado
Commentary / Comentario
```

Esto no es solamente un problema de sintaxis.

Si el test utiliza un nombre diferente al que realmente utiliza el modelo o serializer, podemos terminar probando otra cosa o haciendo que el test falle por una razón irrelevante.

Antes de escribir el test debemos conocer el contrato real de:

- modelo
- serializer
- endpoint
- factory

---

## Falla 4 — Importar una dependencia incorrecta

También encontramos problemas con:

```python
from .factories import ...
```

y:

```python
from tickets.tests.factories import ...
```

La enseñanza es que los tests también dependen de una estructura correcta de paquetes.

No debemos solucionar errores de importación cambiando rutas a ciegas.

---

## Falla 5 — Comprobar demasiado poco

Por ejemplo:

```python
assert response.status_code == 200
```

puede ser insuficiente.

Si estamos probando que un cliente solamente vea sus tickets, es mejor comprobar también los IDs:

```python
ids = [ticket['id'] for ticket in response.data]

assert ids == [own_ticket.id]
```

Así comprobamos el comportamiento real y no solamente que la petición fue aceptada.

---

# 20. Cómo pensar un buen test

Antes de escribirlo podemos pensar en cuatro pasos:

```text
ARRANGE
   ↓
Preparar datos

ACT
   ↓
Ejecutar acción

ASSERT
   ↓
Comprobar resultado
```

Ejemplo:

```python
customer = UserFactory()
ticket = TicketFactory(customer=customer)

api_client.force_authenticate(user=customer)

response = api_client.get(f'/api/tickets/{ticket.id}/')

assert response.status_code == 200
```

Aquí:

### Arrange

```python
customer = UserFactory()
ticket = TicketFactory(customer=customer)
```

### Act

```python
response = api_client.get(...)
```

### Assert

```python
assert response.status_code == 200
```

---

# 21. Cómo pensar un test con Mock

La estructura mental es:

```text
1. Crear los datos reales que necesito
       ↓
2. Sustituir la dependencia externa
       ↓
3. Decidir qué hará el Mock
       ↓
4. Ejecutar mi código
       ↓
5. Comprobar cómo respondió mi aplicación
```

Ejemplo:

```python
ticket = TicketFactory()

with patch('tickets.services.genai.Client') as MockClient:

    MockClient.return_value.models.generate_content.return_value = (
        response_mock(json_valido)
    )

    result = generate_suggestion_ia(ticket)

assert result['suggestion_priority'] == 'alta'
```

La IA es falsa.

El ticket es real.

Nuestro servicio es real.

Eso es exactamente lo que queremos probar.

---

# 22. Qué NO debemos hacer con Mock

No deberíamos mockear todo.

Por ejemplo, sería innecesario hacer un Mock de:

```python
TicketFactory()
```

si queremos probar el comportamiento real de un ticket.

Tampoco tiene sentido mockear el modelo que estamos intentando probar.

Una buena regla:

> **Mockea lo que está fuera de la responsabilidad que estás probando.**

Si estoy probando `generate_suggestion_ia`, puedo mockear la IA.

Si estoy probando cómo funciona el modelo `Ticket`, no debería convertir `Ticket` en un Mock.

---

# 23. Checklist mental para próximos tests

- [ ] ¿Qué comportamiento estoy intentando comprobar?
- [ ] ¿Qué datos reales necesito?
- [ ] ¿Puedo crear esos datos con una Factory?
- [ ] ¿Estoy probando un endpoint? → `APIClient`
- [ ] ¿Necesito simular un usuario? → `force_authenticate`
- [ ] ¿Existe una dependencia externa? → considerar `Mock`
- [ ] ¿Necesito una respuesta controlada? → `return_value`
- [ ] ¿Necesito simular un error? → `side_effect`
- [ ] ¿El request es válido antes de comprobar permisos?
- [ ] ¿Estoy comprobando el resultado real y no solamente `200`?
- [ ] ¿El test garantiza explícitamente las relaciones entre objetos?
- [ ] ¿Estoy probando una sola regla por test?

---

# 24. Resumen final del Día 6

La distinción más importante que debemos recordar es:

```text
FACTORY
Crea datos reales de prueba.

APIClient
Simula peticiones HTTP.

force_authenticate
Simula el usuario autenticado.

MOCK
Simula una dependencia o comportamiento.

patch
Reemplaza temporalmente una dependencia por un Mock.

return_value
Define qué devuelve el Mock.

side_effect
Define qué error/comportamiento provoca el Mock.
```

Y el concepto central:

> **No usamos Mock para crear objetos de la aplicación cuando una Factory puede hacerlo. Usamos Mock cuando queremos aislar nuestro código de una dependencia cuyo comportamiento queremos controlar.**

En nuestro proyecto:

```text
UserFactory()       → usuario real de prueba
TicketFactory()     → ticket real de prueba
CategoryFactory()   → categoría real de prueba

APIClient            → petición falsa a nuestra API

genai.Client         → dependencia externa
        ↓
      patch
        ↓
   MockClient        → versión controlada para el test
```

Ese es el modelo mental que conviene llevarse de esta clase.
