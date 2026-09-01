import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { register as registerUser } from "../services/auth";

export default function Register() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();
  const [errorServidor, setErrorServidor] = useState("");
  const navigate = useNavigate();

  const onSubmit = async (data) => {
    setErrorServidor("");
    try {
      // Usando el alias para no confundir con el register del form
      await registerUser(data.username, data.password, data.email);
      navigate("/login");
    } catch (error) {
      const dataError = error.response?.data;
      const firstError = dataError ? Object.values(dataError)[0]?.[0] : null;
      setErrorServidor(firstError || "No se pudo completar el registro.");
    }
  };

  return (
    <div className="page-auth">
      <form onSubmit={handleSubmit(onSubmit)}>
        <h1> Registrate</h1>

        <div className="field">
          <label htmlFor="username">Usuario</label>
          <input
            id="username"
            {...register("username", { required: "El usuario es obligatorio" })}
          />
          {errors.username && (
            <span className="error">{errors.username.message}</span>
          )}
        </div>

        <div className="field">
          <label htmlFor="password">Contraseña</label>
          <input
            id="password"
            type="password"
            {...register("password", {
              required: "La contraseña es obligatoria",
              minLength: { value: 8, message: "Mínimo 8 caracteres" },
            })}
          />
          {errors.password && (
            <span className="error">{errors.password.message}</span>
          )}
        </div>

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            {...register("email", { required: "El email es obligatorio" })}
          />
          {errors.email && (
            <span className="error">{errors.email.message}</span>
          )}
        </div>

        {errorServidor && <p className="error">{errorServidor}</p>}

        <button type="submit">Registrar</button>
        <p>
          ¿Tienes cuenta? <Link to="/login">Inicia Sesion</Link>
        </p>
      </form>
    </div>
  );
}
