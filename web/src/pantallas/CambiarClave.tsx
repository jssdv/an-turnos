import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ErrorApi, pedir } from "../api/cliente";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Campo } from "../componentes/Campo";
import { useSesion } from "../Sesion";
import e from "./Acceso.module.css";

export function CambiarClave() {
  const { usuario, recargar, salir } = useSesion();
  const ir = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario === undefined) return null;
  if (usuario === null) return <Navigate to="/ingresar" replace />;

  const distinta = repetida !== "" && repetida !== nueva ? "Las contraseñas no coinciden" : null;

  const enviar = async (ev: FormEvent) => {
    ev.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await pedir("POST", "/api/auth/cambiar-clave", { cuerpo: { actual, nueva } });
      await recargar();
      ir("/areas", { replace: true });
    } catch (x) {
      setError(x instanceof ErrorApi ? x.message : "No se pudo cambiar la contraseña");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <main className={e.pagina}>
      <div className={e.panel}>
        <div>
          <h1 className={e.titulo}>Cambiar contraseña</h1>
          <p className={e.sub}>
            {usuario.debe_cambiar ? "Tu contraseña es temporal: elige una nueva para continuar." : `Cuenta de ${usuario.correo}.`}
          </p>
        </div>
        {error && <Aviso nivel="error">{error}</Aviso>}
        <form className={e.form} onSubmit={enviar}>
          <Campo etiqueta="Contraseña actual" type="password" autoComplete="current-password" required autoFocus value={actual} onChange={(x) => setActual(x.target.value)} />
          <Campo etiqueta="Contraseña nueva" type="password" autoComplete="new-password" required value={nueva} onChange={(x) => setNueva(x.target.value)} />
          <Campo etiqueta="Repite la nueva" type="password" autoComplete="new-password" required value={repetida} error={distinta} onChange={(x) => setRepetida(x.target.value)} />
          <Boton type="submit" variante="primario" disabled={enviando || !actual || !nueva || nueva !== repetida}>{enviando ? "Guardando…" : "Guardar contraseña"}</Boton>
          <Boton variante="texto" onClick={salir}>Salir</Boton>
        </form>
      </div>
    </main>
  );
}
