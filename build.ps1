param(
    [switch]$Clean,
    [string]$PythonExe = ""
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# Build only with a Python distribution that has a working Tcl/Tk runtime.
# Some minimal/embedded Python builds can import tkinter but cannot package or
# run a Tk window because they omit the Tcl/Tk resource files.
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $anacondaPython = 'C:\ProgramData\anaconda3\python.exe'
    if (Test-Path -LiteralPath $anacondaPython) {
        $PythonExe = $anacondaPython
    } else {
        $PythonExe = 'python'
    }
}

& $PythonExe -c "import tkinter as tk; root = tk.Tk(); root.destroy()"
if ($LASTEXITCODE -ne 0) {
    throw 'Tkinter/Tcl-Tk가 정상 동작하는 Python을 찾지 못했습니다. -PythonExe로 Python 경로를 지정하세요.'
}

$venvPython = Join-Path $root 'work\packaging-venv-tk\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $PythonExe -m venv (Join-Path $root 'work\packaging-venv-tk')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist
}

& $venvPython -m pip install --upgrade pyinstaller
& $venvPython -m PyInstaller --noconfirm --clean --windowed --name BlogDraftAgent app.py

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "완료: $root\dist\BlogDraftAgent\BlogDraftAgent.exe"
