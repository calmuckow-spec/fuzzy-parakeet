# IES Generator — Windows build

This folder holds the Python source for **IES Generator**, a Tkinter desktop
tool for regenerating IESNA LM-63 photometric (`.ies`) files and producing
Excel reports. The full user manual (in Russian) is in `Инструкция.md`.

## Getting a ready-to-run Windows .exe (no Python required)

A GitHub Actions workflow at `.github/workflows/build-windows.yml` builds a
self-contained Windows executable on a real `windows-latest` runner —
PyInstaller can't cross-compile, so this is the way to get a genuine Windows
build without owning a Windows machine yourself.

### 1. Start the build

- Open this repository on GitHub and go to the **Actions** tab.
- Select **Build Windows executable** in the workflow list on the left.
- Click **Run workflow**, pick the branch to build, and confirm.
- (It also runs automatically whenever a commit changes anything under
  `ies-generator/`.)

### 2. Download the result

- Wait for the run to finish — typically 2–4 minutes.
- Open the completed run and scroll to the **Artifacts** section at the
  bottom of the run summary page.
- Download **`IES-Generator-Windows`**. GitHub delivers artifacts as a
  `.zip`; inside it is a single file, `IES_Generator.exe`.

### 3. Run it on Windows 10/11

- Unzip the downloaded artifact anywhere (Desktop, `C:\IES`, a USB stick —
  it doesn't matter).
- Double-click `IES_Generator.exe`. Nothing else needs to be installed:
  Python, tkinter and openpyxl are all bundled inside the executable.
- On the first launch, Windows SmartScreen may show **"Windows protected
  your PC"** because the file isn't code-signed (a signing certificate
  costs money and isn't set up for this project). Click **More info** →
  **Run anyway**. That's expected for any unsigned executable, not a sign
  of a broken build.

For the alternative — building locally by double-clicking a `.bat` file on
your own Windows machine instead of using GitHub Actions — see the
"Как получить файл .exe" section of `Инструкция.md`.
