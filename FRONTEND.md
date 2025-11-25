# Frontend Application

A simple web interface for querying Multi-Academy Trust newsletters using a ChatGPT-like interface.

## Features

- **MAT Selection**: View all Multi-Academy Trusts with their logos
- **Chat Interface**: Ask questions about a MAT's newsletters
- **AI-Powered Answers**: Uses GPT to answer questions based on newsletter content

## Running the Application

### 1. Install Dependencies

Make sure you have the latest dependencies installed:

```bash
pip install -e .
```

### 2. Start the Server

Run the web server:

```bash
python3 -m src.schools_scraper.cli serve
```

Or with custom host/port:

```bash
python3 -m src.schools_scraper.cli serve --host 0.0.0.0 --port 8000
```

For development with auto-reload:

```bash
python3 -m src.schools_scraper.cli serve --reload
```

### 3. Open in Browser

Open your browser and navigate to:

```
http://localhost:8000
```

## Usage

1. **Select a MAT**: Click on a Multi-Academy Trust card to view it
2. **Ask Questions**: Type your question in the chat input and press Enter
3. **Get Answers**: The AI will search through newsletters and provide answers

## Adding MAT Logos

To add a logo for a MAT:

1. Place the logo file in `frontend/static/logos/`
2. Update the `MATS` list in `src/schools_scraper/api.py` with the logo URL:

```python
MAT(
    id="your-mat-id",
    name="Your MAT Name",
    logo_url="/static/logos/your-logo.png",
)
```

## Project Structure

```
frontend/
├── index.html          # Main HTML file
├── static/
│   ├── css/
│   │   └── style.css  # Styling
│   ├── js/
│   │   └── app.js     # Frontend logic
│   └── logos/         # MAT logos
```

## API Endpoints

- `GET /api/mats` - List all MATs
- `GET /api/mats/{mat_id}` - Get a specific MAT
- `POST /api/ask` - Ask a question about a MAT's newsletters


