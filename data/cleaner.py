import pandas as pd

def clean_data(df):
    """
    清洗数据：
    1. 剔除停牌数据 (假设停牌日vol=0)
    2. 剔除低流动性数据 (成交量过低)
    """
    # 剔除成交量为0
    df = df[df['vol'] > 0]
    
    # 剔除流动性极差的 (以成交额为阈值，根据具体市场需求设定)
    # df = df[df['amount'] > 1e6] # 示例：日成交额大于100万
    
    # 处理缺失值 (如有必要)
    df = df.dropna()
    
    return df

if __name__ == "__main__":
    # 测试清洗逻辑
    # df = pd.read_parquet('./data/raw/000001.SZ.parquet')
    # cleaned_df = clean_data(df)
    print("数据清洗模块已就绪")
