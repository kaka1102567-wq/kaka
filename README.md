# Health Coach Agent

Đồng hồ Suunto → Intervals.icu → agent đánh giá mức hồi phục mỗi sáng → báo cáo Telegram.

```
Suunto ──→ Intervals.icu ──(API)──→ health_coach.daily ──→ Telegram
             ├ buổi tập + nhịp tim
             └ ngủ, HRV, nhịp tim nghỉ, CTL/ATL
```

## Cài trên máy Mac (chạy tự động mỗi sáng)

```bash
git clone https://github.com/<user>/health-coach.git ~/health-coach
cd ~/health-coach && ./mac/install.sh
```

Script sẽ hỏi Athlete ID, Intervals API key, Telegram bot token, Chat ID và **lưu vào macOS Keychain**
(không ghi ra file), rồi cài lịch launchd chạy **05:47** mỗi ngày và gửi thử 1 báo cáo.

- Đổi giờ: `COACH_HOUR=6 COACH_MINUTE=10 ./mac/install.sh`
- Log (không chứa số liệu sức khoẻ): `~/Library/Logs/health-coach.log`
- Chạy tay: `./mac/run.sh` · Gỡ: `./mac/uninstall.sh`
- Mac đang **ngủ** lúc 05:47 → launchd chạy bù ngay khi máy thức. Mac **tắt hẳn** → bỏ lỡ hôm đó.
  Muốn Mac tự thức: `sudo pmset repeat wakeorpoweron MTWRFSU 05:45:00`

## Chạy tay (mọi máy)

```bash
export INTERVALS_ATHLETE_ID=i123456
export INTERVALS_API_KEY=...        # bỏ qua nếu proxy của môi trường tự gắn khoá
python -m health_coach.daily              # in báo cáo
python -m health_coach.daily --json       # in kèm số liệu
python -m health_coach.daily --telegram   # gửi Telegram (cần TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
```

Không cần thư viện ngoài (chỉ dùng Python 3.9+ stdlib — Python có sẵn trên macOS là đủ).

## Quy tắc (v1, chỉnh trong `RULES` ở `coach.py`)

| Mức | Điều kiện (chỉ cần 1) |
|---|---|
| 🔴 Nghỉ | HRV thấp hơn mốc ≥15% · nhịp tim nghỉ cao hơn mốc ≥7 · ngủ <5 giờ |
| 🟡 Nhẹ | HRV thấp hơn mốc ≥10% · TSB < -10 · nhịp tim nghỉ +5 · ngủ <6,5 giờ · tập ≥4 ngày liên tiếp |
| 🟢 Theo kế hoạch | Không vướng điều kiện nào |

- **Mốc** = trung bình 7 đêm gần nhất *có dữ liệu* (cần tối thiểu 3 đêm).
- **Đêm không có dữ liệu = không đeo đồng hồ**, bị bỏ qua chứ không tính là 0.
- Ngưỡng nhịp tim "chạy dễ" giai đoạn xây nền: **145** (`easy_hr_cap_override`, khớp Vùng 2 = 130–145 trên Suunto). Đặt `None` để lấy đỉnh Z2 môn Run trong Intervals.

## Test

```bash
python3 -m unittest discover -s health_coach/tests -t .
```
