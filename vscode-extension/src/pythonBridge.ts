import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import * as vscode from "vscode";

export interface PythonCommand {
  command: string;
  args: string[];
}

interface PythonExecutionDetails {
  execCommand?: string;
  args?: string[];
}

interface PythonExtensionApi {
  settings: {
    getExecutionDetails(resource: vscode.Uri): PythonExecutionDetails;
  };
}

export async function resolvePython(
  document: vscode.TextDocument,
): Promise<PythonCommand> {
  const extension =
    vscode.extensions.getExtension<PythonExtensionApi>("ms-python.python");
  if (extension) {
    const api = extension.isActive ? extension.exports : await extension.activate();
    const execution = api?.settings.getExecutionDetails(document.uri);
    if (execution?.execCommand) {
      return {
        command: execution.execCommand,
        args: execution.args ?? [],
      };
    }
  }

  const configured = vscode.workspace
    .getConfiguration("python", document.uri)
    .get<string>("defaultInterpreterPath");
  return {
    command: configured || "python",
    args: [],
  };
}

export async function runPythonHelper(
  python: PythonCommand,
  request: Record<string, string>,
  token?: vscode.CancellationToken,
): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child: ChildProcessWithoutNullStreams = spawn(
      python.command,
      [...python.args, "-m", "videokit._vscode"],
      {
        windowsHide: true,
      },
    );
    const output: Buffer[] = [];
    const errors: Buffer[] = [];
    let outputSize = 0;
    let settled = false;
    const finish = (error?: Error, value?: unknown): void => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      cancellation.dispose();
      if (error) {
        reject(error);
      } else {
        resolve(value);
      }
    };
    const timeout = setTimeout(() => {
      child.kill();
      finish(new Error("VideoKit's Python helper did not respond in time."));
    }, 10_000);
    const cancellation =
      token?.onCancellationRequested(() => {
        child.kill();
        finish(new Error("VideoKit request cancelled."));
      }) ?? new vscode.Disposable(() => undefined);

    child.stdout.on("data", (chunk: Buffer) => {
      outputSize += chunk.length;
      if (outputSize > 2_000_000) {
        child.kill();
        finish(new Error("VideoKit returned an unexpectedly large response."));
        return;
      }
      output.push(chunk);
    });
    child.stderr.on("data", (chunk: Buffer) => errors.push(chunk));
    child.on("error", (error: Error) => {
      finish(new Error(`Could not run Python '${python.command}': ${error.message}`));
    });
    child.stdin.on("error", (error: Error) => {
      finish(new Error(`Could not send a request to Python: ${error.message}`));
    });
    child.on("close", (code: number | null) => {
      if (settled) {
        return;
      }
      const stdout = Buffer.concat(output).toString("utf8");
      if (code !== 0) {
        const stderr = Buffer.concat(errors).toString("utf8").trim();
        try {
          const response: unknown = JSON.parse(stdout);
          if (
            typeof response === "object" &&
            response !== null &&
            "error" in response &&
            typeof response.error === "string"
          ) {
            finish(new Error(response.error));
            return;
          }
        } catch {
          // Use stderr below when the helper did not return a JSON error.
        }
        finish(
          new Error(
            stderr || `VideoKit's Python helper exited with status ${String(code)}.`,
          ),
        );
        return;
      }
      try {
        const value: unknown = JSON.parse(stdout);
        finish(undefined, value);
      } catch {
        finish(new Error("VideoKit's Python helper returned invalid JSON."));
      }
    });
    child.stdin.end(JSON.stringify(request));
  });
}
