import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import { login as loginService } from "../services/auth";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  // react-hook-form nos da 3 herramientas:
  // - register: "conecta" cada input con las reglas de validación
  // - handleSubmit: envuelve nuestro onSubmit, y solo lo ejecuta si todo es válido
  // - errors: objeto con los mensajes de error de cada campo
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  const [errorServidor, setErrorServidor] = useState(""); // error que viene del backend (no de validación de formulario)
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const onSubmit = async (data) => {
    setErrorServidor(""); // limpiamos error previo antes de intentar de nuevo
    try {
      await loginService(data.username, data.password); // guarda los tokens si todo sale bien
      refreshUser(); // avisa al Context: "ya hay usuario logueado"
      navigate("/tickets"); // redirige a la lista de tickets
    } catch (error) {
      // Aquí NO diferenciamos si fue usuario incorrecto, contraseña incorrecta,
      // o el servidor caído: mostramos un mensaje genérico por seguridad
      // (no le decimos al atacante "el usuario existe pero la contraseña está mal").
      setErrorServidor("Usuario o contraseña incorrectos.");
    }
  };

  return (
    <div className="page-auth">
      <form onSubmit={handleSubmit(onSubmit)}>
        <h1>Iniciar sesión</h1>

        <div className="field">
          <label htmlFor="username">Usuario</label>
          <input
            id="username"
            // register("username", {...}) conecta este input al formulario
            // y aplica la regla: "es obligatorio, con este mensaje si falla"
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
            })}
          />
          {errors.password && (
            <span className="error">{errors.password.message}</span>
          )}
        </div>

        {errorServidor && <p className="error">{errorServidor}</p>}

        <button type="submit">Entrar</button>
        <p>
          ¿No tienes cuenta? <Link to="/register">Regístrate</Link>
        </p>
      </form>
    </div>
  );
}
