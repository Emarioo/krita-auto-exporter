@echo off
@setlocal enabledelayedexpansion

mkdir bin 2> nul

del bin\auto_exporter.zip
del auto_exporter\__pycache__
rar a -r - bin/auto_exporter.zip auto_exporter.desktop auto_exporter/
