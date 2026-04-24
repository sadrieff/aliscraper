import asyncio
from scraper import AliExpressScraper

async def main():
    # 1. Создаем экземпляр парсера
    # headless=False позволит тебе видеть, как открывается браузер (удобно для тестов)
    scraper = AliExpressScraper(headless=True)
    
    url = "https://aliexpress.ru/item/1005007188393531.html"
    
    print(f"--- Начинаем парсинг {url} ---")
    
    try:
        # 2. Получаем данные
        product = await scraper.scrape(url)
        
        # 3. Используем данные
        print(f"Название: {product.title}")
        print(f"Цена: {product.price} {product.currency}")
        print(f"Доставка: {product.shipping_info}")
        print(f"Описание (первые 100 символов): {product.description[:100]}...")
        print(f"Количество картинок: {len(product.images)}")
        
        # Можно сохранить в JSON (Pydantic V2 style)
        with open("product_data.json", "w", encoding="utf-8") as f:
            f.write(product.model_dump_json(indent=4))
            print("\nДанные сохранены в product_data.json")

    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
