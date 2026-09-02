[
  {
    "id": "daily-morning",
    "enabled": true,
    "username": "target_username",
    "filepath": "media/photo.jpg",
    "caption": "Good morning ❤️",
    "cron": {
      "minute": "30",
      "hour": "8",
      "day": "*",
      "month": "*",
      "weekday": "*"
    },
    "retries": 3
  },
  {
    "id": "daily-night",
    "enabled": true,
    "username": "target_username",
    "filepath": "media/video.mp4",
    "caption": "Good night ❤️",
    "cron": {
      "minute": "0",
      "hour": "21",
      "day": "*",
      "month": "*",
      "weekday": "*"
    },
    "retries": 3
  },
  {
    "id": "one-time",
    "enabled": true,
    "username": "target_username",
    "filepath": "media/photo2.jpg",
    "caption": "Scheduled message ❤️",
    "send_time": "2026-09-05 20:30",
    "retries": 3
  }
]
