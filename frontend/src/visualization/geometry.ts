import type { VisualizationModel } from "../types";

export interface DrawingGeometry {
  widthMm: number;
  heightMm: number;
  plateCount: number;
  plateThicknessMm: number;
  sideThicknessMm: number;
  middleThicknessMm: number;
  dowelDiameterMm: number;
  rowsParallel: number;
  rowsPerpendicular: number;
  forceEdKn: number;
  a1Mm: number;
  a2Mm: number;
  a3tMm: number;
  a4cMm: number;
  e1Mm: number;
  e2Mm: number;
  connectionHalfLengthMm: number;
  plate: {
    lengthMm: number;
    heightMm: number;
    thicknessMm: number;
    positionsMm: number[];
    topMm: number;
    bottomMm: number;
  };
  columnPositionsMm: number[];
  rowPositionsMm: number[];
  dowelPositionsLeftMm: { x: number; y: number }[];
  dowelPositionsRightMm: { x: number; y: number }[];
  crossSectionLayersMm: number[];
}

export function toDrawingGeometry(model: VisualizationModel): DrawingGeometry {
  const rowsParallel = Math.max(1, Math.round(model.rowsParallel));
  const rowsPerpendicular = Math.max(1, Math.round(model.rowsPerpendicular));
  const plateCount = model.plateCount === 1 ? 1 : 2;

  return {
    widthMm: model.sectionWidthMm,
    heightMm: model.sectionHeightMm,
    plateCount,
    plateThicknessMm: model.plateThicknessMm,
    sideThicknessMm: model.sideThicknessMm,
    middleThicknessMm: model.middleThicknessMm,
    dowelDiameterMm: model.dowelDiameterMm,
    rowsParallel,
    rowsPerpendicular,
    forceEdKn: model.forceEdKn,
    a1Mm: model.a1Mm,
    a2Mm: model.a2Mm,
    a3tMm: model.a3tMm,
    a4cMm: model.a4cMm,
    e1Mm: model.e1Mm,
    e2Mm: model.e2Mm,
    connectionHalfLengthMm: model.connectionLengthMm,
    plate: {
      lengthMm: model.plateLengthMm,
      heightMm: model.plateHeightMm,
      thicknessMm: model.plateThicknessMm,
      positionsMm: model.platePositionsMm,
      topMm: model.plateTopMm,
      bottomMm: model.plateBottomMm,
    },
    columnPositionsMm: model.columnPositionsMm,
    rowPositionsMm: model.rowPositionsMm,
    dowelPositionsLeftMm: model.dowelPositionsLeftMm,
    dowelPositionsRightMm: model.dowelPositionsRightMm,
    crossSectionLayersMm: model.crossSectionLayersMm,
  };
}

export const sideDowelCount = (geometry: DrawingGeometry) =>
  geometry.rowsParallel * geometry.rowsPerpendicular;

export function validateDrawingGeometry(geometry: DrawingGeometry): string[] {
  const errors: string[] = [];
  const layerSum = geometry.crossSectionLayersMm.reduce((sum, value) => sum + value, 0);
  if (Math.abs(layerSum - geometry.widthMm) > 1e-6) errors.push("section layers do not sum to b");
  if (geometry.rowPositionsMm.length !== geometry.rowsPerpendicular) errors.push("row count mismatch");
  if (geometry.columnPositionsMm.length !== geometry.rowsParallel) errors.push("column count mismatch");
  if (geometry.dowelPositionsLeftMm.length !== geometry.rowsParallel * geometry.rowsPerpendicular ||
      geometry.dowelPositionsRightMm.length !== geometry.rowsParallel * geometry.rowsPerpendicular)
    errors.push("dowel coordinate count mismatch");
  if (geometry.plate.positionsMm.length !== geometry.plateCount) errors.push("plate position count mismatch");
  if (Math.abs(geometry.plate.heightMm - (geometry.plate.bottomMm - geometry.plate.topMm)) > 1e-6) errors.push("plate height mismatch");
  if (Math.abs(geometry.plate.lengthMm - 2 * (geometry.a3tMm + (geometry.rowsParallel - 1) * geometry.a1Mm + geometry.e1Mm)) > 1e-6) errors.push("plate length mismatch");
  return errors;
}

export function layerRects(
  geometry: DrawingGeometry,
  start: number,
  scale: number,
) {
  let cursor = start;
  return geometry.crossSectionLayersMm.map((size, index) => {
    const rect = { index, x: cursor, width: size * scale, size };
    cursor += rect.width;
    return rect;
  });
}
