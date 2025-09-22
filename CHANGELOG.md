# Changelog

All notable changes to **CosmicReseller** will be documented in this file.  
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2025-09-21
### Added
- Initial public release of **CosmicReseller**
- Core functionality:
  - eBay API scraper
  - Facebook Marketplace scraper (Playwright + profile persistence)
  - Price parsing & threshold filtering (`pricing.py`)
- Telegram bot integration with alerts
- Quart-based Web UI for search and results
- Logging configuration (`logger.py`)
- Orchestrator (`main.py`) to run bot + web together
- Unit & integration tests with pytest
- Docker support (`Dockerfile`, `docker-compose.yml`, `.dockerignore`)
- Project metadata (`pyproject.toml`, `.gitignore`, `.env.example`)
- Documentation (`README.md`, `docs/` with placeholders)
- MIT License

---

## Unreleased
- [ ] CI/CD workflow
- [ ] More scrapers (e.g., other marketplaces)
- [ ] Extended Web UI features
