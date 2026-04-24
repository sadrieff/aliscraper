import os
import traceback
import uvicorn
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from scraper import AliExpressScraper, AliExpressProduct

# Load environment variables
load_dotenv()

app = FastAPI(title="AliExpress Scrapper API")
scraper = AliExpressScraper(headless=True)

# API Key security
API_KEY = os.getenv("API_KEY")

async def verify_token(x_api_key: str = Header(...)):
    # If API_KEY is not set in .env, use a fallback for debugging
    valid_token = API_KEY or "debug_token"
    if x_api_key != valid_token:
        raise HTTPException(status_code=403, detail="Invalid API Key")

class ProductRequest(BaseModel):
    url: str

@app.post("/api/v1/parse", response_model=AliExpressProduct, dependencies=[Depends(verify_token)])
async def parse_endpoint(request: ProductRequest):
    try:
        return await scraper.scrape(request.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=traceback.format_exc())

if __name__ == "__main__":
    # Bind to 0.0.0.0 for VPS access
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
