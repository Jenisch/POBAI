@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

rem Change to the directory containing this script so relative paths work.
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 --version >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    where python >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo Could not locate a Python interpreter. Please install Python 3.9 or newer and add it to PATH.
    goto :end
)

set "DEFAULT_POB_EXE=C:\Program Files\Path of Building Community\PathOfBuilding.exe"
set "POB_PATH=%DEFAULT_POB_EXE%"
if "%~1"=="" goto :prompt

if "%~1"=="--set-pob-path" (
    set "POB_PATH=%~2"
    shift
    shift
    goto :prompt
)

goto :prompt

:prompt
if not exist "%POB_PATH%" (
    echo.
    echo Enter the full path to your PathOfBuilding.exe.
    set /p "POB_PATH=Path to PathOfBuilding.exe [%DEFAULT_POB_EXE%]: "
    if "!POB_PATH!"=="" set "POB_PATH=%DEFAULT_POB_EXE%"
)

if not exist "!POB_PATH!" (
    echo.
    echo The Path of Building executable was not found at:
    echo     !POB_PATH!
    echo Update the path inside run_pob_planner.bat or re-run and enter the correct location.
    goto :pause
)

echo.
echo Choose an option:
echo   1 ^) Get recommendations and open the top result.
echo   2 ^) Open a specific build id directly.
echo   3 ^) Exit.
set /p "USER_OPTION=Enter choice [1-3]: "
if "!USER_OPTION!"=="1" goto :open_top
if "!USER_OPTION!"=="2" goto :open_specific
if "!USER_OPTION!"=="3" goto :end
echo Invalid choice. Try again.
goto :prompt

:open_top
echo.
echo Running recommendation workflow. You can edit playstyle.json to change defaults.
if exist playstyle.json (
    call %PYTHON_CMD% -m pob_build_planner.cli --config playstyle.json --open --open-mode file --pob-executable "!POB_PATH!"
) else (
    call %PYTHON_CMD% -m pob_build_planner.cli --open --open-mode file --pob-executable "!POB_PATH!"
)
set "EXIT_CODE=%errorlevel%"
goto :finish

:open_specific
echo.
set /p "BUILD_ID=Enter the build id (e.g. toxic_rain_pathfinder): "
if "!BUILD_ID!"=="" (
    echo No build id supplied. Returning to menu.
    goto :prompt
)
call %PYTHON_CMD% -m pob_build_planner.cli --open-build "!BUILD_ID!" --open-mode file --pob-executable "!POB_PATH!"
set "EXIT_CODE=%errorlevel%"
goto :finish

:finish
echo.
if not "%EXIT_CODE%"=="0" (
    echo The planner exited with error code %EXIT_CODE%.
) else (
    echo Planner finished successfully.
)

goto :pause

:pause
echo.
pause

:end
endlocal
