import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ErrorApi, pedir } from "../api/cliente";
import { useSesion } from "../Sesion";
import e from "./Acceso.module.css";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Alert } from "@/components/application/alerts/alert";

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
        {error && <Alert color="error">{error}</Alert>}
        <form className={e.form} onSubmit={enviar}>
          <Input value={String(actual)} label="Contraseña actual" hint={usuario.debe_cambiar ? "La temporal que te dio quien administra." : undefined} type="password" autoComplete="current-password" isRequired autoFocus onChange={(x) => setActual(x)} />
          <Input value={String(nueva)} label="Contraseña nueva" hint="Al menos 10 caracteres. Una frase corta es fácil de recordar." type="password" autoComplete="new-password" isRequired onChange={(x) => setNueva(x)} />
          <Input value={String(repetida)} hint={distinta} isInvalid={!!(distinta)} label="Repite la nueva" type="password" autoComplete="new-password" isRequired onChange={(x) => setRepetida(x)} />
          <Button color="primary" size="sm" type="submit" isDisabled={enviando || !actual || !nueva || nueva !== repetida}>{enviando ? "Guardando…" : "Guardar contraseña"}</Button>
          <Button color="link-color" size="sm" onPress={salir}>Salir</Button>
        </form>
      </div>
    </main>
  );
}
