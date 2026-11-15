import * as vscode from "vscode";
import {
  clearApiCache,
  createCompletionProvider,
  createHoverProvider,
  createSignatureHelpProvider,
  reportApiFailure,
} from "./apiProvider";
import { openVideoPreview } from "./videoPreviewPanel";

async function safeRequest<T>(request: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await request();
  } catch (error) {
    reportApiFailure(error);
    return fallback;
  }
}

export function activate(context: vscode.ExtensionContext): void {
  const completionDelegate = createCompletionProvider();
  const hoverDelegate = createHoverProvider();
  const signatureDelegate = createSignatureHelpProvider();

  const completion: vscode.CompletionItemProvider = {
    provideCompletionItems(document, position, token, completionContext) {
      return safeRequest(
        () =>
          Promise.resolve(
            completionDelegate.provideCompletionItems(
              document,
              position,
              token,
              completionContext,
            ),
          ),
        [],
      );
    },
  };
  const hover: vscode.HoverProvider = {
    provideHover(document, position, token) {
      return safeRequest(
        () => Promise.resolve(hoverDelegate.provideHover(document, position, token)),
        undefined,
      );
    },
  };
  const signatures: vscode.SignatureHelpProvider = {
    provideSignatureHelp(document, position, token, signatureContext) {
      return safeRequest(
        () =>
          Promise.resolve(
            signatureDelegate.provideSignatureHelp(
              document,
              position,
              token,
              signatureContext,
            ),
          ),
        undefined,
      );
    },
  };

  context.subscriptions.push(
    vscode.languages.registerCompletionItemProvider(
      { language: "python" },
      completion,
      ".",
    ),
    vscode.languages.registerHoverProvider({ language: "python" }, hover),
    vscode.languages.registerSignatureHelpProvider(
      { language: "python" },
      signatures,
      "(",
      ",",
    ),
    vscode.commands.registerCommand("videokit.refreshApi", () => {
      clearApiCache();
      void vscode.window.showInformationMessage(
        "VideoKit API information will be reloaded from the selected Python environment.",
      );
    }),
    vscode.commands.registerCommand(
      "videokit.openVideoPreview",
      (...args: unknown[]) => {
        const [filePath, name, duration, width, height, fps] = args;
        if (
          typeof filePath !== "string" ||
          typeof name !== "string" ||
          typeof duration !== "number" ||
          typeof width !== "number" ||
          typeof height !== "number" ||
          (fps !== null && typeof fps !== "number")
        ) {
          void vscode.window.showErrorMessage(
            "VideoKit received invalid video preview information.",
          );
          return;
        }
        return safeRequest(
          () =>
            openVideoPreview(
              filePath,
              name,
              duration,
              width,
              height,
              fps,
            ),
          undefined,
        );
      },
    ),
  );
}

export function deactivate(): void {}
