@echo off
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\rebuild_frontend.ps1" %*
