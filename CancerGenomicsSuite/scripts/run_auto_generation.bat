@echo off
REM Auto-Generation Script Runner for Windows
REM This batch file provides easy access to auto-generation commands

echo Cancer Genomics Analysis Suite - Auto-Generation Scripts
echo ========================================================

if "%1"=="" (
    echo Usage: run_auto_generation.bat [command]
    echo.
    echo Available commands:
    echo   setup          - Run full setup process
    echo   blast-db       - Generate BLAST databases only
    echo   mock-data      - Generate mock data only
    echo   check-deps     - Check dependencies
    echo   install-deps   - Install missing dependencies
    echo   clean          - Clean generated files
    echo   help           - Show this help message
    echo.
    echo Examples:
    echo   run_auto_generation.bat setup
    echo   run_auto_generation.bat blast-db
    echo   run_auto_generation.bat mock-data
    goto :eof
)

if "%1"=="help" (
    echo Auto-Generation Scripts Help
    echo ============================
    echo.
    echo This script provides easy access to auto-generation functionality.
    echo.
    echo Commands:
    echo   setup          - Complete setup including dependencies and data generation
    echo   blast-db       - Generate BLAST databases for cancer genomics analysis
    echo   mock-data      - Generate comprehensive mock datasets
    echo   check-deps     - Verify all required dependencies are installed
    echo   install-deps   - Install missing Python packages
    echo   clean          - Remove all generated files and directories
    echo.
    echo For more detailed information, see README.md
    goto :eof
)

echo Running command: %1
echo.

if "%1"=="setup" (
    python setup_auto_generation.py full-setup
) else if "%1"=="blast-db" (
    python setup_auto_generation.py blast-databases
) else if "%1"=="mock-data" (
    python setup_auto_generation.py mock-data
) else if "%1"=="check-deps" (
    python setup_auto_generation.py check-dependencies
) else if "%1"=="install-deps" (
    python setup_auto_generation.py install-dependencies
) else if "%1"=="clean" (
    echo Cleaning generated files...
    if exist "..\blast_databases" rmdir /s /q "..\blast_databases"
    if exist "..\data" rmdir /s /q "..\data"
    if exist "..\logs" rmdir /s /q "..\logs"
    echo Cleanup completed.
) else (
    echo Unknown command: %1
    echo Use 'run_auto_generation.bat help' for available commands.
    exit /b 1
)

echo.
echo Command completed.
pause
