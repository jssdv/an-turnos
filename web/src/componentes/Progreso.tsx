import e from "./Progreso.module.css";

interface Props {
  valor: number; // 0..1
  etiqueta: string;
  detalle?: string;
}

export function Progreso({ valor, etiqueta, detalle }: Props) {
  const pct = Math.round(Math.max(0, Math.min(1, valor)) * 100);
  return (
    <div className={e.progreso}>
      <div className={e.fila}>
        <span>{etiqueta}</span>
        <span>{pct} %</span>
      </div>
      <div className={e.pista} role="progressbar" aria-label={etiqueta} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct}>
        <div className={e.barra} data-pct={pct} ref={(n) => { if (n) n.style.width = `${pct}%`; }} />
      </div>
      {detalle && <span className={e.detalle}>{detalle}</span>}
    </div>
  );
}
