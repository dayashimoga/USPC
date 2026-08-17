# Windows environment discovery helper
$ScriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Env:PYTHONPATH = "$ScriptDir\src;$Env:PYTHONPATH"

& python -c "from cloudctl.core.detect import detect_host; import json; print(json.dumps(detect_host().to_dict(), indent=2))"
