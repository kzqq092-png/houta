# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FactorWeave-Quant 2.0 is a Python-based quantitative trading system with a plugin architecture, multi-data source support, real-time processing, and AI-powered analysis capabilities.

## Development Commands

### Running the Application
```bash
python main.py
```

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m performance   # Performance benchmarks
pytest -m network       # Tests requiring network access
pytest -m database      # Database tests
pytest -m ai            # AI model tests
pytest -m ui            # UI component tests

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test files
python test_tongdaxin_simple.py
python test_official_akshare_integration.py
```

### Development Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Development server with hot reload (if available)
python main.py --dev-mode
```

## Core Architecture

### Service Container System
The application uses a dependency injection container located in `core/containers/`:
- **ServiceContainer**: Main DI container with service registry
- **ServiceScope**: SINGLETON, SCOPED, TRANSIENT lifecycle management
- **ServiceRegistry**: Service registration and health monitoring
- **Service Bootstrap**: `core/services/service_bootstrap.py` initializes 40+ services

### Event-Driven Architecture
- **EventBus**: Async event system in `core/events/`
- Real-time data streaming with deduplication
- Loose coupling between components
- Error handling and recovery mechanisms

### Plugin System
Dynamic plugin architecture with standardized interfaces:
- **Plugin Manager**: `core/plugin_manager.py` handles plugin lifecycle
- **Plugin Types**: DATA_SOURCE, INDICATOR, STRATEGY, ANALYSIS, UI_COMPONENT
- **Plugin States**: CREATED → INITIALIZING → INITIALIZED → CONNECTING → CONNECTED/FAILED
- **Auto-discovery**: Plugins auto-discovered from `plugins/` directories

### Key Directories
- `core/`: Business logic, services, containers, events
- `gui/`: PyQt5 UI components, widgets, dialogs, themes
- `plugins/`: Extensible plugin system (data_sources, indicators, strategies)
- `db/`: Database models, initialization, migrations
- `utils/`: Shared utilities, configuration management
- `config/`: Application and plugin configuration files
- `tests/`: Organized test suites by category

### Service Architecture Patterns
All services inherit from base classes:
- **BaseService**: Foundation for all services
- **AsyncBaseService**: Async operations support
- **ConfigurableService**: Configuration-driven services
- **CacheableService**: Built-in caching functionality

### Data Architecture
- **UnifiedDataManager**: Centralized data access interface
- **Multi-database Support**: DuckDB (analytics), SQLite (configuration)
- **Adaptive Connection Pooling**: Performance optimization
- **Data Quality Monitoring**: Validation and error handling

## Development Guidelines

### Code Style (from .cursorrules)
- Follow PEP 8 Python style guidelines
- Use type hints for better code quality
- Write detailed docstrings and comments
- Implement proper error handling and logging
- Use modular design with clear separation of concerns
- Leverage Python standard library and quality third-party packages

### Service Development
When creating new services:
1. Inherit from appropriate base class (BaseService, AsyncBaseService, etc.)
2. Register service in `core/services/service_bootstrap.py`
3. Use dependency injection for service dependencies
4. Implement health monitoring for production services
5. Add comprehensive tests for all service functionality

### Plugin Development
When creating plugins:
1. Implement appropriate interface (IDataSourcePlugin, IIndicatorPlugin, etc.)
2. Provide complete PluginMetadata
3. Follow lifecycle management patterns
4. Handle initialization and connection failures gracefully
5. Test plugin loading and unloading

### Configuration Management
- Use JSON-based configuration in `config/` directory
- Environment variables via `.env` file
- Configuration validation using `utils/config_types.py`
- Service-specific configuration in respective directories

### Database Operations
- Use database abstraction layer in `core/database/`
- Follow model definitions in `db/models/`
- Use connection pooling for performance
- Implement proper error handling for database operations

## Testing Strategy

### Test Organization
- Unit tests for individual components
- Integration tests for service interactions
- Performance tests for optimization
- Network tests for external API integration
- Database tests for data layer validation
- AI tests for machine learning components
- UI tests for interface components

### Coverage Requirements
- Minimum 80% code coverage
- Comprehensive test coverage for critical services
- Automated regression testing
- Performance baseline tracking

## Important Notes

### Asynchronous Architecture
The application heavily uses AsyncIO with PyQt5 integration via qasync. Understanding async/await patterns is essential for working with most services.

### Multi-Asset Support
The system supports stocks, crypto, forex, futures, and other asset classes through the unified data management layer.

### Real-Time Data Processing
The system is designed for real-time data ingestion and processing with configurable write intervals and event-driven updates.

### AI Integration
The system includes AI-powered features including prediction models, sentiment analysis, and intelligent configuration recommendations.

### Performance Considerations
- WebGPU hardware acceleration for computationally intensive tasks
- Multi-level caching for data access optimization
- Connection pooling for database operations
- Async processing for non-blocking operations

This architecture provides a robust, extensible foundation for quantitative trading applications with strong separation of concerns, comprehensive testing, and production-ready deployment capabilities.