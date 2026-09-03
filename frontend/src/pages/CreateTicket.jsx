import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { createTicket } from "../services/tickets";
import { toListCategories } from "../services/categories";

export default function CreateTicket() {
  // --------------------------------------------------------
  // BLOQUE 1: react-hook-form
  // --------------------------------------------------------
  // register: "conecta" cada <input> con el sistema de validación
  //           de react-hook-form. El string que le pasas (ej. "title")
  //           es la LLAVE con la que luego vas a encontrar tanto el
  //           valor escrito por el usuario como su posible error.
  // handleSubmit: envuelve tu función onSubmit; se encarga de:
  //           1) correr las validaciones primero,
  //           2) si todo está bien, recién ahí llamar a tu función,
  //           3) si algo falla, NO llama a tu función y llena "errors".
  // errors: objeto donde viven los mensajes de error, uno por cada
  //           campo que falló su validación.
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  // --------------------------------------------------------
  // BLOQUE 2: estados locales del componente
  // --------------------------------------------------------
  // categories: lista de categorías que se muestran en el <select>.
  //             Empieza vacía porque aún no llegó la respuesta del backend.
  const [categories, setCategories] = useState([]);

  // errorServidor: mensaje de error que NO viene de una validación de
  //             formulario (esas ya las maneja "errors"), sino de un
  //             fallo real al hablar con el backend (ej. el servidor
  //             cayó, el token expiró, etc.). Por eso es un estado
  //             separado: son dos tipos de error con causas distintas.
  const [errorServidor, setErrorServidor] = useState("");
  // Utilizado para activar o desactivar el boton mientras se crea un ticket
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  // --------------------------------------------------------
  // BLOQUE 3: cargar categorías al montar el componente
  // --------------------------------------------------------
  // Se ejecuta UNA sola vez (arreglo de dependencias vacío: [])
  // apenas el componente aparece en pantalla. Necesitamos las
  // categorías ANTES de que el usuario intente elegir una en el <select>.
  useEffect(() => {
    toListCategories().then(setCategories);
  }, []);

  // --------------------------------------------------------
  // BLOQUE 4: qué pasa cuando el usuario envía el formulario
  // --------------------------------------------------------
  // "datos" ya viene validado por react-hook-form (si llegamos aquí,
  // es porque title, description y category pasaron sus reglas).
  const onSubmit = async (datos) => {
    setErrorServidor(""); // limpiamos cualquier error previo antes de reintentar
    setCreating(true); // activamos el aviso ANTES de mandar la petición
    try {
      const ticket = await createTicket(datos);
      // Si el ticket se creó bien, navegamos directo a su detalle.
      // Usamos ticket.id porque el backend nos devuelve el ticket
      // recién creado, incluyendo el id que Django le asignó.
      navigate(`/tickets/${ticket.id}`);
    } catch (error) {
      // Aquí NO mostramos error.message crudo del backend (podría ser
      // técnico o en inglés); mostramos un mensaje amigable en español.
      setErrorServidor(
        "No se pudo crear el ticket. Revisa los datos e intenta de nuevo.",
      );
    } finally {
      setCreating(false); // se desactiva pase lo que pase, incluso si hubo error
    }
  };

  return (
    <div className="page-form">
      <Link to="/tickets" className="back-link">
        &larr; Volver a mis tickets
      </Link>
      <form onSubmit={handleSubmit(onSubmit)}>
        <h1>Nuevo ticket</h1>

        {/* ---------------------------------------------------
            CAMPO: title
            --------------------------------------------------- */}
        <div className="field">
          <label htmlFor="title">Título</label>
          <input
            id="title"
            {...register("title", {
              required: "El título es obligatorio",
              maxLength: { value: 200, message: "Máximo 200 caracteres" },
            })}
          />
          {errors.title && (
            <span className="error">{errors.title.message}</span>
          )}
        </div>

        {/* ---------------------------------------------------
            CAMPO: description
            --------------------------------------------------- */}
        <div className="field">
          <label htmlFor="description">Descripción</label>
          <textarea
            id="description"
            rows={5}
            {...register("description", {
              required: "Describe el problema con un poco más de detalle",
            })}
          />
          {errors.description && (
            <span className="error">{errors.description.message}</span>
          )}
        </div>

        {errorServidor && <p className="error">{errorServidor}</p>}

        {/*Se entiende que el usestate inicia a creating como false
          Posteriormente en la parte de arriba en el await, se vuelve true al hacer la peticion
          de creacion de ticket, y al final si falla o es exitoso, volvera a false
          Eso en UI se interpreta asi:
          El boton desactivado es cuando creating es True
          y mostrara el aviso "creando"
          mientras que cuando es false, como al inicio
          mostrara "crear ticket" */}
        <button disabled={creating}>
          {creating
            ? "Creando ticket, esto puede tardar unos segundos..."
            : "Crear ticket"}{" "}
        </button>
      </form>
    </div>
  );
}
