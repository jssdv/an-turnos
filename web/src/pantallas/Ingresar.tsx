import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ErrorApi } from "../api/cliente";
import { useSesion } from "../Sesion";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Alert } from "@/components/application/alerts/alert";
import { AnLogo } from "@/components/foundations/logo/an-logo";

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
    <main className="grid min-h-full place-items-center p-4">
      <div className="tarjeta flex w-full max-w-md flex-col gap-5 p-6 sm:p-8">
        <AnLogo area="Turnos claros para todo el equipo" />
        <div>
          <h1 className="text-display-xs font-semibold text-primary">Ingresar</h1>
          <p className="text-md text-tertiary">Usa el correo que te dio coordinación.</p>
        </div>
        {error && <Alert color="error">{error}</Alert>}
        <form className="flex flex-col gap-4" onSubmit={enviar}>
          <Input value={String(correo)} label="Correo" type="email" autoComplete="username" isRequired autoFocus onChange={(x) => setCorreo(x)} />
          <Input value={String(clave)} label="Contraseña" type="password" autoComplete="current-password" isRequired onChange={(x) => setClave(x)} />
          <Button color="primary" size="sm" className="h-11" type="submit" isDisabled={enviando || !correo || !clave}>{enviando ? "Ingresando…" : "Ingresar"}</Button>
        </form>
        <p className="text-sm text-tertiary">¿Olvidaste la contraseña? Pídele a quien administra la clínica que la restablezca.</p>
      </div>
    </main>
  );
}
