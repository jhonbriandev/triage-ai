import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import {
  getTicket,
  updateTicket,
  listAgents,
  assignTicket,
} from "../services/tickets";
import { toListCommentaries, createCommentary } from "../services/commentaries";
import { toListCategories } from "../services/categories";
import { useAuth } from "../context/AuthContext";

export default function DetailTicket() {
  const { id } = useParams();
  const { user } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [commentaries, setCommentaries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [agents, setAgents] = useState([]);
  const canManage = user?.role === "agent" || user?.role === "admin";
  // La asignación es SOLO para admin (distinto de "canManage", que
  // también incluye al agente). Un agente puede gestionar su ticket
  // pero no reasignarlo a otro compañero.
  const canAssign = user?.role === "admin";

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm();

  // Formulario de gestión (estado/prioridad/categoría): SIEMPRE disponible
  // para agente/admin, exista o no una sugerencia de IA.
  const manageForm = useForm();

  const loadAll = async () => {
    try {
      const [dataTicket, dataCommentaries] = await Promise.all([
        getTicket(id),
        toListCommentaries(id),
      ]);
      setTicket(dataTicket);
      setCommentaries(dataCommentaries);

      if (canManage) {
        const cats = await toListCategories();
        setCategories(cats);
        // Precarga con los valores ACTUALES del ticket, no con la sugerencia:
        // la sugerencia (si existe) es solo un atajo opcional, no la fuente
        // principal de estos valores.
        manageForm.setValue("status", dataTicket.status);
        manageForm.setValue("priority", dataTicket.priority);
        manageForm.setValue("category", dataTicket.category ?? "");
      }
      // Solo el admin necesita la lista de agentes y el valor actual
      // precargado en el formulario (los demás roles ni ven este campo).
      if (canAssign) {
        const dataAgents = await listAgents();
        setAgents(dataAgents);
        // Precargamos con el agente YA asignado (o "" si no hay ninguno),
        // mismo patrón que ya usas para status/priority/category.
        manageForm.setValue("assigned_agent", dataTicket.assigned_agent ?? "");
      }
    } catch {
      setError("No se pudo cargar este ticket (¿existe y es tuyo?).");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const onSubmitCommentary = async (data) => {
    await createCommentary({ ticket: id, text: data.text });
    reset();
    setCommentaries(await toListCommentaries(id));
  };

  const useSuggestionAnswer = () => {
    setValue("text", ticket.suggestion_ai.suggestion_answer);
  };

  // Copia los valores SUGERIDOS al formulario de gestión, sin guardarlos
  // todavía — el agente los revisa (y puede corregirlos) antes de enviar.
  const useSuggestedValues = () => {
    const suggestion = ticket.suggestion_ai;
    const match = categories.find(
      (c) =>
        c.name.toLowerCase() === suggestion.suggestion_category.toLowerCase(),
    );
    manageForm.setValue("category", match?.id ?? "");
    manageForm.setValue("priority", suggestion.suggestion_priority);
  };

  const onManageSubmit = async (data) => {
    try {
      const updated = await updateTicket(id, {
        status: data.status,
        priority: data.priority,
        category: data.category || null,
      });

      // El agente se guarda con una llamada aparte, porque el backend
      // lo valida en un endpoint dedicado (/assign/), distinto del PATCH
      // general de tickets — pero desde la UI se siente como un solo
      // "Guardar cambios", ya que ambas llamadas ocurren en este mismo
      // submit, antes de que el usuario vea cualquier resultado.
      let finalTicket = updated;
      if (canAssign) {
        finalTicket = await assignTicket(id, data.assigned_agent || null);
      }

      setTicket({ ...finalTicket, suggestion_ai: ticket.suggestion_ai });
    } catch {
      // Antes, si algo fallaba a mitad de camino, no pasaba NADA visible
      // en pantalla -- ahora al menos el usuario se entera de que algo
      // salió mal, en vez de pensar que "no se guardó" sin explicación.
      setError("No se pudieron guardar los cambios. Intenta de nuevo.");
    }
  };

  // Se ejecuta apenas cambia el <select>, sin esperar a un botón
  // "Guardar" aparte -- así la asignación se siente inmediata.
  const handleAssign = async (e) => {
    const agentId = e.target.value || null; // "" -> null (sin asignar)
    const updated = await assignTicket(id, agentId);
    // Conservamos suggestion_ai porque el PATCH de /assign/ no lo devuelve
    // (mismo patrón que ya usas en onManageSubmit).
    setTicket({ ...updated, suggestion_ai: ticket.suggestion_ai });
  };

  if (loading) return <p>Cargando...</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <div className="page-detail">
      <Link to="/tickets" className="back-link">
        &larr; Volver a mis tickets
      </Link>

      <h1>{ticket.title}</h1>
      <div className="labels">
        <span className="label">{ticket.status_display}</span>
        <span className="label">{ticket.priority_display}</span>
        <span className="label">
          {ticket.category_name ?? "Sin categorizar"}
        </span>
      </div>
      <p>{ticket.description}</p>
      <p className="meta">
        Creado por {ticket.customer_username} ·{" "}
        {new Date(ticket.created_at).toLocaleString()}
      </p>

      {/* Gestión del ticket: SIEMPRE visible para agente/admin,
          sin importar si hay o no sugerencia de IA. Esto es lo que
          faltaba: antes, esto solo existía DENTRO del bloque de la
          sugerencia, así que un ticket sin sugerencia (falló la IA,
          o Gemini tardó) no tenía forma de gestionarse desde aquí. */}
      {canManage && (
        <div className="card-manage">
          <h2>Gestionar ticket</h2>
          <form
            onSubmit={manageForm.handleSubmit(onManageSubmit)}
            className="form-manage"
          >
            <div className="field">
              <label>Estado</label>
              <select {...manageForm.register("status")}>
                <option value="abierto">Abierto</option>
                <option value="en_progreso">En progreso</option>
                <option value="resuelto">Resuelto</option>
                <option value="cerrado">Cerrado</option>
              </select>
            </div>
            <div className="field">
              <label>Prioridad</label>
              <select {...manageForm.register("priority")}>
                <option value="baja">Baja</option>
                <option value="media">Media</option>
                <option value="alta">Alta</option>
                <option value="urgente">Urgente</option>
              </select>
            </div>
            <div className="field">
              <label>Categoría</label>
              <select {...manageForm.register("category")}>
                <option value="">Sin categoría</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            {canAssign && (
              <div className="field">
                <label>Agente asignado</label>
                {/* {...manageForm.register(...)} conecta este <select> al mismo
        formulario que status/priority/category -- ya no dispara nada
        por sí solo, solo guarda su valor hasta que se haga submit. */}
                <select {...manageForm.register("assigned_agent")}>
                  <option value="">Sin asignar</option>
                  {agents.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.username}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <button type="submit">Guardar cambios</button>
          </form>
        </div>
      )}

      {/* La sugerencia de IA: ahora es un AYUDANTE informativo, no la
          única puerta de entrada para gestionar el ticket. */}
      {canManage && ticket.suggestion_ai && (
        <div className="card-ai">
          <h2>Sugerencia de la IA</h2>
          <p>
            <strong>Categoría sugerida:</strong>{" "}
            {ticket.suggestion_ai.suggestion_category}
          </p>
          <p>
            <strong>Prioridad sugerida:</strong>{" "}
            {ticket.suggestion_ai.suggestion_priority}
          </p>
          <p>
            <strong>Resumen:</strong> {ticket.suggestion_ai.generated_summary}
          </p>
          <p>
            <strong>Respuesta sugerida:</strong>{" "}
            {ticket.suggestion_ai.suggestion_answer}
          </p>
          <div className="ai-actions">
            <button type="button" onClick={useSuggestedValues}>
              Usar valores sugeridos en "Gestionar ticket"
            </button>
            <button type="button" onClick={useSuggestionAnswer}>
              Usar esta respuesta como comentario
            </button>
          </div>
        </div>
      )}

      <h2>Comentarios</h2>
      <ul className="list-commentaries">
        {commentaries.length === 0 && <p>Todavía no hay comentarios.</p>}
        {commentaries.map((c) => (
          <li key={c.id}>
            <strong>{c.author_username}:</strong> {c.text}
          </li>
        ))}
      </ul>

      <form
        onSubmit={handleSubmit(onSubmitCommentary)}
        className="form-commentary"
      >
        <textarea
          rows={3}
          placeholder="Escribe un comentario..."
          {...register("text", { required: "Escribe algo antes de enviar" })}
        />
        {errors.text && <span className="error">{errors.text.message}</span>}
        <button type="submit">Comentar</button>
      </form>
    </div>
  );
}
