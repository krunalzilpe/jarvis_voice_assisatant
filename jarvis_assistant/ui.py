from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageTk = None

try:
    import pystray
    from PIL import Image as TrayImage, ImageDraw
except ImportError:  # pragma: no cover
    pystray = None
    TrayImage = None
    ImageDraw = None

from .brain import AssistantBrain
from .config import AppSettings, IMAGE_DIR, save_settings
from .models import ActionResult, AssistantStatus


class JarvisDesktopApp:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.brain = AssistantBrain(settings)
        self.brain.add_listener(self._handle_engine_result)
        self.logger = logging.getLogger(__name__)
        self.root = tk.Tk()
        self.root.title(f"{settings.assistant_name} Desktop Assistant")
        self.root.geometry("1180x760")
        self.root.minsize(1080, 700)
        self._setup_style()
        self.event_queue: queue.Queue[ActionResult] = queue.Queue()
        self.preview_image = None
        self.tray_icon = None

        self.status_var = tk.StringVar(value=AssistantStatus.IDLE.value)
        self.last_command_var = tk.StringVar(value="-")
        self.last_action_var = tk.StringVar(value="-")
        self.active_window_var = tk.StringVar(value="-")
        self.agent_status_var = tk.StringVar(value="stopped")
        self.voice_ready_var = tk.StringVar(value="checking")
        self.api_ready_var = tk.StringVar(value="not configured")
        self.setup_summary_var = tk.StringVar(value="Loading setup state...")

        self.assistant_name_var = tk.StringVar(value=settings.assistant_name)
        self.wake_phrase_var = tk.StringVar(value=settings.wake_phrase)
        self.theme_var = tk.StringVar(value=settings.theme)
        self.reply_style_var = tk.StringVar(value=settings.reply_style)
        self.browser_var = tk.StringVar(value=settings.preferred_browser)
        self.ai_model_var = tk.StringVar(value=settings.ai_model)
        self.image_model_var = tk.StringVar(value=settings.image_model)
        self.openai_key_var = tk.StringVar(value=settings.openai_api_key)
        self.base_url_var = tk.StringVar(value=settings.openai_base_url)
        self.microphone_var = tk.StringVar(value=settings.microphone_name)
        self.speaker_var = tk.StringVar(value=settings.speaker_name)
        self.voice_on_start_var = tk.BooleanVar(value=settings.startup_launch_voice)
        self.tray_var = tk.BooleanVar(value=settings.minimize_to_tray)
        self.always_listen_var = tk.BooleanVar(value=settings.always_listen)
        self.chat_input_var = tk.StringVar()
        self.image_prompt_var = tk.StringVar()
        self.microphone_names = self.brain.voice.available_microphones()
        if settings.microphone_name and settings.microphone_name not in self.microphone_names:
            self.microphone_names.append(settings.microphone_name)

        self.permission_vars = {
            "app_control": tk.BooleanVar(value=settings.permissions.app_control),
            "browser_control": tk.BooleanVar(value=settings.permissions.browser_control),
            "mouse_control": tk.BooleanVar(value=settings.permissions.mouse_control),
            "keyboard_typing": tk.BooleanVar(value=settings.permissions.keyboard_typing),
            "clipboard_access": tk.BooleanVar(value=settings.permissions.clipboard_access),
            "screenshot_access": tk.BooleanVar(value=settings.permissions.screenshot_access),
            "power_actions": tk.BooleanVar(value=settings.permissions.power_actions),
            "dangerous_action_confirmation": tk.BooleanVar(value=settings.permissions.dangerous_action_confirmation),
        }

        self._build_layout()
        self.root.after(200, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        # main container
        self.root.configure(bg="#0f172a")
        header = tk.Frame(self.root, bg="#0b1220", padx=20, pady=18)
        header.pack(fill="x")
        tk.Label(header, text=f"{self.settings.assistant_name} Control Center", font=("Segoe UI Semibold", 22), fg="#fbbf24", bg="#0b1220").pack(side="left")
        tk.Label(header, text="Windows desktop AI assistant", font=("Segoe UI", 11), fg="#cbd5f5", bg="#0b1220").pack(side="left", padx=18, pady=(8, 0))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=14, pady=14)

        tabs = {name: ttk.Frame(notebook) for name in ("Home / Status", "Configuration", "Customization", "Permissions", "Controls", "AI Chat Box", "Image Generation")}
        for name, frame in tabs.items():
            notebook.add(frame, text=name)

        self._build_home_tab(tabs["Home / Status"])
        self._build_configuration_tab(tabs["Configuration"])
        self._build_customization_tab(tabs["Customization"])
        self._build_permissions_tab(tabs["Permissions"])
        self._build_controls_tab(tabs["Controls"])
        self._build_chat_tab(tabs["AI Chat Box"])
        self._build_image_tab(tabs["Image Generation"])

    def _build_home_tab(self, frame: ttk.Frame) -> None:
        outer = ttk.Frame(frame, padding=16)
        outer.pack(fill="both", expand=True)

        hero = tk.Frame(outer, bg="#111827", padx=24, pady=22, highlightthickness=1, highlightbackground="#243244")
        hero.pack(fill="x", pady=(0, 14))
        tk.Label(
            hero,
            text=f"{self.settings.assistant_name} Desktop Operator",
            font=("Segoe UI Semibold", 24),
            fg="#f8fafc",
            bg="#111827",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            hero,
            text="Voice control, AI chat, and end-to-end Windows task execution from one console.",
            font=("Segoe UI", 11),
            fg="#cbd5e1",
            bg="#111827",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        status_chip = tk.Label(
            hero,
            textvariable=self.status_var,
            font=("Segoe UI Semibold", 12),
            fg="#0f172a",
            bg="#fbbf24",
            padx=14,
            pady=6,
        )
        status_chip.grid(row=0, column=1, rowspan=2, sticky="e")
        hero.columnconfigure(0, weight=1)

        quick = ttk.LabelFrame(outer, text="Quick Actions", padding=14, style="Card.TLabelframe")
        quick.pack(fill="x", pady=(0, 14))
        quick_actions = [
            ("Start Voice", self._start_agent),
            ("Test Mic", self._test_microphone),
            ("Open Notepad", lambda: self._run_command("notepad kholo")),
            ("Google Search", lambda: self._run_command("google pe python automation search karo")),
            ("Play YouTube", lambda: self._run_command("youtube pe believer song baja")),
            ("Take Screenshot", lambda: self._run_command("screenshot lo")),
        ]
        for index, (label, command) in enumerate(quick_actions):
            ttk.Button(quick, text=label, command=command).grid(row=index // 3, column=index % 3, sticky="ew", padx=8, pady=8)
        for column in range(3):
            quick.columnconfigure(column, weight=1)

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))

        for label, variable in (
            ("Last Command", self.last_command_var),
            ("Last Action", self.last_action_var),
            ("Active Window", self.active_window_var),
            ("Background Agent", self.agent_status_var),
        ):
            card = ttk.LabelFrame(left, text=label, padding=14, style="Card.TLabelframe")
            card.pack(fill="x", pady=8)
            ttk.Label(card, textvariable=variable, font=("Segoe UI", 12)).pack(anchor="w")

        setup = ttk.LabelFrame(right, text="Readiness", padding=14, style="Card.TLabelframe")
        setup.pack(fill="x", pady=8)
        ttk.Label(setup, text="Voice", font=("Segoe UI Semibold", 11)).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(setup, textvariable=self.voice_ready_var, font=("Segoe UI", 11)).grid(row=0, column=1, sticky="w", pady=4, padx=(18, 0))
        ttk.Label(setup, text="OpenAI", font=("Segoe UI Semibold", 11)).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(setup, textvariable=self.api_ready_var, font=("Segoe UI", 11)).grid(row=1, column=1, sticky="w", pady=4, padx=(18, 0))

        checklist = ttk.LabelFrame(right, text="Setup Notes", padding=14, style="Card.TLabelframe")
        checklist.pack(fill="both", expand=True, pady=8)
        ttk.Label(checklist, textvariable=self.setup_summary_var, wraplength=360, justify="left", font=("Segoe UI", 10)).pack(anchor="w")

    def _build_configuration_tab(self, frame: ttk.Frame) -> None:
        form = ttk.Frame(frame, padding=16)
        form.pack(fill="both", expand=True)
        rows = [
            ("AI model", self.ai_model_var),
            ("Image model", self.image_model_var),
            ("OpenAI API key", self.openai_key_var),
            ("Base URL", self.base_url_var),
            ("Speaker", self.speaker_var),
        ]
        for index, (label, variable) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", pady=8, padx=8)
            ttk.Entry(form, textvariable=variable, width=64, show="*" if "key" in label.lower() else "").grid(row=index, column=1, sticky="ew", pady=8, padx=8)
        ttk.Label(form, text="Microphone").grid(row=5, column=0, sticky="w", pady=8, padx=8)
        microphone_values = self.microphone_names if self.microphone_names else [self.microphone_var.get() or "Default system microphone"]
        microphone_box = ttk.Combobox(form, textvariable=self.microphone_var, values=microphone_values, state="normal")
        microphone_box.grid(row=5, column=1, sticky="ew", pady=8, padx=8)
        ttk.Checkbutton(form, text="Start voice agent on launch", variable=self.voice_on_start_var).grid(row=6, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(form, text="Minimize to tray", variable=self.tray_var).grid(row=7, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(form, text="Always listen (without wake phrase)", variable=self.always_listen_var).grid(row=8, column=0, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Button(form, text="Save Configuration", command=self._save_settings).grid(row=9, column=0, pady=18, padx=8, sticky="w")
        ttk.Label(
            form,
            text="Tip: choose the exact microphone used for wake-word commands to reduce missed recognition.",
            wraplength=560,
            justify="left",
        ).grid(row=10, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 0))
        form.columnconfigure(1, weight=1)

    def _build_customization_tab(self, frame: ttk.Frame) -> None:
        form = ttk.Frame(frame, padding=16)
        form.pack(fill="both", expand=True)
        rows = [
            ("Assistant name", self.assistant_name_var),
            ("Wake phrase", self.wake_phrase_var),
            ("Theme", self.theme_var),
            ("Reply style", self.reply_style_var),
            ("Preferred browser", self.browser_var),
        ]
        for index, (label, variable) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", pady=8, padx=8)
            ttk.Entry(form, textvariable=variable, width=40).grid(row=index, column=1, sticky="ew", pady=8, padx=8)
        ttk.Button(form, text="Save Customization", command=self._save_settings).grid(row=6, column=0, pady=18, padx=8, sticky="w")
        form.columnconfigure(1, weight=1)

    def _build_permissions_tab(self, frame: ttk.Frame) -> None:
        panel = ttk.Frame(frame, padding=16)
        panel.pack(fill="both", expand=True)
        labels = {
            "app_control": "App control",
            "browser_control": "Browser control",
            "mouse_control": "Mouse control",
            "keyboard_typing": "Keyboard typing",
            "clipboard_access": "Clipboard access",
            "screenshot_access": "Screenshot access",
            "power_actions": "Shutdown / restart / lock",
            "dangerous_action_confirmation": "Dangerous action confirmation",
        }
        for index, (key, variable) in enumerate(self.permission_vars.items()):
            ttk.Checkbutton(panel, text=labels[key], variable=variable).grid(row=index, column=0, sticky="w", pady=6, padx=8)
        ttk.Button(panel, text="Save Permissions", command=self._save_settings).grid(row=10, column=0, pady=18, padx=8, sticky="w")

    def _build_controls_tab(self, frame: ttk.Frame) -> None:
        panel = ttk.Frame(frame, padding=16)
        panel.pack(fill="both", expand=True)
        buttons = [
            ("Start Assistant", self._start_agent),
            ("Pause Assistant", lambda: self._run_command("pause assistant")),
            ("Resume Assistant", lambda: self._run_command("resume assistant")),
            ("Stop Assistant", self._stop_agent),
            ("Test Microphone", self._test_microphone),
            ("Test Automation", lambda: self._run_command("screenshot lo")),
            ("Test Browser Typing", lambda: self._run_command("google pe python automation search karo")),
            ("Test Notepad Typing", lambda: self._run_command("notepad kholo")),
        ]
        for index, (label, command) in enumerate(buttons):
            ttk.Button(panel, text=label, command=command).grid(row=index // 2, column=index % 2, sticky="ew", padx=8, pady=8)
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

    def _build_chat_tab(self, frame: ttk.Frame) -> None:
        outer = ttk.Frame(frame, padding=16)
        outer.pack(fill="both", expand=True)
        self.chat_log = tk.Text(
            outer,
            wrap="word",
            font=("Consolas", 11),
            bg="#0b1220",
            fg="#e5e7eb",
            insertbackground="#fbbf24",
            height=20,
            highlightthickness=1,
            highlightbackground="#1f2937",
        )
        self.chat_log.pack(fill="both", expand=True, pady=(0, 10))
        self.chat_log.configure(state="disabled")

        input_row = ttk.Frame(outer)
        input_row.pack(fill="x", pady=(0, 12))
        ttk.Entry(input_row, textvariable=self.chat_input_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(input_row, text="Send", command=self._send_chat).pack(side="left")

        ttk.Label(outer, text="Command History").pack(anchor="w")
        self.history_table = ttk.Treeview(outer, columns=("time", "intent", "success", "target"), show="headings", height=10)
        for column, label, width in (("time", "Time", 180), ("intent", "Intent", 180), ("success", "Success", 100), ("target", "Target", 360)):
            self.history_table.heading(column, text=label)
            self.history_table.column(column, width=width, anchor="w")
        self.history_table.pack(fill="both", expand=True)
        self._refresh_history()

    def _build_image_tab(self, frame: ttk.Frame) -> None:
        outer = ttk.Frame(frame, padding=16)
        outer.pack(fill="both", expand=True)
        top = ttk.Frame(outer)
        top.pack(fill="x")
        ttk.Entry(top, textvariable=self.image_prompt_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(top, text="Generate", command=self._generate_image).pack(side="left")
        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True, pady=16)
        self.image_history = tk.Listbox(content, bg="#0b1220", fg="#e5e7eb", highlightbackground="#1f2937", selectbackground="#334155")
        self.image_history.pack(side="left", fill="y")
        self.image_history.bind("<<ListboxSelect>>", self._show_selected_image)
        self.image_preview = ttk.Label(content, text="Generated image preview", background="#0f172a", foreground="#e5e7eb")
        self.image_preview.pack(side="left", fill="both", expand=True, padx=16)
        self._load_image_history()

    def _save_settings(self) -> None:
        self.settings.assistant_name = self.assistant_name_var.get().strip() or "Jarvis"
        self.settings.wake_phrase = self.wake_phrase_var.get().strip() or "hey jarvis"
        self.settings.theme = self.theme_var.get().strip() or "light"
        self.settings.reply_style = self.reply_style_var.get().strip() or "professional"
        self.settings.preferred_browser = self.browser_var.get().strip() or "default"
        self.settings.ai_model = self.ai_model_var.get().strip() or self.settings.ai_model
        self.settings.image_model = self.image_model_var.get().strip() or self.settings.image_model
        self.settings.openai_api_key = self.openai_key_var.get().strip()
        self.settings.openai_base_url = self.base_url_var.get().strip()
        self.settings.microphone_name = self.microphone_var.get().strip()
        self.settings.speaker_name = self.speaker_var.get().strip()
        self.settings.startup_launch_voice = self.voice_on_start_var.get()
        self.settings.minimize_to_tray = self.tray_var.get()
        self.settings.always_listen = self.always_listen_var.get()
        for key, variable in self.permission_vars.items():
            setattr(self.settings.permissions, key, variable.get())
        save_settings(self.settings)
        messagebox.showinfo("Saved", "Settings save kar diye gaye.")

    def _append_chat(self, speaker: str, message: str) -> None:
        self.chat_log.configure(state="normal")
        self.chat_log.insert("end", f"{speaker}: {message}\n")
        self.chat_log.see("end")
        self.chat_log.configure(state="disabled")

    def _send_chat(self) -> None:
        text = self.chat_input_var.get().strip()
        if not text:
            return
        self.chat_input_var.set("")
        self._append_chat("You", text)
        self._run_command(text)

    def _run_command(self, text: str) -> None:
        threading.Thread(target=self.brain.handle_input, args=(text, "chat"), daemon=True).start()

    def _handle_engine_result(self, result: ActionResult) -> None:
        self.event_queue.put(result)

    def _poll_events(self) -> None:
        while not self.event_queue.empty():
            result = self.event_queue.get()
            self._append_chat(self.settings.assistant_name, result.reply)
            self._refresh_runtime_labels()
            self._refresh_history()
            if result.payload.get("path"):
                self._load_image_history()
                self._show_image(Path(result.payload["path"]))
        self._refresh_runtime_labels()
        self.root.after(250, self._poll_events)

    def _refresh_runtime_labels(self) -> None:
        state = self.brain.context_manager.state
        self.status_var.set(state.status.value)
        self.last_command_var.set(state.last_command or "-")
        self.last_action_var.set(state.last_action or "-")
        self.active_window_var.set(state.active_window or state.active_app or "-")
        self.agent_status_var.set("running" if state.background_agent_running else "stopped")
        self.voice_ready_var.set(self._voice_readiness_label())
        self.api_ready_var.set("configured" if self.settings.openai_api_key else "not configured")
        self.setup_summary_var.set(self._setup_summary())

    def _refresh_history(self) -> None:
        for row in self.history_table.get_children():
            self.history_table.delete(row)
        for item in self.brain.history_store.recent(25):
            self.history_table.insert("", "end", values=(item["created_at"].replace("T", " ")[:19], item["interpreted_intent"], "yes" if item["success"] else "no", item["target"] or "-"))

    def _start_agent(self) -> None:
        started = self.brain.start_background_agent()
        self._refresh_runtime_labels()
        if started:
            self._append_chat(self.settings.assistant_name, "Background assistant start kar diya.")
        else:
            detail = self.brain.voice.last_error_message() or "Voice backend available nahi hai."
            self._append_chat(self.settings.assistant_name, f"Voice agent start nahi ho paya: {detail}")

    def _stop_agent(self) -> None:
        self.brain.stop_background_agent()
        self._refresh_runtime_labels()
        self._append_chat(self.settings.assistant_name, "Background assistant stop kar diya.")

    def _test_microphone(self) -> None:
        self._append_chat("Mic", "Listening for a short sample...")

        def runner() -> None:
            heard = self.brain.voice.listen_once(timeout=3, phrase_time_limit=5)
            diagnostics = self.brain.voice.diagnostics()
            if heard:
                message = heard
            else:
                detail = diagnostics.get("last_error")
                backend = diagnostics.get("backend")
                if detail:
                    message = f"No voice input captured. Backend: {backend}. Detail: {detail}"
                else:
                    message = f"No voice input captured. Backend: {backend}. Check microphone selection and Windows microphone privacy."
            self.root.after(0, lambda: self._append_chat("Mic", message))

        threading.Thread(target=runner, daemon=True).start()

    def _generate_image(self) -> None:
        prompt = self.image_prompt_var.get().strip()
        if not prompt:
            messagebox.showwarning("Prompt required", "Image prompt dalo.")
            return
        self._append_chat("You", f"Image prompt: {prompt}")
        self._run_command(f"generate image {prompt}")

    def _load_image_history(self) -> None:
        self.image_history.delete(0, "end")
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        for path in sorted(IMAGE_DIR.glob("*.png"), reverse=True):
            self.image_history.insert("end", str(path))

    def _show_selected_image(self, _event=None) -> None:
        selection = self.image_history.curselection()
        if selection:
            self._show_image(Path(self.image_history.get(selection[0])))

    def _show_image(self, path: Path) -> None:
        if not Image or not ImageTk or not path.exists():
            self.image_preview.configure(text=str(path))
            return
        image = Image.open(path)
        image.thumbnail((620, 420))
        self.preview_image = ImageTk.PhotoImage(image)
        self.image_preview.configure(image=self.preview_image, text="")

    def _create_tray_icon(self):
        if not pystray or not TrayImage or not ImageDraw:
            return None
        icon_image = TrayImage.new("RGB", (64, 64), color=(22, 48, 43))
        draw = ImageDraw.Draw(icon_image)
        draw.ellipse((10, 10, 54, 54), fill=(225, 183, 96))
        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda: self.root.after(0, self._restore_window)),
            pystray.MenuItem("Start Voice", lambda: self.root.after(0, self._start_agent)),
            pystray.MenuItem("Quit", lambda: self.root.after(0, self._quit_from_tray)),
        )
        return pystray.Icon("jarvis_assistant", icon_image, self.settings.assistant_name, menu)

    def _minimize_to_tray(self) -> None:
        if not self.settings.minimize_to_tray:
            self.root.destroy()
            return
        if self.tray_icon is None:
            self.tray_icon = self._create_tray_icon()
            if self.tray_icon:
                threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.root.withdraw()

    def _restore_window(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def _quit_from_tray(self) -> None:
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def _on_close(self) -> None:
        self._minimize_to_tray()

    def run(self) -> None:
        self.brain.start()
        self._refresh_runtime_labels()
        self.root.mainloop()

    def _setup_style(self) -> None:
        # Vibrant but readable palette and typography
        self.root.configure(bg="#0f172a")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TNotebook",
            background="#0f172a",
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            padding=(14, 8),
            font=("Segoe UI Semibold", 11),
            background="#0f172a",
            foreground="#cbd5f5",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#1e293b")],
            foreground=[("selected", "#e2e8f0")],
        )
        style.configure(
            "Card.TLabelframe",
            background="#111827",
            foreground="#e5e7eb",
            borderwidth=1,
            relief="solid",
            labeloutside=False,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background="#111827",
            foreground="#e5e7eb",
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "TLabel",
            background="#0f172a",
            foreground="#e5e7eb",
            font=("Segoe UI", 10),
        )
        style.configure(
            "TButton",
            font=("Segoe UI Semibold", 10),
            foreground="#0f172a",
            background="#fbbf24",
            borderwidth=0,
            focusthickness=3,
            focuscolor="none",
            padding=8,
        )
        style.map(
            "TButton",
            background=[("active", "#f59e0b")],
            foreground=[("disabled", "#94a3b8")],
        )
        style.configure(
            "TEntry",
            fieldbackground="#0b1220",
            foreground="#e5e7eb",
            insertcolor="#fbbf24",
            bordercolor="#1f2937",
        )
        style.configure(
            "TCombobox",
            fieldbackground="#0b1220",
            foreground="#e5e7eb",
            bordercolor="#1f2937",
            arrowsize=16,
        )
        style.configure(
            "TCheckbutton",
            background="#0f172a",
            foreground="#e5e7eb",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview",
            background="#0b1220",
            fieldbackground="#0b1220",
            foreground="#e5e7eb",
            bordercolor="#1f2937",
            rowheight=24,
        )
        style.configure(
            "Treeview.Heading",
            background="#1f2937",
            foreground="#e5e7eb",
            font=("Segoe UI Semibold", 10),
        )
        style.map("Treeview", background=[("selected", "#334155")])

    def _voice_readiness_label(self) -> str:
        diagnostics = self.brain.voice.diagnostics()
        if diagnostics["microphone_count"]:
            if self.settings.microphone_name:
                return f"ready ({self.settings.microphone_name})"
            return "ready (default microphone)"
        return "microphone not detected"

    def _setup_summary(self) -> str:
        diagnostics = self.brain.voice.diagnostics()
        lines = [
            f"Voice agent: {'running' if self.brain.context_manager.state.background_agent_running else 'stopped'}",
            f"Wake phrase: {self.settings.wake_phrase or 'not set'}",
            f"Microphone: {self.settings.microphone_name or 'system default'}",
            f"Voice backend: {diagnostics['backend']}",
            f"OpenAI image/chat: {'enabled' if self.settings.openai_api_key else 'disabled'}",
        ]
        if not self.settings.openai_api_key:
            lines.append("Add OPENAI_API_KEY in Configuration for AI chat and image generation.")
        if not diagnostics["microphone_count"]:
            lines.append("No microphone was detected by SpeechRecognition on this machine.")
        if diagnostics["last_error"]:
            lines.append(f"Last voice error: {diagnostics['last_error']}")
        return "\n".join(lines)
