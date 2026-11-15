import { randomBytes } from "node:crypto";
import { stat } from "node:fs/promises";
import { dirname } from "node:path";
import * as vscode from "vscode";

let panel: vscode.WebviewPanel | undefined;

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatTime(seconds: number): string {
  const safe = Number.isFinite(seconds) && seconds >= 0 ? seconds : 0;
  const minutes = Math.floor(safe / 60);
  const remainder = Math.floor(safe % 60);
  const fraction = Math.floor((safe % 1) * 10);
  return `${minutes}:${String(remainder).padStart(2, "0")}.${fraction}`;
}

function previewHtml(
  webview: vscode.Webview,
  videoUri: vscode.Uri,
  name: string,
  videoDuration: number,
  width: number,
  height: number,
  fps: number | null,
): string {
  const nonce = randomBytes(16).toString("base64");
  const title = escapeHtml(name);
  const source = escapeHtml(videoUri.toString());
  const dimensions = `${width} × ${height}`;
  const frameRate = fps ? ` · ${fps.toFixed(2)} fps` : "";
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; media-src ${webview.cspSource}; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <title>${title}</title>
  <style>
    :root { color-scheme: light dark; }
    body { margin: 0; padding: 14px; color: var(--vscode-foreground); background: var(--vscode-editor-background); font: 13px var(--vscode-font-family); }
    .header { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; margin-bottom: 10px; }
    .name { font-weight: 600; overflow-wrap: anywhere; }
    .meta, .status { color: var(--vscode-descriptionForeground); }
    video { display: block; width: 100%; max-height: 55vh; background: #111; object-fit: contain; }
    .controls { display: grid; grid-template-columns: auto minmax(70px, 1fr) auto; align-items: center; gap: 10px; margin-top: 12px; }
    button { color: var(--vscode-button-foreground); background: var(--vscode-button-background); border: 0; border-radius: 3px; padding: 6px 12px; cursor: pointer; }
    button:hover { background: var(--vscode-button-hoverBackground); }
    input[type=range] { width: 100%; accent-color: var(--vscode-focusBorder); cursor: pointer; }
    .time { font-variant-numeric: tabular-nums; white-space: nowrap; }
    .status { min-height: 1.4em; margin-top: 8px; }
  </style>
</head>
<body>
  <div class="header">
    <span class="name">${title}</span>
    <span class="meta">${dimensions}${frameRate}</span>
  </div>
  <video id="video" src="${source}" preload="metadata" playsinline></video>
  <div class="controls">
    <button id="play" type="button" aria-label="Play video">Play</button>
    <input id="seek" type="range" min="0" max="0" step="0.01" value="0" aria-label="Seek through video">
      <span class="time"><span id="current">0:00.0</span> / <span id="duration">${formatTime(videoDuration)}</span></span>
  </div>
  <div id="status" class="status" role="status">Loading video metadata…</div>
  <script nonce="${nonce}">
    const video = document.getElementById("video");
    const playButton = document.getElementById("play");
    const seek = document.getElementById("seek");
    const current = document.getElementById("current");
    const duration = document.getElementById("duration");
    const status = document.getElementById("status");
    const format = (seconds) => {
      if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
      const minutes = Math.floor(seconds / 60);
      const whole = Math.floor(seconds % 60);
      const fraction = Math.floor((seconds % 1) * 10);
      return minutes + ":" + String(whole).padStart(2, "0") + "." + fraction;
    };
    const updateTime = () => {
      current.textContent = format(video.currentTime);
      seek.value = String(video.currentTime);
    };
    video.addEventListener("loadedmetadata", () => {
      seek.max = String(video.duration);
      duration.textContent = format(video.duration);
      status.textContent = "Ready";
      updateTime();
    });
    video.addEventListener("timeupdate", updateTime);
    video.addEventListener("play", () => {
      playButton.textContent = "Pause";
      playButton.setAttribute("aria-label", "Pause video");
      status.textContent = "Playing";
    });
    video.addEventListener("pause", () => {
      playButton.textContent = "Play";
      playButton.setAttribute("aria-label", "Play video");
      status.textContent = "Paused";
    });
    video.addEventListener("waiting", () => { status.textContent = "Buffering…"; });
    video.addEventListener("seeked", () => {
      updateTime();
      status.textContent = video.paused ? "Paused" : "Playing";
    });
    video.addEventListener("error", () => {
      status.textContent = "This video could not be played by the VS Code preview. Try an MP4 encoded with H.264.";
    });
    playButton.addEventListener("click", () => {
      if (video.paused) {
        video.play().catch(() => { status.textContent = "Playback could not start."; });
      } else {
        video.pause();
      }
    });
    let seekFrame = 0;
    seek.addEventListener("input", () => {
      current.textContent = format(Number(seek.value));
      status.textContent = "Seeking…";
      if (!seekFrame) {
        seekFrame = requestAnimationFrame(() => {
          video.currentTime = Number(seek.value);
          seekFrame = 0;
        });
      }
    });
    seek.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        requestAnimationFrame(updateTime);
      }
    });
  </script>
</body>
</html>`;
}

export async function openVideoPreview(
  filePath: string,
  name: string,
  duration: number,
  width: number,
  height: number,
  fps: number | null,
): Promise<void> {
  if (
    typeof filePath !== "string" ||
    typeof name !== "string" ||
    !Number.isFinite(duration) ||
    !Number.isFinite(width) ||
    !Number.isFinite(height)
  ) {
    throw new Error("The video preview received invalid file information.");
  }
  const mediaUri = vscode.Uri.file(filePath);
  const details = await stat(mediaUri.fsPath);
  if (!details.isFile()) {
    throw new Error(`Video file is no longer available: ${filePath}`);
  }
  const roots = [dirname(mediaUri.fsPath)];

  if (!panel) {
    panel = vscode.window.createWebviewPanel(
      "videokit.videoPreview",
      `VideoKit Preview: ${name}`,
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: false,
        localResourceRoots: roots.map((root) => vscode.Uri.file(root)),
      },
    );
    panel.onDidDispose(() => {
      panel = undefined;
    });
  } else {
    panel.title = `VideoKit Preview: ${name}`;
    panel.reveal(vscode.ViewColumn.Beside, true);
    panel.webview.options = {
      enableScripts: true,
      localResourceRoots: roots.map((root) => vscode.Uri.file(root)),
    };
  }

  const webviewUri = panel.webview.asWebviewUri(mediaUri);
  panel.webview.html = previewHtml(
    panel.webview,
    webviewUri,
    name,
    duration,
    width,
    height,
    fps,
  );
}
