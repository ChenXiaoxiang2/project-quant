import backtrader as bt

class BacktestEngine:
    def __init__(self, strategy_class, data_path, cash=100000.0):
        self.cerebro = bt.Cerebro()
        self.cerebro.addstrategy(strategy_class)
        
        # 加载数据 (示例)
        data = bt.feeds.GenericCSVData(
            dataname=data_path,
            dtformat='%Y%m%d',
            openinterest=-1
        )
        self.cerebro.adddata(data)
        self.cerebro.broker.setcash(cash)
        
    def run(self):
        print("开始回测...")
        self.cerebro.run()
        print("回测结束。")
        self.cerebro.plot()
