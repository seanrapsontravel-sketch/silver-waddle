# Schools Scraper

A Python package for scraping websites, storing data in a database, and running analysis with GPT integration.

## Features

- **Web Scraping**: HTTP client with retry logic and rate limiting
- **Database**: DuckDB for fast analytical queries
- **Analysis**: Built-in data analysis utilities
- **GPT Integration**: OpenAI API integration for data insights
- **CLI**: Command-line interface for all operations

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e .
# Or for development:
pip install -e ".[dev]"
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

## Usage

### Scraping

Scrape a website and store data:
```bash
schools-scraper scrape https://example.com --table-name schools
```

### Database Queries

Execute SQL queries:
```bash
schools-scraper query "SELECT * FROM schools LIMIT 10"
```

Save query results:
```bash
schools-scraper query "SELECT * FROM schools" --output data/exports/schools.csv
```

### Analysis

Get descriptive statistics:
```bash
schools-scraper analyze schools
```

Count by column:
```bash
schools-scraper analyze schools --column state
```

### GPT Integration

Send a prompt:
```bash
schools-scraper gpt-prompt "What are the best practices for web scraping?"
```

Analyze a table with GPT:
```bash
schools-scraper gpt-analyze schools --question "What patterns do you see in this data?"
```

### List Tables

View all tables in the database:
```bash
schools-scraper list-tables
```

## Project Structure

```
.
├── src/
│   └── schools_scraper/
│       ├── __init__.py
│       ├── cli.py          # CLI interface
│       ├── config.py       # Configuration
│       ├── database.py     # Database management
│       ├── scraper.py      # Web scraping
│       ├── analysis.py     # Data analysis
│       ├── gpt.py          # GPT integration
│       └── io.py           # I/O utilities
├── tests/                  # Test files
├── data/                   # Data directory
│   ├── schools.db         # Database file
│   └── exports/           # CSV/Parquet exports
├── .env.example           # Environment template
├── pyproject.toml         # Project configuration
└── README.md
```

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black src/ tests/
ruff check src/ tests/
```

## License

MIT


