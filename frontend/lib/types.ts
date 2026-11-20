export type Box = [number, number, number, number];
export type Poly = number[][];

export interface Word {
  id: string; text: string; conf: number | null; poly: Poly | null; box: Box | null;
  flags: string[]; alts: { text: string; engine: string; conf: number | null }[];
  status: "recognized" | "uncertain" | "corrected" | "inferred"; est_box: boolean; engine: string;
}
export interface Line {
  id: string; text: string; conf: number | null; poly: Poly | null; box: Box | null; words: Word[];
  engine: string; kind: string; order: number;
}
export interface TableCell { text: string; box: Box; word_ids: string[] }
export interface Block {
  type: "paragraph" | "heading" | "list" | "table" | "checkbox" | "form-field" | "header" | "footer" | "page-number" | "footnote";
  line_ids: string[]; box: Box | null; text?: string; lines?: string[]; level?: number; items?: string[];
  ordered?: boolean; checked?: boolean; label?: string; rows?: TableCell[][];
}
export interface Issue { type: string; detail: string; line?: number | null; word?: number; text?: string; alt?: string }
export interface Page {
  page: number; width: number; height: number; source: string; mode: string;
  analysis: Record<string, any> | null;
  enhancement: { level: string; steps: string[]; rotate90: number };
  language: { code: string | null; name: string; source: string; basis: string; confidence: number; rtl: boolean; trials: [string, number][]; note: string };
  handwriting: Record<string, any> | null;
  engines: Record<string, any>[]; primary_engine: string;
  verification: { level: string; engines_compared: string[]; agreement: { compared_words: number; agree: number; conflict: number; agreement: number | null } | null; statement: string };
  lines: Line[]; blocks: Block[]; raw_text: string; cleaned_text: string;
  cleaning_log: { change: string; before: string; after: string }[];
  layout_notes: string[]; issues: Issue[]; warnings: string[];
  math: { latex_from_vlm: string | null; normalized_latex: string; chemical_formulas: { recognized: string; normalized: string }[]; note: string } | null;
  stats: { lines: number; words: number; characters: number; mean_conf: number | null; uncertain_words: number; flagged_words: number; columns: number; tables: number; seconds: number };
  edited_text: string | null; has_word_boxes: boolean; crop?: Box;
}
export interface Progress { stage: number; stage_name: string; pct: number; message: string; page: number; pages: number }
export interface Job {
  id: string; filename: string; kind: string; size: number; created: number;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  progress: Progress; options: Record<string, any>; pages: number; error: string | null; attempts: number;
  summary: null | { words: number; lines: number; mean_conf: number | null; uncertain: number; language: string | null; language_name: string; verification: string; seconds: number; preview: string; warnings: number; empty: boolean };
}
export interface EngineInfo { name: string; label: string; kind: string; available: boolean; reason: string; languages: string[] }
export interface Config {
  engines: EngineInfo[]; modes: string[]; stages: string[]; max_upload_mb: number; max_pdf_pages: number; retention_hours: number; formats: string[];
  languages: { code: string; name: string; script: string; rtl: boolean; rapidocr: boolean; tesseract: boolean; vlm: boolean }[]; notes: string[];
}
