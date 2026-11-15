import * as vscode from "vscode";
import { resolvePython, runPythonHelper } from "./pythonBridge";

export interface VideoPreview {
  line: number;
  start_column: number;
  end_column: number;
  path?: string;
  name?: string;
  duration?: number;
  width?: number;
  height?: number;
  fps?: number | null;
  thumbnail?: string;
  error?: string;
}

const previewCache = new Map<string, VideoPreview>();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function cursorIsInsideString(line: string, character: number): boolean {
  let quote = "";
  let triple = false;
  let escaped = false;
  for (let index = 0; index < Math.min(character, line.length); index += 1) {
    const current = line[index];
    if (!quote) {
      if (current === "#") {
        return false;
      }
      if (current === "'" || current === '"') {
        quote = current;
        triple =
          line[index + 1] === current && line[index + 2] === current;
        if (triple) {
          index += 2;
        }
      }
      continue;
    }

    if (escaped) {
      escaped = false;
      continue;
    }
    if (current === "\\") {
      escaped = true;
      continue;
    }
    if (current === quote) {
      if (triple) {
        if (
          line[index + 1] === quote &&
          line[index + 2] === quote &&
          index + 2 >= character
        ) {
          return true;
        }
        if (
          line[index + 1] === quote &&
          line[index + 2] === quote
        ) {
          quote = "";
          triple = false;
          index += 2;
        }
      } else {
        quote = "";
      }
    }
  }
  return quote !== "";
}

function parsePreview(value: unknown): VideoPreview | null {
  if (!isRecord(value) || typeof value.line !== "number") {
    return null;
  }
  if (
    typeof value.start_column !== "number" ||
    typeof value.end_column !== "number"
  ) {
    return null;
  }
  const preview: VideoPreview = {
    line: value.line,
    start_column: value.start_column,
    end_column: value.end_column,
  };
  if (typeof value.error === "string") {
    preview.error = value.error;
    return preview;
  }
  if (
    typeof value.path !== "string" ||
    typeof value.name !== "string" ||
    typeof value.duration !== "number" ||
    typeof value.width !== "number" ||
    typeof value.height !== "number" ||
    typeof value.thumbnail !== "string"
  ) {
    return null;
  }
  preview.path = value.path;
  preview.name = value.name;
  preview.duration = value.duration;
  preview.width = value.width;
  preview.height = value.height;
  preview.fps = typeof value.fps === "number" ? value.fps : null;
  preview.thumbnail = value.thumbnail;
  return preview;
}

export async function videoPreviewAt(
  document: vscode.TextDocument,
  position: vscode.Position,
  token: vscode.CancellationToken,
): Promise<VideoPreview | null> {
  const currentLine = document.lineAt(position.line).text;
  if (!cursorIsInsideString(currentLine, position.character)) {
    return null;
  }

  const key = `${document.uri.toString()}:${document.version}:${position.line}`;
  const cached = previewCache.get(key);
  if (
    cached &&
    cached.line === position.line &&
    position.character >= cached.start_column &&
    position.character <= cached.end_column
  ) {
    return cached;
  }
  if (token.isCancellationRequested) {
    return null;
  }

  const python = await resolvePython(document);
  const workspace = vscode.workspace.getWorkspaceFolder(document.uri);
  const result = await runPythonHelper(
    python,
    {
      command: "preview",
      source: document.getText(),
      source_path: document.uri.scheme === "file" ? document.uri.fsPath : "",
      workspace_path: workspace?.uri.fsPath ?? "",
      line: String(position.line + 1),
      character: String(position.character),
    },
    token,
  );
  if (result === null) {
    return null;
  }
  const preview = parsePreview(result);
  if (!preview) {
    throw new Error("VideoKit returned invalid video preview information.");
  }
  previewCache.set(key, preview);
  if (previewCache.size > 32) {
    const oldest = previewCache.keys().next().value;
    if (oldest) {
      previewCache.delete(oldest);
    }
  }
  return preview;
}

export function clearVideoPreviewCache(): void {
  previewCache.clear();
}

export function createVideoPreviewHover(
  preview: VideoPreview,
): vscode.Hover {
  const contents = new vscode.MarkdownString();
  if (preview.error) {
    contents.appendMarkdown("**Video preview unavailable**\n\n");
    contents.appendText(preview.error);
    return new vscode.Hover(contents);
  }

  const path = preview.path!;
  const name = preview.name!;
  const duration = preview.duration!;
  const details = `${preview.width} × ${preview.height} · ${duration.toFixed(2)} s`;
  const commandUri = vscode.Uri.parse(
    `command:videokit.openVideoPreview?${encodeURIComponent(
      JSON.stringify([
        path,
        name,
        duration,
        preview.width,
        preview.height,
        preview.fps ?? null,
      ]),
    )}`,
  );
  contents.isTrusted = { enabledCommands: ["videokit.openVideoPreview"] };
  contents.appendMarkdown("**");
  contents.appendText(name);
  contents.appendMarkdown(`**\n\n${details}`);
  if (preview.fps) {
    contents.appendMarkdown(` · ${preview.fps.toFixed(2)} fps`);
  }
  contents.appendMarkdown("\n\n");
  contents.appendMarkdown(
    `![Video thumbnail](data:image/jpeg;base64,${preview.thumbnail})\n\n`,
  );
  contents.appendMarkdown(`[Open interactive video preview](${commandUri})`);
  return new vscode.Hover(contents);
}
