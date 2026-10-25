import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ErrorApi } from "../api/cliente";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Campo } from "../componentes/Campo";
import { useSesion } from "../Sesion";
import e from "./Acceso.module.css";

export function Ingresar() {
  const { usuario, entrar } = useSesion();
  const ir = useNavigate();
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to={usuario.debe_cambiar ? "/cambiar-clave" : "/areas"} replace />;

  const enviar = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const u = await entrar(correo.trim(), clave);
      ir(u.debe_cambiar ? "/cambiar-clave" : "/areas", { replace: true });
    } catch (x) {
      setError(x instanceof ErrorApi ? x.message : "No se pudo ingresar");
      setClave("");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main className={e.pagina}>
      <div className={e.panel}>
        <div className={e.marca}>
          <span className={e.logo} aria-hidden="true">An</span>
          <div>
            <h1 className={e.titulo}>Ingresar</h1>
            <p className={e.sub}>Programación de turnos</p>
          </div>
        </div>
        {error && <Aviso nivel="error">{error}</Aviso>}
        <form className={e.form} onSubmit={enviar}>
          <Campo etiqueta="Correo" type="email" autoComplete="username" required autoFocus value={correo} onChange={(x) => setCorreo(x.target.value)} />
          <Campo etiqueta="Contraseña" type="password" autoComplete="current-password" required value={clave} onChange={(x) => setClave(x.target.value)} />
          <Boton type="submit" variante="primario" disabled={enviando || !correo || !clave}>{enviando ? "Ingresando…" : "Ingresar"}</Boton>
        </form>
      </div>
    </main>
  );
}
