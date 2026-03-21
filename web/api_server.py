import sys
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_loader import StockDataLoader
from trading.risk_manager import RiskManager
from tasks.stock_analyzer import StockAnalyzer

app = FastAPI(title="量化交易系统 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"message": "量化交易系统 API 运行正常"}


ACCOUNT_SIZE = 100000.0


@app.post("/api/trade")
def place_order(data: dict = Body(...)):
    ts_code = data.get("ts_code")
    side = data.get("side")
    price = data.get("price")

    if not price:
        raise HTTPException(status_code=400, detail="缺少价格参数")

    risk_manager = RiskManager(account_size=ACCOUNT_SIZE)
    stop_loss = price * 0.95
    position = risk_manager.calculate_position(price, stop_loss)

    if position <= 0:
        raise HTTPException(status_code=400, detail="风险校验失败，禁止下单")

    return {"status": "success", "message": f"{side} {ts_code} 成功", "size": position}


@app.get("/reports/latest")
def get_latest_report():
    reports_dir = "./reports"
    if not os.path.exists(reports_dir):
        raise HTTPException(status_code=404, detail="报告目录不存在")
    reports = [f for f in os.listdir(reports_dir) if f.endswith('.md')]
    if not reports:
        raise HTTPException(status_code=404, detail="未找到复盘报告")
    latest_report = sorted(reports)[-1]
    with open(os.path.join(reports_dir, latest_report), 'r', encoding='utf-8') as f:
        content = f.read()
    return {"filename": latest_report, "content": content}


@app.get("/stocks/query/{code}")
def query_stock(code: str):
    """
    查询指定股票实时行情
    code 格式: '600519' (6位代码，自动识别沪/深)
    """
    loader = StockDataLoader()
    try:
        # 自动补充市场前缀
        if not code.startswith(('sh', 'sz')):
            code = 'sh' + code if code.startswith(('6', '5', '9')) else 'sz' + code

        quote = loader.get_single_quote(_normalize_ts_code(code))
        return quote
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据查询失败: {str(e)}")


@app.get("/stocks/realtime")
def query_multiple_stocks(codes: str = ""):
    """
    批量查询多只股票实时行情
    codes: 逗号分隔的代码列表，如 '600519,000001,600036'
    """
    if not codes:
        raise HTTPException(status_code=400, detail="缺少 codes 参数")

    loader = StockDataLoader()
    code_list = codes.split(',')

    # 补充市场前缀
    normalized = []
    for c in code_list:
        c = c.strip()
        if not c.startswith(('sh', 'sz')):
            normalized.append(('sh' + c if c.startswith(('6', '5', '9')) else 'sz' + c))
        else:
            normalized.append(c)

    try:
        df = loader.get_realtime_quotes(normalized)
        return df.to_dict(orient='records')
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stocks/history/{ts_code}")
def query_history(
    ts_code: str,
    start_date: str = "20240101",
    end_date: str = "",
):
    """
    查询个股历史K线
    ts_code: '000001.SZ' 或 '600519.SH' 格式
    """
    if not end_date:
        from datetime import datetime
        end_date = datetime.now().strftime('%Y%m%d')

    loader = StockDataLoader()
    try:
        df = loader.get_historical(ts_code, start_date, end_date)
        return df.to_dict(orient='records')
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market/industry")
def query_industry_board():
    """查询行业板块涨跌"""
    loader = StockDataLoader()
    try:
        df = loader.get_industry_board()
        return df.to_dict(orient='records')
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stocks/analyze/{code}")
def analyze_stock(code: str):
    """
    综合分析指定股票，生成完整报告
    code: '600519' 或 '600519.SH'
    """
    try:
        analyzer = StockAnalyzer()
        result = analyzer.analyze(code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


def _normalize_ts_code(code: str) -> str:
    """将 6 位代码转换为 ts_code 格式"""
    if '.' in code:
        return code
    market = 'SH' if code.startswith(('6', '5', '9')) else 'SZ'
    return f"{code}.{market}"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
