@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul
cd /d "%~dp0"
cl /nologo /O2 /MT /EHa /W3 /LD ee_fps.cpp /Fe:..\ee_fps.dll /link /NOLOGO user32.lib kernel32.lib
