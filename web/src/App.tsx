import { Navigate, Outlet, Route, Routes } from "react-router";
import { useSesion } from "./Sesion";
import { CambiarClave } from "./pantallas/CambiarClave";
import { Cuadro } from "./pantallas/Cuadro";
import { Disposicion } from "./pantallas/Disposicion";
import { Ingresar } from "./pantallas/Ingresar";

/** Exige sesión; con `debe_cambiar` solo deja ver «Cambiar contraseña». */
function Protegida() {
  const { usuario } = useSesion();
  if (usuario === undefined) return <p className="solo-lectores" role="status">Cargando…</p>;
  if (usuario === null) return <Navigate to="/ingresar" replace />;
  if (usuario.debe_cambiar) return <Navigate to="/cambiar-clave" replace />;
  return <Outlet />;
}

function Inicio() {
  const { usuario } = useSesion();
  if (usuario === undefined) return null;
  return <Navigate to={usuario ? "/areas" : "/ingresar"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Inicio />} />
      <Route path="/ingresar" element={<Ingresar />} />
      <Route path="/cambiar-clave" element={<CambiarClave />} />
      <Route element={<Protegida />}>
        <Route path="/areas" element={<Disposicion />} />
        <Route path="/areas/:area" element={<Disposicion />}>
          <Route index element={<Navigate to="cuadro" replace />} />
          <Route path="cuadro" element={<Cuadro />} />
          <Route path="cuadro/:periodo" element={<Cuadro />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
