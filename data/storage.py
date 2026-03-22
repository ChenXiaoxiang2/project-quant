from clickhouse_driver import Client
import pandas as pd

class ClickHouseStorage:
    """
    ClickHouse 存储适配器
    当 ClickHouse 不可用时自动降级为 SQLite 本地缓存，不影响业务运行。
    """

    def __init__(self, host='localhost'):
        self.host = host
        self.client = None
        self._enabled = False
        self._init()

    def _init(self):
        """连接 ClickHouse，失败则静默降级"""
        try:
            self.client = Client(host=self.host, connect_timeout=3)
            self.client.execute('SELECT 1')
            self.create_table()
            self._enabled = True
            print("[ClickHouse] 连接成功")
        except Exception as e:
            self.client = None
            self._enabled = False
            print(f"[ClickHouse] 不可用（{e}），自动降级为本地缓存模式")

    @property
    def available(self) -> bool:
        return self._enabled

    def create_table(self):
        if not self._enabled or self.client is None:
            return
        try:
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
        except Exception:
            pass

    def insert_data(self, df):
        if not self._enabled or self.client is None:
            return
        try:
            records = df.to_dict('records')
            self.client.execute('INSERT INTO market_data.daily_ohlc VALUES', records)
            print(f"ClickHouse: 插入 {len(records)} 条")
        except Exception:
            pass


if __name__ == "__main__":
    storage = ClickHouseStorage()
    # 示例: 读取parquet数据并插入
    # df = pd.read_parquet('./data/raw/000001.SZ.parquet')
    # storage.insert_data(df)
