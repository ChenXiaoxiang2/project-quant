import pandas as pd
import numpy as np

class AlphaFactors:
    """量化策略核心因子计算模块"""
    
    @staticmethod
    def calculate_rsi(df, period=14):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_momentum(df, period=5):
        return df['close'].pct_change(period)

    @staticmethod
    def calculate_score(df):
        """计算综合选股评分"""
        rsi = AlphaFactors.calculate_rsi(df)
        mom = AlphaFactors.calculate_momentum(df)
        # 简单评分加权
        score = (rsi * 0.4) + (mom * 100 * 0.6)
        return score
