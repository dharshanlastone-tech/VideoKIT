# VideoKit for VS Code

[GitHub repository](https://github.com/dharshanlastone-tech/VideoKIT)

VideoKit for VS Code helps you understand and preview VideoKit media while
writing Python. It reads the **installed VideoKit package API** for coding
assistance and uses a temporary hover thumbnail plus an interactive preview
panel for a video loaded with a literal path.

The extension is optional. The Python package works independently of VS Code.
When published, its Marketplace identifier will be
`dharshanlastone-tech.videokit`.

## At a glance

| What you do | What the extension shows |
| --- | --- |
| Type `video.` or `clip.` for a recognized VideoKit variable | Implemented methods and attributes from the installed package |
| Hover over a VideoKit method | Its signature and package docstring |
| Type a method call or comma | Parameter names, types, defaults, docs, and active argument |
| Hover over the path in `Video("movie.mp4")` | A thumbnail, duration, resolution, frame rate, and preview link |
| Click **Open interactive video preview** | A video player with playback status, elapsed/total time, and a draggable seek bar |

## Hover video preview

In a Python file, load a video using a string literal:

```python
from videokit import Video

video = Video("media/scene.mp4")
```

Hover your mouse over the `"media/scene.mp4"` string. The hover shows a small
representative thumbnail and actual media information from FFprobe. Select
**Open interactive video preview** in the hover to open the temporary
**VideoKit Preview** panel beside your code.

The panel provides:

- Play and pause controls.
- Current playback state such as **Loading**, **Ready**, **Playing**,
  **Paused**, or **Buffering**.
- The current time and total duration.
- A draggable seek bar. Drag or use the arrow keys to move through the video.
- The video's resolution and frame rate.

The panel uses VS Code's built-in webview video playback. It does not autoplay.
Playback depends on the codecs supported by the installed VS Code runtime; H.264
MP4 is a good choice when a format cannot be played. Close the panel when you are
done. Opening another hover preview reuses the panel for that video.

**Why does hover need a click?** VS Code hover popups are static documentation
surfaces; they cannot contain a reliable interactive video player or draggable
timeline. VideoKit uses the hover for the thumbnail and one-click launch, then
opens a real player panel for smooth seeking and playback.

### Supported path pattern and path resolution

The current preview recognizes a string path passed directly to the `Video`
constructor, including an aliased import such as `from videokit import Video as
VKVideo` followed by `VKVideo("scene.mp4")`. The Python helper uses the AST; it
does **not** run or import the user's open script to discover paths.

Absolute paths are used directly. For relative paths, the extension first looks
relative to the VS Code workspace folder, then relative to the Python file's
folder. It displays a helpful preview-unavailable message if the file is missing
or cannot be decoded. Dynamic paths such as `Video(path_variable)`, paths built
with joins, notebook cells, and multi-line path literals are not inferred by
this first version.

The thumbnail is generated only when a path is hovered, is bounded to about
360 × 203 pixels, and is cached for the same document version and path line.
The actual player reads the original local file on demand and only requests its
metadata initially, rather than copying the full video into the extension.

## Python coding help

### Completions

After a known VideoKit value and a dot, completions list implemented methods and
attributes for its inferred package type. API names and signatures are queried
from the installed Python package, so the extension does not advertise an
independently maintained list of methods.

### Hover documentation

Hover over a recognized VideoKit method to see its signature and docstring from
the package. Hover over a simple inferred variable to see the corresponding
VideoKit class documentation. Media-path hovers show the video preview described
above.

### Signature help

As you type calls such as `video.cut(`, the extension displays the live
signature, parameter documentation, and active parameter. Typing a comma moves
the highlighted parameter.

### Snippets

Python snippets are available for:

- Loading a video, cutting a section, and exporting it.
- Chaining supported clip edits.
- Building a timeline with a crossfade.
- Adding audio to a timeline.

### Refreshing package information

Run **VideoKit: Refresh Python API** after changing the selected Python
environment or upgrading VideoKit. The command clears cached API and preview
information so it is read again on the next request.

## Python environment and requirements

- Visual Studio Code 1.85 or newer.
- VideoKit installed in the selected Python environment.
- FFmpeg and FFprobe on `PATH` to read media and generate hover thumbnails.
- The Microsoft Python extension is recommended; the extension otherwise falls
  back to `python.defaultInterpreterPath`, then `python` on `PATH`.

From the project checkout, choose the environment in VS Code and install the
package into it:

```powershell
python -m pip install -e .\python-package
```

When VideoKit is published, a normal `python -m pip install videokit` install
will also be supported.

The extension communicates with the package by launching a short-lived Python
helper and exchanging JSON over stdin/stdout. It does not execute the Python
file being edited. Requests are cancellable, have a timeout, and the extension
reports missing package or preview errors rather than silently pretending a
preview succeeded.

## Current limits

- The extension does not edit or export videos; use the Python package for that.
- A hover itself cannot host interactive playback, so the player is a separate
  webview panel opened from the hover.
- Video previews currently require a direct string literal in `Video(...)`.
- Browser playback is limited by codecs supported by the VS Code runtime.
- There are no VideoKit-specific diagnostics, colour picker, animated hover,
  or automatic subject tracking yet.
- Python type inference is intentionally lightweight. It handles common
  assignments and method chains without executing the user's code; dynamic
  Python and complex control flow can be beyond its reach.
- Python's ordinary language features and diagnostics remain the responsibility
  of the Python extension.

## Development

From this directory:

```powershell
npm install
npm run compile
```

The project is licensed under MIT; the license text is included in the extension
package as `LICENSE`.

Open the parent VideoKit workspace, choose **Run VideoKit Extension**, and try
the hover preview in the Extension Development Host. The extension is version
0.1.0 and has not been published.
