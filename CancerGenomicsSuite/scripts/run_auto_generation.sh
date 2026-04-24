#!/bin/bash
# Auto-Generation Script Runner for Unix/Linux/macOS
# This script provides easy access to auto-generation commands

echo "Cancer Genomics Analysis Suite - Auto-Generation Scripts"
echo "========================================================"

if [ $# -eq 0 ]; then
    echo "Usage: ./run_auto_generation.sh [command]"
    echo ""
    echo "Available commands:"
    echo "  setup          - Run full setup process"
    echo "  blast-db       - Generate BLAST databases only"
    echo "  mock-data      - Generate mock data only"
    echo "  check-deps     - Check dependencies"
    echo "  install-deps   - Install missing dependencies"
    echo "  clean          - Clean generated files"
    echo "  help           - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_auto_generation.sh setup"
    echo "  ./run_auto_generation.sh blast-db"
    echo "  ./run_auto_generation.sh mock-data"
    exit 1
fi

if [ "$1" = "help" ]; then
    echo "Auto-Generation Scripts Help"
    echo "============================"
    echo ""
    echo "This script provides easy access to auto-generation functionality."
    echo ""
    echo "Commands:"
    echo "  setup          - Complete setup including dependencies and data generation"
    echo "  blast-db       - Generate BLAST databases for cancer genomics analysis"
    echo "  mock-data      - Generate comprehensive mock datasets"
    echo "  check-deps     - Verify all required dependencies are installed"
    echo "  install-deps   - Install missing Python packages"
    echo "  clean          - Remove all generated files and directories"
    echo ""
    echo "For more detailed information, see README.md"
    exit 0
fi

echo "Running command: $1"
echo ""

case "$1" in
    "setup")
        python setup_auto_generation.py full-setup
        ;;
    "blast-db")
        python setup_auto_generation.py blast-databases
        ;;
    "mock-data")
        python setup_auto_generation.py mock-data
        ;;
    "check-deps")
        python setup_auto_generation.py check-dependencies
        ;;
    "install-deps")
        python setup_auto_generation.py install-dependencies
        ;;
    "clean")
        echo "Cleaning generated files..."
        rm -rf ../blast_databases
        rm -rf ../data
        rm -rf ../logs
        echo "Cleanup completed."
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use './run_auto_generation.sh help' for available commands."
        exit 1
        ;;
esac

echo ""
echo "Command completed."
