# Suggested Commands for FactorWeave-Quant Development

## Running the Application
```bash
python main.py                    # Start main application
python quick_start.py            # Quick start mode
python api_server.py             # API server mode
```

## Testing
```bash
python -m pytest                 # Run all tests
python -m pytest tests/final/    # Run integration tests
python -m pytest tests/performance/  # Run performance tests
```

## Code Quality
```bash
# No specific linting commands found in project
# Standard Python tools can be used:
python -m flake8 .
python -m black .
python -m isort .
```

## Windows-specific Commands
```powershell
Get-ChildItem -Recurse -Name "*.py"  # Find Python files
Select-String -Pattern "pattern" -Path "*.py"  # Search in files
tasklist | findstr python        # Find Python processes
taskkill /F /IM python.exe      # Kill Python processes
```

## Project Maintenance
```bash
python cleanup_invalid_code.py   # Clean up backup files
python analyze_cleanup_candidates.py  # Analyze cleanup candidates
python verify_system_integration.py   # Verify system integration
```