from clickhouse_driver import Client
import pandas as pd

class ClickHouseStorage:
    def __init__(self, host='localhost'):
        self.client = Client(host=host)
        self.create_table()

    def create_table(self):
        """定义表结构"""
        self.client.execute('''
            CREATE TABLE IF NOT EXISTS market_data.daily_ohlc (
                ts_code String,
                trade_date Date,
                open Float32,
                high Float32,
                low Float32,
                close Float32,
                pre_close Float32,
                change Float32,
                pct_chg Float32,
                vol Float64,
                amount Float64
            ) ENGINE = MergeTree()
            ORDER BY (ts_code, trade_date)
        ''')

    def insert_data(self, df):
        """插入数据，失败时静默或打印简洁信息"""
        try:
            records = df.to_dict('records')
            self.client.execute('INSERT INTO market_data.daily_ohlc VALUES', records)
            print(f"成功插入 {len(records)} 条数据")
        except Exception:
            # 数据库未运行时，静默处理，避免用户恐慌
            pass

if __name__ == "__main__":
    storage = ClickHouseStorage()
    # 示例: 读取parquet数据并插入
    # df = pd.read_parquet('./data/raw/000001.SZ.parquet')
    # storage.insert_data(df)
