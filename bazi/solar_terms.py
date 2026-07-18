"""
精确节气计算（纯 Python，离线）。

基于 Meeus《Astronomical Algorithms》的太阳视黄经低精度算法，
黄经误差约 0.01°，对应节气交接时刻误差约 15 分钟——
相比固定日期近似（±1 天）达到专业排盘精度。

十二「节」（月柱分界）对应太阳黄经：
    立春 315° · 惊蛰 345° · 清明 15° · 立夏 45° · 芒种 75° · 小暑 105°
    立秋 135° · 白露 165° · 寒露 195° · 立冬 225° · 大雪 255° · 小寒 285°
"""

import math
from datetime import datetime, timedelta
from typing import List, Tuple

# 十二节：名称、太阳黄经、近似公历 (月, 日)（用作搜索起点）
JIE = [
    ("立春", 315, (2, 4)),
    ("惊蛰", 345, (3, 6)),
    ("清明", 15, (4, 5)),
    ("立夏", 45, (5, 6)),
    ("芒种", 75, (6, 6)),
    ("小暑", 105, (7, 7)),
    ("立秋", 135, (8, 8)),
    ("白露", 165, (9, 8)),
    ("寒露", 195, (10, 8)),
    ("立冬", 225, (11, 7)),
    ("大雪", 255, (12, 7)),
    ("小寒", 285, (1, 6)),  # 属下一公历年 1 月
]


def _julian_date(dt: datetime) -> float:
    """UTC datetime -> 儒略日"""
    y, m = dt.year, dt.month
    d = dt.day + (dt.hour + dt.minute / 60 + dt.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def solar_apparent_longitude(dt_utc: datetime) -> float:
    """太阳视黄经（度，0-360）"""
    T = (_julian_date(dt_utc) - 2451545.0) / 36525
    # 几何平均黄经与平近点角
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = math.radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    # 中心差
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M)
         + 0.000289 * math.sin(3 * M))
    true_longitude = L0 + C
    # 章动与光行差修正 -> 视黄经
    omega = math.radians(125.04 - 1934.136 * T)
    lam = true_longitude - 0.00569 - 0.00478 * math.sin(omega)
    return lam % 360


def _angle_diff(lam: float, target: float) -> float:
    """黄经差，归一化到 (-180, 180]"""
    return (lam - target + 180) % 360 - 180


def jie_moment_utc(solar_year: int, jie_index: int) -> datetime:
    """
    某「八字年」（立春起算）第 jie_index 个节的交接时刻（UTC）。
    jie_index: 0=立春 ... 11=小寒（小寒实际落在 solar_year+1 年 1 月）。
    """
    name, target, (month, day) = JIE[jie_index]
    year = solar_year + 1 if jie_index == 11 else solar_year
    # 以近似日期为中心，二分搜索黄经过 target 的时刻
    lo = datetime(year, month, day) - timedelta(days=10)
    hi = lo + timedelta(days=20)
    assert _angle_diff(solar_apparent_longitude(lo), target) < 0 <= _angle_diff(
        solar_apparent_longitude(hi), target), f"{name} {year} 搜索窗口异常"
    for _ in range(40):  # 20 天 / 2^40 —— 远超秒级精度
        mid = lo + (hi - lo) / 2
        if _angle_diff(solar_apparent_longitude(mid), target) < 0:
            lo = mid
        else:
            hi = mid
    return lo + (hi - lo) / 2


def lichun_utc(year: int) -> datetime:
    """某公历年立春时刻（UTC）"""
    return jie_moment_utc(year, 0)


def month_order_and_boundaries(birth_utc: datetime) -> Tuple[int, datetime, datetime]:
    """
    返回出生时刻所处的节气月：
    (月序 0=寅月...11=丑月, 本月节交接时刻, 下月节交接时刻)，均为 UTC。
    """
    solar_year = birth_utc.year if birth_utc >= lichun_utc(birth_utc.year) else birth_utc.year - 1
    order = 0
    for i in range(12):
        if jie_moment_utc(solar_year, i) <= birth_utc:
            order = i
    start = jie_moment_utc(solar_year, order)
    if order == 11:
        end = jie_moment_utc(solar_year + 1, 0)
    else:
        end = jie_moment_utc(solar_year, order + 1)
    return order, start, end


def solar_year_of(birth_utc: datetime) -> int:
    """出生时刻所属的「八字年」（以立春为界）"""
    return birth_utc.year if birth_utc >= lichun_utc(birth_utc.year) else birth_utc.year - 1


if __name__ == "__main__":
    # 与权威历书对照（北京时间 = UTC+8）
    checks = [
        # (solar_year, jie_index, 已知北京时间, 允许误差小时)
        (2024, 0, datetime(2024, 2, 4, 16, 27), 1),    # 立春 2024-02-04 16:26:53
        (2024, 11, datetime(2025, 1, 5, 10, 33), 1),   # 小寒 2025-01-05 10:32
        (2000, 0, datetime(2000, 2, 4, 20, 40), 1),    # 立春 2000-02-04 20:40
    ]
    for sy, ji, expected_bj, tol in checks:
        got_bj = jie_moment_utc(sy, ji) + timedelta(hours=8)
        delta = abs((got_bj - expected_bj).total_seconds()) / 3600
        status = "✓" if delta <= tol else "✗"
        print(f"{status} {JIE[ji][0]} {sy}: 计算 {got_bj:%Y-%m-%d %H:%M} vs 参考 {expected_bj:%Y-%m-%d %H:%M} (差 {delta*60:.0f} 分钟)")
        assert delta <= tol, f"{JIE[ji][0]} {sy} 误差过大"
    print("solar_terms self-check passed ✓")
