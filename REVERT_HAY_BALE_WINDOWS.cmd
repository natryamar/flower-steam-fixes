@echo off
setlocal
pushd "%~dp0" >nul 2>nul
if errorlevel 1 goto directory_error
if exist "flower_haybale_fix.py" goto run
echo ERROR: Incomplete bundle. Extract the entire ZIP before running this launcher. 1>&2
set "flower_fix_exit=2"
goto finish

:run
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 flower_haybale_fix.py restore %*
set "flower_fix_exit=%errorlevel%"
goto finish

:use_python
python flower_haybale_fix.py restore %*
set "flower_fix_exit=%errorlevel%"

:finish
popd
echo.
pause
exit /b %flower_fix_exit%

:directory_error
echo ERROR: Could not open the bundle folder. Extract the ZIP to a local folder and try again. 1>&2
echo.
pause
exit /b 2
