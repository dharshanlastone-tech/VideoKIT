# VideoKit

[![PyPI](https://img.shields.io/pypi/v/videokit.svg)](https://pypi.org/project/videokit/)
[![Python versions](https://img.shields.io/pypi/pyversions/videokit.svg)](https://pypi.org/project/videokit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/dharshanlastone-tech/VideoKIT/blob/main/python-package/LICENSE)

VideoKit is a Python video-editing library with an optional VS Code extension,
created by **Dharshan**. The package performs media operations; the extension
reads the installed package's API to provide Python completions, hover
documentation, signature help, API-based snippets, and a video-path hover
thumbnail with an interactive playback and seek panel.

[PyPI package](https://pypi.org/project/videokit/) ·
[VS Code extension](https://marketplace.visualstudio.com/items?itemName=dharshanlastone-tech.videokit) ·
[GitHub repository](https://github.com/dharshanlastone-tech/VideoKIT)

## Install

```powershell
python -m pip install videokit
```

The VS Code extension is optional:

```powershell
code --install-extension dharshanlastone-tech.videokit
```

Install FFmpeg and FFprobe and place them on `PATH` to use media operations.
Install VideoKit into the Python environment selected in VS Code to use the
extension's API-aware features.

## Projects

- [Python package](./python-package/README.md): metadata, cuts, clip transforms
  and effects, audio, frame extraction, and timeline composition.
- [VS Code extension](./vscode-extension/README.md): completions, hover docs,
  signature help, API-based snippets, and a video-path hover thumbnail with an
  interactive playback and seek panel.
- [Publishing guide](./PUBLISHING.md): release process, artifact checks, and
  safe publishing steps.

## Development

Install the package in editable mode:

```powershell
python -m pip install -e .\python-package
```

Compile the extension:

```powershell
Set-Location .\vscode-extension
npm install
npm run compile
```

The Python package is published on PyPI as `videokit`. The extension is
published on the Visual Studio Marketplace as
`dharshanlastone-tech.videokit`. The Marketplace publisher ID is
`dharshanlastone-tech`.

## Author

Dharshan
