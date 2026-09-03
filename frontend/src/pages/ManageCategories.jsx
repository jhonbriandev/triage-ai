import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import {
  toListCategories,
  createCategory,
  deleteCategory,
} from "../services/categories";

export default function ManageCategories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorServer, setErrorServer] = useState("");
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm();

  const load = () => {
    toListCategories()
      .then(setCategories)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const onSubmit = async (data) => {
    setErrorServer("");
    try {
      await createCategory(data.name);
      reset();
      load();
    } catch (error) {
      setErrorServer("No se pudo crear (¿ya existe una con ese nombre?).");
    }
  };

  const deleteOptionsCategory = async (id) => {
    try {
      await deleteCategory(id);
      load();
    } catch (error) {
      alert(
        "No se pudo borrar: probablemente hay tickets usando esta categoría.",
      );
    }
  };

  if (loading) return <p>Cargando...</p>;

  return (
    <div className="page-form">
      <Link to="/tickets" className="back-link">
        &larr; Volver a mis tickets
      </Link>
      <h1>Gestionar categorías</h1>
      <p className="help">
        Solo un administrador puede crear, editar o borrar categorías.
      </p>

      <ul className="list-categories">
        {categories.map((c) => (
          <li key={c.id}>
            {c.name}
            <button
              className="button-danger"
              onClick={() => deleteOptionsCategory(c.id)}
            >
              Borrar
            </button>
          </li>
        ))}
      </ul>

      <form onSubmit={handleSubmit(onSubmit)} className="form-inline">
        <input
          placeholder="Nombre de la nueva categoría"
          {...register("name", { required: true })}
        />
        <button type="submit">Agregar</button>
      </form>
      {errors.name && <span className="error">El nombre es obligatorio</span>}
      {errorServer && <p className="error">{errorServer}</p>}
    </div>
  );
}
