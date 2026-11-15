# VideoKit publishing guide

This document describes how to release VideoKit when the project owner is ready.
**Nothing has been uploaded or published.** The project repository URL supplied
by the owner is https://github.com/dharshanlastone-tech/VideoKIT. The local
workspace still needs to be connected to that GitHub repository before source
changes can be pushed.

## What users will install

The Python project distribution is named `videokit`. PyPI package names are
case-insensitive, so after a successful release both of these refer to the same
distribution:

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
ID `dharshanlastone-tech`, and `vscode-extension/package.json` now uses it.
Publisher IDs are Marketplace namespaces; they are separate from GitHub
usernames, although this owner chose matching names.

## Publishing accounts and costs

- PyPI accounts and package installs are free. Use a unique PyPI account and
  enable account security features, including two-factor authentication.
- Marketplace extension installs are free. The owner has created the
  `dharshanlastone-tech` publisher. Manage it at the [Marketplace publisher
  management page](https://marketplace.visualstudio.com/manage).
- Publishing tokens are credentials. Do not paste them into source files,
  commit them, or send them in chat. Prefer PyPI Trusted Publishing with a
  repository CI workflow after the repository is established. Microsoft's
  current Marketplace guidance recommends GitHub Actions Trusted Publishing
  with OIDC; if you use a personal access token instead, keep it out of source
  files and store it only as a protected CI secret.

## Before the first public release

1. **Confirm ownership and identity.** Confirm the license header and that the
   publisher account belongs to the project owner.
2. **Connect the source checkout.** The repository URL has been added to the
   extension and Python package metadata. Connect this local checkout to the
   owner's GitHub repository before pushing any changes.
3. **Check the names again.** PyPI's `videokit` lookup returned 404 during the
   local pre-release check. The Marketplace page lookup for `videokit.videokit`
   also returned 404. These results are not reservations or guarantees; check
   registration and ownership directly immediately before release.
4. **Review the distribution names and legal details.** The package name is
   provisional. Check names and trademarks. MIT permits free use and
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
have been reviewed. Prefer configuring PyPI Trusted Publishing in the owner's
repository and publishing from a protected release workflow. For a deliberate
manual release, upload the built artifacts with Twine from a protected local
environment:

```powershell
python -m twine upload dist/*
```

Do not put a PyPI token in this command, a script, or a committed file. Follow
PyPI's current token/keyring guidance when authenticating.

After publication, verify the release from a clean environment:

```powershell
python -m pip install VideoKIT
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

1. The owner has created the `dharshanlastone-tech` publisher; the extension
   manifest is configured to publish as `dharshanlastone-tech.videokit`.
2. Prefer configuring Marketplace Trusted Publishing for the GitHub Actions
   release workflow, so it can publish through OIDC without a stored token.
   Microsoft's setup steps are in the [official
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

## Current release blockers

- The repository URL is configured, but this local checkout still needs to be
  connected to it before changes can be pushed.
- Account ownership and name availability must be confirmed at release time.
- PyPI/Marketplace release artifacts have only been built locally; no public
  upload or Extension Development Host UI test has been performed.
- Users must install FFmpeg separately for media operations.
