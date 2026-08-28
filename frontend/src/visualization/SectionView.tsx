import type { ReactNode } from "react";
import type { VisualizationModel } from "../types";
import { layerRects, toDrawingGeometry, validateDrawingGeometry } from "./geometry";

function HorizontalDimension({ x1, x2, y, referenceY, label }: {
  x1: number; x2: number; y: number; referenceY: number; label: ReactNode;
}) {
  const middle = (x1 + x2) / 2;
  return <g className="dimension-segment">
    <line x1={x1} y1={referenceY} x2={x1} y2={y - 5} className="extension-line" />
    <line x1={x2} y1={referenceY} x2={x2} y2={y - 5} className="extension-line" />
    <line x1={x1} y1={y} x2={x2} y2={y} className="dim-line" />
    <line x1={x1 - 3} y1={y + 4} x2={x1 + 3} y2={y - 4} className="dim-tick" />
    <line x1={x2 - 3} y1={y + 4} x2={x2 + 3} y2={y - 4} className="dim-tick" />
    <text x={middle} y={y + 15} textAnchor="middle">{label}</text>
  </g>;
}

function VerticalTotalDimension({ x, y1, y2, referenceX, label }: {
  x: number; y1: number; y2: number; referenceX: number; label: ReactNode;
}) {
  const middle = (y1 + y2) / 2;
  return <g className="dimension-segment">
    <line x1={referenceX} y1={y1} x2={x + 5} y2={y1} className="extension-line" />
    <line x1={referenceX} y1={y2} x2={x + 5} y2={y2} className="extension-line" />
    <line x1={x} y1={y1} x2={x} y2={y2} className="dim-line" />
    <line x1={x - 4} y1={y1 - 3} x2={x + 4} y2={y1 + 3} className="dim-tick" />
    <line x1={x - 4} y1={y2 - 3} x2={x + 4} y2={y2 + 3} className="dim-tick" />
    <text x={x - 13} y={middle} textAnchor="middle" dominantBaseline="middle"
      transform={`rotate(-90 ${x - 13} ${middle})`}>{label}</text>
  </g>;
}

function VerticalSegmentDimension({ x, y1, y2, referenceX, label }: {
  x: number; y1: number; y2: number; referenceX: number; label: ReactNode;
}) {
  const middle = (y1 + y2) / 2;
  return <g className="dimension-segment">
    <line x1={referenceX} y1={y1} x2={x + 5} y2={y1} className="extension-line" />
    <line x1={referenceX} y1={y2} x2={x + 5} y2={y2} className="extension-line" />
    <line x1={x} y1={y1} x2={x} y2={y2} className="dim-line" />
    <line x1={x - 4} y1={y1 - 3} x2={x + 4} y2={y1 + 3} className="dim-tick" />
    <line x1={x - 4} y1={y2 - 3} x2={x + 4} y2={y2 + 3} className="dim-tick" />
    <text x={x + 11} y={middle} dominantBaseline="middle">{label}</text>
  </g>;
}

export default function SectionView({ model, dimensions }: { model: VisualizationModel; dimensions: boolean }) {
  const geometry = toDrawingGeometry(model);
  const errors = validateDrawingGeometry(geometry);
  if (errors.length) return <div className="drawing-error" role="status">Die Zeichnungsgeometrie ist unvollständig.</div>;

  // One shared scale preserves the real b:h ratio and every thickness ratio.
  const scale = Math.min(1.45, 350 / geometry.widthMm, 350 / geometry.heightMm);
  const displayWidth = geometry.widthMm * scale;
  const displayHeight = geometry.heightMm * scale;
  const x0 = 325 - displayWidth / 2;
  const y0 = 34;
  const bottom = y0 + displayHeight;
  const layers = layerRects(geometry, x0, scale);
  const plateTop = y0 + geometry.plate.topMm * scale;
  const plateBottom = y0 + geometry.plate.bottomMm * scale;
  const dowelThickness = geometry.dowelDiameterMm * scale;
  const dowelAxes = geometry.rowPositionsMm.map((position) => y0 + position * scale);
  const firstDowel = dowelAxes[0];
  const lastDowel = dowelAxes.at(-1)!;
  const actualTopEdge = geometry.rowPositionsMm[0];
  const actualBottomEdge = geometry.heightMm - geometry.rowPositionsMm.at(-1)!;
  const topMatchesA4c = Math.abs(actualTopEdge - geometry.a4cMm) < 1e-6;
  const bottomMatchesA4c = Math.abs(actualBottomEdge - geometry.a4cMm) < 1e-6;
  const right = x0 + displayWidth;
  const plateChainX = right + 35;
  const plateHeightX = right + 105;
  const timberChainX = right + 180;
  const totalHeightX = right + 285;
  const layerLabel = (index: number) => {
    if (index % 2 === 1) return <>t<tspan baselineShift="sub">s</tspan></>;
    if (index === 0 || index === layers.length - 1) return <>t<tspan baselineShift="sub">1</tspan></>;
    return <>t<tspan baselineShift="sub">2</tspan></>;
  };

  return <svg className="engineering-svg section-view" viewBox="0 10 860 500" role="img"
    aria-label={`Schnitt A-A, Querschnitt ${geometry.widthMm} mal ${geometry.heightMm} Millimeter`}>
    <defs><clipPath id="section-wood-clip">
      <rect x={x0} y={y0} width={displayWidth} height={displayHeight} />
    </clipPath></defs>
    {/* 1. Holzfläche */}
    <rect x={x0} y={y0} width={displayWidth} height={displayHeight}
      fill="var(--wood)" stroke="none" />

    {/* 2. Stahlbleche: exakt dieselben Grenzen wie in der Seitenansicht. */}
    <g clipPath="url(#section-wood-clip)">
      {layers.filter((layer) => layer.index % 2 === 1).map((layer) =>
        <rect key={layer.index} x={layer.x} y={plateTop}
          width={layer.width} height={plateBottom - plateTop}
          fill="var(--steel)" stroke="none" />,
      )}

      {/* 3. Stabdübel durchlaufen b, enden aber exakt an der Holzkontur. */}
      {dowelAxes.map((axis) => <rect key={axis} x={x0}
        y={axis - dowelThickness / 2} width={displayWidth} height={dowelThickness}
        fill="#aeb4b8" stroke="none" />)}
    </g>

    {/* 4. Holzkontur liegt sichtbar über allen Füllungen. */}
    <rect x={x0} y={y0} width={displayWidth} height={displayHeight}
      fill="none" stroke="#34383d" strokeWidth="1.5" />

    {/* 5. Schlichte technische Maßketten. */}
    {dimensions && <g className="dimensions visible">
      {layers.map((layer) => <HorizontalDimension key={`layer-${layer.index}`}
        x1={layer.x} x2={layer.x + layer.width} y={bottom + 25} referenceY={bottom}
        label={layerLabel(layer.index)} />)}
      <HorizontalDimension x1={x0} x2={x0 + displayWidth} y={bottom + 64} referenceY={bottom}
        label={<>b = {geometry.widthMm} mm</>} />

      <VerticalSegmentDimension x={plateChainX} y1={plateTop} y2={firstDowel} referenceX={right}
        label={<>e<tspan baselineShift="sub">2</tspan> = {geometry.e2Mm}</>} />
      {dowelAxes.length > 1 && <VerticalSegmentDimension x={plateChainX} y1={firstDowel} y2={lastDowel} referenceX={right}
        label={<>{dowelAxes.length - 1} × a<tspan baselineShift="sub">2</tspan> = {(dowelAxes.length - 1) * geometry.a2Mm}</>} />}
      <VerticalSegmentDimension x={plateChainX} y1={lastDowel} y2={plateBottom} referenceX={right}
        label={<>e<tspan baselineShift="sub">2</tspan> = {geometry.e2Mm}</>} />
      <VerticalTotalDimension x={plateHeightX} y1={plateTop} y2={plateBottom} referenceX={right}
        label={<>Blechhöhe = {geometry.plate.bottomMm - geometry.plate.topMm} mm</>} />

      <VerticalSegmentDimension x={timberChainX} y1={y0} y2={firstDowel} referenceX={right}
        label={topMatchesA4c ? <>a<tspan baselineShift="sub">4,c</tspan> = {actualTopEdge}</> : <>Rand = {actualTopEdge}</>} />
      {dowelAxes.length > 1 && <VerticalSegmentDimension x={timberChainX} y1={firstDowel} y2={lastDowel} referenceX={right}
        label={<>{dowelAxes.length - 1} × a<tspan baselineShift="sub">2</tspan> = {(dowelAxes.length - 1) * geometry.a2Mm}</>} />}
      <VerticalSegmentDimension x={timberChainX} y1={lastDowel} y2={bottom} referenceX={right}
        label={bottomMatchesA4c ? <>a<tspan baselineShift="sub">4,c</tspan> = {actualBottomEdge}</> : <>Rand = {actualBottomEdge}</>} />
      <VerticalTotalDimension x={totalHeightX} y1={y0} y2={bottom} referenceX={right}
        label={<>h = {geometry.heightMm} mm</>} />
    </g>}
  </svg>;
}
