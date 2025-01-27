from pydantic import BaseModel


class CoingeckoMarketData(BaseModel):
    coin_id: str


class BinancePriceData(BaseModel):
    symbol: str
