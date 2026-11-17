# Documentación del flujo de IA — Proyecto Triage IA

Documento informativo sobre cómo el proyecto genera sugerencias con IA al crear un ticket, qué datos se guardan y qué ocurre cuando algo falla. Cada fila indica el archivo y la función donde se puede comprobar lo descrito.

---

## Preguntas y respuestas

| N.º | Pregunta                                                                                     | Respuesta                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Código relacionado                                                                        |
| --- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 1   | ¿Cuántos tests tiene el proyecto y pasan?                                                    | El proyecto tiene **17 tests**, ejecutados con `pytest`. Todos pasan correctamente.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | —                                                                                         |
| 2   | Si la IA falla o tarda, ¿el ticket se crea igual?                                            | **Sí, si la IA falla.** El ticket se guarda primero con `serializer.save()` y después se intenta generar la sugerencia. Si el servicio lanza `ErrorGenerationAI`, `perform_create()` registra el error en el log y el ticket queda creado sin sugerencia.<br><br>**Si la IA tarda:** la llamada ocurre dentro de la petición, por lo que quien crea el ticket espera. Ante errores temporales (por ejemplo, saturación de Gemini) el servicio reintenta con esperas crecientes (`time.sleep`), y esas esperas también ocurren dentro de la petición (ver Parte final, caso 1).<br><br>`perform_create()` solo captura `ErrorGenerationAI`; la Parte final detalla qué casos terminan como esa excepción. | `tickets/views.py` — `perform_create()`                                                   |
| 3   | ¿La llamada a la IA ocurre dentro de la petición (el usuario espera) o en segundo plano?     | **Dentro de la petición.** `generate_suggestion_ai(ticket)` se llama dentro de `perform_create()`, así que la respuesta HTTP no se envía hasta que termina esa llamada (incluidos los reintentos, si los hay) y se procesa su resultado. No se ejecuta en segundo plano.<br><br>Dato de referencia: una _signal_ de Django se ejecuta de forma síncrona por defecto, por lo que tampoco movería la llamada fuera de la petición. Para ejecutarla en segundo plano se necesita un sistema de tareas, por ejemplo Celery.                                                                                                                                                                                  | `tickets/views.py` — `perform_create()`                                                   |
| 4   | ¿Hay una regla en código que suba la prioridad por palabras críticas, sin depender de la IA? | **No.** Los tickets tienen un campo de prioridad, pero no existe una regla propia que detecte palabras críticas y eleve la prioridad sin depender de la IA.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | —                                                                                         |
| 5   | ¿Se guarda qué sugirió la IA y qué decidió finalmente el agente?                             | **Sí.** La sugerencia se guarda en el modelo `SuggestionAi` (`suggestion_category`, `suggestion_priority`, `generated_summary`, `suggestion_answer`) y se muestra al agente. La decisión del agente se conserva por separado, en el propio ticket (`priority`, `category`, `status`), y no sobrescribe la sugerencia original.<br><br>`SuggestionAiSerializer` expone los datos de la sugerencia y `TicketSerializer` los incluye mediante `suggestion_ai` y `has_suggestion_ai`.                                                                                                                                                                                                                        | `tickets/serializers.py` — `SuggestionAiSerializer`, `TicketSerializer`                   |
| 6   | ¿Hay un test del caso "la IA falla"?                                                         | **Sí.** El test simula un fallo de la IA con `patch`, comprueba que la API responde con estado `201` y que el ticket se creó sin sugerencia (`has_suggestion_ai is False`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | `tickets/tests/test_views.py` — `test_ticket_is_created_without_suggestion_if_ai_fails()` |
| 7   | ¿Hay alguna línea donde la prioridad del ticket se asigne desde `suggestion_priority`?       | **No.** Las sugerencias se muestran en el admin o al agente encargado, y el agente gestiona manualmente la categoría, la prioridad y la respuesta.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | No aplica: esa asignación no existe, por lo que no hay archivo ni función que citar.      |

ACTUALIZACION:
Estamos usando la funcion de palabras criticas, por lo tanto ahora algunas palabras lanzaran que el ticket obtenga la prioridad mas alta, la cual es URGENTE
Tener en cuenta que, aun no hemos restringido que el usuario pueda pasar la prioridad o estado en formato JSOn por lo cual es algo que debemos de controlar proximamente con:

```python
@pytest.mark.xfail(reason="...")
```

---

## Código de referencia

### 2 y 3. Creación del ticket y llamada a la IA — `tickets/views.py`

```python
def perform_create(self, serializer):
    # Guarda el ticket asociado al usuario autenticado (el cliente que lo crea)
    ticket = serializer.save(customer=self.request.user)
    try:
        # Pide la sugerencia a la IA (la petición espera hasta que termine)
        datos_ia = generate_suggestion_ai(ticket)
        # Guarda la sugerencia en su propio modelo, ligada al ticket
        SuggestionAi.objects.create(ticket=ticket, **datos_ia)
    except ErrorGenerationAI as exc:
        # Si la IA falla, solo se registra el error: el ticket ya está guardado
        logger.error(
            'Ticket #%s creado SIN sugerencia de IA: %s',
            ticket.pk,
            exc
        )
```

**Lectura del flujo:**

1. Se guarda el ticket asociado al usuario autenticado.
2. Se solicita la sugerencia de IA.
3. Si se obtiene un resultado válido, se crea el registro `SuggestionAi`.
4. Si se lanza `ErrorGenerationAI`, se registra el error y el ticket ya guardado se conserva.

### 5. Serialización de la sugerencia — `tickets/serializers.py`

```python
class SuggestionAiSerializer(serializers.ModelSerializer):

    class Meta:
        model = SuggestionAi  # modelo que se convierte a JSON
        fields = [
            'id',
            'ticket',                # ticket al que pertenece la sugerencia
            'suggestion_category',   # categoría que propuso la IA
            'suggestion_priority',   # prioridad que propuso la IA
            'generated_summary',     # resumen generado por la IA
            'suggestion_answer',     # respuesta sugerida por la IA
            'generation_date',       # cuándo se generó
            'updated_at',            # última modificación
        ]
```

```python
class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket  # modelo que se convierte a JSON
        fields = [
            'id',
            'title',
            'description',
            'status',                   # valor guardado del estado
            'status_display',           # versión legible del estado
            'priority',                 # valor guardado de la prioridad
            'priority_display',         # versión legible de la prioridad
            'category',                 # id de la categoría
            'category_name',            # nombre de la categoría
            'customer',                 # id del cliente que creó el ticket
            'customer_username',        # nombre de usuario del cliente
            'assigned_agent',           # id del agente asignado
            'assigned_agent_username',  # nombre de usuario del agente
            'created_at',
            'has_suggestion_ai',        # indica si el ticket tiene sugerencia
            'suggestion_ai',            # datos de la sugerencia (si existe)
        ]
```

### 6. Test del fallo de IA — `tickets/tests/test_views.py`

```python
def test_ticket_is_created_without_suggestion_if_ai_fails(self):
    # Factory: necesitamos datos reales para probar la creación del ticket.
    customer = UserFactory()
    category = CategoryFactory()

    client = APIClient()
    client.force_authenticate(user=customer)

    # Mock: simulamos que la IA no responde.
    # No queremos depender de una API externa durante el test.
    with patch('tickets.services.genai.Client') as MockClient:
        MockClient.return_value.models.generate_content.side_effect = (
            Exception('la IA no responde')
        )

        response = client.post(
            '/api/tickets/',
            {
                'title': 'Prueba',
                'description': 'x',
                'category': category.id,
            },
            format='json'
        )

    # El ticket se creó (201) aunque la IA falló...
    assert response.status_code == 201
    # ...y quedó sin sugerencia
    assert response.data['has_suggestion_ai'] is False
```

---

## Parte final — Qué puede salir mal

Casos en los que la respuesta de la IA no se puede usar y si el servicio los convierte en `ErrorGenerationAI`. Cuando eso ocurre, `perform_create()` lo registra en el log y el ticket permanece creado sin sugerencia.

| N.º | Caso                             | ¿Termina como `ErrorGenerationAI`? | Qué ocurre                                                                                                                                                                                      | Evidencia |
| --- | -------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| 1   | Error de red o tiempo agotado    | **Sí**                             | Si el error es temporal y quedan intentos, espera y reintenta (1 s, 2 s y 4 s según el comentario del código). Si el error no es temporal, o se agotan los intentos, lanza `ErrorGenerationAI`. | Bloque 1  |
| 2   | La IA devuelve JSON inválido     | **Sí**                             | `json.loads()` no puede leer la respuesta (texto que no es JSON, o respuesta sin texto) y se lanza `ErrorGenerationAI`.                                                                         | Bloque 2  |
| 3   | Falta una clave esperada         | **Sí**                             | La respuesta omite uno o más campos esperados y se lanza `ErrorGenerationAI` indicando cuáles faltan.                                                                                           | Bloque 3  |
| 4   | Categoría sugerida que no existe | **No**                             | La categoría es de texto libre: no se valida contra una lista, por lo que no genera error.                                                                                                      | —         |
| 5   | Prioridad sugerida que no existe | **Sí**                             | La prioridad debe ser una de las permitidas (`VALID_PRIORITY`); si no lo es, se lanza `ErrorGenerationAI`.                                                                                      | Bloque 4  |

### Evidencia (`tickets/services.py` — `generate_suggestion_ai()`)

**Bloque 1 — Error de red o tiempo agotado**

```python
# Error temporal y todavía quedan intentos
if is_temporal and tried < max_tried - 1:
    wait = 2 ** tried  # 1er reintento: 1s, 2do: 2s, 3er: 4s
    logger.warning(
        'Gemini saturado (intento %s/%s) para ticket #%s, reintentando en %ss',
        tried + 1, max_tried, ticket.pk, wait,
    )
    time.sleep(wait)  # pausa antes de volver a intentar
    continue  # vuelve a intentar

# Error no temporal, o se agotaron los intentos: se informa y se lanza la excepción
logger.warning('Gemini respondió con un error para el ticket #%s: %s', ticket.pk, exc)
raise ErrorGenerationAI(f'La API de Gemini respondió con un error: {exc}') from exc
```

**Bloque 2 — La IA devuelve JSON inválido**

```python
try:
    # Convierte el texto de la IA en un diccionario de Python
    data = json.loads(response.text)
except (json.JSONDecodeError, TypeError, AttributeError):
    # JSONDecodeError: el texto no es JSON
    # TypeError / AttributeError: la respuesta no trae texto
    logger.warning(
        'La IA no devolvió JSON válido para el ticket #%s. Respuesta cruda: %r',
        ticket.pk, getattr(response, 'text', None),
    )
    raise ErrorGenerationAI('La IA no devolvió un JSON válido')
```

**Bloque 3 — Falta una clave esperada**

```python
# `missing` contiene las claves esperadas que la IA no envió
if missing:
    logger.warning('La IA omitió campos %s para el ticket #%s', missing, ticket.pk)
    raise ErrorGenerationAI(f'Faltan campos en la respuesta de la IA: {missing}')
```

**Bloque 4 — Prioridad sugerida que no existe**

```python
# VALID_PRIORITY contiene las prioridades permitidas
if data['suggestion_priority'] not in VALID_PRIORITY:
    logger.warning(
        'Prioridad sugerida inválida "%s" para el ticket #%s',
        data['suggestion_priority'], ticket.pk,
    )
    raise ErrorGenerationAI(f"Prioridad sugerida inválida: {data['suggestion_priority']!r}")
```

## EXTRA

Reconocer que el valor mas alto de prioridad definido en models es "URGENTE"
