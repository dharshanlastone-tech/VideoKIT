# VideoKit publishing guide

This document describes how VideoKit is released and how to ship future
versions.

**Release status (2026-11-15):** VideoKit `0.1.1` is published on
[PyPI](https://pypi.org/project/videokit/). The VS Code extension is published
on the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=dharshanlastone-tech.videokit).
The source is at https://github.com/dharshanlastone-tech/VideoKIT, and the
release is pushed to the `main` branch. Version `0.1.1` fixes the rotated-frame
size calculation and adds `Clip.tilt()` for smooth animated rotation beats.

## What users will install

The Python project distribution is named `videokit`. PyPI package names are
case-insensitive, so both of these install the same published distribution:

```powershell
python -m pip install videokit
python -m pip install VideoKIT
```

VideoKit's Python package does not bundle FFmpeg. Users must install FFmpeg and
FFprobe separately and place them on `PATH`. FFmpeg is free software; it does
not require a paid VideoKit account or service.

The VS Code extension is a different product, published through the Visual
Studio Marketplace. Its full Marketplace identifier is
`dharshanlastone-tech.videokit`. The owner confirmed the Marketplace publisher
ID `dharshanlastone-tech`; `vscode-extension/package.json` uses it, and version
`0.1.0` is published.
Publisher IDs are Marketplace namespaces; they are separate from GitHub
usernames, although this owner chose matching names.

## Publishing accounts and costs

- PyPI accounts and package installs are free. Use a unique PyPI account and
  enable account security features, including two-factor authentication.
- Marketplace extension installs are free. The owner has created the
  `dharshanlastone-tech` publisher. Manage it at the [Marketplace publisher
  management page](https://marketplace.visualstudio.com/manage).
- Publishing tokens are credentials. Do not paste them into source files,
  commit them, send them in chat, or include them in shell history. Prefer PyPI
  Trusted Publishing with a repository CI workflow for future releases. For
  manual uploads, store a PyPI API token in the operating system keyring and
  delete any temporary file that held it. Rotate any credential that is
  accidentally exposed.

## Before each release

1. **Confirm ownership and identity.** Confirm the license header and that the
   PyPI and Marketplace accounts belong to the project owner.
2. **Connect the source checkout.** The local checkout is connected to
   https://github.com/dharshanlastone-tech/VideoKIT. Push approved changes to
   `main` before publishing.
3. **Check names and versions.** The `videokit` name is registered on PyPI;
   never reuse the published `0.1.0` or `0.1.1` versions. Confirm that the
   Marketplace listing still belongs to the `dharshanlastone-tech` publisher.
4. **Review the distribution names and legal details.** The package name is
   registered. Check names and trademarks. MIT permits free use and
   redistribution; it does not make the project public domain.
5. **Choose a version.** Keep `python-package/pyproject.toml`,
   `python-package/src/videokit/__init__.py`, and
   `vscode-extension/package.json` versions aligned where the releases represent
   the same API. Never reuse a published version number.
6. **Test release artifacts.** Build the source distribution and wheel; install
   the wheel into a clean environment; run package tests and a real FFmpeg
   workflow. Compile and package the extension, then test it in a VS Code
   Extension Development Host with the package installed in the selected Python
   environment.
7. **Inspect public content.** Check the READMEs, changelogs, license files,
   included files, publisher ID, support contacts, and all external links.

## Build and validate the Python distribution

From `python-package`:

```powershell
python -m pip install -e ".[release]"
python -m unittest discover -s tests -v
python -m build
python -m twine check dist/*
```

To install-test a wheel, create a fresh virtual environment, install the wheel
from `dist`, and verify `import videokit` there. Also run a small edit against a
test video with FFmpeg and FFprobe installed. Do not mistake a successful wheel
build for proof that an external FFmpeg installation is present on a user's
computer.

## Upload the Python distribution

Do this only after account, package name, repository, version, and artifacts
have been reviewed. The initial `0.1.0` release was uploaded manually with
Twine. For future releases, prefer configuring PyPI Trusted Publishing and
publishing from a protected release workflow.

For a deliberate manual release, store an API token in the operating system
keyring and upload the built artifacts from a protected local environment:

```powershell
python -m keyring set https://upload.pypi.org/legacy/ __token__
python -m twine upload --non-interactive -u __token__ dist/*
```

Enter the token only at the hidden keyring prompt. Do not put a PyPI token in
this command, a script, or a committed file. For future releases, create a
token scoped to the `videokit` project instead of an account-wide token.

After publication, verify the release from a clean environment:

```powershell
python -m pip install --upgrade videokit
python -c "import videokit; print(videokit.__version__)"
```

## Build and validate the VS Code extension

From `vscode-extension`:

```powershell
npm ci
npm run compile
npx --yes @vscode/vsce package
```

Install the generated `.vsix` into a test VS Code profile or Extension
Development Host. Test API completion, hover/signature help, video-path hover,
the interactive preview panel, playback/seek, missing FFmpeg behavior, and a
missing VideoKit installation before publishing.

The repository URL is configured in the extension and Python package metadata.

## Publish the VS Code extension

1. The `dharshanlastone-tech` publisher owns the extension; version `0.1.0` is
   published as `dharshanlastone-tech.videokit`.
2. For future releases, prefer configuring Marketplace Trusted Publishing for
   the GitHub Actions release workflow, so it can publish through OIDC without a
   stored token. Microsoft's setup steps are in the [official
   guide](https://code.visualstudio.com/api/working-with-extensions/publishing-extension#publish-with-github-actions-and-trusted-publishing).
   If you choose a personal access token instead, protect it as a CI secret;
   never commit or share it.
3. Increase the extension version and update its changelog.
4. Package and test the `.vsix` locally.
5. Publish only after explicit approval:

   ```powershell
   npx --yes @vscode/vsce publish
   ```

VSCE may prompt for authentication. Use the official publisher workflow and
store credentials securely. Verify the Marketplace listing and install it from
a clean VS Code profile after publication.

## Release status and follow-ups

- VideoKit `0.1.0` is live on PyPI and the VS Code extension is live on the
  Visual Studio Marketplace.
- The source is pushed to the `main` branch at
  https://github.com/dharshanlastone-tech/VideoKIT.
- Add CI and PyPI Trusted Publishing for future releases when the repository
  workflow permissions are configured.
- Use a project-scoped PyPI token or Trusted Publishing for later versions.
  Rotate any credential that is exposed.
- Users must install FFmpeg separately for media operations.
