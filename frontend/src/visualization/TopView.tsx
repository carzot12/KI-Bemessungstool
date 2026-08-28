import type { ReactNode } from "react";
import type { VisualizationModel } from "../types";
import { layerRects, toDrawingGeometry, validateDrawingGeometry } from "./geometry";

function VerticalDimension({
  x, y1, y2, referenceX, label,
}: { x: number; y1: number; y2: number; referenceX: number; label: ReactNode }) {
  const middle = (y1 + y2) / 2;
  return <g className="dimension-segment">
    <line x1={referenceX} y1={y1} x2={x + 5} y2={y1} className="extension-line" />
    <line x1={referenceX} y1={y2} x2={x + 5} y2={y2} className="extension-line" />
    <line x1={x} y1={y1} x2={x} y2={y2} className="dim-line" />
    <line x1={x - 4} y1={y1 - 3} x2={x + 4} y2={y1 + 3} className="dim-tick" />
    <line x1={x - 4} y1={y2 - 3} x2={x + 4} y2={y2 + 3} className="dim-tick" />
    <text x={x + 12} y={middle} dominantBaseline="middle">{label}</text>
  </g>;
}

export default function TopView({ model, dimensions }: { model: VisualizationModel; dimensions: boolean }) {
  const geometry = toDrawingGeometry(model);
  const errors = validateDrawingGeometry(geometry);
  if (errors.length) return <div className="drawing-error" role="status">Die Zeichnungsgeometrie ist unvollständig.</div>;

  const seam = 465;
  const top = 76;
  const maxBodyHeight = 205;
  const scaleY = Math.min(1, maxBodyHeight / geometry.widthMm);
  const totalHeight = geometry.widthMm * scaleY;
  const plateHalfLengthMm = geometry.plate.lengthMm / 2;
  const metricHalfLengthMm = Math.max(geometry.connectionHalfLengthMm, plateHalfLengthMm);
  const scaleX = Math.min(1.6, 300 / metricHalfLengthMm);
  const timberHalfDrawing = Math.max(metricHalfLengthMm * scaleX, totalHeight * 1.75);
  const woodLeft = seam - timberHalfDrawing;
  const woodRight = seam + timberHalfDrawing;
  const plateLeft = seam - plateHalfLengthMm * scaleX;
  const plateRight = seam + plateHalfLengthMm * scaleX;
  const layers = layerRects(geometry, top, scaleY);
  const plateLayers = layers.filter((layer) => layer.index % 2 === 1);
  const columns = [
    ...geometry.columnPositionsMm.map((position) => seam - position * scaleX),
    ...geometry.columnPositionsMm.map((position) => seam + position * scaleX),
  ].sort((left, right) => left - right);
  // In the top view, both b/ts and the dowel diameter are transverse
  // dimensions. Using the same scale preserves d:b and d:ts exactly.
  const dowelWidth = geometry.dowelDiameterMm * scaleY;
  const bottom = top + totalHeight;
  const sectionX = seam - 30;
  const layerLabel = (index: number) => {
    if (index % 2 === 1) return <>t<tspan baselineShift="sub">s</tspan></>;
    if (index === 0 || index === layers.length - 1) return <>t<tspan baselineShift="sub">1</tspan></>;
    return <>t<tspan baselineShift="sub">2</tspan></>;
  };

  return <svg className="engineering-svg top-view" viewBox="0 15 1080 340" role="img"
    aria-label={`Technische Draufsicht mit ${geometry.plateCount} innenliegenden Stahlblechen und ${columns.length} Dübelachsen`}>
    <defs>
      <marker id="section-arrow-down" markerWidth="8" markerHeight="8" refX="4" refY="6" orient="auto">
        <path d="M0,0 L8,0 L4,8 Z" fill="#25282c" />
      </marker>
      <marker id="section-arrow-up" markerWidth="8" markerHeight="8" refX="4" refY="2" orient="auto">
        <path d="M4,0 L8,8 L0,8 Z" fill="#25282c" />
      </marker>
    </defs>

    <rect x={woodLeft} y={top} width={seam - woodLeft} height={totalHeight}
      className="timber-fill" style={{ strokeWidth: 1.4 }} />
    <rect x={seam} y={top} width={woodRight - seam} height={totalHeight}
      className="timber-fill" style={{ strokeWidth: 1.4 }} />

    {plateLayers.map((layer) => <rect key={layer.index} x={plateLeft} y={layer.x}
      width={plateRight - plateLeft} height={layer.width} className="top-plate"
      style={{ strokeWidth: 1, fillOpacity: 0.78 }} />)}

    {columns.map((column) => <rect key={column} x={column - dowelWidth / 2} y={top - 2}
      width={dowelWidth} height={totalHeight + 4} rx={Math.min(3, dowelWidth / 4)}
      className="dowel" style={{ strokeWidth: 1, fill: "#c5c9cc" }} />)}

    <line x1={seam} y1={top} x2={seam} y2={bottom} className="joint" style={{ strokeWidth: 1.5 }} />

    <g aria-label="Schnittlinie A-A">
      <line x1={sectionX} y1={top - 54} x2={sectionX} y2={top - 14}
        stroke="#34383d" strokeWidth="1" strokeDasharray="6 4" markerEnd="url(#section-arrow-down)" />
      <line x1={sectionX} y1={bottom + 54} x2={sectionX} y2={bottom + 14}
        stroke="#34383d" strokeWidth="1" strokeDasharray="6 4" markerEnd="url(#section-arrow-up)" />
      <text x={sectionX + 14} y={top - 45} className="view-title">A</text>
      <text x={sectionX + 14} y={bottom + 52} className="view-title">A</text>
    </g>

    {dimensions && <g className="dimensions visible">
      {layers.map((layer) => <VerticalDimension key={`layer-${layer.index}`}
        x={875} y1={layer.x} y2={layer.x + layer.width} referenceX={woodRight}
        label={layerLabel(layer.index)} />)}
      <VerticalDimension x={970} y1={top} y2={bottom} referenceX={woodRight}
        label={<>b = {geometry.widthMm} mm</>} />
    </g>}
  </svg>;
}
