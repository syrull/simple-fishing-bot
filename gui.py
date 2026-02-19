import os
import tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime

from PIL import Image
from pynput import keyboard

from fishingbot import FishingBot
from autocrop import autocrop_bait


class FishingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fishing Bot")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.bot = None
        self.bait_path = None

        self._build_ui()
        self._start_hotkey_listener()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # --- Bait Image Section ---
        bait_frame = ttk.LabelFrame(self.root, text="Bait Image")
        bait_frame.pack(fill="x", **pad)

        btn_row = ttk.Frame(bait_frame)
        btn_row.pack(fill="x", **pad)
        ttk.Button(btn_row, text="Browse...", command=self._browse_bait).pack(
            side="left", padx=(0, 4)
        )
        ttk.Button(btn_row, text="Auto-Crop", command=self._autocrop_bait).pack(
            side="left"
        )
        self.bait_info_var = tk.StringVar(value="No image loaded")
        ttk.Label(btn_row, textvariable=self.bait_info_var).pack(
            side="left", padx=(8, 0)
        )

        # --- Configuration Section ---
        cfg_frame = ttk.LabelFrame(self.root, text="Configuration")
        cfg_frame.pack(fill="x", **pad)

        self.cfg_entries = {}
        fields = [
            ("Fishing Key", "b"),
            ("Confidence", "0.7"),
            ("Mouse Offset (px)", "35"),
            ("Edge Reset X", "10"),
            ("Edge Reset Y", "10"),
            ("Start Delay (s)", "2"),
        ]
        for i, (label, default) in enumerate(fields):
            ttk.Label(cfg_frame, text=label).grid(
                row=i // 3, column=(i % 3) * 2, sticky="e", padx=(8, 2), pady=2
            )
            var = tk.StringVar(value=default)
            entry = ttk.Entry(cfg_frame, textvariable=var, width=10)
            entry.grid(row=i // 3, column=(i % 3) * 2 + 1, sticky="w", padx=(0, 8), pady=2)
            self.cfg_entries[label] = (var, entry)

        # --- Controls Section ---
        ctrl_frame = ttk.LabelFrame(self.root, text="Controls")
        ctrl_frame.pack(fill="x", **pad)

        self.start_btn = ttk.Button(
            ctrl_frame, text="START FISHING", command=self._toggle_bot
        )
        self.start_btn.pack(fill="x", **pad)
        ttk.Label(ctrl_frame, text="Global hotkey: F6").pack(**pad)

        # --- Status Section ---
        status_frame = ttk.LabelFrame(self.root, text="Status")
        status_frame.pack(fill="both", expand=True, **pad)

        info_row = ttk.Frame(status_frame)
        info_row.pack(fill="x", **pad)
        self.state_var = tk.StringVar(value="Idle")
        ttk.Label(info_row, textvariable=self.state_var, font=("", 10, "bold")).pack(
            side="left"
        )
        self.fish_var = tk.StringVar(value="Fish: 0")
        ttk.Label(info_row, textvariable=self.fish_var).pack(side="right")

        self.log_text = tk.Text(status_frame, height=8, width=50, state="disabled")
        self.log_text.pack(fill="both", expand=True, **pad)

    # ── Bait image handling ──────────────────────────────────────

    def _browse_bait(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All", "*.*")]
        )
        if path:
            self.bait_path = path
            self._update_bait_info(path)

    def _autocrop_bait(self):
        if not self.bait_path:
            self._log("No bait image loaded.")
            return
        try:
            cropped = autocrop_bait(self.bait_path)
            base, ext = os.path.splitext(self.bait_path)
            out_path = base + "_cropped.png"
            cropped.save(out_path)
            self.bait_path = out_path
            self._update_bait_info(out_path)
            self._log("Auto-cropped and saved to {}".format(os.path.basename(out_path)))
        except Exception as e:
            self._log("Auto-crop failed: {}".format(e))

    def _update_bait_info(self, path):
        try:
            img = Image.open(path)
            w, h = img.size
            self.bait_info_var.set("{}  ({}x{})".format(os.path.basename(path), w, h))
        except Exception as e:
            self.bait_info_var.set("Error: {}".format(e))

    # ── Bot start / stop ─────────────────────────────────────────

    def _toggle_bot(self):
        if self.bot and self.bot.running:
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self):
        if not self.bait_path:
            self._log("Please load a bait image first.")
            return

        try:
            cfg = {k: v.get() for k, (v, _) in self.cfg_entries.items()}
            self.bot = FishingBot(
                bait_image=self.bait_path,
                fishing_button=cfg["Fishing Key"],
                mouse_offset_px=int(cfg["Mouse Offset (px)"]),
                edge_reset=(int(cfg["Edge Reset X"]), int(cfg["Edge Reset Y"])),
                start_delay=float(cfg["Start Delay (s)"]),
                confidence=float(cfg["Confidence"]),
                on_status=lambda msg: self.root.after(0, self._on_bot_status, msg),
                on_fish_caught=lambda n: self.root.after(0, self._on_fish_caught, n),
            )
        except (ValueError, KeyError) as e:
            self._log("Config error: {}".format(e))
            return

        self.bot.start()
        self.start_btn.configure(text="STOP")
        self.state_var.set("Running")
        self._set_config_state("disabled")
        self._poll_bot_stopped()

    def _stop_bot(self):
        if self.bot:
            self.bot.stop()

    def _poll_bot_stopped(self):
        if self.bot and self.bot.running:
            self.root.after(100, self._poll_bot_stopped)
        else:
            self.start_btn.configure(text="START FISHING")
            self.state_var.set("Idle")
            self._set_config_state("normal")

    def _set_config_state(self, state):
        for _, entry in self.cfg_entries.values():
            entry.configure(state=state)

    # ── Bot callbacks (called on main thread via root.after) ─────

    def _on_bot_status(self, msg):
        self.state_var.set(msg)
        self._log(msg)

    def _on_fish_caught(self, count):
        self.fish_var.set("Fish: {}".format(count))

    # ── Log ───────────────────────────────────────────────────────

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "[{}] {}\n".format(ts, msg))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ── Global hotkey (F6) ───────────────────────────────────────

    def _start_hotkey_listener(self):
        def on_press(key):
            if key == keyboard.Key.f6:
                self.root.after(0, self._toggle_bot)

        self._hotkey_listener = keyboard.Listener(on_press=on_press)
        self._hotkey_listener.daemon = True
        self._hotkey_listener.start()

    # ── Window close ─────────────────────────────────────────────

    def _on_close(self):
        if self.bot and self.bot.running:
            self.bot.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    FishingBotGUI(root)
    root.mainloop()
