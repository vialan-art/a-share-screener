"""评估插件系统对真实 A 股数据的覆盖度和效果。

用法：
    python backend/scripts/evaluate_plugins.py
"""
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base
from backend.plugins.adapter import PluginAdapter
from backend.plugins.data_service import PluginDataService
from backend.plugins.registry import registry


SAMPLE_SYMBOLS = [
    "000001",  # 平安银行
    "000002",  # 万科A
    "000858",  # 五粮液
    "002594",  # 比亚迪
    "600000",  # 浦发银行
    "600519",  # 贵州茅台
    "600036",  # 招商银行
    "300750",  # 宁德时代
]


def main():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    data_service = PluginDataService(db)
    adapter = PluginAdapter()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_dt = datetime.now() - timedelta(days=400)
    start_date = start_dt.strftime("%Y-%m-%d")

    print(f"评估区间: {start_date} ~ {end_date}")
    print(f"样本股票: {len(SAMPLE_SYMBOLS)} 只")
    print("-" * 60)

    results = {}
    ohlcv_map = {}
    for symbol in SAMPLE_SYMBOLS:
        try:
            ohlcv = data_service.fetch_ohlcv(symbol, days=300, end_date=end_date)
            if not ohlcv:
                print(f"[{symbol}] 无 K 线数据")
                continue
            ohlcv_map[symbol] = ohlcv
        except Exception as e:
            print(f"[{symbol}] 取 K 线异常: {e}")

    # 批量 enrich，这样才能计算 RPS
    enriched_map = adapter.enrich_batch(
        [{"symbol": s} for s in ohlcv_map.keys()],
        {},
        ohlcv_map,
    )

    for symbol, metrics in enriched_map.items():
        signals = metrics.get("_plugin_signals", {})
        results[symbol] = signals
        print(f"[{symbol}] K线 {len(ohlcv_map[symbol])} 条 | 信号 {len(signals)} 个 | rps_120={metrics.get('rps_120')}")

    print("-" * 60)
    print("汇总:")
    plugin_names = registry.list_plugins()
    coverage = {name: 0 for name in plugin_names}
    for sym, signals in results.items():
        for name in plugin_names:
            sig = signals.get(name, {})
            if sig.get("score") is not None or sig.get("passed") is not None:
                coverage[name] += 1

    for name in plugin_names:
        count = coverage[name]
        pct = count / len(SAMPLE_SYMBOLS) * 100 if SAMPLE_SYMBOLS else 0
        print(f"  {name:30s} 覆盖 {count}/{len(SAMPLE_SYMBOLS)} ({pct:.0f}%)")

    # 输出每个股票触发通过的插件
    print("-" * 60)
    print("每只股票触发的策略/形态:")
    for sym, signals in results.items():
        passed = [n for n, s in signals.items() if s.get("passed")]
        if passed:
            print(f"  {sym}: {', '.join(passed)}")
        else:
            print(f"  {sym}: 无")


if __name__ == "__main__":
    main()
