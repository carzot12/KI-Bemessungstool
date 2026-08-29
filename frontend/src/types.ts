export interface VisualizationModel {
  sectionWidthMm: number;
  sectionHeightMm: number;
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
  connectionLengthMm: number;
  plateLengthMm: number;
  plateHeightMm: number;
  plateTopMm: number;
  plateBottomMm: number;
  platePositionsMm: number[];
  crossSectionLayersMm: number[];
  columnPositionsMm: number[];
  rowPositionsMm: number[];
  dowelPositionsLeftMm: { x: number; y: number }[];
  dowelPositionsRightMm: { x: number; y: number }[];
  topTimberEdgeDistanceMm: number;
  bottomTimberEdgeDistanceMm: number;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}
export interface Variant {
  id: string;
  label: string;
  fastenerCount: number;
  rowsParallel: number;
  rowsPerpendicular: number;
  diameterMm: number;
  plateCount: number;
  plateThicknessMm: number;
  utilization: number;
  passed: boolean;
  normAdmissible: boolean;
  governingCheck: string;
  interestReason: string;
  reserve: number;
  connectionAreaMm2: number;
  input: Record<string, unknown>;
  visualizationModel: VisualizationModel;
  connectionGeometry: VisualizationModel;
  reportIncluded?: boolean;
}
export interface UISnapshot {
  technicalState: Record<string, unknown>;
  currentResult: null | {
    passed: boolean;
    normAdmissible: boolean;
    utilization: number;
    governingCheck: string;
    checks: unknown[];
    geometryRequirements: unknown[];
    input: Record<string, unknown>;
  };
  lastOptimization: null | {
    evaluatedCount: number;
    feasibleCount: number;
    rejectedCount: number;
    shortlistedCount: number;
    selectedVariantRank: number | null;
    objective: string | null;
    selectedVariant: string | null;
    message: string;
  };
  lastMaximumLoad: null | {
    forceEdKn: number;
    utilization: number;
    governingCheck: string;
    input: Record<string, unknown>;
  };
  variants: Variant[];
  reportVariants: Variant[];
  recommendedVariant: Variant | null;
  currentVariant: Variant | null;
  recommendation: string;
  sources: string[];
  optimizationGoal: string | null;
  agentStatus: {
    mode: "online" | "local" | "error";
    label: string;
    model: string | null;
    detail: string;
    provider: "local" | "openai";
    available: boolean;
    privacyDetail: string;
  };
  conversation: ConversationMessage[];
  visualizationModel: VisualizationModel | null;
  connectionGeometry: VisualizationModel | null;
  demoMode: boolean;
  projectName: string;
  reportVariantIds: string[];
}
export interface BridgeEnvelope {
  ok: boolean;
  revision: number;
  data: UISnapshot;
  error: string | null;
}
export interface FormOptions {
  timberGrades: string[];
  loadDurations: string[];
  manualDefaults: Record<string, string | number>;
}

declare global {
  interface Window {
    pywebview?: {
      api: {
        bootstrap(): Promise<BridgeEnvelope>;
        reset_design(): Promise<BridgeEnvelope>;
        send_message(payload: { text: string }): Promise<BridgeEnvelope>;
        copy_chat_text(): Promise<string>;
        form_options(): Promise<FormOptions>;
        set_llm_provider(payload: { provider: "local" | "openai" }): Promise<BridgeEnvelope>;
        compact_calculate(
          payload: Record<string, string | number>,
        ): Promise<BridgeEnvelope>;
        manual_calculate(
          payload: Record<string, string | number>,
        ): Promise<BridgeEnvelope>;
        manual_example(): Promise<{
          ok: boolean;
          data: Record<string, string | number>;
          error: string | null;
        }>;
        create_pdf_report(payload: { type: "calculation" | "variants" }): Promise<{
          status: "success" | "cancelled" | "error";
          path?: string;
          size?: number;
          message?: string;
        }>;
        adopt_variant(payload: { variant_id: string }): Promise<BridgeEnvelope>;
        set_report_selection(payload: { variant_ids: string[] }): Promise<BridgeEnvelope>;
        set_project_name(payload: { project_name: string }): Promise<BridgeEnvelope>;
        open_report(payload: { path: string }): Promise<{ ok: boolean; error: string | null }>;
        reveal_report(payload: { path: string }): Promise<{ ok: boolean; error: string | null }>;
      };
    };
  }
}
