# HIkyuu-UI Project Overview

## Purpose
HIkyuu-UI is a comprehensive quantitative trading platform built on Python. It provides:
- Stock data analysis and visualization
- Technical indicator calculations
- Backtesting capabilities
- Plugin-based architecture for data sources
- Real-time market data integration

## Tech Stack
- **Language**: Python 3.x
- **GUI Framework**: PyQt/PySide
- **Data Processing**: pandas, numpy
- **Database**: SQLite, DuckDB
- **Visualization**: matplotlib, pyqtgraph
- **Architecture**: Microservices with dependency injection

## Key Components
- Core services (15 main services after refactoring)
- Plugin system for data sources
- Event-driven architecture
- Unified data management system
- Performance monitoring and optimization

## Entry Points
- `main.py` - Main application entry point
- `quick_start.py` - Quick startup script
- `api_server.py` - API server mode