"""滚动回测引擎。

目标：
- 每月第一个交易日调仓，买入当时 DailySnapshot 的 Top N。
- 等权重持有到下次调仓。
- 与沪深300对比，计算年化收益、最大回撤、胜率、夏普近似。
- 同时输出随机选股对照组，验证策略是否真正有效。
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import random

import pandas as pd
from sqlalchemy.orm import Session

from backend.database.models import DailySnapshot, StockPrice
from backend.data.price_service import PriceService


class RollingBacktest:
    """月度滚动回测。"""

    def __init__(self, db: Session, seed: int = 42):
        self.db = db
        self.price_service = PriceService(db)
        random.seed(seed)

    def _snapshot_dates(self) -> List[str]:
        """获取所有快照日期并排序。"""
        rows = (
            self.db.query(DailySnapshot.snapshot_date)
            .distinct()
            .order_by(DailySnapshot.snapshot_date.asc())
            .all()
        )
        return [r[0] for r in rows]

    def _top_n_symbols(self, snapshot_date: str, top_n: int) -> List[str]:
        items = (
            self.db.query(DailySnapshot)
            .filter(DailySnapshot.snapshot_date == snapshot_date)
            .order_by(DailySnapshot.total_score.desc())
            .limit(top_n)
            .all()
        )
        return [i.symbol for i in items]

    def _random_symbols(self, snapshot_date: str, top_n: int) -> List[str]:
        """随机对照组：从同一期快照里随机选 N 只。"""
        items = (
            self.db.query(DailySnapshot.symbol)
            .filter(DailySnapshot.snapshot_date == snapshot_date)
            .all()
        )
        symbols = [i[0] for i in items]
        if len(symbols) <= top_n:
            return symbols
        return random.sample(symbols, top_n)

    def _monthly_rebalance_dates(self, start_date: str, end_date: str, all_snapshot_dates: List[str], frequency: str = "monthly") -> List[str]:
        """生成调仓日（必须是快照日）。

        frequency: monthly（每月首个快照日） 或 weekly（每周首个快照日）。
        当快照数量不足时，weekly 可产生多期结果。
        """
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        dates = []

        if frequency == "weekly":
            current = start
            while current <= end:
                candidate = next((d for d in all_snapshot_dates if d >= current.strftime("%Y-%m-%d")), None)
                if candidate and candidate <= end_date and candidate not in dates:
                    dates.append(candidate)
                current += timedelta(days=7)
        elif frequency == "daily":
            for candidate in all_snapshot_dates:
                if start_date <= candidate <= end_date:
                    dates.append(candidate)
        else:
            current = datetime(start.year, start.month, 1)
            while current <= end:
                candidate = next((d for d in all_snapshot_dates if d >= current.strftime("%Y-%m-%d")), None)
                if candidate and candidate <= end_date and candidate not in dates:
                    dates.append(candidate)
                if current.month == 12:
                    current = datetime(current.year + 1, 1, 1)
                else:
                    current = datetime(current.year, current.month + 1, 1)
        return dates

    def _portfolio_return_between(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
    ) -> Tuple[Optional[float], int, int]:
        """计算等权组合在两个日期之间的收益率。"""
        start_ymd = start_date.replace("-", "")
        end_ymd = end_date.replace("-", "")
        returns = []
        valid = 0
        missing = 0
        for symbol in symbols:
            df = self.price_service.get_adj_close(symbol, start_date=start_ymd, end_date=end_ymd)
            if df is None or df.empty:
                missing += 1
                continue
            df = df.sort_values("trade_date").reset_index(drop=True)
            buy = None
            sell = None
            for _, row in df.iterrows():
                if buy is None and row["trade_date"] >= start_ymd:
                    buy = float(row["adj_close"])
                if row["trade_date"] <= end_ymd:
                    sell = float(row["adj_close"])
            if buy is None or sell is None or buy <= 0:
                missing += 1
                continue
            returns.append((sell - buy) / buy)
            valid += 1
        if valid == 0:
            return None, 0, missing
        return sum(returns) / len(returns) * 100, valid, missing

    def _latest_price_date(self) -> Optional[str]:
        """本地缓存中最新的一条交易日（YYYY-MM-DD），没有则返回 None。"""
        row = self.db.query(StockPrice.trade_date).order_by(StockPrice.trade_date.desc()).first()
        if not row:
            return None
        d = str(row[0])
        if len(d) == 8:
            return f"{d[:4]}-{d[4:6]}-{d[6:]}"
        return d

    def run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        top_n: int = 20,
        frequency: str = "auto",
    ) -> Dict[str, Any]:
        """运行滚动回测。

        frequency: monthly / weekly / daily / auto。auto 会在快照数量不足以支撑月度时自动降级。
        为避免查询未来无价格的日期导致外部拉取超时，end_date 会被限制在本地缓存最新交易日。
        """
        all_dates = self._snapshot_dates()
        if not all_dates:
            return {"error": "没有可用的快照数据"}

        if start_date is None:
            start_date = all_dates[0]
        if end_date is None:
            end_date = all_dates[-1]

        latest_price = self._latest_price_date()
        if latest_price and end_date > latest_price:
            end_date = latest_price

        chosen_frequency = frequency
        if frequency == "auto":
            # 估算月度周期数：若不足 2 期则改为周度，周度仍不足 2 期改为日度
            monthly_dates = self._monthly_rebalance_dates(start_date, end_date, all_dates, frequency="monthly")
            if len(monthly_dates) >= 2:
                chosen_frequency = "monthly"
            else:
                weekly_dates = self._monthly_rebalance_dates(start_date, end_date, all_dates, frequency="weekly")
                chosen_frequency = "daily" if len(weekly_dates) < 2 else "weekly"

        rebalance_dates = self._monthly_rebalance_dates(start_date, end_date, all_dates, frequency=chosen_frequency)
        if len(rebalance_dates) < 2:
            return {"error": "可调仓日期不足，需要至少两个快照"}

        strategy_returns = []
        random_returns = []
        benchmark_returns = []
        records = []

        for i in range(len(rebalance_dates) - 1):
            buy_date = rebalance_dates[i]
            sell_date = rebalance_dates[i + 1]

            symbols = self._top_n_symbols(buy_date, top_n)
            random_symbols = self._random_symbols(buy_date, top_n)

            if not symbols:
                continue

            strategy_ret, valid_s, miss_s = self._portfolio_return_between(symbols, buy_date, sell_date)
            random_ret, valid_r, miss_r = self._portfolio_return_between(random_symbols, buy_date, sell_date)
            benchmark_ret = self.price_service.get_index_return(
                "000300.SH",
                start_date=buy_date.replace("-", ""),
                end_date=sell_date.replace("-", ""),
            )

            if strategy_ret is None:
                continue

            strategy_returns.append(strategy_ret / 100)
            random_returns.append(random_ret / 100 if random_ret is not None else 0)
            benchmark_returns.append((benchmark_ret or 0) / 100)

            records.append({
                "start_date": buy_date,
                "end_date": sell_date,
                "strategy_return": round(strategy_ret, 2),
                "random_return": round(random_ret, 2) if random_ret is not None else None,
                "benchmark_return": round(benchmark_ret, 2) if benchmark_ret is not None else None,
                "valid_stocks": valid_s,
                "missing_stocks": miss_s,
                "holdings": symbols,
            })

        if not strategy_returns:
            return {"error": "没有足够的价格数据计算收益"}

        def _nav_series(returns):
            nav = [1.0]
            for r in returns:
                nav.append(nav[-1] * (1 + r))
            return nav

        strategy_nav = _nav_series(strategy_returns)
        random_nav = _nav_series(random_returns)
        benchmark_nav = _nav_series(benchmark_returns)

        def _max_drawdown(nav):
            peak = nav[0]
            dd = 0.0
            for v in nav:
                if v > peak:
                    peak = v
                d = (peak - v) / peak
                if d > dd:
                    dd = d
            return round(dd * 100, 2)

        def _annualized(returns, periods_per_year=12):
            if not returns:
                return None
            # 回测时间过短时年化数字没有意义，直接返回 None
            if chosen_frequency == "daily" and len(returns) < 20:
                return None
            if chosen_frequency == "weekly" and len(returns) < 6:
                return None
            if chosen_frequency == "monthly" and len(returns) < 3:
                return None
            if chosen_frequency == "daily":
                periods_per_year = 252
            elif chosen_frequency == "weekly":
                periods_per_year = 52
            avg = sum(returns) / len(returns)
            return round(((1 + avg) ** periods_per_year - 1) * 100, 2)

        def _sharpe(returns, periods_per_year=12):
            if len(returns) < 2:
                return None
            if chosen_frequency == "daily" and len(returns) < 20:
                return None
            if chosen_frequency == "weekly" and len(returns) < 6:
                return None
            if chosen_frequency == "monthly" and len(returns) < 3:
                return None
            if chosen_frequency == "daily":
                periods_per_year = 252
            elif chosen_frequency == "weekly":
                periods_per_year = 52
            avg = sum(returns) / len(returns)
            variance = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
            std = variance ** 0.5
            if std == 0:
                return None
            return round((avg / std) * (periods_per_year ** 0.5), 2)

        total_strategy = round((strategy_nav[-1] - 1) * 100, 2)
        total_random = round((random_nav[-1] - 1) * 100, 2)
        total_benchmark = round((benchmark_nav[-1] - 1) * 100, 2)

        return {
            "start_date": rebalance_dates[0],
            "end_date": rebalance_dates[-1],
            "top_n": top_n,
            "frequency": chosen_frequency,
            "periods": len(records),
            "strategy": {
                "total_return": total_strategy,
                "annualized_return": _annualized(strategy_returns, periods_per_year=52 if chosen_frequency == "weekly" else 12),
                "max_drawdown": _max_drawdown(strategy_nav),
                "sharpe": _sharpe(strategy_returns, periods_per_year=52 if chosen_frequency == "weekly" else 12),
                "win_rate": round(sum(1 for r in strategy_returns if r > 0) / len(strategy_returns) * 100, 2),
            },
            "random": {
                "total_return": total_random,
                "annualized_return": _annualized(random_returns, periods_per_year=52 if chosen_frequency == "weekly" else 12),
                "max_drawdown": _max_drawdown(random_nav),
                "win_rate": round(sum(1 for r in random_returns if r > 0) / len(random_returns) * 100, 2),
            },
            "benchmark": {
                "total_return": total_benchmark,
                "annualized_return": _annualized(benchmark_returns, periods_per_year=52 if chosen_frequency == "weekly" else 12),
                "max_drawdown": _max_drawdown(benchmark_nav),
            },
            "records": records,
        }
