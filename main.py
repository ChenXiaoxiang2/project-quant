import yaml
import os

def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    print("量化投资系统启动...")
    # 加载配置: 使用绝对路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, "config")
    settings = load_config(os.path.join(config_dir, "settings.yaml"))
    params = load_config(os.path.join(config_dir, "strategy_params.yaml"))
    
    print(f"系统配置已加载，风险限制: 最大回撤{settings['risk']['max_drawdown']}")
    print(f"趋势策略已加载，ADX阈值: {params['trend_strategy']['adx_threshold']}")

if __name__ == "__main__":
    main()
