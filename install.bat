@echo off
@setlocal enabledelayedexpansion

set PLUGIN_FOLDER=%APPDATA%\krita\pykrita

del /Q %PLUGIN_FOLDER%\auto_exporter\
del /Q %PLUGIN_FOLDER%\auto_exporter.desktop

xcopy /S /Q /Y auto_exporter %APPDATA%\krita\pykrita\auto_exporter\
copy auto_exporter.desktop %PLUGIN_FOLDER%\auto_exporter.desktop
