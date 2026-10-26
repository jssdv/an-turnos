import { RouterProvider } from "react-aria-components";
import { Navigate, Outlet, Route, Routes, useHref, useNavigate } from "react-router";
import { useSesion } from "./Sesion";
import { CambiarClave } from "./pantallas/CambiarClave";
import { Analiticas } from "./pantallas/Analiticas";
import { Cuadro } from "./pantallas/Cuadro";
import { Disposicion } from "./pantallas/Disposicion";
import { Ingresar } from "./pantallas/Ingresar";
import { Novedades } from "./pantallas/Novedades";
import { Parametros } from "./pantallas/Parametros";
import { Personal } from "./pantallas/Personal";
import { Radiologia } from "./pantallas/Radiologia";
import { Puestos } from "./pantallas/Puestos";
import { Solicitudes } from "./pantallas/Solicitudes";
import { Usuarios } from "./pantallas/Usuarios";

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

/** RouterProvider: los enlaces de React Aria (navegación de Untitled UI) navegan con react-router, sin recargar. */
export default function App() {
  const navigate = useNavigate();
  return (
    <RouterProvider navigate={navigate} useHref={useHref}>
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
          <Route path="solicitudes" element={<Solicitudes />} />
          <Route path="personal" element={<Personal />} />
          <Route path="novedades" element={<Novedades />} />
          <Route path="puestos" element={<Puestos />} />
          <Route path="parametros" element={<Parametros />} />
          <Route path="analiticas" element={<Analiticas />} />
          <Route path="usuarios" element={<Usuarios />} />
          <Route path="radiologia" element={<Navigate to="resumen" replace />} />
          <Route path="radiologia/:seccion" element={<Radiologia />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </RouterProvider>
  );
}
