# Changelog

## 2025.9.2.1 [in development]
### Changed
- Versioning scheme changed to `year.month.day.increment`.

### CI/CD
- CI/CD pipeline modernized and refactored.

## 1.0.0 (2025-09-01)
Initial fork release.

### Added
- DFM plugin for OneOfSchema inlining.
- Per-schema controls for aggressive mode and context isolation.
- Aggressive instance caching for dump/load.
- Low-copy type field removal for default `get_data_type`.
- Grouped `many=True` load path for default `get_data_type`.
- Extensive test suite covering all features and behaviors.

### Changed
- Python support: 3.11+.
- Updated `pyproject.toml` with DFM plugin entry point.

### Documentation
- Updated README with DFM plugin notes and per-schema controls.
- Updated docs with DFM plugin notes and per-schema controls.
