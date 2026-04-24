import asyncio
import sys
from scraper import AliExpressScraper

# Fix for Windows console encoding
if sys.platform == "win32":
    try:
        import codecs
        sys.stdout.reconfigure(encoding='utf-8')
    except: pass

async def main():
    scraper = AliExpressScraper(headless=True)
    url = "https://aliexpress.ru/item/1005007188393531.html"
    
    print(f"--- Starting scraping: {url} ---")
    
    try:
        product = await scraper.scrape(url)
        
        # Save to JSON FIRST (to avoid console encoding issues)
        output_file = "product_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(product.model_dump_json(indent=4))
        
        print(f"Data successfully saved to {output_file}")
        
        # Now try to print to console
        print(f"Title: {product.title}")
        print(f"Price: {product.price} {product.currency}")
        print(f"Images count: {len(product.images)}")

    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
