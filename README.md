# AliExpress Product Scraper

High-performance product data extractor for AliExpress Russia based on Playwright.

## Features
- Full Metadata Extraction: Captures titles, prices, currencies, and images.
- Detailed Shipping Information: Extracts all available shipping methods and identifies the primary postal option.
- Description Parsing: Retrieves full product descriptions from the DOM or nested frames.
- Performance Optimization: Includes resource blocking (images, fonts, analytics) and optimized page load strategies.
- Stealth Mode: Implements stealth plugins to minimize detection by anti-bot systems.
- API Support: Includes a FastAPI-based server for integration with other services.

## Requirements
- Python 3.10 or higher
- Playwright
- FastAPI / Uvicorn

## Installation

1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

## Configuration

Create a `.env` file in the root directory (you can use `.env.example` as a template):
```bash
API_KEY=your_secret_token_here
```

## Usage

### Running as an API Service
Start the FastAPI server:
```bash
python main.py
```
The service will be available at `http://0.0.0.0:8000`.

### Authentication
All API requests require the `X-API-Key` header.
```http
POST /api/v1/parse
X-API-Key: your_secret_token_here
Content-Type: application/json

{
  "url": "https://aliexpress.ru/item/PRODUCT_ID.html"
}
```

### Importing as a Module
```python
import asyncio
from scraper import AliExpressScraper

async def main():
    scraper = AliExpressScraper(headless=True)
    product = await scraper.scrape("https://aliexpress.ru/item/PRODUCT_ID.html")
    print(f"Title: {product.title}")
    print(f"Price: {product.price} {product.currency}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Project Structure
- `scraper.py`: Core logic for web scraping and data extraction.
- `main.py`: FastAPI server implementation.
- `example.py`: Demonstration of direct module usage.
- `requirements.txt`: List of required Python packages.
- `.gitignore`: Rules for excluding temporary files from the repository.
