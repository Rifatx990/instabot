import os
import json
import time
import threading
import datetime
import getpass
import sys
from zoneinfo import ZoneInfo

from flask import Flask, jsonify
from instagrapi import Client


# ============================================================
# CONFIGURATION
# ============================================================

BD_TZ = ZoneInfo("Asia/Dhaka")

SESSION_FILE = "session.json"
SCHEDULE_FILE = "schedule.json"
SENT_FILE = "sent.json"

PORT = 8080


# ============================================================
# HARD-CODED SOCKS5 PROXY
# ============================================================

PROXY_USER = "YOUR_PROXY_USERNAME"
PROXY_PASS = "YOUR_PROXY_PASSWORD"
PROXY_HOST = "1.bdixbypass.com"
PROXY_PORT = "6969"

PROXY = (
    f"socks5://{PROXY_USER}:"
    f"{PROXY_PASS}@{PROXY_HOST}:"
    f"{PROXY_PORT}"
)


# ============================================================
# INSTAGRAM CLIENT
# ============================================================

cl = Client()
cl.set_proxy(PROXY)


# ============================================================
# STATUS
# ============================================================

bot_status = "🤖 Initializing..."
sent_count = 0
failed_count = 0


# ============================================================
# JSON HELPERS
# ============================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {filename}: {e}")
        return default


def save_json(filename, data):
    temp = filename + ".tmp"

    try:
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        os.replace(temp, filename)

    except Exception as e:
        print(f"❌ Failed to save {filename}: {e}")


# ============================================================
# SENT TRACKING
# ============================================================

def get_task_id(task):
    return str(task.get("id", ""))


def already_sent(task):
    task_id = get_task_id(task)
    sent = load_json(SENT_FILE, [])
    return task_id in sent


def mark_sent(task):
    task_id = get_task_id(task)
    sent = load_json(SENT_FILE, [])

    if task_id not in sent:
        sent.append(task_id)
        save_json(SENT_FILE, sent)


# ============================================================
# INTERACTIVE LOGIN
# ============================================================

def ask_credentials():

    print()
    print("=" * 60)
    print("🔐 INSTAGRAM LOGIN")
    print("=" * 60)

    username = input(
        "Instagram username: "
    ).strip()

    password = getpass.getpass(
        "Instagram password: "
    )

    return username, password


def login_instagram(interactive=True):

    global bot_status

    # --------------------------------------------------------
    # Try saved session first
    # --------------------------------------------------------

    if os.path.exists(SESSION_FILE):

        try:

            print(
                "🔄 Loading saved Instagram session..."
            )

            with open(
                SESSION_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                settings = json.load(f)

            cl.set_settings(settings)
            cl.set_proxy(PROXY)

            # Test session
            cl.get_timeline_feed()

            bot_status = (
                f"✅ Session restored as "
                f"@{cl.username}"
            )

            print(bot_status)

            return True

        except Exception as e:

            print(
                f"⚠️ Saved session failed: {e}"
            )

            if not interactive:

                bot_status = (
                    "❌ Saved Instagram session "
                    "is invalid"
                )

                return False

            print(
                "🔐 Starting fresh login..."
            )


    # --------------------------------------------------------
    # Never ask from cron
    # --------------------------------------------------------

    if not interactive:

        bot_status = (
            "❌ No valid saved session"
        )

        print(bot_status)

        return False


    # --------------------------------------------------------
    # Ask credentials
    # --------------------------------------------------------

    username, password = ask_credentials()

    if not username or not password:

        bot_status = (
            "❌ Username and password are required"
        )

        print(bot_status)

        return False


    # --------------------------------------------------------
    # Fresh login
    # --------------------------------------------------------

    try:

        print()
        print(
            f"🔐 Logging in as @{username}..."
        )

        result = cl.login(
            username,
            password
        )

        if result:

            cl.dump_settings(
                SESSION_FILE
            )

            bot_status = (
                f"✅ Login successful as "
                f"@{cl.username}"
            )

            print(bot_status)

            return True


    except Exception as e:

        error = str(e)

        print(
            f"⚠️ Instagram login response: "
            f"{error}"
        )

        error_lower = error.lower()

        # ----------------------------------------------------
        # 2FA detection
        # ----------------------------------------------------

        needs_2fa = any(
            x in error_lower
            for x in [
                "two_factor",
                "two factor",
                "2fa",
                "verification code",
                "challenge"
            ]
        )

        if needs_2fa:

            print()
            print("=" * 60)
            print("🔐 INSTAGRAM 2FA REQUIRED")
            print("=" * 60)

            print(
                "Enter the verification code "
                "from Instagram."
            )

            print()

            code = input(
                "2FA code: "
            ).strip()

            if not code:

                bot_status = (
                    "❌ Empty 2FA code"
                )

                print(bot_status)

                return False


            try:

                result = cl.login(
                    username,
                    password,
                    verification_code=code
                )

                if result:

                    cl.dump_settings(
                        SESSION_FILE
                    )

                    bot_status = (
                        f"✅ 2FA login successful "
                        f"as @{cl.username}"
                    )

                    print(bot_status)

                    return True

                bot_status = (
                    "❌ 2FA login failed"
                )

                print(bot_status)

                return False


            except Exception as twofa_error:

                bot_status = (
                    f"❌ 2FA error: "
                    f"{twofa_error}"
                )

                print(bot_status)

                return False


        bot_status = (
            f"❌ Login failed: {error}"
        )

        print(bot_status)

        return False

    return False


# ============================================================
# SEND MEDIA
# ============================================================

def send_media(
    receiver_id,
    filepath,
    caption=""
):

    if not filepath:
        return "❌ No file specified"

    if not os.path.exists(filepath):
        return f"❌ File not found: {filepath}"

    filepath = os.path.abspath(filepath)

    try:

        extension = os.path.splitext(
            filepath
        )[1].lower()


        if extension in (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        ):

            cl.direct_send_photo(
                filepath,
                [receiver_id]
            )


        elif extension in (
            ".mp4",
            ".mov",
            ".mkv"
        ):

            cl.direct_send_video(
                filepath,
                [receiver_id]
            )


        else:

            return (
                f"❌ Unsupported media type: "
                f"{extension}"
            )


        if caption.strip():

            cl.direct_send(
                caption,
                [receiver_id]
            )


        return (
            f"✅ Sent "
            f"{os.path.basename(filepath)}"
        )


    except Exception as e:

        return f"❌ Send failed: {e}"


# ============================================================
# PROCESS TASK
# ============================================================

def process_task(task):

    global sent_count
    global failed_count

    if already_sent(task):

        print(
            f"⏭️ Already processed: "
            f"{task.get('id')}"
        )

        return


    username = task.get("username")
    filepath = task.get("filepath")
    caption = task.get("caption", "")

    retries = int(
        task.get("retries", 3)
    )


    if not username:

        print(
            "❌ Missing recipient username"
        )

        failed_count += 1

        return


    try:

        print(
            f"🔎 Finding @{username}..."
        )

        receiver_id = (
            cl.user_id_from_username(
                username
            )
        )

    except Exception as e:

        print(
            f"❌ Cannot find @{username}: {e}"
        )

        failed_count += 1

        return


    for attempt in range(
        1,
        retries + 1
    ):

        print(
            f"📤 Sending to @{username} "
            f"({attempt}/{retries})"
        )

        result = send_media(
            receiver_id,
            filepath,
            caption
        )

        print(result)


        if result.startswith("✅"):

            mark_sent(task)
            sent_count += 1

            return


        if attempt < retries:

            print(
                "⏳ Retrying in 5 seconds..."
            )

            time.sleep(5)


    failed_count += 1

    print(
        f"❌ Failed after "
        f"{retries} attempts"
    )


# ============================================================
# CRON MATCH
# ============================================================

def cron_match(value, expression):

    expression = str(
        expression
    ).strip()

    if expression == "*":
        return True


    try:

        # */5
        if expression.startswith("*/"):

            step = int(
                expression[2:]
            )

            return (
                step > 0
                and value % step == 0
            )


        # 1,2,3
        if "," in expression:

            values = [
                int(x.strip())
                for x in expression.split(",")
            ]

            return value in values


        # 1-5
        if "-" in expression:

            start, end = map(
                int,
                expression.split(
                    "-",
                    1
                )
            )

            return (
                start <= value <= end
            )


        return value == int(
            expression
        )


    except Exception:

        return False


def cron_matches_now(cron):

    now = datetime.datetime.now(
        BD_TZ
    )

    # Cron weekday:
    # Sunday = 0
    # Monday = 1
    # ...
    # Saturday = 6

    cron_weekday = (
        (now.weekday() + 1) % 7
    )


    return (
        cron_match(
            now.minute,
            cron.get("minute", "*")
        )
        and
        cron_match(
            now.hour,
            cron.get("hour", "*")
        )
        and
        cron_match(
            now.day,
            cron.get("day", "*")
        )
        and
        cron_match(
            now.month,
            cron.get("month", "*")
        )
        and
        cron_match(
            cron_weekday,
            cron.get("weekday", "*")
        )
    )


# ============================================================
# PROCESS SCHEDULES
# ============================================================

def process_schedules():

    schedules = load_json(
        SCHEDULE_FILE,
        []
    )

    if not schedules:

        print(
            "📭 No schedules"
        )

        return


    now = datetime.datetime.now(
        BD_TZ
    )

    print(
        "🕐 Bangladesh time:",
        now.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    for task in schedules:

        try:

            if task.get(
                "enabled",
                True
            ) is False:

                continue


            # ------------------------------------------------
            # ONE-TIME SCHEDULE
            # ------------------------------------------------

            send_time_str = task.get(
                "send_time"
            )

            if send_time_str:

                if already_sent(task):
                    continue


                naive = (
                    datetime.datetime.strptime(
                        send_time_str,
                        "%Y-%m-%d %H:%M"
                    )
                )

                send_time = (
                    naive.replace(
                        tzinfo=BD_TZ
                    )
                )


                if now >= send_time:

                    print(
                        f"🚀 Due: "
                        f"{task.get('id')}"
                    )

                    process_task(task)

                continue


            # ------------------------------------------------
            # CRON SCHEDULE
            # ------------------------------------------------

            cron = task.get(
                "cron"
            )

            if not cron:

                print(
                    f"⚠️ No cron/send_time: "
                    f"{task.get('id')}"
                )

                continue


            current_minute = (
                now.strftime(
                    "%Y-%m-%d-%H-%M"
                )
            )

            cron_task = dict(task)

            cron_task["id"] = (
                f"{task.get('id')}"
                f"@{current_minute}"
            )


            if cron_matches_now(
                cron
            ):

                print(
                    f"🚀 Cron matched: "
                    f"{task.get('id')}"
                )

                process_task(
                    cron_task
                )


        except Exception as e:

            print(
                f"❌ Schedule error: {e}"
            )


# ============================================================
# FLASK STATUS API
# ============================================================

app = Flask(__name__)


@app.route("/")
def status():

    return jsonify({

        "bot_status": bot_status,

        "sent_count": sent_count,

        "failed_count": failed_count,

        "logged_in_as": (
            cl.username
            if cl.username
            else None
        ),

        "user_id": (
            cl.user_id
            if cl.user_id
            else None
        ),

        "proxy_enabled": True,

        "timezone": "Asia/Dhaka",

        "time": datetime.datetime.now(
            BD_TZ
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    })


def run_flask():

    app.run(
        host="0.0.0.0",
        port=PORT,
        threaded=True
    )


# ============================================================
# CRON MODE
# ============================================================

def cron_mode():

    print()
    print("=" * 60)
    print("⏰ INSTAGRAM CRON MODE")
    print("=" * 60)

    # Cron NEVER asks for username/password/2FA.
    # It only uses session.json.

    if not login_instagram(
        interactive=False
    ):

        print(
            "❌ Cron stopped: "
            "no valid Instagram session."
        )

        return


    process_schedules()

    print()
    print(
        f"📤 Sent: {sent_count}"
    )

    print(
        f"❌ Failed: {failed_count}"
    )

    print(
        "✅ Cron execution finished."
    )


# ============================================================
# NORMAL TERMUX MODE
# ============================================================

def normal_mode():

    print()
    print("=" * 60)
    print("🤖 INSTAGRAM SCHEDULER")
    print("=" * 60)


    # Interactive login
    if not login_instagram(
        interactive=True
    ):

        print(
            "❌ Unable to login."
        )

        return


    # Flask status server
    threading.Thread(
        target=run_flask,
        daemon=True
    ).start()


    print()
    print(
        f"🟢 Logged in as @{cl.username}"
    )

    print(
        f"🌐 Status: "
        f"http://127.0.0.1:{PORT}/"
    )

    print(
        "⏰ Scheduler checking every 60 seconds"
    )

    print()


    while True:

        try:

            process_schedules()

        except Exception as e:

            print(
                f"❌ Scheduler error: {e}"
            )

        time.sleep(60)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if "--cron" in sys.argv:

        cron_mode()

    else:

        normal_mode()
