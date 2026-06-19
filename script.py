#!/usr/bin/env python3

# ========================= CONFIG =========================
SKIP_TIMING = False          # False=next midnight, True=manual
MANUAL_FIRE_HOUR = 19        # Beijing hour
MANUAL_FIRE_MIN = 37         # Beijing minute
MANUAL_FIRE_SEC = 0          # Beijing second
OFFSET_MS = 120              # First shot Xms BEFORE midnight
BURST_INTERVAL_MS = 50       # 50ms between shots

# ========================= IMPORTS =========================
import subprocess, sys, os, time, json, hashlib, random, signal
from datetime import datetime, timezone, timedelta
import ntplib, pytz, urllib3
from colorama import init, Fore, Style

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

for p in ("ntplib", "pytz", "urllib3", "colorama"):
    try: __import__(p)
    except: install(p)

init(autoreset=True)
G, Y, R, B, GB = Fore.GREEN, Fore.YELLOW, Fore.RED, Fore.BLUE, Style.BRIGHT + Fore.GREEN

def clear(): os.system("cls" if os.name == "nt" else "clear")
clear()

def signal_handler(sig, frame):
    print(f'\n{R}[!] Interrupted - Clean exit')
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# ========================= TOKEN HANDLING =========================
TOKEN_FILE = "token.txt"
URL_STATUS = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
URL_APPLY = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
UA = "okhttp/4.12.0"
NTP_SERVERS = ["ntp0.ntp-servers.net", "ntp1.ntp-servers.net", "ntp2.ntp-servers.net"]

class Session:
    def __init__(self):
        self.http = urllib3.PoolManager(
            maxsize=10,
            retries=urllib3.Retry(total=1, backoff_factor=0),
            timeout=urllib3.Timeout(connect=2.0, read=5.0)
        )
    def request(self, method, url, headers=None, body=None):
        try:
            h = headers or {}
            if method == 'POST':
                body = body or b'{"is_retry":true}'
                h.update({
                    'Content-Type': 'application/json',
                    'Content-Length': str(len(body)),
                    'User-Agent': UA,
                    'Connection': 'keep-alive',
                    'Accept-Encoding': 'gzip'
                })
            return self.http.request(method, url, headers=h, body=body, preload_content=False)
        except KeyboardInterrupt:
            raise
        except:
            return None

def gen_device_id():
    return hashlib.sha1(f"{random.random()}-{time.time()}".encode()).hexdigest().upper()

def load_tokens():
    if os.path.exists(TOKEN_FILE) and os.path.getsize(TOKEN_FILE) > 20:
        with open(TOKEN_FILE, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) >= 2:
            return lines[0], lines[1]
    return None, None

def save_tokens(t1, t2):
    with open(TOKEN_FILE, "w") as f:
        f.write(t1 + "\n" + t2 + "\n")

def prompt_tokens():
    print(f'{Y}[+] Enter fresh cookies (full new_bbs_serviceToken values)')
    t1 = input(f'{G}Token 1 (slots 1 & 3): ').strip()
    t2 = input(f'{G}Token 2 (slots 2 & 4): ').strip()
    if len(t1) < 60 or len(t2) < 60:
        print(f'{R}[!] Tokens look incomplete. Please copy the full token.')
        sys.exit(1)
    save_tokens(t1, t2)
    print(f'{GB}[+] Tokens saved.')
    return t1, t2

def check_token_valid(token):
    """Return True only if the token is confirmed valid by the API."""
    if not token:
        return False
    device_id = gen_device_id()
    s = Session()
    h = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"}
    try:
        r = s.request('GET', URL_STATUS, headers=h)
        if r is None:
            return False
        data = json.loads(r.data.decode('utf-8', errors='ignore'))
        return data.get("code") == 0
    except:
        return False

# ========================= BEIJING TIME =========================
def show_beijing_time():
    beijing = datetime.now(timezone.utc).astimezone(pytz.timezone("Asia/Shanghai"))
    print(f'{B}[BEIJING] {beijing.strftime("%H:%M:%S.%f")[:-3]}{Fore.RESET}')

def get_ntp_beijing():
    tz = pytz.timezone("Asia/Shanghai")
    c = ntplib.NTPClient()
    for s in NTP_SERVERS:
        try:
            r = c.request(s, version=3, timeout=3)
            bt = datetime.fromtimestamp(r.tx_time, timezone.utc).astimezone(tz)
            print(f'{G}[NTP] {bt.strftime("%H:%M:%S.%f")[:-3]}{Fore.RESET}')
            return bt
        except:
            pass
    bt = datetime.now(timezone.utc).astimezone(tz)
    print(f'{Y}[SYS] {bt.strftime("%H:%M:%S.%f")[:-3]}{Fore.RESET}')
    return bt

def synced_time(start_bt, start_ts):
    return start_bt + timedelta(seconds=(time.time() - start_ts))

def get_target(start_bt):
    if SKIP_TIMING:
        target = start_bt.replace(hour=MANUAL_FIRE_HOUR, minute=MANUAL_FIRE_MIN,
                                  second=MANUAL_FIRE_SEC, microsecond=0)
        print(f'{Y}[MANUAL] {target.strftime("%H:%M:%S Beijing")}')
        return target
    target = (start_bt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    print(f'{Y}[AUTO] Midnight target: {target.strftime("%H:%M:%S Beijing")}')
    return target

def wait_target(start_bt, start_ts, target):
    print(f'{Y}Waiting for exact target...')
    last_show = 0
    while True:
        now = synced_time(start_bt, start_ts)
        diff = (target - now).total_seconds()
        if time.time() - last_show > 1:
            show_beijing_time()
            last_show = time.time()
        if diff > 0.01:
            time.sleep(min(diff - 0.005, 0.1))
        elif diff > 0:
            time.sleep(0.0001)
        else:
            break

# ========================= HTTP ACTIONS =========================
def check_status(session, token, device_id):
    h = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"}
    r = session.request('GET', URL_STATUS, headers=h)
    if not r:
        return False
    try:
        data = json.loads(r.data.decode('utf-8'))
        r.release_conn()
        if data.get("code") == 100004:
            print(f'{R}Cookie has expired. Please get new cookies.')
            sys.exit(1)
        info = data.get("data", {})
        is_pass, button = info.get("is_pass"), info.get("button_state")
        print(f'{G}[Status]: ', end='')
        if is_pass == 4 and button == 1:
            print(f'{GB}READY!')
            return True
        elif is_pass == 1:
            print(f'{GB}Already approved!')
            sys.exit(0)
        else:
            print(f'{R}Not ready')
            return False
    except:
        return False

def fire(session, token, device_id):
    h = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"}
    try:
        r = session.request("POST", URL_APPLY, headers=h)
        if not r:
            return None
        data = json.loads(r.data.decode('utf-8'))
        r.release_conn()
        return data
    except KeyboardInterrupt:
        raise
    except:
        return None

def handle_resp(resp):
    if resp.get("code") != 0:
        print(f'{R}❌ API ERR')
        return False
    result = resp.get("data", {}).get("apply_result")
    deadline = resp.get("data", {}).get("deadline_format", "")
    if result == 1:
        print(f'{GB}✅ APPROVED! 🎉')
        return True
    elif result == 3:
        print(f'{Y}⏳ QUOTA: {deadline}')
        return False
    elif result == 4:
        print(f'{R}⛔ BLOCKED: {deadline}')
        return False
    else:
        print(f'{R}❓ {resp}')
        return False

# ========================= MAIN HAMMERING LOGIC =========================
def main(token, token_num):
    device_id = gen_device_id()
    session = Session()

    print(f'{Y}🔍 Checking status for Token #{token_num}...')
    clear()
    if not check_status(session, token, device_id):
        return

    start_bt = get_ntp_beijing()
    start_ts = time.time()
    target = get_target(start_bt)

    # Wait for target minus OFFSET_MS
    wait_target(start_bt, start_ts, target - timedelta(milliseconds=OFFSET_MS))

    clear()
    show_beijing_time()
    print(f'{GB}🚀 PRECISE 10x BURST STARTS NOW!{Fore.RESET}\n')

    success = False
    try:
        for i in range(10):
            shot_target = target + timedelta(milliseconds=i * BURST_INTERVAL_MS)

            # Spin‑wait until the exact millisecond
            while True:
                shot_time = synced_time(start_bt, start_ts)
                diff = (shot_target - shot_time).total_seconds()
                if diff <= 0:
                    break
                time.sleep(diff * 0.8)  # micro‑sleep

            now_beijing = datetime.now(timezone.utc).astimezone(pytz.timezone("Asia/Shanghai"))
            print(f'[{i+1}/10] ', end='')
            resp = fire(session, token, device_id)

            if resp:
                print(f'{B}@{now_beijing.strftime("%H:%M:%S.%f")}{Fore.RESET} ', end='')
                if handle_resp(resp):
                    success = True
                    print(f'\n{GB}🎉 SUCCESS on shot {i+1}!')
                    break

    except KeyboardInterrupt:
        print(f'\n{Y}[!] Burst interrupted')

    if not success:
        print(f'{R}\n❌ Burst complete - No approval')
    print(f'{Y}[*] Next quota: 00:00 Beijing tomorrow')

# ========================= ENTRY POINT =========================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--slot', type=int, default=0)
    args = parser.parse_args()

    if args.setup:
        t1, t2 = load_tokens()
        if t1 and check_token_valid(t1) and t2 and check_token_valid(t2):
            print(f'{G}[+] Tokens are valid.')
        else:
            print(f'{Y}[+] Tokens missing or expired. Please enter new tokens.')
            t1, t2 = prompt_tokens()
        sys.exit(0)

    slot = args.slot
    if slot not in (1, 2, 3, 4):
        print(f'{R}Invalid slot. Use --slot 1-4')
        sys.exit(1)

    t1, t2 = load_tokens()
    if not t1 or not t2:
        print(f'{R}Token file missing or empty. Please run --setup first.')
        sys.exit(1)

    token = t1 if slot in (1, 3) else t2
    token_num = 1 if slot in (1, 3) else 2

    clear()
    show_beijing_time()
    print(f'{GB}Using Token #{token_num} for Slot {slot}')
    main(token, token_num)
