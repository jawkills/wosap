import json
import os
import shutil
import subprocess
import threading
import re
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD


class AdbDistributorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wosap")
        self.root.geometry("400x550")
        self.root.resizable(False, False)

        # Theme variables
        self.dark_mode = tk.BooleanVar(value=True)  # Default dark mode
        self.auto_refresh_interval = tk.IntVar(value=30)

        # Variables
        self.source_dir = tk.StringVar()
        self.source_dir.trace_add("write", lambda *args: self.on_folder_change())
        self.devices = []
        self.is_running = False
        self.is_paused = False
        self.device_progress = {}
        self.selected_devices = {}  # {serial: BooleanVar} - device selection controller
        self.total_progress = {"completed": 0, "total": 0}
        self.refresh_timer = None

        # Device labels storage
        self.device_labels = {}  # {serial: custom_name}
        self.device_labels_file = "device_labels.json"
        self.load_device_labels()

        # QtScrcpy Dark Theme Colors
        self.colors = {
            "bg": "#3d3d3d",  # Main background
            "bg_card": "#4a4a4a",  # Section background
            "bg_input": "#404040",  # Input fields
            "fg": "#e0e0e0",  # Primary text
            "fg_secondary": "#999999",  # Secondary text
            "border": "#555555",  # Borders
            "accent": "#5a5a5a",  # Button background
            "accent_hover": "#6a6a6a",  # Button hover
            "success": "#4CAF50",
            "error": "#e53935",
            "warning": "#fb8c00",
            "info": "#2196F3",
        }

        self.setup_styles()
        self.create_widgets()
        self.setup_shortcuts()
        self.refresh_devices()
        self.start_auto_refresh()

    def setup_styles(self):
        """Setup ttk styles"""
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "TProgressbar",
            thickness=6,
            background=self.colors["info"],
            troughcolor=self.colors["bg_input"],
        )

    def create_widgets(self):
        # Main container - QtScrcpy flat style
        self.root.configure(bg=self.colors["bg"])
        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.pack(fill="both", expand=True, padx=6, pady=4)

        # === HEADER ===
        header = tk.Frame(main_container, bg=self.colors["bg_card"], padx=6, pady=4)
        header.pack(fill="x", pady=(0, 4))

        tk.Label(
            header,
            text="Wosap",
            font=("Segoe UI", 10),
            bg=self.colors["bg_card"],
            fg=self.colors["fg"],
        ).pack(side="left")

        # === SOURCE SECTION ===
        source_frame = tk.Frame(
            main_container, bg=self.colors["bg_card"], padx=6, pady=4
        )
        source_frame.pack(fill="x", pady=(0, 4))

        # Path entry with browse button (2 column)
        path_row = tk.Frame(source_frame, bg=self.colors["bg_card"])
        path_row.pack(fill="x")

        self.path_entry = tk.Entry(
            path_row,
            textvariable=self.source_dir,
            font=("Segoe UI", 8),
            relief="flat",
            bg=self.colors["bg_input"],
            fg=self.colors["fg"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        tk.Button(
            path_row,
            text="Pilih",
            command=self.browse_folder,
            bg=self.colors["accent"],
            fg=self.colors["fg"],
            font=("Segoe UI", 8),
            relief="flat",
            padx=10,
            cursor="hand2",
        ).pack(side="right")

        # File count label
        self.file_count_label = tk.Label(
            source_frame,
            text="File: 0",
            font=("Segoe UI", 8),
            fg=self.colors["fg_secondary"],
            bg=self.colors["bg_card"],
        )
        self.file_count_label.pack(anchor="w", pady=(4, 0))

        # === DEVICES SECTION ===
        devices_frame = tk.Frame(
            main_container, bg=self.colors["bg_card"], padx=6, pady=4
        )
        devices_frame.pack(fill="x", pady=(0, 4), expand=True)

        # Section header with controls inline
        dev_header = tk.Frame(devices_frame, bg=self.colors["bg_card"])
        dev_header.pack(fill="x", pady=(0, 4))

        self.devices_count_label = tk.Label(
            dev_header,
            text="Perangkat (0)",
            font=("Segoe UI", 8),
            fg=self.colors["fg"],
            bg=self.colors["bg_card"],
        )
        self.devices_count_label.pack(side="left")

        # Refresh interval inline
        tk.Label(
            dev_header,
            text="Refresh:",
            font=("Segoe UI", 7),
            fg=self.colors["fg_secondary"],
            bg=self.colors["bg_card"],
        ).pack(side="right", padx=(0, 2))
        tk.Spinbox(
            dev_header,
            from_=10,
            to=300,
            textvariable=self.auto_refresh_interval,
            width=3,
            font=("Segoe UI", 7),
            bg=self.colors["bg_input"],
            fg=self.colors["fg"],
            relief="flat",
        ).pack(side="right")

        # Device list frame
        list_frame = tk.Frame(devices_frame, bg=self.colors["bg_input"], padx=2, pady=2)
        list_frame.pack(fill="both", expand=True)

        self.device_canvas = tk.Canvas(
            list_frame, bg=self.colors["bg_input"], highlightthickness=0, height=120
        )
        scrollbar = tk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.device_canvas.yview,
        )
        self.device_scrollable_frame = tk.Frame(
            self.device_canvas, bg=self.colors["bg_input"]
        )

        self.device_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.device_canvas.configure(
                scrollregion=self.device_canvas.bbox("all")
            ),
        )

        self.device_canvas.create_window(
            (0, 0), window=self.device_scrollable_frame, anchor="nw"
        )
        self.device_canvas.configure(yscrollcommand=scrollbar.set)

        self.device_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scroll
        self.device_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Device controls - 2 columns
        ctrl_frame = tk.Frame(devices_frame, bg=self.colors["bg_card"])
        ctrl_frame.pack(fill="x", pady=(4, 0))

        tk.Button(
            ctrl_frame,
            text="Pilih Semua",
            command=self.select_all_devices,
            bg=self.colors["accent"],
            fg=self.colors["fg"],
            font=("Segoe UI", 8),
            relief="flat",
            height=1,
            cursor="hand2",
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        tk.Button(
            ctrl_frame,
            text="Hapus Semua",
            command=self.deselect_all_devices,
            bg=self.colors["error"],
            fg="white",
            font=("Segoe UI", 8),
            relief="flat",
            height=1,
            cursor="hand2",
        ).pack(side="right", fill="x", expand=True, padx=(2, 0))

        # === PROGRESS SECTION ===
        progress_frame = tk.Frame(
            main_container, bg=self.colors["bg_card"], padx=6, pady=4
        )
        progress_frame.pack(fill="x", pady=(0, 4))

        # Progress row with label and percentage
        prog_row = tk.Frame(progress_frame, bg=self.colors["bg_card"])
        prog_row.pack(fill="x")

        tk.Label(
            prog_row,
            text="Progres:",
            font=("Segoe UI", 8),
            bg=self.colors["bg_card"],
            fg=self.colors["fg"],
        ).pack(side="left")

        self.progress_percent_label = tk.Label(
            prog_row,
            text="0%",
            font=("Segoe UI", 8),
            fg=self.colors["info"],
            bg=self.colors["bg_card"],
        )
        self.progress_percent_label.pack(side="right")

        self.total_progress_var = tk.DoubleVar(value=0)
        self.total_progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.total_progress_var,
            maximum=100,
            mode="determinate",
        )
        self.total_progress_bar.pack(fill="x", pady=(2, 0))

        self.progress_label = tk.Label(
            progress_frame,
            text="0/0 file",
            font=("Segoe UI", 8),
            fg=self.colors["fg_secondary"],
            bg=self.colors["bg_card"],
        )
        self.progress_label.pack(anchor="w")

        # === LOG SECTION ===
        log_frame = tk.Frame(main_container, bg=self.colors["bg_card"], padx=6, pady=4)
        log_frame.pack(fill="both", expand=True, pady=(0, 4))

        self.log_area = scrolledtext.ScrolledText(
            log_frame,
            height=5,
            font=("Consolas", 8),
            bg=self.colors["bg_input"],
            fg=self.colors["fg"],
            relief="flat",
            state="disabled",
        )
        self.log_area.pack(fill="both", expand=True)

        # === CONTROL BUTTONS ===
        control_frame = tk.Frame(main_container, bg=self.colors["bg"])
        control_frame.pack(fill="x")

        self.preview_btn = tk.Button(
            control_frame,
            text="Preview",
            command=self.show_transfer_preview,
            bg=self.colors["accent"],
            fg=self.colors["fg"],
            font=("Segoe UI", 9),
            relief="flat",
            height=1,
            cursor="hand2",
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, 2))

        self.start_btn = tk.Button(
            control_frame,
            text="Mulai",
            command=self.start_process,
            bg=self.colors["success"],
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            height=1,
            cursor="hand2",
        )
        self.start_btn.pack(side="right", fill="x", expand=True, padx=(2, 0))

        self.pause_btn = tk.Button(
            control_frame,
            text="Jeda",
            command=self.toggle_pause,
            bg=self.colors["warning"],
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            height=1,
            state="disabled",
            cursor="hand2",
        )

        # Enable drag and drop
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self.on_drop)

    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind("<Control-o>", lambda e: self.browse_folder())
        self.root.bind("<Control-O>", lambda e: self.browse_folder())
        self.root.bind("<Control-r>", lambda e: self.refresh_devices())
        self.root.bind("<Control-R>", lambda e: self.refresh_devices())
        self.root.bind("<Control-s>", lambda e: self.start_process())
        self.root.bind("<Control-S>", lambda e: self.start_process())

    def on_drop(self, event):
        """Handle drag and drop"""
        path = event.data
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        if os.path.isdir(path):
            self.source_dir.set(path)
        else:
            messagebox.showwarning("Peringatan", "Tolong drop folder, bukan file.")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.source_dir.set(folder)

    def select_all_devices(self):
        """Select all devices"""
        for serial, var in self.selected_devices.items():
            var.set(True)
        self.log("Semua perangkat dipilih")

    def deselect_all_devices(self):
        """Deselect all devices"""
        for serial, var in self.selected_devices.items():
            var.set(False)
        self.log("Semua perangkat tidak dipilih")

    def load_device_labels(self):
        """Load device labels from JSON file"""
        try:
            if os.path.exists(self.device_labels_file):
                with open(self.device_labels_file, "r") as f:
                    self.device_labels = json.load(f)
        except Exception:
            self.device_labels = {}

    def save_device_label(self, serial, label):
        """Save device label to JSON file"""
        self.device_labels[serial] = label
        try:
            with open(self.device_labels_file, "w") as f:
                json.dump(self.device_labels, f)
        except Exception:
            pass

    def get_device_display_name(self, serial):
        """Get display name for device (label or serial)"""
        return self.device_labels.get(serial, serial)

    def show_transfer_preview(self):
        """Show transfer preview dialog"""
        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "Pilih folder sumber yang valid.")
            return

        if not self.devices:
            messagebox.showwarning("Peringatan", "Tidak ada perangkat terhubung.")
            return

        # Get selected devices
        selected_devices = [
            serial for serial, var in self.selected_devices.items() if var.get()
        ]
        if not selected_devices:
            messagebox.showwarning("Peringatan", "Pilih minimal satu perangkat.")
            return

        # Calculate distribution
        files = self.get_sorted_files(src)
        valid_files = self.validate_files(src, files)
        distribution = self.calculate_distribution(valid_files, selected_devices, src)

        if not valid_files:
            messagebox.showwarning("Peringatan", "Tidak ada file valid untuk transfer.")
            return

        # Calculate total size
        total_size = sum(os.path.getsize(os.path.join(src, f)) for f in valid_files)

        # Build preview text
        preview_text = f"Ringkasan Transfer\n"
        preview_text += "=" * 40 + "\n\n"
        preview_text += f"Folder: {os.path.basename(src)}\n"
        preview_text += (
            f"File: {len(valid_files)} tar.gz ({self._format_size(total_size)})\n"
        )
        preview_text += f"Perangkat: {len(selected_devices)}\n\n"
        preview_text += "Distribusi:\n"
        preview_text += "-" * 40 + "\n"

        for i, (serial, file_list) in enumerate(distribution.items(), 1):
            display_name = self.get_device_display_name(serial)
            device_size = sum(os.path.getsize(os.path.join(src, f)) for f in file_list)
            preview_text += f"{i}. {display_name}\n"
            preview_text += (
                f"   {len(file_list)} file ({self._format_size(device_size)})\n"
            )

        preview_text += "\n" + "=" * 40 + "\n"

        # Show preview dialog
        # Show preview dialog - QtScrcpy style
        preview_window = tk.Toplevel(self.root)
        preview_window.title("Preview")
        preview_window.geometry("320x280")
        preview_window.resizable(False, False)
        preview_window.transient(self.root)
        preview_window.grab_set()
        preview_window.configure(bg=self.colors["bg_card"])

        # Center window
        preview_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 320) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 280) // 2
        preview_window.geometry(f"+{x}+{y}")

        # Header
        tk.Label(
            preview_window,
            text="Ringkasan Transfer",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["fg"],
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Preview text widget dengan scrollbar sendiri
        text_frame = tk.Frame(preview_window, bg=self.colors["bg_card"])
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)

        text_widget = tk.Text(
            text_frame,
            font=("Consolas", 8),
            wrap="word",
            padx=8,
            pady=8,
            bg=self.colors["bg_input"],
            fg=self.colors["fg"],
            relief="flat",
            height=12,
        )
        text_widget.pack(side="left", fill="both", expand=True)
        text_widget.insert("1.0", preview_text)
        text_widget.config(state="disabled")

        # Scrollbar untuk preview text
        preview_scrollbar = tk.Scrollbar(
            text_frame,
            orient="vertical",
            command=text_widget.yview,
            bg=self.colors["bg_card"],
            troughcolor=self.colors["bg_input"],
        )
        preview_scrollbar.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=preview_scrollbar.set)

        # Buttons frame - 2 columns
        btn_frame = tk.Frame(preview_window, bg=self.colors["bg_card"])
        btn_frame.pack(fill="x", padx=10, pady=(5, 10))

        tk.Button(
            btn_frame,
            text="Batal",
            command=preview_window.destroy,
            bg=self.colors["accent"],
            fg=self.colors["fg"],
            font=("Segoe UI", 9),
            relief="flat",
            height=1,
            cursor="hand2",
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))

        tk.Button(
            btn_frame,
            text="Mulai",
            command=lambda: [preview_window.destroy(), self.start_process()],
            bg=self.colors["success"],
            fg="white",
            font=("Segoe UI", 9),
            relief="flat",
            height=1,
            cursor="hand2",
        ).pack(side="right", fill="x", expand=True, padx=(2, 0))

    def calculate_distribution(self, files, devices, src_dir):
        """Calculate file distribution per device"""
        num_devices = len(devices)
        chunk_size = len(files) // num_devices
        remainder = len(files) % num_devices

        distribution = {}
        current_idx = 0

        for i, serial in enumerate(devices):
            count = chunk_size + (1 if i < remainder else 0)
            device_files = files[current_idx : current_idx + count]
            current_idx += count
            distribution[serial] = device_files

        return distribution

    def _format_size(self, size_bytes):
        """Format size in human readable format"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

    def get_sorted_files(self, src_dir):
        """Get files sorted by number in filename"""
        files = [f for f in os.listdir(src_dir) if f.endswith(".tar.gz")]

        def extract_sort_key(filename):
            match = re.search(r"-(\d{3})-", filename)
            return int(match.group(1)) if match else 0

        files.sort(key=extract_sort_key)
        return files

    def on_folder_change(self):
        src = self.source_dir.get()
        if os.path.exists(src):
            try:
                files = self.get_sorted_files(src)
                self.file_count_label.config(
                    text=f"File: {len(files)}",
                    fg=self.colors["fg_secondary"],
                )
            except Exception as e:
                self.file_count_label.config(text=f"Error", fg=self.colors["error"])
        else:
            self.file_count_label.config(
                text="Folder tidak valid", fg=self.colors["error"]
            )

    def validate_files(self, src_dir, files):
        """Pre-flight validation"""
        valid_files = []
        self.log(f"Memvalidasi {len(files)} file...")

        for f in files:
            filepath = os.path.join(src_dir, f)
            try:
                if os.path.getsize(filepath) == 0:
                    self.log(f"  ✗ {f}: File kosong")
                    continue
                with open(filepath, "rb") as file:
                    if file.read(2) != b"\x1f\x8b":
                        self.log(f"  ✗ {f}: Format tidak valid")
                        continue
                valid_files.append(f)
            except Exception as e:
                self.log(f"  ✗ {f}: {str(e)}")

        if len(valid_files) < len(files):
            self.log(f"✓ {len(valid_files)}/{len(files)} file valid")

        return valid_files

    def log(self, message):
        self.log_area.config(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll"""
        self.device_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def refresh_devices(self):
        try:
            for widget in self.device_scrollable_frame.winfo_children():
                widget.destroy()

            output = subprocess.check_output(["adb", "devices"]).decode("utf-8")
            lines = output.strip().split("\n")[1:]
            self.devices = [line.split("\t")[0] for line in lines if "\tdevice" in line]
            self.device_progress = {}
            self.selected_devices = {}

            # Update device count label
            if hasattr(self, "devices_count_label"):
                self.devices_count_label.config(text=f"Perangkat ({len(self.devices)})")

            if self.devices:
                for i, serial in enumerate(self.devices):
                    # Flat device item
                    dev_frame = tk.Frame(
                        self.device_scrollable_frame,
                        bg=self.colors["bg_input"],
                        padx=2,
                        pady=1,
                    )
                    dev_frame.pack(fill="x", pady=(0, 1))

                    # Device info row - compact
                    info_row = tk.Frame(dev_frame, bg=self.colors["bg_input"])
                    info_row.pack(fill="x")

                    # Checkbox for device selection (default checked)
                    selected_var = tk.BooleanVar(value=True)
                    self.selected_devices[serial] = selected_var

                    checkbox = tk.Checkbutton(
                        info_row,
                        variable=selected_var,
                        bg=self.colors["bg_input"],
                        selectcolor=self.colors["bg_input"],
                        activebackground=self.colors["bg_input"],
                    )
                    checkbox.pack(side="left")

                    # Label entry for device name
                    label_text = self.device_labels.get(serial, f"HP-{i + 1}")
                    label_var = tk.StringVar(value=label_text)
                    label_entry = tk.Entry(
                        info_row,
                        textvariable=label_var,
                        font=("Segoe UI", 8),
                        width=10,
                        relief="flat",
                        bg=self.colors["bg_input"],
                        fg=self.colors["fg"],
                        highlightbackground=self.colors["border"],
                        highlightthickness=0,
                    )
                    label_entry.pack(side="left", padx=(0, 2))

                    # Save label on focus out
                    def on_label_change(event, s=serial, v=label_var):
                        self.save_device_label(s, v.get())

                    label_entry.bind("<FocusOut>", on_label_change)
                    label_entry.bind("<Return>", on_label_change)

                    # Serial label (compact, gray)
                    serial_label = tk.Label(
                        info_row,
                        text=serial[:8],
                        font=("Segoe UI", 7),
                        fg=self.colors["fg_secondary"],
                        bg=self.colors["bg_input"],
                    )
                    serial_label.pack(side="left")

                    # Status icon (● = ready, green when done)
                    status_label = tk.Label(
                        info_row,
                        text="●",
                        font=("Segoe UI", 8),
                        fg=self.colors["fg_secondary"],
                        bg=self.colors["bg_input"],
                    )
                    status_label.pack(side="right")

                    # Compact progress bar
                    progress_var = tk.DoubleVar(value=0)
                    progress_bar = ttk.Progressbar(
                        dev_frame,
                        variable=progress_var,
                        maximum=100,
                        length=100,
                        mode="determinate",
                    )
                    progress_bar.pack(fill="x", pady=(0, 0))

                    self.device_progress[serial] = {
                        "var": progress_var,
                        "bar": progress_bar,
                        "label": status_label,
                    }

                self.log(f"Ditemukan {len(self.devices)} perangkat")
            else:
                tk.Label(
                    self.device_scrollable_frame,
                    text="Tidak ada perangkat",
                    fg=self.colors["fg_secondary"],
                    bg=self.colors["bg_input"],
                    font=("Segoe UI", 8),
                ).pack(anchor="w", pady=4)

        except Exception as e:
            messagebox.showerror("Error ADB", "Tidak bisa menjalankan ADB. Cek PATH.")
            self.log(f"Error: {str(e)}")

    def start_auto_refresh(self):
        if self.refresh_timer:
            self.root.after_cancel(self.refresh_timer)
        interval = self.auto_refresh_interval.get() * 1000
        self.refresh_devices()
        self.refresh_timer = self.root.after(interval, self.start_auto_refresh)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(bg=self.colors["accent"])
            self.log("Dijeda")
        else:
            self.pause_btn.config(bg=self.colors["warning"])
            self.log("Dilanjutkan")

    def start_process(self):
        if self.is_running:
            return

        src = self.source_dir.get()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Peringatan", "Pilih folder sumber yang valid.")
            return

        if not self.devices:
            messagebox.showwarning("Peringatan", "Tidak ada perangkat terhubung.")
            return

        # Check if at least one device is selected
        selected_devices = [
            serial for serial, var in self.selected_devices.items() if var.get()
        ]
        if not selected_devices:
            messagebox.showwarning("Peringatan", "Pilih minimal satu perangkat.")
            return

        self.is_running = True
        self.is_paused = False
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")

        threading.Thread(target=self.run_distribution, args=(src,), daemon=True).start()

    def run_distribution(self, src_dir):
        try:
            all_files = self.get_sorted_files(src_dir)
            all_files = self.validate_files(src_dir, all_files)

            if not all_files:
                self.log("Tidak ada file valid untuk didistribusikan")
                self.reset_ui()
                return

            # Get only selected devices
            selected_devices = [
                serial for serial, var in self.selected_devices.items() if var.get()
            ]

            self.log(
                f"Mendistribusikan {len(all_files)} file ke {len(selected_devices)} perangkat..."
            )
            self.total_progress = {"completed": 0, "total": len(all_files)}

            num_devices = len(selected_devices)
            chunk_size = len(all_files) // num_devices
            remainder = len(all_files) % num_devices

            today_folder = datetime.now().strftime("%Y%m%d")
            remote_path = f"//sdcard/XPersonal/{today_folder}"

            threads = []
            current_idx = 0

            for i, serial in enumerate(selected_devices):
                count = chunk_size + (1 if i < remainder else 0)
                device_files = all_files[current_idx : current_idx + count]
                current_idx += count

                if device_files:
                    t = threading.Thread(
                        target=self.push_to_device,
                        args=(serial, src_dir, device_files, remote_path),
                    )
                    threads.append(t)
                    t.start()

            for t in threads:
                t.join()

            self.log("✓ Distribusi selesai!")
            messagebox.showinfo("Sukses", "Distribusi berhasil!")

        except Exception as e:
            self.log(f"✗ Error: {str(e)}")
        finally:
            self.reset_ui()

    def push_to_device(self, serial, src_dir, file_list, remote_path):
        try:
            while self.is_paused:
                import time

                time.sleep(0.5)

            if serial in self.device_progress:
                self.device_progress[serial]["label"].config(
                    text="○", fg=self.colors["warning"]
                )

            subprocess.run(
                ["adb", "-s", serial, "shell", f"mkdir -p {remote_path}"],
                check=True,
                capture_output=True,
            )

            temp_path = f"temp_{serial}"
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
            os.makedirs(temp_path)

            for idx, f in enumerate(file_list):
                while self.is_paused:
                    import time

                    time.sleep(0.5)

                shutil.copy(os.path.join(src_dir, f), os.path.join(temp_path, f))

                progress = ((idx + 1) / len(file_list)) * 100
                if serial in self.device_progress:
                    self.device_progress[serial]["var"].set(progress)
                    self.device_progress[serial]["label"].config(
                        text="○", fg=self.colors["info"]
                    )

                self.total_progress["completed"] += 1
                total_pct = (
                    self.total_progress["completed"] / self.total_progress["total"]
                ) * 100
                self.total_progress_var.set(total_pct)
                self.progress_label.config(
                    text=f"{self.total_progress['completed']}/{self.total_progress['total']} file"
                )
                if hasattr(self, "progress_percent_label"):
                    self.progress_percent_label.config(text=f"{int(total_pct)}%")

            subprocess.run(
                ["adb", "-s", serial, "push", f"{temp_path}/.", remote_path + "/"],
                check=True,
                capture_output=True,
            )

            shutil.rmtree(temp_path)

            if serial in self.device_progress:
                self.device_progress[serial]["label"].config(
                    text="✓", fg=self.colors["success"]
                )

            display_name = self.get_device_display_name(serial)
            self.log(f"✓ {display_name}: {len(file_list)} file")

        except Exception as e:
            display_name = self.get_device_display_name(serial)
            self.log(f"✗ {display_name}: {str(e)}")
            if serial in self.device_progress:
                self.device_progress[serial]["label"].config(
                    text="✗", fg=self.colors["error"]
                )

    def reset_ui(self):
        self.is_running = False
        self.is_paused = False
        self.start_btn.config(state="normal", text="Mulai")
        self.pause_btn.config(state="disabled")
        self.total_progress_var.set(0)
        self.progress_label.config(text="0/0 file")
        if hasattr(self, "progress_percent_label"):
            self.progress_percent_label.config(text="0%")

        for serial, widgets in self.device_progress.items():
            widgets["var"].set(0)
            widgets["label"].config(text="●", fg=self.colors["fg_secondary"])


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = AdbDistributorApp(root)
    root.mainloop()
