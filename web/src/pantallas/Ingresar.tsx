import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ErrorApi } from "../api/cliente";
import { useSesion } from "../Sesion";
import e from "./Acceso.module.css";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Alert } from "@/components/application/alerts/alert";

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
    <main className={e.dividida}>
      <section className={e.bienvenida} aria-hidden="true">
        <span className={e.logoGrande}>An</span>
        <p className={e.lema}>Turnos claros para todo el equipo.</p>
        <ul className={e.puntos}>
          <li>El sistema arma el cuadro respetando descansos y horas legales.</li>
          <li>Ves al instante qué falta cubrir y qué revisar.</li>
          <li>Cada cambio queda registrado con su motivo.</li>
        </ul>
      </section>
      <div className={e.pagina}>
      <div className={e.panel}>
        <div className={e.marca}>
          <span className={e.logo} aria-hidden="true">An</span>
          <div>
            <h1 className={e.titulo}>Ingresar</h1>
            <p className={e.sub}>Usa el correo que te dio coordinación.</p>
          </div>
        </div>
        {error && <Alert color="error">{error}</Alert>}
        <form className={e.form} onSubmit={enviar}>
          <Input value={String(correo)} label="Correo" type="email" autoComplete="username" isRequired autoFocus onChange={(x) => setCorreo(x)} />
          <Input value={String(clave)} label="Contraseña" type="password" autoComplete="current-password" isRequired onChange={(x) => setClave(x)} />
          <Button color="primary" size="sm" type="submit" isDisabled={enviando || !correo || !clave}>{enviando ? "Ingresando…" : "Ingresar"}</Button>
        </form>
        <p className={e.nota}>¿Olvidaste la contraseña? Pídele a quien administra la clínica que la restablezca.</p>
      </div>
      </div>
    </main>
  );
}
