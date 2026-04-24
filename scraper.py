import asyncio
import logging
import re
import json
import os
import sys
import traceback
from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import Stealth
from pydantic import BaseModel, Field

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("ali_scraper")

class AliExpressProduct(BaseModel):
    """AliExpress product data model"""
    title: str = Field(..., description="Product title")
    price: str = Field(..., description="Product price")
    currency: str = Field("RUB", description="Currency code")
    images: List[str] = Field(default_factory=list, description="List of product image URLs")
    description: str = Field("", description="Full product description")
    shipping_info: str = Field("Not found", description="Summary of shipping info")
    shipping_methods: List[Dict[str, str]] = Field(default_factory=list, description="List of shipping options")
    sku_variants: List[Dict[Any, Any]] = Field(default_factory=list, description="SKU variants")
    description_url: Optional[str] = Field(None, description="Source URL")

class AliExpressScraper:
    """Professional scraper for AliExpress Russia"""

    TRASH_PATTERNS = [
        '800x800', '100x100', '50x50', '120x120', '220x220', '480x480', 
        'placeholder', 'logo', 'recommend', 'similar', 'ae04.alicdn.com', 'data:image'
    ]

    def __init__(self, headless: bool = True, user_data_dir: str = "browser_profile"):
        self.headless = headless
        self.user_data_dir = os.path.abspath(user_data_dir)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def scrape(self, url: str) -> AliExpressProduct:
        """Main method to scrape a product URL"""
        async with async_playwright() as p:
            context = await self._setup_context(p)
            page = context.pages[0] if context.pages else await context.new_page()
            
            # Turbo mode: block unnecessary resources
            await page.route("**/*", self._request_filter)
            await Stealth().apply_stealth_async(page)
            
            api_data = []
            page.on("response", lambda res: asyncio.create_task(self._capture_api(res, api_data)))

            try:
                logger.info(f"Scraping started: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Даем странице больше времени на прогрузку скриптов
                await page.wait_for_timeout(5000)
                
                current_title = await page.title()
                logger.info(f"Page title: {current_title}")

                if "проверку" in current_title.lower() or "security" in current_title.lower():
                    logger.warning("CAPTCHA DETECTED! Taking screenshot...")
                    await page.screenshot(path="captcha_debug.png")
                    raise Exception("Blocked by Captcha")

                await self._interact_with_page(page)
                
                content = await page.content()
                data_json = await self._get_best_json(content, api_data)
                
                product_dict = await self._parse_all(page, data_json, url)
                
                return AliExpressProduct(**product_dict)

            except Exception as e:
                logger.error(f"Scraping error: {e}\n{traceback.format_exc()}")
                raise e
            finally:
                await context.close()

    async def _setup_context(self, p) -> BrowserContext:
        """Setup persistent browser context"""
        return await p.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )

    async def _request_filter(self, route):
        """Block images, fonts, and analytics for speed"""
        bad_types = ["image", "font", "media", "other"]
        if route.request.resource_type in bad_types:
            await route.abort()
        else:
            await route.continue_()

    async def _interact_with_page(self, page: Page):
        """Emulate user behavior to trigger lazy loading"""
        await page.mouse.wheel(0, 1000)
        await page.wait_for_timeout(1000)
        
        # Try to expand description
        try:
            btn = await page.query_selector('text="Полное описание", text="Описание"')
            if btn:
                await btn.click(force=True)
                await page.wait_for_timeout(1500)
        except: pass

    async def _capture_api(self, response, storage: list):
        """Capture API JSON responses"""
        if any(x in response.url for x in ["api", "h5api"]):
            try:
                data = await response.json()
                if data: storage.append(data)
            except: pass

    async def _get_best_json(self, html: str, api_data: list) -> Optional[dict]:
        """Find the most complete product JSON"""
        for entry in api_data:
            if entry.get("data", {}).get("productInfoComponent"):
                return entry
        
        patterns = [
            r'window\.runParams\s*=\s*(\{.*?\});',
            r'id="__AER_DATA__"\s*type="application/json">(.*?)</script>'
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1).strip())
                except: continue
        return None

    async def _parse_all(self, page: Page, data: Optional[dict], url: str) -> dict:
        """Aggregate data from JSON and DOM"""
        methods = await self._extract_shipping_methods(page)
        res = {
            "title": await self._extract_title(page, data),
            "price": await self._extract_price(page, data),
            "currency": data.get("data", {}).get("priceComponent", {}).get("currencyCode", "RUB") if data else "RUB",
            "images": await self._extract_images(page, data),
            "description": await self._extract_description(page),
            "shipping_methods": methods,
            "shipping_info": self._derive_shipping_info(methods),
            "sku_variants": data.get("data", {}).get("skuComponent", {}).get("skuPriceList", []) if data else [],
            "description_url": url
        }
        return res

    async def _extract_title(self, page: Page, data: Optional[dict]) -> str:
        if data:
            comp = data.get("data", {}).get("productInfoComponent", {}) or data.get("productInfo", {})
            if comp.get("subject"): return comp["subject"]
        title = await page.title()
        return title.split('|')[0].strip() if '|' in title else title

    async def _extract_price(self, page: Page, data: Optional[dict]) -> str:
        if data:
            c = data.get("data", {}).get("priceComponent", {})
            v = c.get("formatPrice") or data.get("priceInfo", {}).get("formattedPrice")
            if v: return v
        
        selectors = [
            '[class*="Price--currentPriceText"]', 
            '[class*="snow-price_SnowPrice__mainM"]',
            '[class*="Price--priceText"]',
            '.snow-price_SnowPrice__mainM__1p9jc'
        ]
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    text = await elem.inner_text()
                    if any(c in text for c in ['₽', 'руб']): return text.strip().split('\n')[0]
            except: continue

        try:
            content = await page.inner_text('body')
            match = re.search(r'(\d[\d\s,.]*(?:руб|₽))', content)
            if match: return match.group(1).strip()
        except: pass
        
        return "Not found"

    async def _extract_images(self, page: Page, data: Optional[dict]) -> List[str]:
        raw = []
        if data:
            raw = data.get("data", {}).get("imageComponent", {}).get("imagePathList", []) or \
                  data.get("productInfo", {}).get("imagePathList", [])
        
        if not raw:
            gallery = await page.query_selector('[class*="Gallery"], [class*="ProductImage"]')
            container = gallery if gallery else page
            imgs = await container.query_selector_all('img')
            raw = [await i.get_attribute('src') for i in imgs]
        
        return self._clean_images(raw)

    def _clean_images(self, urls: List[str]) -> List[str]:
        seen, cleaned = set(), []
        for url in urls:
            if not url or 'data:image' in url: continue
            base = re.sub(r'(_\d+x\d+\.(?:jpg|png|jpeg))$', '', url).split('.jpg_')[0].split('.png_')[0]
            if not base.endswith(('.jpg', '.png', '.jpeg', '.webp')) and '.jpg' in url:
                base = url.split('.jpg')[0] + '.jpg'
            
            final = base if base.startswith('http') else 'https:' + base
            if final not in seen and not any(p in final.lower() for p in self.TRASH_PATTERNS):
                seen.add(final)
                cleaned.append(final)
        return cleaned[:25]

    async def _extract_shipping_methods(self, page: Page) -> List[Dict[str, str]]:
        methods = []
        items = await page.query_selector_all('[class*="DeliveryMethodItem__item"], [class*="Delivery--item"]')
        for item in items:
            try:
                n = await item.query_selector('[class*="groupName"], [class*="title"]')
                p = await item.query_selector('[class*="price"], [class*="free"]')
                if n and p:
                    methods.append({
                        "method": (await n.inner_text()).strip(),
                        "price": (await p.inner_text()).strip()
                    })
            except: continue
        return methods

    def _derive_shipping_info(self, methods: List[Dict]) -> str:
        if not methods: return "Not found"
        post = next((m for m in methods if "почтой" in m['method'].lower()), methods[0])
        return f"Post: {post['price']}" if "почтой" in post['method'].lower() else post['price']

    async def _extract_description(self, page: Page) -> str:
        selectors = ['[id="content_anchor"]', '[class*="SnowProductContent"]', '[class*="ProductDescription"]']
        for sel in selectors:
            dom = await page.query_selector(sel)
            if dom: return (await dom.inner_text()).strip()
        return ""
