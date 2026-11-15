# VideoKit

VideoKit is a Python video-editing library with an optional VS Code extension.
The package performs media operations; the extension reads the installed
package's API to provide Python completions and documentation.

[GitHub repository](https://github.com/dharshanlastone-tech/VideoKIT)

## Projects

- [Python package](./python-package/README.md): metadata, cuts, clip transforms
  and effects, audio, frame extraction, and timeline composition.
- [VS Code extension](./vscode-extension/README.md): completions, hover docs,
  signature help, API-based snippets, and a video-path hover thumbnail with an
  interactive playback and seek panel.
- [Publishing guide](./PUBLISHING.md): free distribution paths, release
  prerequisites, artifact checks, and safe publishing steps. No artifacts have
  been published yet.

The package and extension are developed separately. Install FFmpeg and FFprobe
to use media operations. Install VideoKit into the Python environment selected
in VS Code to use the extension's API-aware features.

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

Neither project is published yet. The VS Code Marketplace publisher ID is
`dharshanlastone-tech`; the extension will be listed as
`dharshanlastone-tech.videokit` when published.
