# USPC cloudctl Windows PowerShell execution wrapper
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Env:PYTHONPATH = "$ScriptDir\src;$Env:PYTHONPATH"

$PythonExe = "python"
if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonExe = "$ScriptDir\.venv\Scripts\python.exe"
}

& $PythonExe -m cloudctl $args
