@echo off
echo Stopping donateNgo server...
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*app.py*' }; if ($p) { $p | ForEach-Object { Write-Host ('Stopped PID ' + $_.ProcessId) }; $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Write-Host 'Server stopped.' } else { Write-Host 'No donateNgo server process found.' }"
pause
