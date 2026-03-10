@echo off
echo ============================================
echo   Portfolio Tracker Manager
echo ============================================
echo.
echo   1. Start (hidden, no console window)
echo   2. Stop
echo   3. Restart
echo   4. Check if running
echo   5. Open in browser
echo   6. Add to Windows Startup (auto-start on login)
echo   7. Remove from Windows Startup
echo   8. View logs
echo   9. Start with console (for debugging)
echo.
set /p choice="Select option: "

if "%choice%"=="1" goto :start
if "%choice%"=="2" goto :stop
if "%choice%"=="3" goto :restart
if "%choice%"=="4" goto :check
if "%choice%"=="5" goto :browse
if "%choice%"=="6" goto :add_startup
if "%choice%"=="7" goto :remove_startup
if "%choice%"=="8" goto :logs
if "%choice%"=="9" goto :debug
goto :end

:start
echo.
echo Starting Portfolio Tracker...
:: Check if already running
powershell -command "if (Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object {$_.CommandLine -like '*run_server*'}) { Write-Host 'Already running'; exit 1 } else { exit 0 }"
if %errorlevel%==1 (
    echo Use option 3 to restart, or option 2 to stop first.
    goto :end
)
wscript "%~dp0start_hidden.vbs"
timeout /t 3 >nul
:: Verify it started
powershell -command "if (Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object {$_.CommandLine -like '*run_server*'}) { Write-Host 'Portfolio Tracker is running at http://tradepc:5000' } else { Write-Host 'Failed to start. Try option 9 to debug.' }"
goto :end

:stop
echo.
echo Stopping Portfolio Tracker...
powershell -command "$procs = Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object {$_.CommandLine -like '*run_server*'}; if ($procs) { $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host \"Stopped (PID: $($_.ProcessId))\" } } else { Write-Host 'Portfolio Tracker was not running.' }"
goto :end

:restart
call :stop
timeout /t 2 >nul
goto :start

:check
echo.
powershell -command "$procs = Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | Where-Object {$_.CommandLine -like '*run_server*'}; if ($procs) { $procs | ForEach-Object { Write-Host \"Portfolio Tracker is RUNNING (PID: $($_.ProcessId)) on http://tradepc:5000\" } } else { Write-Host 'Portfolio Tracker is NOT running.' }"
goto :end

:browse
start http://tradepc:5000
goto :end

:add_startup
echo.
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
echo Creating startup shortcut...
powershell -command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP_DIR%\PortfolioTracker.lnk'); $s.TargetPath = 'wscript'; $s.Arguments = '\"%~dp0start_hidden.vbs\"'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Portfolio Tracker'; $s.Save()"
echo.
echo Done! Portfolio Tracker will start automatically when you log in.
echo Shortcut created in: %STARTUP_DIR%
goto :end

:remove_startup
echo.
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
if exist "%STARTUP_DIR%\PortfolioTracker.lnk" (
    del "%STARTUP_DIR%\PortfolioTracker.lnk"
    echo Startup shortcut removed.
) else (
    echo No startup shortcut found.
)
goto :end

:logs
echo.
if exist "%~dp0logs\server.log" (
    echo === server.log [last 30 lines] ===
    echo.
    powershell -command "Get-Content '%~dp0logs\server.log' -Tail 30"
) else (
    echo No server.log found yet.
)
goto :end

:debug
echo.
echo Starting in debug mode (console visible, Ctrl+C to stop)...
echo.
python "%~dp0run_server.py"
goto :end

:end
echo.
pause
