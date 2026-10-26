import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ErrorApi } from "../api/cliente";
import { useSesion } from "../Sesion";
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
    <main className="grid min-h-full lg:grid-cols-2">
      <section className="hidden flex-col justify-center gap-6 bg-brand-section p-16 lg:flex" aria-hidden="true">
        <span className="grid size-12 place-items-center rounded-xl bg-brand-solid text-xl font-bold text-white">An</span>
        <p className="max-w-[16ch] text-display-md font-semibold text-white">Turnos claros para todo el equipo.</p>
        <ul className="flex flex-col gap-3 text-lg text-brand-200">
          <li>✓ El sistema arma el cuadro respetando descansos y horas legales.</li>
          <li>✓ Ves al instante qué falta cubrir y qué revisar.</li>
          <li>✓ Cada cambio queda registrado con su motivo.</li>
        </ul>
      </section>
      <div className="grid min-h-full place-items-center bg-secondary p-4">
      <div className="flex w-full max-w-md flex-col gap-5 rounded-2xl bg-primary p-8 shadow-lg ring-1 ring-secondary ring-inset">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-lg bg-brand-solid font-bold text-white" aria-hidden="true">An</span>
          <div>
            <h1 className="text-display-xs font-semibold text-primary">Ingresar</h1>
            <p className="text-md text-tertiary">Usa el correo que te dio coordinación.</p>
          </div>
        </div>
        {error && <Alert color="error">{error}</Alert>}
        <form className="flex flex-col gap-4" onSubmit={enviar}>
          <Input value={String(correo)} label="Correo" type="email" autoComplete="username" isRequired autoFocus onChange={(x) => setCorreo(x)} />
          <Input value={String(clave)} label="Contraseña" type="password" autoComplete="current-password" isRequired onChange={(x) => setClave(x)} />
          <Button color="primary" size="md" type="submit" isDisabled={enviando || !correo || !clave}>{enviando ? "Ingresando…" : "Ingresar"}</Button>
        </form>
        <p className="text-sm text-tertiary">¿Olvidaste la contraseña? Pídele a quien administra la clínica que la restablezca.</p>
      </div>
      </div>
    </main>
  );
}
