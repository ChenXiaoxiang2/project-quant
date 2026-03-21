import pandas as pd

class RiskManager:
    def __init__(self, account_size, max_drawdown=0.15, max_risk_pct=0.02):
        self.account_size = account_size
        self.max_drawdown = max_drawdown
        self.max_risk_pct = max_risk_pct
        self.peak_equity = account_size
        
    def calculate_position(self, entry_price, stop_loss_price):
        """基于ATR的仓位管理"""
        risk_amount = self.account_size * self.max_risk_pct
        price_diff = abs(entry_price - stop_loss_price)
        if price_diff == 0:
            return 0
        position_size = risk_amount / price_diff
        return position_size
    
    def check_drawdown(self, current_equity):
        """回撤熔断检查"""
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        drawdown = (self.peak_equity - current_equity) / self.peak_equity
        if drawdown > self.max_drawdown:
            return False # 触发熔断
        return True
