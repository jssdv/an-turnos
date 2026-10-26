import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import App from "./App";
import { Sesion } from "./Sesion";
import "./tokens.css";
import "./styles/globals.css";

createRoot(document.getElementById("raiz")!).render(
  <StrictMode>
    <BrowserRouter>
      <Sesion>
        <App />
      </Sesion>
    </BrowserRouter>
  </StrictMode>,
);
