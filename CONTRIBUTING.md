# Contributing to Media Flow

Thanks for your interest in improving Media Flow. This project is a local
Windows app for converting audio, video, and image files with `ffmpeg`.

## Before You Start

- Check the open issues and recent releases to avoid duplicate work.
- Keep changes focused. Small pull requests are easier to review and test.
- Do not add features that download media from third-party services.
- Do not add telemetry, account login, or upload behavior without discussing it
  first.

## Development Setup

Requirements:

- Windows 10 or Windows 11
- Python 3
- `ffmpeg` and `ffprobe` available in the project folder or in `PATH`

Run the app locally:

```powershell
python app.py
```

If dependencies are added in the future, install them with:

```powershell
python -m pip install -r requirements.txt
```

## Project Structure

- `app.py` - main application code
- `assets/` - app assets used by the interface and packaging
- `packaging/` - packaging-related files
- `.github/` - GitHub workflows and repository automation
- `installer.iss` - Inno Setup installer configuration
- `README.md` - user-facing overview
- `CHANGELOG.md` - release history

## Making Changes

1. Create a branch from `main`.
2. Make a focused change.
3. Run the app locally and test the affected workflow.
4. Update documentation when behavior changes.
5. Add an entry to `CHANGELOG.md` for user-visible changes.
6. Open a pull request with a clear summary and testing notes.

## Testing Checklist

For conversion changes, test at least one successful conversion in the affected
mode:

- Audio
- Video
- Image
- Batch conversion, if the change touches shared conversion logic

Also check:

- Light and dark mode still render correctly.
- Output folder selection still works.
- File information still appears when `ffprobe` is available.
- Error messages are understandable when conversion fails.

## Code Style

- Follow the style already used in `app.py`.
- Prefer clear names over clever abstractions.
- Keep UI text concise and user-facing.
- Avoid unrelated formatting-only changes.
- Keep comments short and useful.

## Privacy and Security

Media Flow is designed to process local files locally. Contributions should
preserve that behavior.

- Do not upload user files to external services.
- Do not collect analytics or personal data.
- Do not read browser credentials or cookies.
- Report security issues according to `SECURITY.md`.

## Pull Request Guidelines

Include:

- What changed
- Why it changed
- How it was tested
- Screenshots for visible UI changes

Pull requests that change packaging, releases, updating, or installer behavior
should explain the expected installation/update flow clearly.
