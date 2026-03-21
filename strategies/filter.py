import pandas as pd
import numpy as np

class StockFilter:
    def __init__(self, adx_threshold=25, min_turnover=0.01):
        self.adx_threshold = adx_threshold
        self.min_turnover = min_turnover

    def filter(self, df):
        """
        股票筛选逻辑：
        1. ADX > 阈值 (趋势市场)
        2. 换手率过滤 (去除极低流动性)
        3. 去除高波动 (如波动率过高)
        """
        # 假设 df 中有 'adx', 'turnover', 'volatility' 列
        
        # 1. ADX 过滤
        filtered_df = df[df['adx'] > self.adx_threshold]
        
        # 2. 流动性过滤
        filtered_df = filtered_df[filtered_df['turnover'] > self.min_turnover]
        
        # 3. 去除高波动（假设波动率是 daily_return 的标准差）
        # filtered_df = filtered_df[filtered_df['volatility'] < 0.05]
        
        return filtered_df
