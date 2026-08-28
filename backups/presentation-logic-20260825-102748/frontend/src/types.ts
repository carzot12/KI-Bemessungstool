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
  visualizationModel: VisualizationModel;
}
export interface UISnapshot {
  technicalState: Record<string, unknown>;
  currentResult: null | {
    passed: boolean;
    normAdmissible: boolean;
    utilization: number;
    governingCheck: string;
    checks: unknown[];
    input: Record<string, unknown>;
  };
  lastOptimization: null | {
    evaluatedCount: number;
    feasibleCount: number;
    message: string;
  };
  variants: Variant[];
  agentStatus: {
    mode: "online" | "local" | "error";
    label: string;
    model: string | null;
    detail: string;
  };
  conversation: ConversationMessage[];
  visualizationModel: VisualizationModel | null;
  demoMode: boolean;
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
        send_message(payload: { text: string }): Promise<BridgeEnvelope>;
        copy_chat_text(): Promise<string>;
        form_options(): Promise<FormOptions>;
        compact_calculate(
          payload: Record<string, string | number>,
        ): Promise<BridgeEnvelope>;
        manual_calculate(
          payload: Record<string, string | number>,
        ): Promise<BridgeEnvelope>;
      };
    };
  }
}
