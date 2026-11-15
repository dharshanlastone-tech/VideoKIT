import { createHash } from "node:crypto";
import * as vscode from "vscode";
import {
  resolvePython,
  runPythonHelper,
  type PythonCommand,
} from "./pythonBridge";
import {
  clearVideoPreviewCache,
  createVideoPreviewHover,
  videoPreviewAt,
} from "./videoPreview";

export interface ApiParameter {
  name: string;
  kind: string;
  type: string | null;
  has_default: boolean;
  default: string | null;
}

export interface ApiMethod {
  parameters: ApiParameter[];
  return_type: string | null;
  documentation: string;
}

export interface ApiClass {
  documentation: string;
  parameters: ApiParameter[];
  methods: Record<string, ApiMethod>;
  attributes: Record<string, string | null>;
}

export interface ApiDescription {
  version: string;
  classes: Record<string, ApiClass>;
}

const apiCache = new Map<string, Promise<ApiDescription>>();
const receiverCache = new Map<string, Promise<Record<string, string>>>();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseParameters(value: unknown): ApiParameter[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const result: ApiParameter[] = [];
  for (const item of value) {
    if (
      !isRecord(item) ||
      typeof item.name !== "string" ||
      typeof item.kind !== "string" ||
      typeof item.has_default !== "boolean"
    ) {
      return undefined;
    }
    result.push({
      name: item.name,
      kind: item.kind,
      type: typeof item.type === "string" ? item.type : null,
      has_default: item.has_default,
      default: typeof item.default === "string" ? item.default : null,
    });
  }
  return result;
}

function parseApi(value: unknown): ApiDescription {
  if (!isRecord(value) || !isRecord(value.classes)) {
    throw new Error("The installed VideoKit package returned an invalid API description.");
  }
  const classes: Record<string, ApiClass> = {};
  for (const [className, rawClass] of Object.entries(value.classes)) {
    if (!isRecord(rawClass) || !isRecord(rawClass.methods)) {
      throw new Error(`VideoKit returned invalid details for ${className}.`);
    }
    const methods: Record<string, ApiMethod> = {};
    for (const [methodName, rawMethod] of Object.entries(rawClass.methods)) {
      if (!isRecord(rawMethod) || typeof rawMethod.documentation !== "string") {
        throw new Error(`VideoKit returned invalid details for ${className}.${methodName}.`);
      }
      const parameters = parseParameters(rawMethod.parameters);
      if (!parameters) {
        throw new Error(`VideoKit returned invalid parameters for ${className}.${methodName}.`);
      }
      methods[methodName] = {
        parameters,
        return_type:
          typeof rawMethod.return_type === "string" ? rawMethod.return_type : null,
        documentation: rawMethod.documentation,
      };
    }
    const parameters = parseParameters(rawClass.parameters);
    if (!parameters) {
      throw new Error(`VideoKit returned invalid constructor details for ${className}.`);
    }
    const attributes: Record<string, string | null> = {};
    if (isRecord(rawClass.attributes)) {
      for (const [name, type] of Object.entries(rawClass.attributes)) {
        attributes[name] = typeof type === "string" ? type : null;
      }
    }
    classes[className] = {
      documentation:
        typeof rawClass.documentation === "string" ? rawClass.documentation : "",
      parameters,
      methods,
      attributes,
    };
  }
  return {
    version: typeof value.version === "string" ? value.version : "unknown",
    classes,
  };
}

async function getApi(
  python: PythonCommand,
  token?: vscode.CancellationToken,
): Promise<ApiDescription> {
  const key = JSON.stringify([python.command, python.args]);
  let pending = apiCache.get(key);
  if (!pending) {
    pending = runPythonHelper(python, { command: "api" }, token).then(parseApi);
    apiCache.set(key, pending);
    void pending.catch(() => apiCache.delete(key));
  }
  return pending;
}

async function getReceiverTypes(
  python: PythonCommand,
  document: vscode.TextDocument,
  source: string,
  token?: vscode.CancellationToken,
): Promise<Record<string, string>> {
  const sourceHash = createHash("sha256").update(source).digest("hex");
  const key = `${python.command}:${document.uri.toString()}:${document.version}:${sourceHash}`;
  let pending = receiverCache.get(key);
  if (!pending) {
    pending = runPythonHelper(python, { command: "infer", source }, token).then(
      (value) => {
        if (!isRecord(value)) {
          throw new Error("VideoKit could not infer variable types from this Python file.");
        }
        const result: Record<string, string> = {};
        for (const [name, type] of Object.entries(value)) {
          if (typeof type === "string") {
            result[name] = type;
          }
        }
        return result;
      },
    );
    receiverCache.set(key, pending);
    if (receiverCache.size > 64) {
      const oldest = receiverCache.keys().next().value;
      if (oldest) {
        receiverCache.delete(oldest);
      }
    }
    void pending.catch(() => receiverCache.delete(key));
  }
  return pending;
}

async function inferExpression(
  python: PythonCommand,
  expression: string,
  source: string,
  token?: vscode.CancellationToken,
): Promise<string | null> {
  const value = await runPythonHelper(
    python,
    { command: "infer_expression", expression, source },
    token,
  );
  return typeof value === "string" ? value : null;
}

function formatParameter(parameter: ApiParameter): string {
  let value = parameter.name;
  if (parameter.type) {
    value += `: ${parameter.type}`;
  }
  if (parameter.has_default) {
    value += ` = ${parameter.default ?? "..."}`;
  }
  return value;
}

function methodSignature(name: string, method: ApiMethod): string {
  const parameters = method.parameters
    .map(formatParameter)
    .join(", ");
  const returnType = method.return_type ? ` -> ${method.return_type}` : "";
  return `${name}(${parameters})${returnType}`;
}

function methodSnippet(name: string, method: ApiMethod): vscode.SnippetString {
  const required = method.parameters.filter(
    (parameter) => !parameter.has_default && parameter.kind !== "VAR_KEYWORD",
  );
  const argumentsText = required
    .map((parameter, index) => `\${${index + 1}:${parameter.name}}`)
    .join(", ");
  return new vscode.SnippetString(
    required.length ? `${name}(${argumentsText})$0` : `${name}()$0`,
  );
}

function methodDocumentation(
  className: string,
  methodName: string,
  method: ApiMethod,
): vscode.MarkdownString {
  const content = new vscode.MarkdownString();
  content.appendCodeblock(methodSignature(methodName, method), "python");
  content.appendMarkdown(`\n\n**${className}**\n\n${method.documentation}`);
  return content;
}

async function classForReceiver(
  document: vscode.TextDocument,
  position: vscode.Position,
  receiver: string,
  token?: vscode.CancellationToken,
): Promise<{ api: ApiDescription; python: PythonCommand; className: string } | null> {
  const python = await resolvePython(document);
  const api = await getApi(python, token);
  const source = document.getText(
    new vscode.Range(new vscode.Position(0, 0), new vscode.Position(position.line, 0)),
  );
  const variables = await getReceiverTypes(python, document, source, token);
  const className = variables[receiver];
  return className && api.classes[className]
    ? { api, python, className }
    : null;
}

export function createCompletionProvider(): vscode.CompletionItemProvider {
  return {
    async provideCompletionItems(document, position, token, _context) {
      const line = document.lineAt(position.line).text.slice(0, position.character);
      const match = /([A-Za-z_]\w*)\.\w*$/.exec(line);
      if (!match) {
        return [];
      }
      const target = await classForReceiver(
        document,
        position,
        match[1],
        token,
      );
      if (!target) {
        return [];
      }
      const descriptor = target.api.classes[target.className];
      const items: vscode.CompletionItem[] = [];
      for (const [name, method] of Object.entries(descriptor.methods)) {
        const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Method);
        item.detail = methodSignature(name, method);
        item.documentation = methodDocumentation(target.className, name, method);
        item.insertText = methodSnippet(name, method);
        items.push(item);
      }
      for (const [name, type] of Object.entries(descriptor.attributes)) {
        const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Field);
        item.detail = type ? `${name}: ${type}` : name;
        items.push(item);
      }
      return items;
    },
  };
}

export function createHoverProvider(): vscode.HoverProvider {
  return {
    async provideHover(document, position, token) {
      const videoPreview = await videoPreviewAt(document, position, token);
      if (videoPreview) {
        return createVideoPreviewHover(videoPreview);
      }

      const word = document.getWordRangeAtPosition(position);
      if (!word) {
        return undefined;
      }
      const name = document.getText(word);
      const line = document.lineAt(position.line).text;
      const beforeWord = line.slice(0, word.start.character);
      const member = /([A-Za-z_]\w*)\s*\.\s*$/.exec(beforeWord);
      if (member) {
        const target = await classForReceiver(
          document,
          position,
          member[1],
          token,
        );
        const method = target?.api.classes[target.className].methods[name];
        if (target && method) {
          return new vscode.Hover(
            methodDocumentation(target.className, name, method),
            word,
          );
        }
      }

      const python = await resolvePython(document);
      const api = await getApi(python, token);
      const source = document.getText(
        new vscode.Range(new vscode.Position(0, 0), new vscode.Position(position.line, 0)),
      );
      const variables = await getReceiverTypes(python, document, source, token);
      const className = variables[name];
      const descriptor = className ? api.classes[className] : undefined;
      if (!descriptor) {
        return undefined;
      }
      const contents = new vscode.MarkdownString();
      contents.appendMarkdown(`**VideoKit ${className}**\n\n${descriptor.documentation}`);
      return new vscode.Hover(contents, word);
    },
  };
}

function activeCall(source: string): { open: number; method: string; receiver: string } | null {
  const stack: number[] = [];
  let quote = "";
  let escaped = false;
  for (let index = 0; index < source.length; index += 1) {
    const character = source[index];
    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === quote) {
        quote = "";
      }
    } else if (character === "'" || character === '"' || character === "`") {
      quote = character;
    } else if (character === "(") {
      stack.push(index);
    } else if (character === ")") {
      stack.pop();
    }
  }
  const open = stack.at(-1);
  if (open === undefined) {
    return null;
  }
  const match = /([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)\s*$/.exec(
    source.slice(0, open),
  );
  return match ? { open, receiver: match[1], method: match[2] } : null;
}

function activeParameter(source: string, open: number): number {
  let depth = 0;
  let count = 0;
  let quote = "";
  let escaped = false;
  for (let index = open + 1; index < source.length; index += 1) {
    const character = source[index];
    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (character === "\\") {
        escaped = true;
      } else if (character === quote) {
        quote = "";
      }
    } else if (character === "'" || character === '"' || character === "`") {
      quote = character;
    } else if (character === "(" || character === "[" || character === "{") {
      depth += 1;
    } else if (character === ")" || character === "]" || character === "}") {
      depth -= 1;
    } else if (character === "," && depth === 0) {
      count += 1;
    }
  }
  return count;
}

export function createSignatureHelpProvider(): vscode.SignatureHelpProvider {
  return {
    async provideSignatureHelp(document, position, token, _context) {
      const source = document.getText(
        new vscode.Range(new vscode.Position(0, 0), position),
      );
      const call = activeCall(source);
      if (!call) {
        return undefined;
      }
      const python = await resolvePython(document);
      const api = await getApi(python, token);
      const lineStart = source.lastIndexOf("\n", call.open) + 1;
      const priorSource = source.slice(0, lineStart);
      const variables = await getReceiverTypes(
        python,
        document,
        priorSource,
        token,
      );
      let className: string | null | undefined = variables[call.receiver];
      if (!className) {
        className = await inferExpression(
          python,
          call.receiver,
          priorSource,
          token,
        ) ?? undefined;
      }
      const method = className
        ? api.classes[className]?.methods[call.method]
        : undefined;
      if (!method || !className) {
        return undefined;
      }
      const signature = new vscode.SignatureInformation(
        methodSignature(call.method, method),
        method.documentation,
      );
      signature.parameters = method.parameters.map(
        (parameter) =>
          new vscode.ParameterInformation(
            formatParameter(parameter),
            parameter.type ?? undefined,
          ),
      );
      const help = new vscode.SignatureHelp();
      help.signatures = [signature];
      help.activeSignature = 0;
      help.activeParameter = Math.min(
        activeParameter(source, call.open),
        Math.max(0, method.parameters.length - 1),
      );
      return help;
    },
  };
}

export function clearApiCache(): void {
  apiCache.clear();
  receiverCache.clear();
  clearVideoPreviewCache();
}

export function reportApiFailure(error: unknown): void {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes("cancelled")) {
    return;
  }
  if (reportedFailures.has(message)) {
    return;
  }
  reportedFailures.add(message);
  if (message.includes("No module named") || message.includes("videokit._vscode")) {
    void vscode.window.showWarningMessage(
      "VideoKit is not installed in the selected Python environment. Install it with `python -m pip install -e <path-to-VideoKit>\\python-package`.",
    );
    return;
  }
  void vscode.window.showErrorMessage(`VideoKit API lookup failed: ${message}`);
}

const reportedFailures = new Set<string>();
