# Documentación: Asignación de Tickets a Agentes

**Proyecto:** Sistema de Triage de Tickets con IA
**Feature:** Asignación manual de tickets a agentes por parte del admin
**Estado:** Implementado y probado (con 2 bugs corregidos durante el desarrollo)

---

## 1. Contexto y decisión de diseño

### El problema
Al revisar el sistema ya "culminado" según los requerimientos, se detectó un vacío: **no estaba definido quién asigna un ticket a un agente**, dado que los agentes no pueden elegir sus propios tickets. Sin esta pieza, un ticket creado por un cliente no tenía forma de llegar a ningún agente.

### La decisión
Se evaluaron 3 opciones:

| Opción | Descripción | Complejidad |
|---|---|---|
| **Manual por admin** ✅ elegida | El admin ve los tickets y asigna un agente a cada uno | Baja |
| Automática (round-robin) | El sistema reparte solo, rotando entre agentes | Media |
| Asistida por IA | Se sugiere agente según la clasificación de IA ya existente | Alta (fuera de alcance) |

Se eligió **asignación manual por el admin** por ser la más simple de implementar, consistente con el sistema de roles y permisos ya construido, y suficiente para el alcance del proyecto.

---

## 2. Cambios en el Backend (Django + DRF)

### 2.1 Modelo — campo `assigned_agent`

```python
# models.py
class Ticket(models.Model):
    # ... campos existentes
    assigned_agent = models.ForeignKey(
        User,
        null=True,           # el ticket nace sin agente
        blank=True,
        on_delete=models.SET_NULL,  # si se borra el agente, el ticket queda "sin asignar"
        related_name="assigned_tickets"
    )
```

### 2.2 Serializers

```python
# serializers.py
from django.contrib.auth import get_user_model
User = get_user_model()

# Serializer minimalista: solo lo necesario para el <select> del admin
class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class TicketSerializer(serializers.ModelSerializer):
    # ... otros campos
    assigned_agent_username = serializers.CharField(
        source='assigned_agent.username',
        read_only=True,
        default=None
    )

    class Meta:
        model = Ticket
        fields = [
            # ...
            'assigned_agent',
            'assigned_agent_username',
        ]
        read_only_fields = [
            'customer', 'created_at', 'has_suggestion_ai',
            'assigned_agent', 'assigned_agent_username',  # <- se agregó para
            # evitar que el PATCH general de tickets pueda modificar el
            # agente asignado sin pasar por la validación del endpoint /assign/
        ]
```

### 2.3 Permisos

```python
# permissions.py
class PermissionAssignTicket(permissions.BasePermission):
    """Solo el admin puede ver la lista de agentes y asignar tickets."""
    def has_permission(self, request, view):
        return request.user.profile.role == 'admin'
```

### 2.4 Vistas — dos acciones nuevas en `TicketViewSet`

```python
# views.py
class TicketViewSet(viewsets.ModelViewSet):
    # ... get_queryset, perform_create, stats (ya existentes)

    @action(detail=False, methods=['get'], permission_classes=[PermissionAssignTicket])
    def agents(self, request):
        """GET /tickets/agents/ — lista de usuarios con rol 'agent'."""
        agentes = User.objects.filter(profile__role='agent')
        return Response(AgentSerializer(agentes, many=True).data)

    @action(detail=True, methods=['patch'], permission_classes=[PermissionAssignTicket])
    def assign(self, request, pk=None):
        """PATCH /tickets/<id>/assign/ — asigna o desasigna un agente."""
        ticket = self.get_object()
        agent_id = request.data.get('assigned_agent')

        # "Sin agente" es un valor válido (desasignar), no un error
        if agent_id in (None, "", "null"):
            ticket.assigned_agent = None
            ticket.save()
            return Response(TicketSerializer(ticket).data)

        try:
            agent = User.objects.get(id=agent_id, profile__role='agent')
        except User.DoesNotExist:
            return Response(
                {"error": "El usuario indicado no existe o no es un agente."},
                status=400
            )

        ticket.assigned_agent = agent
        ticket.save()
        return Response(TicketSerializer(ticket).data)
```

### 2.5 Filtrado por rol (ya existente, reutilizado)

`get_queryset()` ya filtraba tickets por rol; los agentes automáticamente ven solo lo que tienen asignado:

```python
elif role == 'agent':
    queryset = Ticket.objects.filter(assigned_agent=user)
```

---

## 3. Cambios en el Frontend (React)

### 3.1 `services/tickets.js`

```javascript
export async function listAgents() {
  const { data } = await api.get("/tickets/agents/");
  return data;
}

export async function assignTicket(id, agentId) {
  const { data } = await api.patch(`/tickets/${id}/assign/`, {
    assigned_agent: agentId,
  });
  return data;
}
```

### 3.2 `DetailTicket.jsx`

**Decisión de UX:** se descartó la primera versión (asignar al instante con `onChange`) porque rompía la consistencia con el resto del formulario. Versión final: el selector de agente vive **dentro** de "Gestionar ticket" y se guarda junto con estado/prioridad/categoría en un solo click de "Guardar cambios".

```jsx
const canAssign = user?.role === "admin";

// En loadAll(), si es admin:
if (canAssign) {
  const dataAgents = await listAgents();
  setAgents(dataAgents);
  manageForm.setValue("assigned_agent", dataTicket.assigned_agent ?? "");
}

// Submit combinado: guarda gestión + asignación en un solo paso
const onManageSubmit = async (data) => {
  try {
    const updated = await updateTicket(id, {
      status: data.status,
      priority: data.priority,
      category: data.category || null,
    });

    let finalTicket = updated;
    if (canAssign) {
      finalTicket = await assignTicket(id, data.assigned_agent || null);
    }

    setTicket({ ...finalTicket, suggestion_ai: ticket.suggestion_ai });
  } catch {
    setError("No se pudieron guardar los cambios. Intenta de nuevo.");
  }
};
```

```jsx
{/* Dentro del <form> de "Gestionar ticket", después de Categoría */}
{canAssign && (
  <div className="field">
    <label>Agente asignado</label>
    <select {...manageForm.register("assigned_agent")}>
      <option value="">Sin asignar</option>
      {agents.map((a) => (
        <option key={a.id} value={a.id}>{a.username}</option>
      ))}
    </select>
  </div>
)}
```

---

## 4. Bugs encontrados y corregidos

| # | Bug | Causa | Corrección |
|---|---|---|---|
| 1 | El endpoint `/assign/` rompía con `TypeError` | `permission_classes=['PermissionAssignTicket']` — la clase estaba entre comillas (string), no era la clase real | Se quitaron las comillas: `permission_classes=[PermissionAssignTicket]` |
| 2 | Los badges de estado/prioridad/categoría dejaban de actualizarse tras "Guardar cambios" (sin refrescar la página) | Al elegir "Sin asignar", se mandaba `agent_id = null`; el backend intentaba `User.objects.get(id=None, ...)`, fallaba con `DoesNotExist` (HTTP 400), y esa excepción cortaba el `await` en el frontend antes de llegar a `setTicket(...)` | Se agregó un caso explícito en `assign()`: si `agent_id` es vacío/null, se trata como "desasignar" válido, no como error |

**Lección para el futuro:** cuando se combinan dos llamadas a la API en un solo submit (`updateTicket` + `assignTicket`), un error en la segunda llamada puede tragarse silenciosamente el resultado exitoso de la primera si no hay `try/catch`. Por eso se agregó manejo de error explícito en `onManageSubmit`.

---

## 5. Pendientes / próximos pasos

- [ ] Actualizar el **README** del proyecto con la sección de asignación de tickets (texto sugerido más abajo)
- [ ] Actualizar el documento de **arquitectura** general
- [ ] (Opcional, no implementado) Filtro "sin asignar" en `ListTickets.jsx`, siguiendo el mismo patrón que el filtro por `status` ya existente
- [ ] Confirmar prueba end-to-end completa (crear ticket → admin asigna → agente lo ve en su lista)

### Texto sugerido para el README

> **Asignación de tickets:** los tickets se crean sin agente asignado. Solo el rol `admin` puede asignar un ticket a un agente específico, desde el formulario de gestión del ticket. Los agentes no pueden auto-asignarse tickets ni ver tickets que no les fueron asignados.
