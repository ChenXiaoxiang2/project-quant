import os
import sys
# Debug path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from data.data_loader import AKShareDataLoader
from strategies.trend_strategy import TrendStrategy
from strategies.filter import StockFilter

def run_eod_summary(mock_mode=True):
    if mock_mode:
        print("--- 正在使用模拟数据运行系统 (跳过网络请求) ---")
        # 生成模拟数据，结构与 AKShare 兼容
        data = {
            'ts_code': [f'600{i:03}' for i in range(100)],
            'name': [f'测试股票{i}' for i in range(100)],
            'pct_chg': np.random.uniform(-0.1, 0.1, 100),
            'close': np.random.uniform(10, 100, 100),
            'adx': np.random.uniform(10, 50, 100),
            'turnover': np.random.uniform(0, 0.05, 100)
        }
        df = pd.DataFrame(data)
    else:
        # 真实数据逻辑
        print("--- 正在连接真实行情接口 ---")
        loader = AKShareDataLoader()
        df = loader.fetch_daily_all()
        df['pct_chg'] = pd.to_numeric(df['pct_chg'], errors='coerce')
    
    # 2. Summary
    top_gainers = df.nlargest(10, 'pct_chg')
    print("\n--- 今日涨幅前十 ---")
    print(top_gainers[['ts_code', 'name', 'pct_chg', 'close']])
    
    # 3. Stock Selection & Recommendation
    # 使用过滤器与策略
    filter = StockFilter()
    
    # 示例过滤
    selected = filter.filter(df)
    
    print("\n--- 趋势型推荐名单 (基于当前行情候选) ---")
    print(selected[['ts_code', 'name', 'close', 'pct_chg']].head())

if __name__ == "__main__":
    # 默认为模拟模式，若要使用真实接口请改为 False
    run_eod_summary(mock_mode=True)
