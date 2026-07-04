"""最小回测引擎。

只做一件事：
- 取最新 DailySnapshot 的 Top N 股票，等权重买入。
- 算持有到今天（或指定结束日）的后复权收益率。
- 和沪深300基准对比。

不涉及神经网络，也不做参数优化。
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
from sqlalchemy.orm import Session

from backend.database.models import DailySnapshot
from backend.data.price_service import PriceService


def _annualized_return(total_return_pct: float, days: int) -> Optional[float]:
    """把总收益率换算成年化收益率。"""
    if days <= 0:
        return None
    total = 1 + total_return_pct / 100
    try:
        return round((total ** (365 / days) - 1) * 100, 2)
    except Exception:
        return None


def _compute_drawdown(prices: pd.Series) -> float:
    """计算价格序列的最大回撤百分比。"""
    if prices.empty:
        return 0.0
    cummax = prices.cummax()
    drawdown = (prices - cummax) / cummax
    return round(drawdown.min() * 100, 2)


class SimpleBacktest:
    """单点持有回测。"""

    def __init__(self, db: Session):
        self.db = db
        self.price_service = PriceService(db)

    def _latest_snapshot_date(self) -> Optional[str]:
        latest = (
            self.db.query(DailySnapshot.snapshot_date)
            .distinct()
            .order_by(DailySnapshot.snapshot_date.desc())
            .first()
        )
        return latest[0] if latest else None

    def run(
        self,
        snapshot_date: Optional[str] = None,
        buy_date: Optional[str] = None,
        end_date: Optional[str] = None,
        top_n: int = 20,
    ) -> Dict[str, Any]:
        """回测某快照 Top N 从 buy_date 持有到 end_date 的收益。"""
        # 默认用最新快照
        if snapshot_date is None:
            snapshot_date = self._latest_snapshot_date()
        if snapshot_date is None:
            return {"error": "数据库中没有任何快照，请先运行选股流程"}

        # 默认买入日就是快照日
        if buy_date is None:
            buy_date = snapshot_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # 1. 取快照
        items = (
            self.db.query(DailySnapshot)
            .filter(DailySnapshot.snapshot_date == snapshot_date)
            .order_by(DailySnapshot.total_score.desc())
            .limit(top_n)
            .all()
        )
        if not items:
            return {"error": f"没有找到 {snapshot_date} 的快照"}

        symbols = [i.symbol for i in items]
        buy_ymd = buy_date.replace("-", "")
        end_ymd = end_date.replace("-", "")

        # 2. 获取每只股票在买入日和卖出日的后复权收盘价
        returns = []
        valid_count = 0
        missing_symbols = []
        all_price_dfs: Dict[str, pd.DataFrame] = {}
        for symbol in symbols:
            df = self.price_service.get_adj_close(
                symbol,
                start_date=buy_ymd,
                end_date=end_ymd,
            )
            if df is None or df.empty:
                missing_symbols.append(symbol)
                continue
            # 取买入日及之后的第一个有效交易日
            df = df[df["trade_date"] >= buy_ymd].sort_values("trade_date").reset_index(drop=True)
            if len(df) < 2:
                missing_symbols.append(symbol)
                continue
            buy_price = float(df["adj_close"].iloc[0])
            sell_price = float(df["adj_close"].iloc[-1])
            if buy_price <= 0 or sell_price <= 0:
                missing_symbols.append(symbol)
                continue
            ret = (sell_price - buy_price) / buy_price
            returns.append(ret)
            valid_count += 1
            all_price_dfs[symbol] = df

        if valid_count == 0:
            return {
                "snapshot_date": snapshot_date,
                "buy_date": buy_date,
                "end_date": end_date,
                "top_n": top_n,
                "portfolio_return": None,
                "benchmark_return": None,
                "missing_price_count": len(missing_symbols),
                "error": "没有获取到任何股票的历史价格，可能需要配置 TUSHARE_TOKEN",
            }

        # 3. 等权重组合收益
        portfolio_return = round(sum(returns) / len(returns) * 100, 2)

        # 4. 沪深300基准收益
        benchmark_return = self.price_service.get_index_return(
            "000300.SH",
            start_date=buy_ymd,
            end_date=end_ymd,
        )

        # 5. 组合净值序列（每日等权，简化再平衡）
        portfolio_nav_df = None
        max_drawdown = None
        win_rate = None
        holding_days = None
        if all_price_dfs:
            # 先统一每只股票的净值 = 当日收盘价 / 买入日收盘价
            nav_frames = []
            for symbol, df in all_price_dfs.items():
                base = float(df["adj_close"].iloc[0])
                if base <= 0:
                    continue
                nav = df[["trade_date", "adj_close"]].copy()
                nav["nav"] = nav["adj_close"] / base
                nav_frames.append(nav[["trade_date", "nav"]])

            if nav_frames:
                # 合并所有净值序列，按日期分组取均值
                combined = pd.concat(nav_frames, ignore_index=True)
                combined = combined.groupby("trade_date", as_index=False)["nav"].mean()
                combined = combined.sort_values("trade_date").reset_index(drop=True)
                combined["nav"] = combined["nav"].ffill()
                portfolio_nav_df = combined
                holding_days = len(combined)
                max_drawdown = _compute_drawdown(combined["nav"])
                win_rate = round(sum(1 for r in returns if r > 0) / len(returns) * 100, 2)

        annualized = _annualized_return(portfolio_return, holding_days) if holding_days else None

        return {
            "snapshot_date": snapshot_date,
            "buy_date": buy_date,
            "end_date": end_date,
            "top_n": top_n,
            "valid_stocks": valid_count,
            "missing_price_count": len(missing_symbols),
            "portfolio_return": portfolio_return,
            "annualized_return": annualized,
            "benchmark_return": benchmark_return,
            "excess_return": round(portfolio_return - (benchmark_return or 0), 2) if benchmark_return is not None else None,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "holding_days": holding_days,
            "stocks": [
                {"symbol": i.symbol, "name": i.name, "total_score": i.total_score}
                for i in items
            ],
        }

    def run_multiple_horizons(
        self,
        horizons: List[int] = [365 * 3, 365 * 2, 365],
        top_n: int = 20,
    ) -> List[Dict[str, Any]]:
        """用最新快照的股票名单，回测多个历史买入点的表现。

        注意：这里用的是最新快照的选股结果，但买入日是快照日之前 N 年。
        因此这不是严格的前视回测，而是"当前策略选出的股票在历史表现如何"。
        严格前视回测需要重新跑历史日期的 pipeline。
        """
        snapshot_date = self._latest_snapshot_date()
        if snapshot_date is None:
            return [{"error": "数据库中没有任何快照"}]

        snapshot_dt = datetime.strptime(snapshot_date, "%Y-%m-%d")
        results = []
        for days in horizons:
            buy_dt = snapshot_dt - timedelta(days=days)
            buy_str = buy_dt.strftime("%Y-%m-%d")
            result = self.run(snapshot_date=snapshot_date, buy_date=buy_str, top_n=top_n)
            result["label"] = f"{days // 365}年前买入"
            result["note"] = "使用最新快照的选股名单，买入日为历史日期"
            results.append(result)
        return results
