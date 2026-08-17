# USPC cloudctl Windows PowerShell execution wrapper
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Env:PYTHONPATH = "$ScriptDir\src;$Env:PYTHONPATH"

& python -m cloudctl $args
