
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import requests, threading, time, json

DATABASE_URL="sqlite:///./portfolio.db"
engine=sa.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal=sessionmaker(bind=engine)
Base=declarative_base()

class Asset(Base):
    __tablename__='assets'
    id=sa.Column(sa.Integer, primary_key=True)
    name=sa.Column(sa.String)
    ticker=sa.Column(sa.String)
    quantity=sa.Column(sa.Float)
    cost_price=sa.Column(sa.Float)
    type=sa.Column(sa.String)
    updated_at=sa.Column(sa.DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

app=FastAPI(title="Portfolio API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AssetIn(BaseModel):
    name:str
    ticker:Optional[str]=None
    quantity:float
    cost_price:float
    type:Optional[str]="other"

def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

# --- Price Cache ---
price_cache={"forex":{}, "prices":{}}
CACHE_TTL=300  # 5 min

def fetch_forex():
    try:
        r=requests.get("https://api.exchangerate.host/latest?base=USD&symbols=EUR",timeout=5).json()
        return r["rates"]["EUR"]
    except: return 1

def fetch_price(ticker, t):
    try:
        if t=="crypto":
            url=f"https://api.coingecko.com/api/v3/simple/price?ids={ticker}&vs_currencies=eur"
            r=requests.get(url,timeout=5).json()
            return r.get(ticker,{}).get("eur")
        url=f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d"
        r=requests.get(url,timeout=5).json()
        return r["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except:
        return None

def refresh_prices():
    while True:
        session=SessionLocal()
        assets=session.query(Asset).all()
        fx=fetch_forex()
        price_cache["forex"]={"value":fx,"ts":time.time()}
        for a in assets:
            p=fetch_price(a.ticker,a.type)
            if p:
                price_cache["prices"][a.ticker]={"price":p,"ts":time.time()}
        session.close()
        time.sleep(CACHE_TTL)

threading.Thread(target=refresh_prices, daemon=True).start()

@app.get("/api/assets")
def list_assets(db:Session=Depends(get_db)):
    return db.query(Asset).all()

@app.post("/api/assets")
def add_asset(asset:AssetIn, db:Session=Depends(get_db)):
    a=Asset(**asset.dict())
    db.add(a); db.commit(); db.refresh(a)
    return {"id":a.id}

@app.put("/api/assets/{aid}")
def update_asset(aid:int, asset:AssetIn, db:Session=Depends(get_db)):
    a=db.query(Asset).filter(Asset.id==aid).first()
    if not a: raise HTTPException(404)
    for k,v in asset.dict().items(): setattr(a,k,v)
    a.updated_at=datetime.utcnow()
    db.commit()
    return {"ok":True}

@app.delete("/api/assets/{aid}")
def delete_asset(aid:int, db:Session=Depends(get_db)):
    a=db.query(Asset).filter(Asset.id==aid).first()
    if not a: raise HTTPException(404)
    db.delete(a); db.commit()
    return {"ok":True}

@app.get("/api/summary")
def summary(db:Session=Depends(get_db)):
    fx=price_cache["forex"].get("value",1)
    rows=db.query(Asset).all()
    total=0; data=[]
    for r in rows:
        p=price_cache["prices"].get(r.ticker,{}).get("price",r.cost_price)
        val=r.quantity*p
        total+=val
        data.append({"id":r.id,"name":r.name,"value":val,"price":p})
    for d in data:
        d["weight"]=round((d["value"]/total*100),2) if total>0 else 0
    return {"total_value":total,"forex_usd_eur":fx,"assets":data}
