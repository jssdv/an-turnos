import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { alVencerSesion, ErrorApi, pedir } from "./api/cliente";
import { borrador } from "./api/cambios";
import type { Usuario } from "./api/tipos";

interface Valor {
  /** `undefined` mientras se consulta; `null` sin sesión. */
  usuario: Usuario | null | undefined;
  entrar: (correo: string, clave: string) => Promise<Usuario>;
  salir: () => Promise<void>;
  recargar: () => Promise<Usuario | null>;
}
const Ctx = createContext<Valor | null>(null);

export function useSesion() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSesion fuera de <Sesion>");
  return v;
}

export function Sesion({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null | undefined>(undefined);
  const ir = useNavigate();

  const recargar = useCallback(async () => {
    try {
      const u = await pedir<Usuario>("GET", "/api/auth/yo", { sinAviso401: true });
      setUsuario(u);
      return u;
    } catch (x) {
      if (!(x instanceof ErrorApi) || x.estado !== 401) throw x;
      setUsuario(null);
      return null;
    }
  }, []);

  useEffect(() => {
    recargar().catch(() => setUsuario(null));
  }, [recargar]);

  useEffect(() => {
    alVencerSesion(() => { setUsuario(null); ir("/ingresar", { replace: true }); });
    return () => alVencerSesion(null);
  }, [ir]);

  const valor = useMemo<Valor>(() => ({
    usuario,
    recargar,
    entrar: async (correo, clave) => {
      const r = await pedir<{ usuario: Usuario }>("POST", "/api/auth/entrar", { cuerpo: { correo, clave }, sinAviso401: true });
      setUsuario(r.usuario);
      return r.usuario;
    },
    salir: async () => {
      await pedir("POST", "/api/auth/salir", { cuerpo: {}, sinAviso401: true }).catch(() => undefined);
      borrador.borrar();
      setUsuario(null);
      ir("/ingresar", { replace: true });
    },
  }), [usuario, recargar, ir]);

  return <Ctx value={valor}>{children}</Ctx>;
}

