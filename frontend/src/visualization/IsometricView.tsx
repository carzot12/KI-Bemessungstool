import type { VisualizationModel } from "../types";
import { sideDowelCount, toDrawingGeometry } from "./geometry";

export default function IsometricView({ model, dimensions }: { model: VisualizationModel; dimensions: boolean }) {
  const geometry = toDrawingGeometry(model);
  const scale = 1.82;
  const seam = 450;
  const plateLeft = seam - geometry.plate.lengthMm / 2 * scale;
  const plateRight = seam + geometry.plate.lengthMm / 2 * scale;
  const faceTop = 102;
  const faceHeight = 245;
  const radius = Math.max(4, geometry.dowelDiameterMm * 0.3);
  const dowels = [...geometry.dowelPositionsLeftMm, ...geometry.dowelPositionsRightMm].map((point) =>
    <circle key={`${point.x}-${point.y}`} cx={seam + point.x * scale}
      cy={faceTop + point.y * faceHeight / geometry.heightMm} r={radius} className="dowel" />,
  );
  return <svg className="engineering-svg" viewBox="0 28 950 390" role="img" aria-label="Technische isometrische Ansicht des Zuglaschenstoßes">
    <polygon points="38,102 450,102 520,62 108,62" className="iso-top" />
    <polygon points="450,102 862,102 932,62 520,62" className="iso-top" />
    <rect x="38" y={faceTop} width="412" height={faceHeight} className="iso-face" />
    <rect x="450" y={faceTop} width="412" height={faceHeight} className="iso-face" />
    <line x1={seam} y1="95" x2={seam} y2={faceTop + faceHeight + 7} className="joint" />
    {geometry.plate.positionsMm.map((position, index) => {
      const ratio = position / geometry.widthMm;
      const dx = 70 * ratio;
      const dy = -40 * ratio;
      const top = faceTop + geometry.plate.topMm * faceHeight / geometry.heightMm;
      const bottom = faceTop + geometry.plate.bottomMm * faceHeight / geometry.heightMm;
      return <g key={position}>
        <polygon
          points={`${plateLeft + dx},${top + dy} ${plateRight + dx},${top + dy} ${plateRight + dx},${bottom + dy} ${plateLeft + dx},${bottom + dy}`}
          className="iso-hidden-plate"
        />
        <line x1={plateLeft + dx} y1={faceTop + dy} x2={plateRight + dx} y2={faceTop + dy} className="slot-plate" />
        <text x={plateRight + dx + 8} y={top + dy + 14} className="plate-index">B{index + 1}</text>
      </g>;
    })}
    {dowels}
    <text x="450" y="370" textAnchor="middle" className="svg-label">
      {geometry.plateCount} innenliegende Stahlblech{geometry.plateCount === 1 ? "" : "e"} · {geometry.rowsParallel} × {geometry.rowsPerpendicular} · {sideDowelCount(geometry)} je Seite
    </text>
    {dimensions && <text x="450" y="400" textAnchor="middle">Ft,Ed = {geometry.forceEdKn} kN · b = {geometry.widthMm} · h = {geometry.heightMm} · Ø{geometry.dowelDiameterMm} mm</text>}
  </svg>;
}
