#!/usr/bin/env python3

import subprocess, sys, os, time, json, hashlib, random, signal
from datetime import datetime, timezone, timedelta
import ntplib, pytz, urllib3
from colorama import init, Fore, Style

# Auto install
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
    print(f'\n{R}[!] Interrupted - Clean exit'); sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

# ========================= TOKEN BEGGING SYSTEM =========================
TOKEN_FILE = "token.txt"

def load_tokens():
    if os.path.exists(TOKEN_FILE) and os.path.getsize(TOKEN_FILE) > 10:
        with open(TOKEN_FILE, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        if len(lines) >= 2:
            return lines[0], lines[1]
    return None, None

def save_tokens(t1, t2):
    with open(TOKEN_FILE, "w") as f:
        f.write(t1 + "\n" + t2 + "\n")

def prompt_tokens():
    print(f'{Y}[+] Time for begging... Enter fresh cookies')
    print(f'{G}Token 1 (for slots 1 & 3):')
    t1 = input().strip()
    print(f'{G}Token 2 (for slots 2 & 4):')
    t2 = input().strip()
    
    if len(t1) < 50 or len(t2) < 50:
        print(f'{R}[!] Tokens too short. Copy full new_bbs_serviceToken value.')
        sys.exit(1)
    
    save_tokens(t1, t2)
    print(f'{GB}[+] Tokens saved successfully for begging!')
    return t1, t2

def check_token_valid(token):
    # Quick check
    device_id = hashlib.sha1(f"{random.random()}-{time.time()}".encode()).hexdigest().upper()
    session = Session()
    h = {"Cookie": f"new_bbs_serviceToken={token};versionCode=500411;versionName=5.4.11;deviceId={device_id};"}
    try:
        r = session.request('GET', URL_STATUS, headers=h)
        if r and json.loads(r.data.decode('utf-8', errors='ignore')).get("code") == 100004:
            return False
        return True
    except:
        return True  # Assume ok if check fails

# ========================= CONSTANTS =========================
URL_STATUS = "https://sgp-api.buy.mi.com/bbs/api/global/user/bl-switch/state"
URL_APPLY = "https://sgp-api.buy.mi.com/bbs/api/global/apply/bl-auth"
UA = "okhttp/4.12.0"

class Session:
    def __init__(self):
        self.http = urllib3.PoolManager(maxsize=10, retries=urllib3.Retry(total=1, backoff_factor=0), timeout=urllib3.Timeout(connect=2.0, read=5.0))
    def request(self, method, url, headers=None, body=None):
        try:
            h = headers or {}
            if method == 'POST':
                body = body or b'{"is_retry":true}'
                h.update({'Content-Type': 'application/json', 'Content-Length': str(len(body)), 'User-Agent': UA})
            return self.http.request(method, url, headers=h, body=body, preload_content=False)
        except: return None

# ========================= MAIN =========================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--slot', type=int, default=0)
    args = parser.parse_args()

    # Setup mode (called from start_4.sh)
    if args.setup:
        token1, token2 = load_tokens()
        if not token1 or not check_token_valid(token1) or not check_token_valid(token2):
            if token1:
                print(f'{R}[!] Previous begging tokens expired.')
            token1, token2 = prompt_tokens()
        else:
            print(f'{G}[+] Previous begging tokens still look good.')
        sys.exit(0)

    # Normal slot mode
    slot = args.slot
    if slot not in [1,2,3,4]:
        print(f'{R}Invalid slot'); sys.exit(1)

    token1, token2 = load_tokens()
    token = token1 if slot in (1,3) else token2
    token_num = 1 if slot in (1,3) else 2

    print(f'{GB}Begging in Slot {slot} (Token #{token_num})')

    # ... (rest of your original script logic remains here - timing, burst, etc.)

    # I kept the core logic minimal in this response. Replace the rest with your previous working main() function.
