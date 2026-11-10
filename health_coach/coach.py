"""Daily readiness rules and Vietnamese report for the health coach agent.

Pure functions only: feed them Intervals.icu wellness + activity records and
an "as of" date; they return a dict of metrics and a report string. Thresholds
are deliberately simple (v1) and live in RULES so they are easy to tune.

Key principle: a night with no sleep/HRV record means the watch was not worn,
not that the athlete did not sleep. Such nights are skipped, never zero-filled.
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass, field

RULES = {
    "baseline_nights": 7,        # valid nights used for HRV / resting HR baseline
    "baseline_min_nights": 3,    # fewer than this -> baseline not trusted
    "hrv_drop_red": 0.15,        # >=15% below baseline -> rest
    "hrv_drop_yellow": 0.10,     # >=10% below baseline -> easy
    "tsb_yellow": -10,           # form below -10 -> easy
    "rhr_up_red": 7,             # resting HR >= baseline + 7 -> rest
    "rhr_up_yellow": 5,
    "sleep_red_h": 5.0,
    "sleep_yellow_h": 6.5,
    "consecutive_days_yellow": 4,  # 4+ training days in a row -> easy/rest day due
    "weekly_ramp_warn": 0.10,    # weekly distance up >10% vs previous week
    "min_steps_worn": 500,       # fewer steps than this -> watch likely not worn
    "hot_temp_c": 30.0,
    "default_easy_hr_cap": 150,
    # Aerobic base phase: run until HR hits this, then walk (Suunto Zone 2 = 130-145).
    # Set to None to fall back to the top of the Intervals Run Z2.
    "easy_hr_cap_override": 145,
}

RUN_TYPES = {"Run", "VirtualRun", "TrailRun"}


@dataclass
class Readiness:
    level: str                      # "RED" | "YELLOW" | "GREEN"
    reasons: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def _night_valid(w: dict) -> bool:
    return bool(w.get("sleepSecs")) or w.get("hrv") is not None


def _baseline(values: list[float], n: int, min_n: int):
    vals = [v for v in values if v is not None][-n:]
    if len(vals) < min_n:
        return None, len(vals)
    return statistics.mean(vals), len(vals)


def easy_hr_cap(athlete: dict | None) -> int:
    """Easy-run HR ceiling: explicit override, else top of Intervals Run Z2."""
    if RULES.get("easy_hr_cap_override"):
        return int(RULES["easy_hr_cap_override"])
    for s in (athlete or {}).get("sportSettings", []) or []:
        if "Run" in (s.get("types") or []) and s.get("hr_zones"):
            zones = s["hr_zones"]
            if len(zones) >= 2:
                return int(zones[1])
    return RULES["default_easy_hr_cap"]


def assess(wellness: list[dict], activities: list[dict], as_of: dt.date,
           athlete: dict | None = None) -> Readiness:
    r = RULES
    wellness = sorted(wellness, key=lambda w: w["id"])
    today = next((w for w in wellness if w["id"] == as_of.isoformat()), None)
    past = [w for w in wellness if _d(w["id"]) < as_of]
    m: dict = {"date": as_of.isoformat(), "easy_hr_cap": easy_hr_cap(athlete)}
    reasons_red: list[str] = []
    reasons_yellow: list[str] = []

    # --- last night ---
    worn = bool(today and _night_valid(today))
    m["watch_worn_last_night"] = worn
    if worn:
        m["sleep_h"] = round((today.get("sleepSecs") or 0) / 3600, 2) or None
        m["sleep_score"] = int(today["sleepScore"]) if today.get("sleepScore") is not None else None
        m["hrv"] = today.get("hrv")
        if isinstance(m["hrv"], float) and m["hrv"].is_integer():
            m["hrv"] = int(m["hrv"])
        m["rhr"] = today.get("restingHR")
    valid_past = [w for w in past if _night_valid(w)]
    m["missing_nights_last7"] = sum(
        1 for i in range(1, 8)
        if not any(w["id"] == (as_of - dt.timedelta(days=i)).isoformat() and _night_valid(w)
                   for w in wellness)
    )

    hrv_base, n_hrv = _baseline([w.get("hrv") for w in valid_past], r["baseline_nights"], r["baseline_min_nights"])
    rhr_base, _ = _baseline([w.get("restingHR") for w in valid_past], r["baseline_nights"], r["baseline_min_nights"])
    m["hrv_baseline"] = round(hrv_base, 1) if hrv_base else None
    m["rhr_baseline"] = round(rhr_base, 1) if rhr_base else None
    m["baseline_nights_used"] = n_hrv

    if worn and hrv_base and m.get("hrv") is not None:
        drop = (hrv_base - m["hrv"]) / hrv_base
        m["hrv_drop_pct"] = round(drop * 100)
        if drop >= r["hrv_drop_red"]:
            reasons_red.append(f"HRV {m['hrv']} ms thấp hơn mốc {m['hrv_baseline']} ms ({m['hrv_drop_pct']}%)")
        elif drop >= r["hrv_drop_yellow"]:
            reasons_yellow.append(f"HRV {m['hrv']} ms thấp hơn mốc {m['hrv_baseline']} ms ({m['hrv_drop_pct']}%)")
    if worn and rhr_base and m.get("rhr"):
        up = m["rhr"] - rhr_base
        m["rhr_up"] = round(up, 1)
        if up >= r["rhr_up_red"]:
            reasons_red.append(f"Nhịp tim nghỉ {m['rhr']} cao hơn mốc {m['rhr_baseline']} (+{m['rhr_up']})")
        elif up >= r["rhr_up_yellow"]:
            reasons_yellow.append(f"Nhịp tim nghỉ {m['rhr']} cao hơn mốc {m['rhr_baseline']} (+{m['rhr_up']})")
    if worn and m.get("sleep_h"):
        if m["sleep_h"] < r["sleep_red_h"]:
            reasons_red.append(f"Ngủ chỉ {m['sleep_h']} giờ")
        elif m["sleep_h"] < r["sleep_yellow_h"]:
            reasons_yellow.append(f"Ngủ {m['sleep_h']} giờ (dưới {r['sleep_yellow_h']} giờ)")

    # --- training load (form) ---
    ref = today or (wellness[-1] if wellness else None)
    if ref and ref.get("ctl") is not None and ref.get("atl") is not None:
        m["ctl"] = round(ref["ctl"], 1)
        m["atl"] = round(ref["atl"], 1)
        m["tsb"] = round(ref["ctl"] - ref["atl"], 1)
        if m["tsb"] < r["tsb_yellow"]:
            reasons_yellow.append(f"TSB {m['tsb']} (đang tích mệt)")

    # --- activities ---
    acts = sorted(activities, key=lambda a: a["start_date_local"])
    days_trained = {_d(a["start_date_local"]) for a in acts if (a.get("moving_time") or 0) >= 600}
    streak, d = 0, as_of - dt.timedelta(days=1)
    while d in days_trained:
        streak += 1
        d -= dt.timedelta(days=1)
    m["consecutive_training_days"] = streak
    if streak >= r["consecutive_days_yellow"]:
        reasons_yellow.append(f"Đã tập {streak} ngày liên tiếp")

    def window_km(start: dt.date, end: dt.date) -> float:
        return sum((a.get("distance") or 0) for a in acts
                   if a.get("type") in RUN_TYPES and start <= _d(a["start_date_local"]) < end) / 1000

    wk = window_km(as_of - dt.timedelta(days=7), as_of)
    prev = window_km(as_of - dt.timedelta(days=14), as_of - dt.timedelta(days=7))
    m["run_km_7d"] = round(wk, 1)
    m["run_km_prev_7d"] = round(prev, 1)
    if prev > 0:
        m["weekly_ramp_pct"] = round((wk - prev) / prev * 100)

    runs = [a for a in acts if a.get("type") in RUN_TYPES and _d(a["start_date_local"]) < as_of]
    if runs:
        last = runs[-1]
        spd = last.get("average_speed") or 0
        m["last_run"] = {
            "date": last["start_date_local"][:10],
            "km": round((last.get("distance") or 0) / 1000, 2),
            "pace_s_per_km": round(1000 / spd) if spd else None,
            "avg_hr": last.get("average_heartrate"),
            "max_hr": last.get("max_heartrate"),
            "load": last.get("icu_training_load"),
            "temp_c": last.get("average_weather_temp") or last.get("average_temp"),
        }

    if reasons_red:
        level, reasons = "RED", reasons_red + reasons_yellow
    elif reasons_yellow:
        level, reasons = "YELLOW", reasons_yellow
    else:
        level, reasons = "GREEN", []
    return Readiness(level=level, reasons=reasons, metrics=m)


def _n(x):
    """Format a number without a trailing .0 (27.0 -> 27, 8.74 -> 8.74)."""
    if x is None:
        return "-"
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def _pace(s):
    return f"{int(s // 60)}:{int(s % 60):02d}/km" if s else "-"


def build_report(rd: Readiness) -> str:
    m = rd.metrics
    cap = m["easy_hr_cap"]
    head = {
        "RED": "🔴 HÔM NAY: NGHỈ hoặc đi bộ nhẹ 20–30 phút",
        "YELLOW": f"🟡 HÔM NAY: TẬP NHẸ, giữ nhịp tim ≤ {cap}",
        "GREEN": f"🟢 HÔM NAY: TẬP THEO KẾ HOẠCH (chạy dễ giữ nhịp tim ≤ {cap}, hoặc 1 bài chất lượng nếu đã lên lịch)",
    }[rd.level]
    lines = [f"🏃 Coach sáng {m['date']}", head, ""]

    if m.get("watch_worn_last_night"):
        sl = f"{int(m['sleep_h'])}g{round(m['sleep_h'] % 1 * 60):02d}ph" if m.get("sleep_h") else "-"
        lines.append(f"😴 Ngủ: {sl} (điểm {m.get('sleep_score') or '-'})")
        hb = f" | mốc {_n(m['hrv_baseline'])}" if m.get("hrv_baseline") else ""
        lines.append(f"💓 HRV: {_n(m.get('hrv'))} ms{hb}")
        rb = f" | mốc {_n(m['rhr_baseline'])}" if m.get("rhr_baseline") else ""
        lines.append(f"❤️ Nhịp tim nghỉ: {_n(m.get('rhr'))}{rb}")
    else:
        lines.append("⌚ Đêm qua không có dữ liệu ngủ (chưa đeo đồng hồ?) → chỉ đánh giá theo tải tập.")

    if m.get("tsb") is not None:
        lines.append(f"📊 Thể lực CTL {m['ctl']} | Mệt ATL {m['atl']} | Form TSB {m['tsb']}")
    ramp = f" ({m['weekly_ramp_pct']:+d}% so với tuần trước)" if m.get("weekly_ramp_pct") is not None else ""
    lines.append(f"📏 Chạy 7 ngày: {m['run_km_7d']} km{ramp} | Liên tiếp: {m['consecutive_training_days']} ngày")
    lr = m.get("last_run")
    if lr:
        lines.append(f"🏁 Buổi gần nhất {lr['date']}: {lr['km']} km, {_pace(lr['pace_s_per_km'])}, "
                     f"nhịp tim TB {lr['avg_hr']}/max {lr['max_hr']}")

    if rd.reasons:
        lines += ["", "Lý do:"] + [f"• {x}" for x in rd.reasons]

    tips = []
    if m.get("weekly_ramp_pct") is not None and m["weekly_ramp_pct"] > RULES["weekly_ramp_warn"] * 100 and m["run_km_prev_7d"] >= 5:
        tips.append("Tổng km tuần tăng >10% — tuần này giữ nguyên hoặc giảm nhẹ.")
    if lr and (lr.get("temp_c") or 0) >= RULES["hot_temp_c"]:
        tips.append("Trời ≥30°C: uống thêm 500 ml nước + điện giải trước khi chạy, chạy sau 18h.")
    if m.get("missing_nights_last7", 0) >= 2:
        tips.append(f"{m['missing_nights_last7']}/7 đêm gần đây thiếu dữ liệu — đeo đồng hồ khi ngủ để đo HRV.")
    if tips:
        lines += ["", "Gợi ý:"] + [f"• {t}" for t in tips]

    lines += ["", "Dữ liệu: Suunto → Intervals.icu. Không thay thế tư vấn y tế."]
    return "\n".join(lines)
