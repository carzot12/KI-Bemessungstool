import type { ReactNode } from "react";
import type { VisualizationModel } from "../types";
import { toDrawingGeometry, validateDrawingGeometry } from "./geometry";

function HorizontalDimension({ x1, x2, y, referenceY, label }: { x1: number; x2: number; y: number; referenceY: number; label: ReactNode }) {
  const middle = (x1 + x2) / 2;
  return <g className="dimension-segment">
    <line x1={x1} y1={referenceY} x2={x1} y2={y + 5} className="extension-line" />
    <line x1={x2} y1={referenceY} x2={x2} y2={y + 5} className="extension-line" />
    <line x1={x1} y1={y} x2={x2} y2={y} className="dim-line" />
    <line x1={x1 - 3} y1={y + 4} x2={x1 + 3} y2={y - 4} className="dim-tick" />
    <line x1={x2 - 3} y1={y + 4} x2={x2 + 3} y2={y - 4} className="dim-tick" />
    <text x={middle} y={y - 7} textAnchor="middle">{label}</text>
  </g>;
}

function VerticalDimension({ x, y1, y2, referenceX, label, labelSide = "right", rotateLabel = false }: {
  x: number; y1: number; y2: number; referenceX: number; label: ReactNode; labelSide?: "left" | "right"; rotateLabel?: boolean;
}) {
  const middle = (y1 + y2) / 2;
  const right = labelSide === "right";
  return <g className="dimension-segment">
    <line x1={referenceX} y1={y1} x2={x + (right ? 5 : -5)} y2={y1} className="extension-line" />
    <line x1={referenceX} y1={y2} x2={x + (right ? 5 : -5)} y2={y2} className="extension-line" />
    <line x1={x} y1={y1} x2={x} y2={y2} className="dim-line" />
    <line x1={x - 4} y1={y1 - 3} x2={x + 4} y2={y1 + 3} className="dim-tick" />
    <line x1={x - 4} y1={y2 - 3} x2={x + 4} y2={y2 + 3} className="dim-tick" />
    <text x={x + (right ? 11 : -11)} y={middle} dominantBaseline="middle" textAnchor={rotateLabel ? "middle" : right ? "start" : "end"}
      transform={rotateLabel ? `rotate(-90 ${x + (right ? 11 : -11)} ${middle})` : undefined}>{label}</text>
  </g>;
}

export default function SideView({ model, dimensions }: { model: VisualizationModel; dimensions: boolean }) {
  const geometry = toDrawingGeometry(model);
  const errors = validateDrawingGeometry(geometry);
  if (errors.length) return <div className="drawing-error" role="status">Die Zeichnungsgeometrie ist unvollständig.</div>;

  // A single metric scale is used on both axes.
  const plateHalfLengthMm = geometry.plate.lengthMm / 2;
  const metricHalfLengthMm = Math.max(geometry.connectionHalfLengthMm, plateHalfLengthMm);
  const scale = Math.min(1, 240 / geometry.heightMm, 400 / metricHalfLengthMm);
  const seam = 480;
  const woodTop = 125;
  const woodBottom = woodTop + geometry.heightMm * scale;
  // The unstrained timber continuation is schematic: only the connection
  // coordinates remain metric. This gives the long, flat reference layout.
  const timberHalfLengthMm = Math.max(
    geometry.connectionHalfLengthMm,
    plateHalfLengthMm,
    geometry.heightMm * 1.5,
  );
  const woodLeft = seam - timberHalfLengthMm * scale;
  const woodRight = seam + timberHalfLengthMm * scale;
  const x = (positionMm: number) => seam + positionMm * scale;
  const y = (positionMm: number) => woodTop + positionMm * scale;
  const rows = geometry.rowPositionsMm.map(y);
  const columns = geometry.columnPositionsMm.map(x);
  const plateLeft = x(-plateHalfLengthMm);
  const plateRight = x(plateHalfLengthMm);
  const plateTop = y(geometry.plate.topMm);
  const plateBottom = y(geometry.plate.bottomMm);
  const dowelRadius = Math.max(2.75, geometry.dowelDiameterMm * scale * 0.28);
  const actualTopEdge = geometry.rowPositionsMm[0];
  const actualBottomEdge = geometry.heightMm - geometry.rowPositionsMm.at(-1)!;
  const topMatchesA4c = Math.abs(geometry.a4cMm - actualTopEdge) < 1e-6;
  const bottomMatchesA4c = Math.abs(geometry.a4cMm - actualBottomEdge) < 1e-6;
  const forceY = (woodTop + woodBottom) / 2;

  const viewBoxWidth = 1100;
  const leftForceStart = 90;
  const leftForceEnd = 30;
  const leftForceTextX = 110;
  const overallHeightDimensionX = 115;
  const innerPlateDimensionX = 865;
  const outerTimberDimensionX = 945;
  const rightForceStart = 1040;
  const rightForceEnd = 1070;

  return <svg className="engineering-svg side-view" viewBox={`0 45 ${viewBoxWidth} 375`} role="img"
    aria-label={`Technische Seitenansicht mit ${geometry.rowsParallel * geometry.rowsPerpendicular} Stabdübeln je Stoßseite`}>
    <defs><marker id="side-force-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" className="force-arrowhead" />
    </marker></defs>

    <rect x={woodLeft} y={woodTop} width={seam - woodLeft} height={woodBottom - woodTop} className="timber-fill" style={{ strokeWidth: 1.5 }} />
    <rect x={seam} y={woodTop} width={woodRight - seam} height={woodBottom - woodTop} className="timber-fill" style={{ strokeWidth: 1.5 }} />
    <rect x={plateLeft} y={plateTop} width={plateRight - plateLeft} height={plateBottom - plateTop} className="hidden-plate"
      style={{ strokeWidth: 1.1, strokeDasharray: "6 4", opacity: 1 }} />
    <line x1={seam} y1={woodTop} x2={seam} y2={woodBottom} className="joint" style={{ strokeWidth: 1.5 }} />

    {[...geometry.dowelPositionsLeftMm, ...geometry.dowelPositionsRightMm].map((point) =>
      <circle key={`${point.x}-${point.y}`} cx={x(point.x)} cy={y(point.y)} r={dowelRadius} className="dowel" style={{ strokeWidth: 1 }} />,
    )}

    <line x1={leftForceStart} y1={forceY} x2={leftForceEnd} y2={forceY} className="force-line" markerEnd="url(#side-force-arrow)" />
    <line x1={rightForceStart} y1={forceY} x2={rightForceEnd} y2={forceY} className="force-line" markerEnd="url(#side-force-arrow)" />
    <text x={leftForceTextX} y={forceY - 30} className="force" textAnchor="end">F<tspan baselineShift="sub">t,Ed</tspan> = {geometry.forceEdKn} kN</text>
    <text x={rightForceEnd} y={forceY - 30} className="force" textAnchor="end">F<tspan baselineShift="sub">t,Ed</tspan> = {geometry.forceEdKn} kN</text>

    {dimensions && <g className="dimensions visible">
      <HorizontalDimension x1={seam} x2={columns[0]} y={91} referenceY={woodTop} label={<>a<tspan baselineShift="sub">3,t</tspan> = {geometry.a3tMm}</>} />
      {columns.slice(1).map((position, index) =>
        <HorizontalDimension key={position} x1={columns[index]} x2={position} y={91} referenceY={woodTop} label={<>a<tspan baselineShift="sub">1</tspan> = {geometry.a1Mm}</>} />,
      )}
      <HorizontalDimension x1={columns.at(-1)!} x2={plateRight} y={91} referenceY={plateTop} label={<>e<tspan baselineShift="sub">1</tspan> = {geometry.e1Mm}</>} />

      <VerticalDimension x={outerTimberDimensionX} y1={woodTop} y2={rows[0]} referenceX={woodRight}
        label={topMatchesA4c ? <>a<tspan baselineShift="sub">4,c</tspan> = {actualTopEdge}</> : <>Rand = {actualTopEdge}</>} />
      {rows.length > 1 && <VerticalDimension x={outerTimberDimensionX} y1={rows[0]} y2={rows.at(-1)!} referenceX={woodRight}
        label={<>{rows.length - 1} × a<tspan baselineShift="sub">2</tspan> = {(rows.length - 1) * geometry.a2Mm}</>} />}
      <VerticalDimension x={outerTimberDimensionX} y1={rows.at(-1)!} y2={woodBottom} referenceX={woodRight}
        label={bottomMatchesA4c ? <>a<tspan baselineShift="sub">4,c</tspan> = {actualBottomEdge}</> : <>Rand = {actualBottomEdge}</>} />

      <VerticalDimension x={innerPlateDimensionX} y1={plateTop} y2={rows[0]} referenceX={plateRight} label={<>e<tspan baselineShift="sub">2</tspan> = {geometry.e2Mm}</>} />
      {rows.length > 1 && <VerticalDimension x={innerPlateDimensionX} y1={rows[0]} y2={rows.at(-1)!} referenceX={plateRight}
        label={<>{rows.length - 1} × a<tspan baselineShift="sub">2</tspan> = {(rows.length - 1) * geometry.a2Mm}</>} />}
      <VerticalDimension x={innerPlateDimensionX} y1={rows.at(-1)!} y2={plateBottom} referenceX={plateRight} label={<>e<tspan baselineShift="sub">2</tspan> = {geometry.e2Mm}</>} />

      <VerticalDimension x={overallHeightDimensionX} y1={woodTop} y2={woodBottom} referenceX={woodLeft} labelSide="left" rotateLabel label={<>h = {geometry.heightMm} mm</>} />
    </g>}
  </svg>;
}
