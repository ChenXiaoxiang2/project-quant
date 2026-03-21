import pandas as pd
import numpy as np
import yaml
import os

class TrendStrategy:
    def __init__(self, config_path=None):
        if config_path is None:
            # 自动寻找项目根目录下的 config/strategy_params.yaml
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_path, 'config', 'strategy_params.yaml')
        with open(config_path, 'r') as f:
            self.params = yaml.safe_load(f)['trend_strategy']

    def calculate_indicators(self, df):
        """计算MA, MACD, ADX"""
        # MA
        df[f'ma{self.params["ma_short"]}'] = df['close'].rolling(self.params["ma_short"]).mean()
        df[f'ma{self.params["ma_mid"]}'] = df['close'].rolling(self.params["ma_mid"]).mean()
        df[f'ma{self.params["ma_long"]}'] = df['close'].rolling(self.params["ma_long"]).mean()
        
        # MACD (12, 26, 9)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['diff'] = ema12 - ema26
        df['dea'] = df['diff'].ewm(span=9, adjust=False).mean()
        df['macd'] = 2 * (df['diff'] - df['dea'])
        
        # ADX (14天)
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_di = 100 * (pd.Series(plus_dm).rolling(14).mean() / tr.rolling(14).mean())
        minus_di = 100 * (pd.Series(minus_dm).rolling(14).mean() / tr.rolling(14).mean())
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(14).mean()
        
        return df

    def generate_signal(self, df):
        """生成买卖信号"""
        # 简化版逻辑：均线多头 + ADX > 阈值
        last_row = df.iloc[-1]
        if (last_row[f'ma{self.params["ma_short"]}'] > last_row[f'ma{self.params["ma_mid"]}'] > last_row[f'ma{self.params["ma_long"]}']) \
           and (last_row['adx'] > self.params['adx_threshold']):
            return 'BUY'
        return 'HOLD'
