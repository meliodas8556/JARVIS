@echo off
setlocal
set OWNER_GITHUB=%1
if "%OWNER_GITHUB%"=="" set OWNER_GITHUB=darkex
set RELEASE_SIGNATURE=%2

python "%~dp0build_release_locked.py" %OWNER_GITHUB% %RELEASE_SIGNATURE%
endlocal
