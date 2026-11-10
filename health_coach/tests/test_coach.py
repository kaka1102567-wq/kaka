import datetime as dt
import unittest

from health_coach.coach import assess, build_report, easy_hr_cap

D = dt.date(2026, 11, 10)


def night(day, hrv=34, rhr=57, sleep_h=7.8, ctl=15.0, atl=18.0):
    return {"id": day, "hrv": hrv, "restingHR": rhr, "sleepSecs": int(sleep_h * 3600),
            "sleepScore": 80, "ctl": ctl, "atl": atl}


def empty(day, ctl=15.0, atl=18.0):
    return {"id": day, "hrv": None, "restingHR": None, "sleepSecs": None, "ctl": ctl, "atl": atl}


def run(day, km=5.0, hr=145):
    return {"start_date_local": f"{day}T18:30:00", "type": "Run", "distance": km * 1000,
            "moving_time": 2700, "average_speed": 1.9, "average_heartrate": hr,
            "max_heartrate": 160, "icu_training_load": 40, "average_weather_temp": 31}


def baseline_week():
    return [night(f"2026-11-0{i}") for i in range(3, 10)]


class AssessTests(unittest.TestCase):
    def test_green_when_all_normal(self):
        rd = assess(baseline_week() + [night("2026-11-10")], [], D)
        self.assertEqual(rd.level, "GREEN")

    def test_red_on_big_hrv_drop(self):
        rd = assess(baseline_week() + [night("2026-11-10", hrv=27)], [], D)
        self.assertEqual(rd.level, "RED")
        self.assertEqual(rd.metrics["hrv_drop_pct"], 21)

    def test_missing_night_means_not_worn_not_zero(self):
        w = baseline_week()
        w[2] = empty(w[2]["id"])  # one night without the watch
        rd = assess(w + [empty("2026-11-10")], [], D)
        self.assertFalse(rd.metrics["watch_worn_last_night"])
        self.assertEqual(rd.metrics["baseline_nights_used"], 6)
        self.assertEqual(rd.metrics["hrv_baseline"], 34)  # empty night not counted as 0
        self.assertEqual(rd.level, "GREEN")
        self.assertIn("không có dữ liệu ngủ", build_report(rd))

    def test_yellow_on_negative_tsb(self):
        rd = assess(baseline_week() + [night("2026-11-10", ctl=15, atl=27)], [], D)
        self.assertEqual(rd.level, "YELLOW")

    def test_consecutive_days(self):
        acts = [run(f"2026-11-0{i}") for i in range(6, 10)]
        rd = assess(baseline_week() + [night("2026-11-10")], acts, D)
        self.assertEqual(rd.metrics["consecutive_training_days"], 4)
        self.assertEqual(rd.level, "YELLOW")

    def test_easy_cap_override(self):
        self.assertEqual(easy_hr_cap(None), 145)

    def test_easy_cap_from_run_zones(self):
        from health_coach import coach
        saved = coach.RULES["easy_hr_cap_override"]
        coach.RULES["easy_hr_cap_override"] = None
        self.addCleanup(coach.RULES.__setitem__, "easy_hr_cap_override", saved)
        athlete = {"sportSettings": [{"types": ["Run"], "hr_zones": [141, 150, 158]}]}
        self.assertEqual(easy_hr_cap(athlete), 150)
        self.assertEqual(easy_hr_cap(None), 150)


if __name__ == "__main__":
    unittest.main()
