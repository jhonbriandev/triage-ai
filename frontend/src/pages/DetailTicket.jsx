import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { getTicket, updateTicket } from "../services/tickets";
import { toListCommentaries, createCommentary } from "../services/commentaries";
import { getActualRole } from "../services/auth";
import { toListCategories } from "../services/categories";

export default function DetailTicket() {
  // useParams lee el ":id" que viene en la URL, ej. /tickets/7 → id = "7"
  const { id } = useParams();
  const role = getActualRole();
  const [ticket, setTicket] = useState(null); // null = "todavía no llegó"
  const [commentaries, setCommentaries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const canManage = role === "agent" || role === "admin";
  const {
    register,
    handleSubmit,
    reset, // función que limpia el formulario después de comentar
    setValue,
    formState: { errors },
  } = useForm();
  const formApply = useForm();

  // --------------------------------------------------------
  // BLOQUE: cargar el ticket Y sus comentarios juntos
  // --------------------------------------------------------
  // Usamos Promise.all para pedir ambas cosas EN PARALELO en vez de
  // una tras otra (ticket primero, comentarios después). Es como pedir
  // dos platos al mismo mesero al mismo tiempo, en vez de esperar a que
  // te traiga el primero para recién pedir el segundo: ambas peticiones
  // viajan a la vez, y solo esperamos el tiempo del más lento de los dos.
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
        if (dataTicket.suggestion_ai) {
          const coincidence = cats.find(
            (c) =>
              c.name.toLowerCase() ===
              dataTicket.suggestion_ai.suggestion_category.toLowerCase(),
          );
          formApply.setValue("category", coincidence?.id ?? "");
          formApply.setValue(
            "priority",
            dataTicket.suggestion_ai.suggestion_priority,
          );
        }
      }
    } catch {
      setError("No se pudo cargar este ticket (¿existe y es tuyo?).");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
    // Este comentario de eslint desactiva la regla que pediría agregar
    // "loadAll" al arreglo de dependencias. No lo hacemos a propósito:
    // "loadAll" se vuelve a crear en cada render (es una función nueva
    // cada vez), así que si la pusiéramos ahí, el efecto se ejecutaría
    // en un bucle infinito. Lo único que realmente queremos "vigilar"
    // es el "id": si cambia (el usuario navega a otro ticket), ahí sí
    // queremos recargar todo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // --------------------------------------------------------
  // BLOQUE: enviar un nuevo comentario
  // --------------------------------------------------------
  const onSubmitCommentary = async (data) => {
    // data.text: "text" es el nombre EXACTO del campo en el modelo
    // Commentary y en su serializer. Al usar el mismo nombre en el
    // formulario, podemos mandarlo directo al backend sin tener que
    // "traducir" nombres (ver explicación detallada más abajo).
    await createCommentary({ ticket: id, text: data.text });
    reset(); // vacía el textarea después de comentar
    // Volvemos a pedir la lista completa de comentarios para que el
    // nuevo aparezca en pantalla (más simple que insertarlo a mano
    // en el array local, aunque un poco menos eficiente).
    const newCommentaries = await toListCommentaries(id);
    setCommentaries(newCommentaries);
  };

  if (loading) return <p>Cargando...</p>;
  if (error) return <p className="error">{error}</p>;
  // --------------------------------------------------------
  // BLOQUE: Gestionar Sugerencias
  // --------------------------------------------------------
  const useSuggestionAnswer = () => {
    setValue("text", ticket.suggestion_ai.suggestion_answer);
  };

  const applySuggestion = async (data) => {
    const loadingUpdate = await updateTicket(id, {
      category: data.category || null,
      priority: data.priority,
    });
    setTicket({ ...loadingUpdate, suggestion_ai: ticket.suggestion_ai });
  };

  return (
    <div className="page-detail">
      <Link to="/tickets">&larr; Volver a mis tickets</Link>

      <h1>{ticket.title}</h1>

      <div className="labels">
        <span className="label">{ticket.status_display}</span>
        <span className="label">{ticket.priority_display}</span>
        <span className="label">{ticket.category_name}</span>
      </div>
      <p>{ticket.description}</p>
      <p className="meta">
        Creado por {ticket.customer_username} ·{" "}
        {new Date(ticket.created_at).toLocaleString()}
      </p>

      {/* ---------------------------------------------------
          Bloque condicional: la sugerencia de la IA
          ticket.suggestion_ai viene del get_suggestion_ai() que
          arreglamos antes. Si es null (aún no hay sugerencia o
          falló la IA), este bloque completo NO se renderiza.
          --------------------------------------------------- */}
      {canManage && ticket.suggestion_ai && (
        <div className="card-ai">
          <h2>Sugerencia de la IA(solo visible para agentes/admin)</h2>
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
          <button type="button" onClick={useSuggestionAnswer}>
            Usar esta respuesta
          </button>

          <form
            onSubmit={formApply.handleSubmit(applySuggestion)}
            className="form-apply"
          >
            <div className="field">
              <label>Categoría a aplicar</label>
              <select {...formApply.register("category")}>
                <option value="">Sin categoría</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Prioridad a aplicar</label>
              <select {...formApply.register("priority")}>
                <option value="baja">Baja</option>
                <option value="media">Media</option>
                <option value="alta">Alta</option>
                <option value="urgente">Urgente</option>
              </select>
            </div>
            <button type="submit">Aplicar al ticket</button>
          </form>
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

      {/* ---------------------------------------------------
          Formulario para comentar
          --------------------------------------------------- */}
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
