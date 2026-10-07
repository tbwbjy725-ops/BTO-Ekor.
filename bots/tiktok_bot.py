#!/usr/bin/env python3
import itertools, random, re, string, threading, time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------- CONFIGURATION
THREADS = 20  # Increased thread count for maximum speed

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

LOOK = {
    "o": "0", "0": "o", "l": "1i", "1": "li", "i": "1l", "s": "5", "5": "s",
    "z": "2", "2": "z", "e": "3", "3": "e", "a": "4", "4": "a", "g": "9q",
    "9": "gq", "q": "9g", "t": "7", "7": "t", "b": "86", "8": "b", "6": "b",
    "u": "v", "v": "u", "m": "n", "n": "m",
}

lock = threading.Lock()
GEN = {"it": None}
S = {"running": False, "finished": False, "rid": 0, "done": 0, "yes": [], "no": 0, "start_time": 0}

# Create a fast shared HTTP session with retries
session = requests.Session()
adapter = HTTPAdapter(pool_connections=THREADS, pool_maxsize=THREADS * 2)
session.mount("https://", adapter)
session.mount("http://", adapter)

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive"
    }

# ---------------------------------------------------------------- CHECK FUNCTION (TIKTOK)
def check_username(username):
    try:
        r = session.get(f"https://www.tiktok.com/@{username}", headers=get_headers(), timeout=(1, 2.5), verify=False)
        t = r.text
        if r.status_code == 404 or '"statusCode":10221' in t:
            return True, ""
        return False, ""
    except Exception:
        return False, ""

# Disable SSL warnings for faster requests
requests.packages.urllib3.disable_warnings()

# ---------------------------------------------------------------- GENERATORS
def variants(name):
    res, seen = [], set()
    for i, ch in enumerate(name):
        for r in LOOK.get(ch, ""):
            v = name[:i] + r + name[i + 1:]
            if v != name and v not in seen:
                seen.add(v)
                res.append(v)
    return res

def near(name, pool):
    res = []
    for i, ch in enumerate(name):
        for c in pool:
            if c != ch:
                res.append(name[:i] + c + name[i + 1:])
    random.shuffle(res)
    return res

def runs(L, pool):
    out = []
    for seq in (string.ascii_lowercase, string.digits):
        for step in (1, 2):
            for s in range(len(seq)):
                idx = [s + step * i for i in range(L)]
                if idx[-1] < len(seq):
                    w = "".join(seq[i] for i in idx)
                    out += [w, w[::-1]]
    return [w for w in out if all(c in pool for c in w)]

def special_set(L, pool):
    out = set()
    for c in pool:
        out.add(c * L)
    for a in pool:
        for b in pool:
            if a != b:
                out.add("".join(a if i % 2 == 0 else b for i in range(L)))
            for k in range(1, L):
                out.add(a * k + b * (L - k))
    h = (L + 1) // 2
    for half in itertools.product(pool, repeat=h):
        s = "".join(half)
        out.add(s + s[::-1][L % 2:])
    out.update(runs(L, pool))
    return out

def gen_random(L, pool):
    seen, total = set(), len(pool) ** L
    while len(seen) < total:
        n = "".join(random.choices(pool, k=L))
        if n not in seen:
            seen.add(n)
            yield n

def gen_ordered(L, pool):
    first = sorted(set(runs(L, pool)))
    seen = set(first)
    for w in first:
        yield w
    for t in itertools.product(pool, repeat=L):
        w = "".join(t)
        if w not in seen:
            yield w

def gen_similar(L, pool, base, tak):
    m = len(base)
    if m == L:
        lk = variants(base)
        nr = [v for v in near(base, pool) if v not in lk]
        if tak:
            for v in lk + nr:
                yield (base, v)
        else:
            yield base
            for v in lk + nr:
                yield v
        return
    seen, miss = set(), 0
    cap = (L - m + 1) * len(pool) ** (L - m)
    while len(seen) < cap and miss < 5000:
        p = random.randint(0, L - m)
        n = ("".join(random.choices(pool, k=p)) + base + "".join(random.choices(pool, k=L - m - p)))
        if n in seen:
            miss += 1
            continue
        miss = 0
        seen.add(n)
        if tak:
            v = variants(n) or near(n, pool)
            yield (n, random.choice(v))
        else:
            yield n

def make_gen(L, mode, pool, base, tak):
    if mode == "random":
        return gen_random(L, pool)
    if mode == "special":
        items = list(special_set(L, pool))
        random.shuffle(items)
        return iter(items)
    if mode == "ordered":
        return gen_ordered(L, pool)
    return gen_similar(L, pool, base, tak)

# ---------------------------------------------------------------- USER INTERFACE (GUI)
class TikTokApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TikTok Username Checker ⚡")
        self.geometry("520x670")
        self.configure(bg="#1e1e2e")
        self.resizable(False, False)

        self.cfg = {"length": 4, "mode": "random", "digits": False, "base": "", "tak": False}
        self.history = []

        # Top Bar
        self.top_bar = tk.Frame(self, bg="#181825", height=45)
        self.top_bar.pack(fill="x", side="top")

        self.btn_back = tk.Button(self.top_bar, text="↩ Back", font=("Arial", 11, "bold"),
                                  bg="#f38ba8", fg="#11111b", command=self.go_back, state="disabled")
        self.btn_back.pack(side="right", padx=10, pady=5)

        self.lbl_title = tk.Label(self.top_bar, text="TikTok Fast Checker (20 Threads)", font=("Arial", 12, "bold"),
                                  bg="#181825", fg="#cdd6f4")
        self.lbl_title.pack(side="left", padx=15, pady=5)

        # Main Frame
        self.main_frame = tk.Frame(self, bg="#1e1e2e")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Start background threads
        for _ in range(THREADS):
            threading.Thread(target=self.worker_thread, daemon=True).start()

        self.show_step_length()

    def set_back_state(self, enabled=True):
        self.btn_back.config(state="normal" if enabled else "disabled")

    def go_back(self):
        if S["running"]:
            S["running"] = False
        if self.history:
            last_step = self.history.pop()
            last_step()

    def clear_frame(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

    # --- Step 1: Length Selection ---
    def show_step_length(self):
        self.clear_frame()
        self.set_back_state(bool(self.history))
        
        lbl = tk.Label(self.main_frame, text="Select Username Length:", font=("Arial", 14, "bold"),
                       bg="#1e1e2e", fg="#cdd6f4")
        lbl.pack(pady=20)

        btn_frame = tk.Frame(self.main_frame, bg="#1e1e2e")
        btn_frame.pack(pady=10)

        for l_num, text in [(3, "3 Characters (3 Letter)"), (4, "4 Characters (4 Letter)"), (5, "5 Characters (5 Letter)")]:
            btn = tk.Button(btn_frame, text=text, font=("Arial", 12), width=28, bg="#313244", fg="#cdd6f4",
                            activebackground="#45475a", command=lambda l=l_num: self.select_length(l))
            btn.pack(pady=8)

    def select_length(self, length):
        self.cfg["length"] = length
        self.history.append(self.show_step_length)
        self.show_step_mode()

    # --- Step 2: Mode Selection ---
    def show_step_mode(self):
        self.clear_frame()
        self.set_back_state(True)

        lbl = tk.Label(self.main_frame, text=f"Selected Length: ({self.cfg['length']}) Chars\nSelect Generation Mode:",
                       font=("Arial", 13, "bold"), bg="#1e1e2e", fg="#cdd6f4")
        lbl.pack(pady=15)

        modes = [
            ("special", "⭐ Special (Rare patterns & sequences)"),
            ("random", "🎲 Random (Unordered generation)"),
            ("ordered", "📐 Ordered (Sequential alphabet)"),
            ("similar", "🪞 Similar (Based on custom word)")
        ]

        for m_key, m_text in modes:
            btn = tk.Button(self.main_frame, text=m_text, font=("Arial", 11), width=32, bg="#313244", fg="#cdd6f4",
                            command=lambda k=m_key: self.select_mode(k))
            btn.pack(pady=6)

    def select_mode(self, mode):
        self.cfg["mode"] = mode
        self.history.append(self.show_step_mode)
        if mode == "similar":
            self.show_step_similar()
        else:
            self.show_step_digits()

    # --- Step 3: Custom Base & Matching ---
    def show_step_similar(self):
        self.clear_frame()
        self.set_back_state(True)

        L = self.cfg["length"]
        lbl = tk.Label(self.main_frame, text=f"Enter 1 to {L} letters/numbers:",
                       font=("Arial", 12, "bold"), bg="#1e1e2e", fg="#cdd6f4")
        lbl.pack(pady=10)

        ent_base = tk.Entry(self.main_frame, font=("Arial", 13), justify="center", bg="#313244", fg="#a6e3a1")
        ent_base.pack(pady=5)

        var_tak = tk.BooleanVar(value=False)
        chk_tak = tk.Checkbutton(self.main_frame, text="Enable Matching Pair (Check 2 similar usernames)",
                                 var=var_tak, font=("Arial", 10), bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244")
        chk_tak.pack(pady=15)

        def confirm():
            val = ent_base.get().strip().lower()
            if not re.fullmatch(r"[a-z0-9_.]{1,%d}" % L, val) or val.endswith("."):
                messagebox.showerror("Error", f"Enter valid text between 1 and {L} chars!")
                return
            self.cfg["base"] = val
            self.cfg["tak"] = var_tak.get()
            self.history.append(self.show_step_similar)
            self.show_step_digits()

        btn_next = tk.Button(self.main_frame, text="Confirm & Continue ➔", font=("Arial", 11, "bold"), bg="#a6e3a1", fg="#11111b", command=confirm)
        btn_next.pack(pady=10)

    # --- Step 4: Digits Option ---
    def show_step_digits(self):
        self.clear_frame()
        self.set_back_state(True)

        var_digits = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(self.main_frame, text="Include numbers (0-9) in generation?", var=var_digits,
                             font=("Arial", 12), bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244")
        chk.pack(pady=20)

        def start_search():
            self.cfg["digits"] = var_digits.get()
            self.history.append(self.show_step_digits)
            self.show_monitor_screen()

        btn_start = tk.Button(self.main_frame, text="▶️ Start Checking ⚡", font=("Arial", 12, "bold"),
                              bg="#89b4fa", fg="#11111b", width=20, command=start_search)
        btn_start.pack(pady=10)

    # --- Final Screen: Live Monitor ---
    def show_monitor_screen(self):
        self.clear_frame()
        self.set_back_state(True)

        pool = string.ascii_lowercase + (string.digits if self.cfg["digits"] else "")
        it = make_gen(self.cfg["length"], self.cfg["mode"], pool, self.cfg["base"], self.cfg["tak"])

        with lock:
            S["rid"] += 1
            S.update(done=0, yes=[], no=0, running=True, finished=False, start_time=time.time())
            GEN["it"] = it

        self.lbl_stats = tk.Label(self.main_frame, text="Checked: 0 | Available: 0", font=("Arial", 11, "bold"),
                                  bg="#1e1e2e", fg="#a6e3a1")
        self.lbl_stats.pack(pady=3)

        self.lbl_eta = tk.Label(self.main_frame, text="⏱ Estimated Time to Hit: Calculating...",
                                font=("Arial", 10, "bold"), bg="#1e1e2e", fg="#f9e2af")
        self.lbl_eta.pack(pady=3)

        lbl_log = tk.Label(self.main_frame, text="🎯 Available Usernames Only (✅):", font=("Arial", 10, "bold"), bg="#1e1e2e", fg="#89b4fa")
        lbl_log.pack(anchor="w", pady=(10, 0))

        self.txt_log = scrolledtext.ScrolledText(self.main_frame, height=14, bg="#181825", fg="#a6e3a1", font=("Consolas", 10, "bold"))
        self.txt_log.pack(fill="both", expand=True, pady=5)

        ctrl_frame = tk.Frame(self.main_frame, bg="#1e1e2e")
        ctrl_frame.pack(pady=5)

        self.btn_stop = tk.Button(ctrl_frame, text="⏹ Stop", font=("Arial", 10, "bold"), bg="#f38ba8", fg="#11111b", command=self.stop_checking)
        self.btn_stop.pack(side="left", padx=5)

        self.update_ui_loop()

    def stop_checking(self):
        S["running"] = False
        messagebox.showinfo("Stopped", "Checking process stopped!")

    def update_ui_loop(self):
        if not self.main_frame.winfo_exists():
            return

        with lock:
            done = S["done"]
            yes_count = len(S["yes"])
            elapsed = time.time() - S["start_time"]

        self.lbl_stats.config(text=f"Checked: {done} | Available: {yes_count}")

        # Calculate ETA
        if elapsed > 2 and done > 0:
            speed = done / elapsed  # Checks per second
            if yes_count > 0:
                avg_checks_per_hit = done / yes_count
                est_seconds = avg_checks_per_hit / speed
                if est_seconds < 60:
                    eta_str = f"~{int(est_seconds)} Seconds"
                elif est_seconds < 3600:
                    eta_str = f"~{int(est_seconds // 60)}m {int(est_seconds % 60)}s"
                else:
                    eta_str = f"~{round(est_seconds / 3600, 1)} Hours"
            else:
                eta_str = f"Scanning ({round(speed, 1)} u/s)..."
            self.lbl_eta.config(text=f"⏱ Estimated Time to Hit: {eta_str}")

        if S["running"]:
            self.after(200, self.update_ui_loop)

    # --- Worker Thread Engine ---
    def worker_thread(self):
        while True:
            if not S["running"]:
                time.sleep(0.05)
                continue

            item = None
            with lock:
                rid = S["rid"]
                try:
                    item = next(GEN["it"])
                except (StopIteration, TypeError):
                    S["running"] = False
                    S["finished"] = True

            if not item or not S["running"]:
                continue

            names = item if isinstance(item, tuple) else (item,)

            res = [check_username(n) for n in names]

            with lock:
                if rid != S["rid"]:
                    continue
                S["done"] += 1
                S["no"] += sum(1 for r, _ in res if r is False)

                ok = [n for n, (r, _) in zip(names, res) if r is True]
                
                # Show only available usernames
                if ok:
                    entry = f"@{ok[0]} Yes ✅" if len(names) == 1 else f"@{names[0]} + @{names[1]} 🔥 Available Match"
                    S["yes"].append(entry)
                    
                    if hasattr(self, 'txt_log') and self.txt_log.winfo_exists():
                        self.txt_log.insert("1.0", entry + "\n")

                    with open("available.txt", "a", encoding="utf-8") as f:
                        f.write(entry + "\n")

if __name__ == "__main__":
    app = TikTokApp()
    app.mainloop()
()
