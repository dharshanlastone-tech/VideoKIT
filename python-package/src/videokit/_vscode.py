"""Small JSON helper used by the optional VS Code extension."""

from __future__ import annotations

import ast
import base64
import inspect
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from . import Audio, AudioClip, Clip, Timeline, Video
from . import __version__
from .exceptions import VideoKitError
from .render import RenderSettings

_CLASSES = (Video, Clip, Audio, AudioClip, Timeline, RenderSettings)
_CLASS_BY_NAME = {item.__name__: item for item in _CLASSES}


def _annotation_name(annotation: Any) -> str | None:
    if annotation is inspect.Signature.empty:
        return None
    value = getattr(annotation, "__name__", None)
    if value:
        return value
    text = str(annotation).strip("'\"")
    return text.split("|", 1)[0].strip().split(".")[-1]


def _parameters(callable_object: Any) -> list[dict[str, Any]]:
    try:
        signature = inspect.signature(callable_object)
    except (TypeError, ValueError):
        return []
    parameters = []
    for parameter in signature.parameters.values():
        if parameter.name in {"self", "cls"}:
            continue
        default = None
        has_default = parameter.default is not inspect.Parameter.empty
        if has_default:
            default = repr(parameter.default)
        parameters.append(
            {
                "name": parameter.name,
                "kind": parameter.kind.name,
                "type": _annotation_name(parameter.annotation),
                "has_default": has_default,
                "default": default,
            }
        )
    return parameters


def api_description() -> dict[str, Any]:
    """Describe the real public methods, docstrings, and signatures."""
    classes: dict[str, Any] = {}
    for cls in _CLASSES:
        methods = {}
        for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("_") or member.__module__ != cls.__module__:
                continue
            signature = inspect.signature(member)
            methods[name] = {
                "parameters": _parameters(member),
                "return_type": _annotation_name(signature.return_annotation),
                "documentation": inspect.getdoc(member) or "",
            }
        attributes = {
            name: _annotation_name(annotation)
            for name, annotation in getattr(cls, "__annotations__", {}).items()
            if not name.startswith("_")
        }
        for name, member in inspect.getmembers(cls, predicate=lambda item: isinstance(item, property)):
            if not name.startswith("_"):
                attributes[name] = _annotation_name(member.fget.__annotations__.get("return"))
        classes[cls.__name__] = {
            "documentation": inspect.getdoc(cls) or "",
            "parameters": _parameters(cls),
            "methods": methods,
            "attributes": attributes,
        }
    return {"version": __version__, "classes": classes}


def _expression_type(node: ast.AST, variables: dict[str, str], api: dict[str, Any]) -> str | None:
    if isinstance(node, ast.Name):
        return variables.get(node.id)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in _CLASS_BY_NAME:
                return node.func.id
            alias_type = variables.get(node.func.id)
            if alias_type in _CLASS_BY_NAME:
                return alias_type
        if isinstance(node.func, ast.Attribute):
            receiver = _expression_type(node.func.value, variables, api)
            method = api["classes"].get(receiver or "", {}).get("methods", {}).get(
                node.func.attr
            )
            result = method.get("return_type") if method else None
            return result if result in _CLASS_BY_NAME else None
    return None


def _walk_statements(
    statements: list[ast.stmt], variables: dict[str, str], api: dict[str, Any]
) -> None:
    for statement in statements:
        if isinstance(statement, ast.ImportFrom) and statement.module == "videokit":
            for item in statement.names:
                if item.name in _CLASS_BY_NAME:
                    variables[item.asname or item.name] = item.name
        elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            value = _expression_type(statement.value, variables, api) if statement.value else None
            for target in targets:
                if isinstance(target, ast.Name):
                    if value:
                        variables[target.id] = value
                    else:
                        variables.pop(target.id, None)
        elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local = dict(variables)
            _walk_statements(statement.body, local, api)
        elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While, ast.If, ast.With)):
            _walk_statements(statement.body, variables, api)
            _walk_statements(statement.orelse, variables, api)


def infer_variables(source: str) -> dict[str, str]:
    """Infer simple VideoKit variables in valid Python source using the AST."""
    api = api_description()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    variables: dict[str, str] = {}
    _walk_statements(tree.body, variables, api)
    return variables


def infer_expression(expression: str, source: str = "") -> str | None:
    """Infer a simple VideoKit expression using names found in Python source."""
    variables = infer_variables(source)
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return None
    return _expression_type(node, variables, api_description())


def _python_to_utf16_column(line: str, byte_column: int) -> int:
    prefix = line.encode("utf-8")[:byte_column].decode("utf-8", errors="ignore")
    return len(prefix.encode("utf-16-le")) // 2


def _video_string_target(
    source: str, line_number: int, character: int
) -> tuple[str, dict[str, int]] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    video_names = {"Video"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "videokit":
            for alias in node.names:
                if alias.name == "Video":
                    video_names.add(alias.asname or alias.name)

    lines = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in video_names or not node.args:
            continue
        value = node.args[0]
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        start_line = getattr(value, "lineno", 0)
        end_line = getattr(value, "end_lineno", start_line)
        if not start_line <= line_number <= end_line:
            continue
        start_column = _python_to_utf16_column(
            lines[start_line - 1], value.col_offset
        )
        end_column = _python_to_utf16_column(
            lines[end_line - 1], value.end_col_offset
        )
        if start_line == end_line and start_column <= character <= end_column:
            return value.value, {
                "line": start_line - 1,
                "start_column": start_column,
                "end_column": end_column,
            }
    return None


def preview_at(
    source: str,
    source_path: str,
    workspace_path: str,
    line: int,
    character: int,
) -> dict[str, Any] | None:
    """Return media details and a small frame for a hovered Video path literal."""
    target = _video_string_target(source, line, character)
    if target is None:
        return None
    relative_path, location = target

    raw_path = Path(os.path.expandvars(relative_path)).expanduser()
    if raw_path.is_absolute():
        media_path = raw_path.resolve()
    else:
        candidates = []
        if workspace_path:
            candidates.append(Path(workspace_path) / raw_path)
        if source_path:
            candidates.append(Path(source_path).parent / raw_path)
        media_path = next(
            (candidate.resolve() for candidate in candidates if candidate.is_file()),
            candidates[0].resolve() if candidates else raw_path.resolve(),
        )

    try:
        video = Video(media_path)
        with tempfile.TemporaryDirectory(prefix="videokit-preview-") as directory:
            thumbnail_path = Path(directory) / "preview.jpg"
            video.thumbnail(thumbnail_path, max_width=360, max_height=203)
            thumbnail = base64.b64encode(thumbnail_path.read_bytes()).decode("ascii")
    except (OSError, VideoKitError) as error:
        return {**location, "path": str(media_path), "error": str(error)}

    return {
        **location,
        "path": str(video.path),
        "name": video.path.name,
        "duration": video.duration,
        "width": video.width,
        "height": video.height,
        "fps": video.fps,
        "thumbnail": thumbnail,
    }


def main() -> None:
    """Read one JSON request from stdin and write one JSON response to stdout."""
    try:
        request = json.load(sys.stdin)
        command = request.get("command")
        if command == "api":
            response: Any = api_description()
        elif command == "infer":
            response = infer_variables(request.get("source", ""))
        elif command == "infer_expression":
            response = infer_expression(
                request.get("expression", ""), request.get("source", "")
            )
        elif command == "preview":
            try:
                response = preview_at(
                    request.get("source", ""),
                    request.get("source_path", ""),
                    request.get("workspace_path", ""),
                    int(request.get("line", "-1")),
                    int(request.get("character", "-1")),
                )
            except (OSError, ValueError, VideoKitError) as error:
                response = {"error": str(error)}
        else:
            raise ValueError("Unknown request command.")
        json.dump(response, sys.stdout)
        sys.stdout.write("\n")
    except (OSError, ValueError, TypeError, VideoKitError) as error:
        json.dump({"error": str(error)}, sys.stdout)
        sys.stdout.write("\n")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
