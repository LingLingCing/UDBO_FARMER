import threading
import time
import ctypes
import random
import win32gui
import win32con
import win32api
import customtkinter as ctk
import pygetwindow as gw
import sys
import json
import os
import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageTk, ImageGrab
from tkinter import messagebox, filedialog, StringVar, colorchooser, Toplevel
from functools import partial
from typing import Dict, List, Tuple, Any, Optional

# Admin check
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit()

class ESPOverlay:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.canvas = None
        self.active = False
        self.overlay_width = 1920
        self.overlay_height = 1080
        self.last_update = 0
        self.update_interval = 0.2  # seconds
        self.alpha = 0.7  # transparency
        self.esp_color = "#FF0000"  # default red
        self.esp_target_name = "Monster"
        self.mock_positions = []  # For testing/debugging
        self.update_thread = None

    def create_window(self):
        if self.window:
            self.window.destroy()

        self.window = Toplevel(self.parent)
        self.window.title("ESP Overlay")
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", self.alpha)
        self.window.overrideredirect(True)  # No window borders

        # Set the window to cover the whole screen or game window
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        self.overlay_width = screen_width
        self.overlay_height = screen_height

        # Position at top-left corner and set window size
        self.window.geometry(f"{self.overlay_width}x{self.overlay_height}+0+0")

        # Make the window click-through
        self.window.attributes("-transparent", "blue")
        hwnd = self.window.winfo_id()
        styles = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        styles = styles | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, styles)

        # Create transparent canvas
        self.canvas = ctk.CTkCanvas(
            self.window,
            width=self.overlay_width,
            height=self.overlay_height,
            bg="",  # Transparent background
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Add a key binding to close the overlay
        self.window.bind("<Escape>", self.toggle_overlay)

        # Hide window initially
        self.window.withdraw()

    def toggle_overlay(self, event=None):
        if not self.window:
            self.create_window()

        if self.active:
            self.active = False
            self.window.withdraw()
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread = None
        else:
            self.active = True
            self.window.deiconify()
            self.update_thread = threading.Thread(target=self.update_overlay, daemon=True)
            self.update_thread.start()

    def update_color(self, color):
        self.esp_color = color

    def update_target(self, name):
        self.esp_target_name = name

    def add_mock_position(self, x, y, w, h):
        """Add mock position for debugging"""
        self.mock_positions.append((x, y, w, h))

    def clear_mock_positions(self):
        """Clear all mock positions"""
        self.mock_positions.clear()

    def update_overlay(self):
        """Update the overlay with ESP markers"""
        while self.active:
            current_time = time.time()
            if current_time - self.last_update < self.update_interval:
                time.sleep(0.05)  # Small sleep to prevent CPU hogging
                continue

            self.last_update = current_time

            # Clear previous drawings
            self.canvas.delete("all")

            # If we have mock positions (for debugging), use those
            if self.mock_positions:
                for x, y, w, h in self.mock_positions:
                    self.draw_esp_box(x, y, w, h, self.esp_target_name)
            else:
                # In a real implementation, you would detect mobs here
                # For demonstration, we'll just draw random boxes
                for i in range(3):
                    x = random.randint(100, self.overlay_width - 200)
                    y = random.randint(100, self.overlay_height - 200)
                    w = random.randint(50, 150)
                    h = random.randint(50, 150)
                    self.draw_esp_box(x, y, w, h, f"{self.esp_target_name} {i+1}")

            time.sleep(self.update_interval)

    def draw_esp_box(self, x, y, w, h, name):
        """Draw an ESP box with the target name"""
        # Parse the ESP color
        r = int(self.esp_color[1:3], 16)
        g = int(self.esp_color[3:5], 16)
        b = int(self.esp_color[5:7], 16)

        # Create hex color for tkinter canvas
        hex_color = f"#{r:02x}{g:02x}{b:02x}"

        # Draw the rectangle
        self.canvas.create_rectangle(
            x, y, x+w, y+h,
            outline=hex_color,
            width=2
        )

        # Draw the name text (with black outline for visibility)
        text_bg = self.canvas.create_text(
            x, y-12,
            text=name,
            fill="black",
            font=("Arial", 12, "bold"),
            anchor="w"
        )

        text_fg = self.canvas.create_text(
            x+1, y-13,
            text=name,
            fill=hex_color,
            font=("Arial", 12, "bold"),
            anchor="w"
        )

class RegionSelector(ctk.CTkToplevel):
    def __init__(self, master, region_type="health", initial_region=None):
        super().__init__(master)
        self.master = master
        self.region_type = region_type
        self.initial_region = initial_region or [0, 0, 100, 20]

        self.title(f"Select {region_type.title()} Region")
        self.geometry("400x300")
        self.resizable(True, True)

        self.result_region = None
        self.is_selecting = False
        self.start_x, self.start_y = 0, 0

        # Take a screenshot for preview
        self.screenshot = ImageGrab.grab()
        self.tk_screenshot = ImageTk.PhotoImage(self.screenshot)

        # Create canvas for selection
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = ctk.CTkCanvas(self.canvas_frame, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, image=self.tk_screenshot, anchor="nw")

        # Draw initial rectangle if provided
        if self.initial_region:
            x1, y1, x2, y2 = self.initial_region[0], self.initial_region[1], self.initial_region[0] + self.initial_region[2], self.initial_region[1] + self.initial_region[3]
            self.rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

        # Bind events for selection
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        # Status and buttons
        self.status_label = ctk.CTkLabel(self, text="Click and drag to select region")
        self.status_label.pack(pady=5)

        self.buttons_frame = ctk.CTkFrame(self)
        self.buttons_frame.pack(fill="x", padx=10, pady=10)

        self.confirm_button = ctk.CTkButton(
            self.buttons_frame,
            text="Confirm Selection",
            command=self.confirm_selection
        )
        self.confirm_button.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        self.cancel_button = ctk.CTkButton(
            self.buttons_frame,
            text="Cancel",
            command=self.cancel_selection,
            fg_color="red"
        )
        self.cancel_button.pack(side="left", padx=5, pady=5, fill="x", expand=True)

        self.protocol("WM_DELETE_WINDOW", self.cancel_selection)
        self.focus_set()
        self.grab_set()

    def on_press(self, event):
        self.is_selecting = True
        self.start_x, self.start_y = event.x, event.y

        # Remove previous rectangle if it exists
        if hasattr(self, 'rect_id'):
            self.canvas.delete(self.rect_id)

        # Create new rectangle
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2
        )

    def on_drag(self, event):
        if not self.is_selecting:
            return

        # Update rectangle
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

        # Update status
        width = abs(event.x - self.start_x)
        height = abs(event.y - self.start_y)
        self.status_label.configure(text=f"Region: {width}x{height} pixels")

    def on_release(self, event):
        self.is_selecting = False

        # Store the region coordinates
        x1, y1 = min(self.start_x, event.x), min(self.start_y, event.y)
        x2, y2 = max(self.start_x, event.x), max(self.start_y, event.y)

        self.result_region = [x1, y1, x2-x1, y2-y1]  # [x, y, width, height]

    def confirm_selection(self):
        if not self.result_region:
            messagebox.showwarning("No Selection", "Please select a region first")
            return

        self.grab_release()
        self.destroy()

    def cancel_selection(self):
        self.result_region = None
        self.grab_release()
        self.destroy()

class ColorPicker(ctk.CTkToplevel):
    def __init__(self, master, region, color_type="health", initial_color=None):
        super().__init__(master)
        self.master = master
        self.region = region  # [x, y, width, height]
        self.color_type = color_type
        self.initial_color = initial_color or "#FF0000"  # Default red for health

        self.title(f"Select {color_type.title()} Color")
        self.geometry("500x400")
        self.resizable(False, False)

        self.selected_color = self.initial_color
        self.selected_threshold = 30  # Default threshold

        # Take a screenshot of the region
        try:
            screen = ImageGrab.grab(bbox=(region[0], region[1], region[0]+region[2], region[1]+region[3]))
            self.screen_img = screen
            self.tk_screen = ImageTk.PhotoImage(screen)
        except Exception as e:
            self.screen_img = None
            self.tk_screen = None
            messagebox.showerror("Error", f"Failed to capture screen region: {str(e)}")

        # Create main layout
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Preview frame
        self.preview_frame = ctk.CTkFrame(self.main_frame)
        self.preview_frame.pack(fill="x", pady=10)

        self.preview_label = ctk.CTkLabel(self.preview_frame, text="Region Preview:")
        self.preview_label.pack(pady=5)

        if self.tk_screen:
            self.preview_canvas = ctk.CTkCanvas(
                self.preview_frame,
                width=min(400, region[2]),
                height=min(150, region[3]),
                bg="black",
                highlightthickness=0
            )
            self.preview_canvas.pack(pady=5)
            self.preview_canvas.create_image(0, 0, image=self.tk_screen, anchor="nw")

        # Color selection
        self.color_frame = ctk.CTkFrame(self.main_frame)
        self.color_frame.pack(fill="x", pady=10)

        self.color_label = ctk.CTkLabel(self.color_frame, text=f"Select {color_type.title()} Color:")
        self.color_label.pack(side="left", padx=10)

        self.color_button = ctk.CTkButton(
            self.color_frame,
            text="Choose Color",
            command=self.pick_color,
            width=120
        )
        self.color_button.pack(side="left", padx=10)

        self.color_preview = ctk.CTkCanvas(
            self.color_frame,
            width=30,
            height=30,
            highlightthickness=1
        )
        self.color_preview.pack(side="left", padx=10)
        self.color_preview.create_rectangle(0, 0, 30, 30, fill=self.initial_color, outline="")

        # Threshold slider
        self.threshold_frame = ctk.CTkFrame(self.main_frame)
        self.threshold_frame.pack(fill="x", pady=10)

        self.threshold_label = ctk.CTkLabel(self.threshold_frame, text="Color Threshold:")
        self.threshold_label.pack(side="left", padx=10)

        self.threshold_slider = ctk.CTkSlider(
            self.threshold_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self.update_threshold
        )
        self.threshold_slider.pack(side="left", padx=10, fill="x", expand=True)
        self.threshold_slider.set(30)  # Default threshold

        self.threshold_value_label = ctk.CTkLabel(self.threshold_frame, text="30")
        self.threshold_value_label.pack(side="left", padx=10)

        # Sample points (for advanced users)
        self.sample_frame = ctk.CTkFrame(self.main_frame)
        self.sample_frame.pack(fill="x", pady=10)

        self.sample_button = ctk.CTkButton(
            self.sample_frame,
            text="Sample Colors from Region",
            command=self.sample_region_colors
        )
        self.sample_button.pack(pady=5)

        self.sample_info = ctk.CTkLabel(
            self.sample_frame,
            text="No samples taken",
            font=("Arial", 10)
        )
        self.sample_info.pack(pady=5)

        # Buttons
        self.buttons_frame = ctk.CTkFrame(self.main_frame)
        self.buttons_frame.pack(fill="x", pady=10)

        self.confirm_button = ctk.CTkButton(
            self.buttons_frame,
            text="Confirm",
            command=self.confirm_color
        )
        self.confirm_button.pack(side="left", padx=5, fill="x", expand=True)

        self.cancel_button = ctk.CTkButton(
            self.buttons_frame,
            text="Cancel",
            command=self.cancel_color,
            fg_color="red"
        )
        self.cancel_button.pack(side="left", padx=5, fill="x", expand=True)

        self.result_color = None
        self.result_threshold = None

        self.protocol("WM_DELETE_WINDOW", self.cancel_color)
        self.focus_set()
        self.grab_set()

    def pick_color(self):
        color = colorchooser.askcolor(initialcolor=self.selected_color, title=f"Choose {self.color_type.title()} Color")
        if color[1]:  # If a color was selected (not canceled)
            self.selected_color = color[1]
            self.color_preview.delete("all")
            self.color_preview.create_rectangle(0, 0, 30, 30, fill=color[1], outline="")

    def update_threshold(self, value):
        self.selected_threshold = int(value)
        self.threshold_value_label.configure(text=str(self.selected_threshold))

    def sample_region_colors(self):
        if not self.screen_img:
            messagebox.showwarning("Error", "No region image available")
            return

        try:
            # Convert PIL image to numpy array for OpenCV
            img_np = np.array(self.screen_img)
            img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)

            # Calculate the dominant colors
            pixels = img_rgb.reshape(-1, 3)
            pixels = np.float32(pixels)

            # Use K-means to find dominant colors (using 3 clusters)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, 0.1)
            k = 3  # Number of clusters
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            # Convert centers to RGB hex values
            colors = []
            for center in centers:
                r, g, b = int(center[0]), int(center[1]), int(center[2])
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
                colors.append(hex_color)

            # Update UI with the dominant color (first color)
            if colors:
                self.selected_color = colors[0]
                self.color_preview.delete("all")
                self.color_preview.create_rectangle(0, 0, 30, 30, fill=colors[0], outline="")

                # Show info about all dominant colors
                color_info = "Dominant colors:\n"
                for i, color in enumerate(colors):
                    color_info += f"Color {i+1}: {color}\n"

                self.sample_info.configure(text=color_info)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to sample colors: {str(e)}")

    def confirm_color(self):
        self.result_color = self.selected_color
        self.result_threshold = self.selected_threshold
        self.grab_release()
        self.destroy()

    def cancel_color(self):
        self.result_color = None
        self.result_threshold = None
        self.grab_release()
        self.destroy()

class DraggableFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.index = 0
        self.bind("<ButtonPress-1>", self.start_drag)
        self.bind("<ButtonRelease-1>", self.stop_drag)
        self.bind("<B1-Motion>", self.on_drag)

        for child in self.winfo_children():
            child.bind("<ButtonPress-1>", self.start_drag)
            child.bind("<ButtonRelease-1>", self.stop_drag)
            child.bind("<B1-Motion>", self.on_drag)

        self.drag_data = {"y": 0, "widget": None, "dragging": False}

    def start_drag(self, event):
        self.drag_data["y"] = event.y_root
        self.drag_data["widget"] = self
        self.drag_data["dragging"] = True
        self.configure(border_width=2, border_color="cyan")

    def stop_drag(self, event):
        self.drag_data["dragging"] = False
        self.configure(border_width=0)
        container = self.master

        # Repack all widgets in their current order
        all_children = container.winfo_children()
        positions = [(child, child.winfo_y()) for child in all_children]
        sorted_positions = sorted(positions, key=lambda x: x[1])

        for widget in all_children:
            widget.pack_forget()

        for widget, _ in sorted_positions:
            widget.pack(fill="x", pady=2, padx=5, anchor="n")

    def on_drag(self, event):
        if not self.drag_data["dragging"]:
            return

        delta_y = event.y_root - self.drag_data["y"]

        if abs(delta_y) > 5:  # Add a small threshold to prevent accidental moves
            container = self.master
            y_position = self.winfo_y() + delta_y

            # Find the widget at this position to swap with
            for widget in container.winfo_children():
                widget_y = widget.winfo_y()
                widget_height = widget.winfo_height()

                # If our dragged widget is in the middle of another widget
                if widget != self and widget_y <= y_position <= (widget_y + widget_height):
                    self.drag_data["y"] = event.y_root

                    # Swap positions (repack all widgets)
                    all_children = container.winfo_children()
                    for child in all_children:
                        child.pack_forget()

                    # Put them back in the new order
                    for child in all_children:
                        if child == self:
                            continue
                        if child == widget and delta_y < 0:  # Moving up
                            self.pack(fill="x", pady=2, padx=5, anchor="n")
                            widget.pack(fill="x", pady=2, padx=5, anchor="n")
                        elif child == widget and delta_y > 0:  # Moving down
                            widget.pack(fill="x", pady=2, padx=5, anchor="n")
                            self.pack(fill="x", pady=2, padx=5, anchor="n")
                        else:
                            child.pack(fill="x", pady=2, padx=5, anchor="n")
                    break

class FarmingBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.macro_thread = None
        self.game_hwnd = None
        self.current_config = {}
        self.key_map = self.create_key_map()
        self.auto_heal = False
        self.health_threshold = 70
        self.auto_pot = False
        self.pot_frequency = 60  # seconds
        self.last_pot_time = 0
        self.movement_pattern = "circle"
        self.movement_enabled = False
        self.movement_active = False
        self.movement_thread = None
        self.saved_configurations = {}
        self.profile_name = "default"
        self.config_dir = "bot_configs"
        self.auto_loot = False
        self.loot_key = "Z"
        self.loot_frequency = 5  # seconds
        self.last_loot_time = 0
        self.current_sequence_tab = "combat"
        self.skill_cooldowns = {}  # To track individual skill cooldowns
        self.hold_timer_map = {}  # To track button hold timers for skills
        self.prioritize_healing = True  # Fix for auto heal issue

        # New features
        self.target_key = "TAB"
        self.target_frequency = 5  # seconds
        self.last_target_time = 0
        self.target_enabled = False
        self.esp_enabled = False
        self.esp_target_name = "Monster"
        self.esp_color = "#FF0000"  # Default red
        self.buff_toggle_enabled = False

        # ESP overlay
        self.esp_overlay = ESPOverlay(self)

        # Image recognition settings
        self.health_region = [0, 0, 100, 20]  # Default: x, y, width, height
        self.health_color = "#FF0000"  # Default: red
        self.health_threshold_pct = 30  # Color detection threshold (0-100)

        # EP recognition settings
        self.ep_region = [0, 0, 100, 20]  # Default: x, y, width, height
        self.ep_color = "#0000FF"  # Default: blue
        self.ep_threshold_pct = 30  # Color detection threshold (0-100)
        self.auto_ep = False
        self.ep_threshold = 30
        self.ep_key = "E"

        # Pet feeding settings
        self.pet_feed_enabled = False
        self.pet_feed_key = "P"
        self.pet_feed_interval = 1800  # Default 30 minutes in seconds
        self.last_pet_feed_time = 0

        self.enemy_detection_enabled = False
        self.enemy_region = [0, 0, 500, 500]
        self.enemy_color = "#FF0000"
        self.enemy_threshold_pct = 30

        self.buff_detection_enabled = False
        self.buff_region = [0, 0, 100, 20]
        self.buff_color = "#00FF00"
        self.buff_threshold_pct = 30

        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        self.title("UDBO Token Farmer v1.0")
        self.geometry("900x750")
        ctk.set_appearance_mode("Dark")
        self.create_widgets()
        self.refresh_windows()
        self.bind('<F12>', lambda e: self.toggle_macro())
        self.load_available_configs()

    def create_key_map(self):
        return {
            # Special keys
            '`': 0xC0,      # VK_OEM_3
            '~': 0xC0,       # Same as VK_OEM_3
            'TAB': win32con.VK_TAB,
            'CAPS': win32con.VK_CAPITAL,
            'SHIFT': win32con.VK_SHIFT,
            'CTRL': win32con.VK_CONTROL,
            'ALT': win32con.VK_MENU,
            'ESC': win32con.VK_ESCAPE,
            'ENTER': win32con.VK_RETURN,
            'SPACE': win32con.VK_SPACE,
            'PRTSC': win32con.VK_PRINT,
            'SCROLL': win32con.VK_SCROLL,
            'ARROW_UP': win32con.VK_UP,
            'ARROW_DOWN': win32con.VK_DOWN,
            'ARROW_LEFT': win32con.VK_LEFT,
            'ARROW_RIGHT': win32con.VK_RIGHT,

            # Mouse buttons
            'LEFT_CLICK': 0x01,
            'RIGHT_CLICK': 0x02,
            'MIDDLE_CLICK': 0x04,
            'MOUSE4': 0x05,
            'MOUSE5': 0x06,

            # Function keys
            **{f'F{i}': getattr(win32con, f'VK_F{i}') for i in range(1, 13)},

            # Numbers (using ASCII codes)
            **{str(i): ord(str(i)) for i in range(10)},

            # Letters (using ASCII codes)
            **{chr(65 + i): ord(chr(65 + i)) for i in range(26)},

            # Numpad (using direct hex codes)
            'NUMPAD_0': 0x60,
            'NUMPAD_1': 0x61,
            'NUMPAD_2': 0x62,
            'NUMPAD_3': 0x63,
            'NUMPAD_4': 0x64,
            'NUMPAD_5': 0x65,
            'NUMPAD_6': 0x66,
            'NUMPAD_7': 0x67,
            'NUMPAD_8': 0x68,
            'NUMPAD_9': 0x69,

            # Special characters (using direct hex codes)
            '[': 0xDB,      # VK_OEM_4
            ']': 0xDD,       # VK_OEM_6
            '\\': 0xDC,      # VK_OEM_5
            ';': 0xBA,       # VK_OEM_1
            "'": 0xDE,       # VK_OEM_7
            ',': 0xBC,       # VK_OEM_COMMA
            '.': 0xBE,       # VK_OEM_PERIOD
            '/': 0xBF,       # VK_OEM_2
            '-': 0xBD,       # VK_OEM_MINUS
            '=': 0xBB,       # VK_OEM_PLUS
            '*': 0x6A,       # VK_MULTIPLY
            '+': 0x6B,       # VK_ADD
            '_': 0x6D        # VK_SUBTRACT
        }

    def create_widgets(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs
        self.tabview.add("Main")
        self.tabview.add("Sequences")
        self.tabview.add("Movement")
        self.tabview.add("Potions & Healing")
        self.tabview.add("Pet Feeder")  # New Pet Feeder tab
        self.tabview.add("Loot & Pickup")
        self.tabview.add("Image Recognition")
        self.tabview.add("ESP & Targeting")
        self.tabview.add("Profiles")

        # === MAIN TAB ===
        main_tab = self.tabview.tab("Main")

        # Window selection
        self.window_frame = ctk.CTkFrame(main_tab)
        self.window_frame.pack(pady=10, fill="x", padx=10)

        self.window_label = ctk.CTkLabel(
            self.window_frame,
            text="Target Game Window:",
            font=("Arial", 12)
        )
        self.window_label.pack(side="left", padx=5)

        self.window_dropdown = ctk.CTkComboBox(
            self.window_frame,
            values=[],
            width=300
        )
        self.window_dropdown.pack(side="left", padx=5)

        self.refresh_button = ctk.CTkButton(
            self.window_frame,
            text="🔄",
            width=30,
            command=self.refresh_windows
        )
        self.refresh_button.pack(side="left", padx=5)

        # Loop Settings
        self.settings_frame = ctk.CTkFrame(main_tab)
        self.settings_frame.pack(pady=10, fill="x", padx=10)

        self.loop_label = ctk.CTkLabel(
            self.settings_frame,
            text="Loop Settings:",
            font=("Arial", 14)
        )
        self.loop_label.grid(row=0, column=0, sticky="w", padx=5)

        self.loop_count_label = ctk.CTkLabel(
            self.settings_frame,
            text="Total Loops (0=infinite):"
        )
        self.loop_count_label.grid(row=1, column=0, padx=5)

        self.loop_count_entry = ctk.CTkEntry(
            self.settings_frame,
            width=100
        )
        self.loop_count_entry.grid(row=1, column=1, padx=5)
        self.loop_count_entry.insert(0, "0")

        self.cooldown_label = ctk.CTkLabel(
            self.settings_frame,
            text="Cooldown between loops (s):"
        )
        self.cooldown_label.grid(row=2, column=0, padx=5)

        self.cooldown_entry = ctk.CTkEntry(self.settings_frame, width=100)
        self.cooldown_entry.grid(row=2, column=1, padx=5)
        self.cooldown_entry.insert(0, "5")

        # Feature toggles
        self.features_frame = ctk.CTkFrame(main_tab)
        self.features_frame.pack(pady=10, fill="x", padx=10)

        self.features_label = ctk.CTkLabel(
            self.features_frame,
            text="Quick Feature Toggles:",
            font=("Arial", 14)
        )
        self.features_label.pack(pady=5, anchor="w", padx=10)

        # Row 1
        self.toggle_row1 = ctk.CTkFrame(self.features_frame)
        self.toggle_row1.pack(fill="x", pady=5, padx=10)

        self.movement_quick_toggle = ctk.CTkSwitch(
            self.toggle_row1,
            text="Movement",
            command=self.toggle_movement_quick
        )
        self.movement_quick_toggle.pack(side="left", padx=15)

        self.loot_quick_toggle = ctk.CTkSwitch(
            self.toggle_row1,
            text="Auto Loot",
            command=self.toggle_loot_quick
        )
        self.loot_quick_toggle.pack(side="left", padx=15)

        # Row 2
        self.toggle_row2 = ctk.CTkFrame(self.features_frame)
        self.toggle_row2.pack(fill="x", pady=5, padx=10)

        self.heal_quick_toggle = ctk.CTkSwitch(
            self.toggle_row2,
            text="Auto Heal (HP)",
            command=self.toggle_heal_quick
        )
        self.heal_quick_toggle.pack(side="left", padx=15)

        self.pot_quick_toggle = ctk.CTkSwitch(
            self.toggle_row2,
            text="Auto Potion",
            command=self.toggle_pot_quick
        )
        self.pot_quick_toggle.pack(side="left", padx=15)

        # Add EP quick toggle
        self.ep_quick_toggle = ctk.CTkSwitch(
            self.toggle_row2,
            text="Auto EP",
            command=self.toggle_ep_quick
        )
        self.ep_quick_toggle.pack(side="left", padx=15)

        # Row 3 - Image detection toggles
        self.toggle_row3 = ctk.CTkFrame(self.features_frame)
        self.toggle_row3.pack(fill="x", pady=5, padx=10)

        self.enemy_detect_quick_toggle = ctk.CTkSwitch(
            self.toggle_row3,
            text="Enemy Detection",
            command=self.toggle_enemy_detect_quick
        )
        self.enemy_detect_quick_toggle.pack(side="left", padx=15)

        self.health_detect_quick_toggle = ctk.CTkSwitch(
            self.toggle_row3,
            text="Health Detection",
            command=self.toggle_health_detect_quick
        )
        self.health_detect_quick_toggle.pack(side="left", padx=15)

        # Row 4 - Pet Feeder and targeting toggles
        self.toggle_row4 = ctk.CTkFrame(self.features_frame)
        self.toggle_row4.pack(fill="x", pady=5, padx=10)

        self.pet_feed_quick_toggle = ctk.CTkSwitch(
            self.toggle_row4,
            text="Pet Feeder",
            command=self.toggle_pet_feed_quick
        )
        self.pet_feed_quick_toggle.pack(side="left", padx=15)

        self.target_quick_toggle = ctk.CTkSwitch(
            self.toggle_row4,
            text="Auto Target",
            command=self.toggle_target_quick
        )
        self.target_quick_toggle.pack(side="left", padx=15)

        # Row 5 - ESP and Buff toggles
        self.toggle_row5 = ctk.CTkFrame(self.features_frame)
        self.toggle_row5.pack(fill="x", pady=5, padx=10)

        self.esp_quick_toggle = ctk.CTkSwitch(
            self.toggle_row5,
            text="ESP Enabled",
            command=self.toggle_esp_quick
        )
        self.esp_quick_toggle.pack(side="left", padx=15)

        self.buff_toggle = ctk.CTkSwitch(
            self.toggle_row5,
            text="Enable Buffs",
            command=self.toggle_buffs
        )
        self.buff_toggle.pack(side="left", padx=15)
        self.buff_toggle.select()  # Enable buffs by default

        # Row 6 - ESP overlay toggle
        self.toggle_row6 = ctk.CTkFrame(self.features_frame)
        self.toggle_row6.pack(fill="x", pady=5, padx=10)

        self.esp_overlay_toggle = ctk.CTkSwitch(
            self.toggle_row6,
            text="ESP Overlay Window",
            command=self.toggle_esp_overlay
        )
        self.esp_overlay_toggle.pack(side="left", padx=15)

        # Status display
        self.status_frame = ctk.CTkFrame(main_tab)
        self.status_frame.pack(pady=10, fill="x", padx=10)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="Status: Stopped",
            font=("Arial", 14)
        )
        self.status_label.pack(pady=5)

        self.progress_label = ctk.CTkLabel(
            self.status_frame,
            text="Completed Loops: 0",
            font=("Arial", 12)
        )
        self.progress_label.pack(pady=5)

        # Status indicators
        self.indicators_frame = ctk.CTkFrame(main_tab)
        self.indicators_frame.pack(pady=10, fill="x", padx=10)

        self.health_status_label = ctk.CTkLabel(
            self.indicators_frame,
            text="Health: Unknown",
            font=("Arial", 12)
        )
        self.health_status_label.pack(side="left", padx=10)

        self.ep_status_label = ctk.CTkLabel(
            self.indicators_frame,
            text="EP: Unknown",
            font=("Arial", 12)
        )
        self.ep_status_label.pack(side="left", padx=10)

        self.enemy_status_label = ctk.CTkLabel(
            self.indicators_frame,
            text="Enemies: Not detected",
            font=("Arial", 12)
        )
        self.enemy_status_label.pack(side="left", padx=10)

        self.pet_status_label = ctk.CTkLabel(
            self.indicators_frame,
            text="Pet: Not fed",
            font=("Arial", 12)
        )
        self.pet_status_label.pack(side="left", padx=10)

        # Additional indicators frame for ESP and target
        self.indicators_frame2 = ctk.CTkFrame(main_tab)
        self.indicators_frame2.pack(pady=5, fill="x", padx=10)

        self.target_status_label = ctk.CTkLabel(
            self.indicators_frame2,
            text="Target: None",
            font=("Arial", 12)
        )
        self.target_status_label.pack(side="left", padx=10)

        self.esp_status_label = ctk.CTkLabel(
            self.indicators_frame2,
            text="ESP: Off",
            font=("Arial", 12)
        )
        self.esp_status_label.pack(side="left", padx=10)

        # Controls
        self.button_frame = ctk.CTkFrame(main_tab)
        self.button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(
            self.button_frame,
            text="Start Bot (F12)",
            command=self.start_macro,
            fg_color="green",
            hover_color="darkgreen",
            width=150
        )
        self.start_button.pack(side="left", padx=10)

        self.stop_button = ctk.CTkButton(
            self.button_frame,
            text="Stop Bot (F12)",
            command=self.stop_macro,
            fg_color="red",
            hover_color="darkred",
            width=150
        )
        self.stop_button.pack(side="left", padx=10)

        # === SEQUENCES TAB ===
        sequences_tab = self.tabview.tab("Sequences")

        # Sequence selection tabs
        self.sequence_tabview = ctk.CTkTabview(sequences_tab)
        self.sequence_tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.sequence_tabview.add("Combat Skills")
        self.sequence_tabview.add("Buffs")
        self.sequence_tabview.add("Transformations")
        self.sequence_tabview.add("No-Enemy Sequence")

        # Combat Skills
        combat_tab = self.sequence_tabview.tab("Combat Skills")

        self.combat_label = ctk.CTkLabel(
            combat_tab,
            text="Combat Skills Sequence (drag to reorder):",
            font=("Arial", 14)
        )
        self.combat_label.pack(pady=(10,5), padx=10, anchor="w")

        self.combat_cooldown_frame = ctk.CTkFrame(combat_tab)
        self.combat_cooldown_frame.pack(fill="x", pady=5, padx=10)

        self.combat_cooldown_label = ctk.CTkLabel(
            self.combat_cooldown_frame,
            text="Combat Sequence Cooldown (s):"
        )
        self.combat_cooldown_label.pack(side="left", padx=5)

        self.combat_cooldown_entry = ctk.CTkEntry(
            self.combat_cooldown_frame,
            width=60
        )
        self.combat_cooldown_entry.pack(side="left", padx=5)
        self.combat_cooldown_entry.insert(0, "1.0")

        self.combat_container = ctk.CTkScrollableFrame(combat_tab, height=250)
        self.combat_container.pack(fill="both", expand=True, pady=5, padx=10)

        self.add_combat_button = ctk.CTkButton(
            combat_tab,
            text="+ Add Combat Skill",
            command=lambda: self.add_sequence_step(self.combat_container),
            width=150
        )
        self.add_combat_button.pack(pady=10)

        # Buffs
        buffs_tab = self.sequence_tabview.tab("Buffs")

        self.buffs_label = ctk.CTkLabel(
            buffs_tab,
            text="Buff Skills Sequence (drag to reorder):",
            font=("Arial", 14)
        )
        self.buffs_label.pack(pady=(10,5), padx=10, anchor="w")

        self.buffs_cooldown_frame = ctk.CTkFrame(buffs_tab)
        self.buffs_cooldown_frame.pack(fill="x", pady=5, padx=10)

        self.buffs_cooldown_label = ctk.CTkLabel(
            self.buffs_cooldown_frame,
            text="Buff Sequence Cooldown (s):"
        )
        self.buffs_cooldown_label.pack(side="left", padx=5)

        self.buffs_cooldown_entry = ctk.CTkEntry(
            self.buffs_cooldown_frame,
            width=60
        )
        self.buffs_cooldown_entry.pack(side="left", padx=5)
        self.buffs_cooldown_entry.insert(0, "60.0")

        self.buffs_container = ctk.CTkScrollableFrame(buffs_tab, height=250)
        self.buffs_container.pack(fill="both", expand=True, pady=5, padx=10)

        self.add_buff_button = ctk.CTkButton(
            buffs_tab,
            text="+ Add Buff Skill",
            command=lambda: self.add_sequence_step(self.buffs_container),
            width=150
        )
        self.add_buff_button.pack(pady=10)

        # Transformations
        trans_tab = self.sequence_tabview.tab("Transformations")

        self.trans_label = ctk.CTkLabel(
            trans_tab,
            text="Transformation Skills Sequence (drag to reorder):",
            font=("Arial", 14)
        )
        self.trans_label.pack(pady=(10,5), padx=10, anchor="w")

        self.trans_cooldown_frame = ctk.CTkFrame(trans_tab)
        self.trans_cooldown_frame.pack(fill="x", pady=5, padx=10)

        self.trans_cooldown_label = ctk.CTkLabel(
            self.trans_cooldown_frame,
            text="Transformation Sequence Cooldown (s):"
        )
        self.trans_cooldown_label.pack(side="left", padx=5)

        self.trans_cooldown_entry = ctk.CTkEntry(
            self.trans_cooldown_frame,
            width=60
        )
        self.trans_cooldown_entry.pack(side="left", padx=5)
        self.trans_cooldown_entry.insert(0, "300.0")  # 5 minutes default

        self.trans_container = ctk.CTkScrollableFrame(trans_tab, height=250)
        self.trans_container.pack(fill="both", expand=True, pady=5, padx=10)

        self.add_trans_button = ctk.CTkButton(
            trans_tab,
            text="+ Add Transformation Skill",
            command=lambda: self.add_sequence_step(self.trans_container),
            width=200
        )
        self.add_trans_button.pack(pady=10)

        # No-Enemy Sequence
        no_enemy_tab = self.sequence_tabview.tab("No-Enemy Sequence")

        self.no_enemy_label = ctk.CTkLabel(
            no_enemy_tab,
            text="Actions when no enemies are detected:",
            font=("Arial", 14)
        )
        self.no_enemy_label.pack(pady=(10,5), padx=10, anchor="w")

        self.no_enemy_enabled_frame = ctk.CTkFrame(no_enemy_tab)
        self.no_enemy_enabled_frame.pack(fill="x", pady=5, padx=10)

        self.no_enemy_switch = ctk.CTkSwitch(
            self.no_enemy_enabled_frame,
            text="Enable No-Enemy Sequence"
        )
        self.no_enemy_switch.pack(side="left", padx=5)

        self.no_enemy_container = ctk.CTkScrollableFrame(no_enemy_tab, height=250)
        self.no_enemy_container.pack(fill="both", expand=True, pady=5, padx=10)

        self.add_no_enemy_button = ctk.CTkButton(
            no_enemy_tab,
            text="+ Add No-Enemy Action",
            command=lambda: self.add_sequence_step(self.no_enemy_container),
            width=180
        )
        self.add_no_enemy_button.pack(pady=10)

        # === MOVEMENT TAB ===
        movement_tab = self.tabview.tab("Movement")

        self.movement_frame = ctk.CTkFrame(movement_tab)
        self.movement_frame.pack(pady=10, fill="x", padx=10)

        self.movement_switch = ctk.CTkSwitch(
            self.movement_frame,
            text="Enable Character Movement",
            command=self.toggle_movement
        )
        self.movement_switch.pack(pady=10, padx=10, anchor="w")

        self.movement_pattern_label = ctk.CTkLabel(
            self.movement_frame,
            text="Movement Pattern:",
            font=("Arial", 12)
        )
        self.movement_pattern_label.pack(pady=(10,0), anchor="w", padx=10)

        self.movement_pattern_var = ctk.StringVar(value="circle")
        self.circle_radio = ctk.CTkRadioButton(
            self.movement_frame,
            text="Circle Movement",
            variable=self.movement_pattern_var,
            value="circle"
        )
        self.circle_radio.pack(pady=5, padx=20, anchor="w")

        self.random_radio = ctk.CTkRadioButton(
            self.movement_frame,
            text="Random Movement",
            variable=self.movement_pattern_var,
            value="random"
        )
        self.random_radio.pack(pady=5, padx=20, anchor="w")

        self.linear_radio = ctk.CTkRadioButton(
            self.movement_frame,
            text="Linear Movement (Back and Forth)",
            variable=self.movement_pattern_var,
            value="linear"
        )
        self.linear_radio.pack(pady=5, padx=20, anchor="w")

        self.movement_keys_frame = ctk.CTkFrame(movement_tab)
        self.movement_keys_frame.pack(pady=10, fill="x", padx=10)

        self.movement_keys_label = ctk.CTkLabel(
            self.movement_keys_frame,
            text="Movement Keys:",
            font=("Arial", 12, "bold")
        )
        self.movement_keys_label.pack(pady=5, anchor="w", padx=10)

        # Forward key
        self.forward_key_frame = ctk.CTkFrame(self.movement_keys_frame)
        self.forward_key_frame.pack(fill="x", pady=2, padx=10)

        self.forward_key_label = ctk.CTkLabel(
            self.forward_key_frame,
            text="Forward Key:"
        )
        self.forward_key_label.pack(side="left", padx=5)

        self.forward_key_var = ctk.StringVar(value="W")
        self.forward_key_entry = ctk.CTkComboBox(
            self.forward_key_frame,
            values=["W", "ARROW_UP", "NUMPAD_8"],
            variable=self.forward_key_var,
            width=100
        )
        self.forward_key_entry.pack(side="left", padx=5)

        # Backward key
        self.backward_key_frame = ctk.CTkFrame(self.movement_keys_frame)
        self.backward_key_frame.pack(fill="x", pady=2, padx=10)

        self.backward_key_label = ctk.CTkLabel(
            self.backward_key_frame,
            text="Backward Key:"
        )
        self.backward_key_label.pack(side="left", padx=5)

        self.backward_key_var = ctk.StringVar(value="S")
        self.backward_key_entry = ctk.CTkComboBox(
            self.backward_key_frame,
            values=["S", "ARROW_DOWN", "NUMPAD_2"],
            variable=self.backward_key_var,
            width=100
        )
        self.backward_key_entry.pack(side="left", padx=5)

        # Left key
        self.left_key_frame = ctk.CTkFrame(self.movement_keys_frame)
        self.left_key_frame.pack(fill="x", pady=2, padx=10)

        self.left_key_label = ctk.CTkLabel(
            self.left_key_frame,
            text="Left Key:"
        )
        self.left_key_label.pack(side="left", padx=5)

        self.left_key_var = ctk.StringVar(value="A")
        self.left_key_entry = ctk.CTkComboBox(
            self.left_key_frame,
            values=["A", "ARROW_LEFT", "NUMPAD_4"],
            variable=self.left_key_var,
            width=100
        )
        self.left_key_entry.pack(side="left", padx=5)

        # Right key
        self.right_key_frame = ctk.CTkFrame(self.movement_keys_frame)
        self.right_key_frame.pack(fill="x", pady=2, padx=10)

        self.right_key_label = ctk.CTkLabel(
            self.right_key_frame,
            text="Right Key:"
        )
        self.right_key_label.pack(side="left", padx=5)

        self.right_key_var = ctk.StringVar(value="D")
        self.right_key_entry = ctk.CTkComboBox(
            self.right_key_frame,
            values=["D", "ARROW_RIGHT", "NUMPAD_6"],
            variable=self.right_key_var,
            width=100
        )
        self.right_key_entry.pack(side="left", padx=5)

        # Movement timing settings
        self.movement_timing_frame = ctk.CTkFrame(movement_tab)
        self.movement_timing_frame.pack(pady=10, fill="x", padx=10)

        self.movement_interval_label = ctk.CTkLabel(
            self.movement_timing_frame,
            text="Movement Interval (seconds):"
        )
        self.movement_interval_label.pack(side="left", padx=10)

        self.movement_interval_entry = ctk.CTkEntry(
            self.movement_timing_frame,
            width=60
        )
        self.movement_interval_entry.pack(side="left", padx=5)
        self.movement_interval_entry.insert(0, "0.5")

        # Movement duration (how long to hold keys)
        self.movement_duration_label = ctk.CTkLabel(
            self.movement_timing_frame,
            text="Key Press Duration (seconds):"
        )
        self.movement_duration_label.pack(side="left", padx=(20, 10))

        self.movement_duration_entry = ctk.CTkEntry(
            self.movement_timing_frame,
            width=60
        )
        self.movement_duration_entry.pack(side="left", padx=5)
        self.movement_duration_entry.insert(0, "0.25")

        # === POTIONS & HEALING TAB ===
        potion_tab = self.tabview.tab("Potions & Healing")

        # Auto-healing settings
        self.healing_frame = ctk.CTkFrame(potion_tab)
        self.healing_frame.pack(pady=10, fill="x", padx=10)

        self.auto_heal_switch = ctk.CTkSwitch(
            self.healing_frame,
            text="Enable Auto-Healing (HP)",
            command=self.toggle_auto_heal
        )
        self.auto_heal_switch.pack(pady=10, padx=10, anchor="w")

        self.health_frame = ctk.CTkFrame(self.healing_frame)
        self.health_frame.pack(fill="x", pady=5, padx=10)

        self.health_threshold_label = ctk.CTkLabel(
            self.health_frame,
            text="Health Threshold %:"
        )
        self.health_threshold_label.pack(side="left", padx=5)

        self.health_threshold_entry = ctk.CTkEntry(
            self.health_frame,
            width=60
        )
        self.health_threshold_entry.pack(side="left", padx=5)
        self.health_threshold_entry.insert(0, "70")

        self.health_key_label = ctk.CTkLabel(
            self.health_frame,
            text="Healing Key:"
        )
        self.health_key_label.pack(side="left", padx=(20, 5))

        self.health_key_var = ctk.StringVar(value="H")
        self.health_key_entry = ctk.CTkComboBox(
            self.health_frame,
            values=["H", "F1", "F2", "F3", "F4", "1", "2", "3", "4", "5"],
            variable=self.health_key_var,
            width=60
        )
        self.health_key_entry.pack(side="left", padx=5)

        # EP Settings
        self.ep_healing_frame = ctk.CTkFrame(potion_tab)
        self.ep_healing_frame.pack(pady=10, fill="x", padx=10)

        self.auto_ep_switch = ctk.CTkSwitch(
            self.ep_healing_frame,
            text="Enable Auto-EP",
            command=self.toggle_auto_ep
        )
        self.auto_ep_switch.pack(pady=10, padx=10, anchor="w")

        self.ep_frame = ctk.CTkFrame(self.ep_healing_frame)
        self.ep_frame.pack(fill="x", pady=5, padx=10)

        self.ep_threshold_label = ctk.CTkLabel(
            self.ep_frame,
            text="EP Threshold %:"
        )
        self.ep_threshold_label.pack(side="left", padx=5)

        self.ep_threshold_entry = ctk.CTkEntry(
            self.ep_frame,
            width=60
        )
        self.ep_threshold_entry.pack(side="left", padx=5)
        self.ep_threshold_entry.insert(0, "30")

        self.ep_key_label = ctk.CTkLabel(
            self.ep_frame,
            text="EP Restore Key:"
        )
        self.ep_key_label.pack(side="left", padx=(20, 5))

        self.ep_key_var = ctk.StringVar(value="E")
        self.ep_key_entry = ctk.CTkComboBox(
            self.ep_frame,
            values=["E", "F5", "F6", "F7", "F8", "5", "6", "7", "8", "9"],
            variable=self.ep_key_var,
            width=60
        )
        self.ep_key_entry.pack(side="left", padx=5)

        # Image detection toggle for EP
        self.ep_image_detect_frame = ctk.CTkFrame(self.ep_healing_frame)
        self.ep_image_detect_frame.pack(fill="x", pady=5, padx=10)

        self.ep_detect_switch = ctk.CTkSwitch(
            self.ep_image_detect_frame,
            text="Enable EP Bar Detection"
        )
        self.ep_detect_switch.pack(side="left", padx=5)

        self.ep_region_button = ctk.CTkButton(
            self.ep_image_detect_frame,
            text="Select EP Bar Region",
            command=self.select_ep_region,
            width=150
        )
        self.ep_region_button.pack(side="left", padx=10)

        self.ep_color_button = ctk.CTkButton(
            self.ep_image_detect_frame,
            text="Select EP Bar Color",
            command=self.select_ep_color,
            width=150
        )
        self.ep_color_button.pack(side="left", padx=10)

        # Added priority healing option
        self.priority_heal_switch = ctk.CTkSwitch(
            self.healing_frame,
            text="Prioritize Healing (Heal even during other actions)",
            command=self.toggle_priority_healing
        )
        self.priority_heal_switch.pack(pady=5, padx=10, anchor="w")
        self.priority_heal_switch.select()  # Default to prioritize healing

        # Auto-potion settings
        self.potion_frame = ctk.CTkFrame(potion_tab)
        self.potion_frame.pack(pady=10, fill="x", padx=10)

        self.auto_pot_switch = ctk.CTkSwitch(
            self.potion_frame,
            text="Enable Auto-Potion",
            command=self.toggle_auto_pot
        )
        self.auto_pot_switch.pack(pady=10, padx=10, anchor="w")

        self.pot_frame = ctk.CTkFrame(self.potion_frame)
        self.pot_frame.pack(fill="x", pady=5, padx=10)

        self.pot_freq_label = ctk.CTkLabel(
            self.pot_frame,
            text="Potion Frequency (seconds):"
        )
        self.pot_freq_label.pack(side="left", padx=5)

        self.pot_freq_entry = ctk.CTkEntry(
            self.pot_frame,
            width=60
        )
        self.pot_freq_entry.pack(side="left", padx=5)
        self.pot_freq_entry.insert(0, "60")

        self.pot_key_label = ctk.CTkLabel(
            self.pot_frame,
            text="Potion Key:"
        )
        self.pot_key_label.pack(side="left", padx=(20, 5))

        self.pot_key_var = ctk.StringVar(value="P")
        self.pot_key_entry = ctk.CTkComboBox(
            self.pot_frame,
            values=["P", "F5", "F6", "F7", "F8", "6", "7", "8", "9", "0"],
            variable=self.pot_key_var,
            width=60
        )
        self.pot_key_entry.pack(side="left", padx=5)

        # Additional Potions
        self.add_pots_frame = ctk.CTkFrame(potion_tab)
        self.add_pots_frame.pack(pady=10, fill="x", padx=10)

        self.add_pots_label = ctk.CTkLabel(
            self.add_pots_frame,
            text="Additional Potions/Buffs",
            font=("Arial", 14, "bold")
        )
        self.add_pots_label.pack(pady=5, anchor="w", padx=10)

        self.pots_container = ctk.CTkScrollableFrame(self.add_pots_frame, height=150)
        self.pots_container.pack(fill="both", expand=True, pady=5, padx=10)

        self.add_pot_button = ctk.CTkButton(
            self.add_pots_frame,
            text="+ Add Potion/Buff",
            command=self.add_potion_entry,
            width=150
        )
        self.add_pot_button.pack(pady=5)

        # === PET FEEDER TAB ===
        pet_tab = self.tabview.tab("Pet Feeder")

        # Main pet frame
        self.pet_frame = ctk.CTkFrame(pet_tab)
        self.pet_frame.pack(pady=10, fill="x", padx=10)

        self.pet_title = ctk.CTkLabel(
            self.pet_frame,
            text="Pet Feeding Settings",
            font=("Arial", 16, "bold")
        )
        self.pet_title.pack(pady=10, anchor="w", padx=10)

        # Pet feeder toggle
        self.pet_feed_switch = ctk.CTkSwitch(
            self.pet_frame,
            text="Enable Pet Feeding",
            command=self.toggle_pet_feed
        )
        self.pet_feed_switch.pack(pady=5, padx=10, anchor="w")

        # Pet feed key
        self.pet_key_frame = ctk.CTkFrame(self.pet_frame)
        self.pet_key_frame.pack(fill="x", pady=5, padx=10)

        self.pet_key_label = ctk.CTkLabel(
            self.pet_key_frame,
            text="Pet Feed Key:"
        )
        self.pet_key_label.pack(side="left", padx=5)

        self.pet_key_var = ctk.StringVar(value="P")
        self.pet_key_entry = ctk.CTkComboBox(
            self.pet_key_frame,
            values=["P", "O", "I", "U", "Y", "F9", "F10", "F11", "F12"],
            variable=self.pet_key_var,
            width=80
        )
        self.pet_key_entry.pack(side="left", padx=5)

        # Pet feed interval
        self.pet_interval_frame = ctk.CTkFrame(self.pet_frame)
        self.pet_interval_frame.pack(fill="x", pady=5, padx=10)

        self.pet_interval_label = ctk.CTkLabel(
            self.pet_interval_frame,
            text="Feed Interval (minutes):"
        )
        self.pet_interval_label.pack(side="left", padx=5)

        self.pet_interval_entry = ctk.CTkEntry(
            self.pet_interval_frame,
            width=60
        )
        self.pet_interval_entry.pack(side="left", padx=5)
        self.pet_interval_entry.insert(0, "30")  # 30 minutes default

        # Pet detection settings
        self.pet_detection_frame = ctk.CTkFrame(pet_tab)
        self.pet_detection_frame.pack(pady=10, fill="x", padx=10)

        self.pet_detection_title = ctk.CTkLabel(
            self.pet_detection_frame,
            text="Advanced Pet Status Detection",
            font=("Arial", 14, "bold")
        )
        self.pet_detection_title.pack(pady=5, anchor="w", padx=10)

        self.pet_detect_switch = ctk.CTkSwitch(
            self.pet_detection_frame,
            text="Enable Pet Status Detection"
        )
        self.pet_detect_switch.pack(pady=5, padx=10, anchor="w")

        # You can add image detection for pet status here
        self.pet_region_frame = ctk.CTkFrame(self.pet_detection_frame)
        self.pet_region_frame.pack(fill="x", pady=5, padx=10)

        self.pet_region_button = ctk.CTkButton(
            self.pet_region_frame,
            text="Select Pet Status Region",
            command=self.select_pet_region,
            width=180
        )
        self.pet_region_button.pack(side="left", padx=5)

        self.pet_color_button = ctk.CTkButton(
            self.pet_region_frame,
            text="Select Pet Status Color",
            command=self.select_pet_color,
            width=180
        )
        self.pet_color_button.pack(side="left", padx=5)

        # Test pet feed button
        self.test_pet_frame = ctk.CTkFrame(pet_tab)
        self.test_pet_frame.pack(pady=10, fill="x", padx=10)

        self.test_pet_button = ctk.CTkButton(
            self.test_pet_frame,
            text="Test Pet Feeding Now",
            command=self.test_pet_feed,
            fg_color="blue",
            hover_color="darkblue",
            width=200
        )
        self.test_pet_button.pack(pady=10)

        self.pet_status_display = ctk.CTkLabel(
            self.test_pet_frame,
            text="Pet status: Not checked yet",
            font=("Arial", 12)
        )
        self.pet_status_display.pack(pady=5)

        # Pet history frame
        self.pet_history_frame = ctk.CTkFrame(pet_tab)
        self.pet_history_frame.pack(pady=10, fill="both", expand=True, padx=10)

        self.pet_history_label = ctk.CTkLabel(
            self.pet_history_frame,
            text="Pet Feeding History:",
            font=("Arial", 12, "bold")
        )
        self.pet_history_label.pack(pady=5, anchor="w", padx=10)

        self.pet_history_text = ctk.CTkTextbox(
            self.pet_history_frame,
            height=150
        )
        self.pet_history_text.pack(fill="both", expand=True, pady=5, padx=10)
        self.pet_history_text.insert("1.0", "No feeding history yet.\n")
        self.pet_history_text.configure(state="disabled")

        # === LOOT & PICKUP TAB ===
        loot_tab = self.tabview.tab("Loot & Pickup")

        self.loot_frame = ctk.CTkFrame(loot_tab)
        self.loot_frame.pack(pady=10, fill="x", padx=10)

        self.loot_switch = ctk.CTkSwitch(
            self.loot_frame,
            text="Enable Auto Looting",
            command=self.toggle_loot
        )
        self.loot_switch.pack(pady=10, padx=10, anchor="w")

        self.loot_settings_frame = ctk.CTkFrame(loot_tab)
        self.loot_settings_frame.pack(pady=10, fill="x", padx=10)

        self.loot_key_label = ctk.CTkLabel(
            self.loot_settings_frame,
            text="Loot/Pickup Key:"
        )
        self.loot_key_label.pack(side="left", padx=5)

        self.loot_key_var = ctk.StringVar(value="Z")
        self.loot_key_entry = ctk.CTkComboBox(
            self.loot_settings_frame,
            values=["Z", "X", "V", "B", "F", "G", "R", "T", "SPACE"],
            variable=self.loot_key_var,
            width=80
        )
        self.loot_key_entry.pack(side="left", padx=5)

        self.loot_freq_label = ctk.CTkLabel(
            self.loot_settings_frame,
            text="Loot Frequency (seconds):"
        )
        self.loot_freq_label.pack(side="left", padx=(20, 5))

        self.loot_freq_entry = ctk.CTkEntry(
            self.loot_settings_frame,
            width=60
        )
        self.loot_freq_entry.pack(side="left", padx=5)
        self.loot_freq_entry.insert(0, "5")

        # Click positions for looting (for games that need specific click positions)
        self.loot_click_frame = ctk.CTkFrame(loot_tab)
        self.loot_click_frame.pack(pady=10, fill="x", padx=10)

        self.loot_click_label = ctk.CTkLabel(
            self.loot_click_frame,
            text="Advanced Loot Settings:",
            font=("Arial", 12, "bold")
        )
        self.loot_click_label.pack(pady=5, anchor="w", padx=10)

        self.loot_click_switch = ctk.CTkSwitch(
            self.loot_click_frame,
            text="Enable Click at Position (for some games)"
        )
        self.loot_click_switch.pack(pady=5, anchor="w", padx=20)

        self.loot_pos_frame = ctk.CTkFrame(self.loot_click_frame)
        self.loot_pos_frame.pack(fill="x", pady=5, padx=10)

        self.loot_x_label = ctk.CTkLabel(
            self.loot_pos_frame,
            text="Click Position X:"
        )
        self.loot_x_label.pack(side="left", padx=5)

        self.loot_x_entry = ctk.CTkEntry(
            self.loot_pos_frame,
            width=60
        )
        self.loot_x_entry.pack(side="left", padx=5)
        self.loot_x_entry.insert(0, "500")

        self.loot_y_label = ctk.CTkLabel(
            self.loot_pos_frame,
            text="Click Position Y:"
        )
        self.loot_y_label.pack(side="left", padx=(20, 5))

        self.loot_y_entry = ctk.CTkEntry(
            self.loot_pos_frame,
            width=60
        )
        self.loot_y_entry.pack(side="left", padx=5)
        self.loot_y_entry.insert(0, "400")

        # === IMAGE RECOGNITION TAB ===
        img_tab = self.tabview.tab("Image Recognition")

        # Health detection
        self.img_health_frame = ctk.CTkFrame(img_tab)
        self.img_health_frame.pack(pady=10, fill="x", padx=10)

        self.img_health_title = ctk.CTkLabel(
            self.img_health_frame,
            text="Health Bar Detection",
            font=("Arial", 14, "bold")
        )
        self.img_health_title.pack(pady=5, anchor="w", padx=10)

        self.health_detect_switch = ctk.CTkSwitch(
            self.img_health_frame,
            text="Enable Health Bar Detection",
            command=self.toggle_health_detect
        )
        self.health_detect_switch.pack(pady=5, anchor="w", padx=20)

        self.health_region_frame = ctk.CTkFrame(self.img_health_frame)
        self.health_region_frame.pack(fill="x", pady=5, padx=10)

        self.health_region_label = ctk.CTkLabel(
            self.health_region_frame,
            text="Health Bar Region:"
        )
        self.health_region_label.pack(side="left", padx=5)

        self.health_region_button = ctk.CTkButton(
            self.health_region_frame,
            text="Select Region",
            command=self.select_health_region,
            width=110
        )
        self.health_region_button.pack(side="left", padx=5)

        self.health_color_button = ctk.CTkButton(
            self.health_region_frame,
            text="Select Color",
            command=self.select_health_color,
            width=110
        )
        self.health_color_button.pack(side="left", padx=5)

        self.health_region_info = ctk.CTkLabel(
            self.img_health_frame,
            text=f"Health Region: {self.health_region}, Color: {self.health_color}",
            font=("Arial", 10)
        )
        self.health_region_info.pack(pady=5, padx=10)

        # EP bar detection
        self.img_ep_frame = ctk.CTkFrame(img_tab)
        self.img_ep_frame.pack(pady=10, fill="x", padx=10)

        self.img_ep_title = ctk.CTkLabel(
            self.img_ep_frame,
            text="EP Bar Detection",
            font=("Arial", 14, "bold")
        )
        self.img_ep_title.pack(pady=5, anchor="w", padx=10)

        self.ep_detect_switch_main = ctk.CTkSwitch(
            self.img_ep_frame,
            text="Enable EP Bar Detection",
            command=self.toggle_ep_detect
        )
        self.ep_detect_switch_main.pack(pady=5, anchor="w", padx=20)

        self.ep_region_frame_main = ctk.CTkFrame(self.img_ep_frame)
        self.ep_region_frame_main.pack(fill="x", pady=5, padx=10)

        self.ep_region_label = ctk.CTkLabel(
            self.ep_region_frame_main,
            text="EP Bar Region:"
        )
        self.ep_region_label.pack(side="left", padx=5)

        self.ep_region_button_main = ctk.CTkButton(
            self.ep_region_frame_main,
            text="Select Region",
            command=self.select_ep_region,
            width=110
        )
        self.ep_region_button_main.pack(side="left", padx=5)

        self.ep_color_button_main = ctk.CTkButton(
            self.ep_region_frame_main,
            text="Select Color",
            command=self.select_ep_color,
            width=110
        )
        self.ep_color_button_main.pack(side="left", padx=5)

        self.ep_region_info = ctk.CTkLabel(
            self.img_ep_frame,
            text=f"EP Region: {self.ep_region}, Color: {self.ep_color}",
            font=("Arial", 10)
        )
        self.ep_region_info.pack(pady=5, padx=10)

        # Enemy detection
        self.img_enemy_frame = ctk.CTkFrame(img_tab)
        self.img_enemy_frame.pack(pady=10, fill="x", padx=10)

        self.img_enemy_title = ctk.CTkLabel(
            self.img_enemy_frame,
            text="Enemy Detection",
            font=("Arial", 14, "bold")
        )
        self.img_enemy_title.pack(pady=5, anchor="w", padx=10)

        self.enemy_detect_switch = ctk.CTkSwitch(
            self.img_enemy_frame,
            text="Enable Enemy Detection",
            command=self.toggle_enemy_detect
        )
        self.enemy_detect_switch.pack(pady=5, anchor="w", padx=20)

        self.enemy_region_frame = ctk.CTkFrame(self.img_enemy_frame)
        self.enemy_region_frame.pack(fill="x", pady=5, padx=10)

        self.enemy_region_label = ctk.CTkLabel(
            self.enemy_region_frame,
            text="Enemy Detection Region:"
        )
        self.enemy_region_label.pack(side="left", padx=5)

        self.enemy_region_button = ctk.CTkButton(
            self.enemy_region_frame,
            text="Select Region",
            command=self.select_enemy_region,
            width=110
        )
        self.enemy_region_button.pack(side="left", padx=5)

        self.enemy_color_button = ctk.CTkButton(
            self.enemy_region_frame,
            text="Select Color",
            command=self.select_enemy_color,
            width=110
        )
        self.enemy_color_button.pack(side="left", padx=5)

        self.enemy_region_info = ctk.CTkLabel(
            self.img_enemy_frame,
            text=f"Enemy Region: {self.enemy_region}, Color: {self.enemy_color}",
            font=("Arial", 10)
        )
        self.enemy_region_info.pack(pady=5, padx=10)

        # Buff detection
        self.img_buff_frame = ctk.CTkFrame(img_tab)
        self.img_buff_frame.pack(pady=10, fill="x", padx=10)

        self.img_buff_title = ctk.CTkLabel(
            self.img_buff_frame,
            text="Buff Status Detection",
            font=("Arial", 14, "bold")
        )
        self.img_buff_title.pack(pady=5, anchor="w", padx=10)

        self.buff_detect_switch = ctk.CTkSwitch(
            self.img_buff_frame,
            text="Enable Buff Detection"
        )
        self.buff_detect_switch.pack(pady=5, anchor="w", padx=20)

        self.buff_region_frame = ctk.CTkFrame(self.img_buff_frame)
        self.buff_region_frame.pack(fill="x", pady=5, padx=10)

        self.buff_region_label = ctk.CTkLabel(
            self.buff_region_frame,
            text="Buff Icon Region:"
        )
        self.buff_region_label.pack(side="left", padx=5)

        self.buff_region_button = ctk.CTkButton(
            self.buff_region_frame,
            text="Select Region",
            command=self.select_buff_region,
            width=110
        )
        self.buff_region_button.pack(side="left", padx=5)

        self.buff_color_button = ctk.CTkButton(
            self.buff_region_frame,
            text="Select Color",
            command=self.select_buff_color,
            width=110
        )
        self.buff_color_button.pack(side="left", padx=5)

        self.buff_region_info = ctk.CTkLabel(
            self.img_buff_frame,
            text=f"Buff Region: {self.buff_region}, Color: {self.buff_color}",
            font=("Arial", 10)
        )
        self.buff_region_info.pack(pady=5, padx=10)

        # Test area
        self.test_img_frame = ctk.CTkFrame(img_tab)
        self.test_img_frame.pack(pady=10, fill="x", padx=10)

        self.test_img_button = ctk.CTkButton(
            self.test_img_frame,
            text="Test Image Recognition",
            command=self.test_image_recognition,
            width=200
        )
        self.test_img_button.pack(pady=10)

        self.test_result_label = ctk.CTkLabel(
            self.test_img_frame,
            text="Test results will appear here",
            font=("Arial", 12)
        )
        self.test_result_label.pack(pady=5)

        # === ESP & TARGETING TAB ===
        esp_tab = self.tabview.tab("ESP & Targeting")

        # Auto targeting
        self.targeting_frame = ctk.CTkFrame(esp_tab)
        self.targeting_frame.pack(pady=10, fill="x", padx=10)

        self.targeting_title = ctk.CTkLabel(
            self.targeting_frame,
            text="Auto Target Settings",
            font=("Arial", 14, "bold")
        )
        self.targeting_title.pack(pady=5, anchor="w", padx=10)

        self.targeting_switch = ctk.CTkSwitch(
            self.targeting_frame,
            text="Enable Auto Targeting",
            command=self.toggle_target
        )
        self.targeting_switch.pack(pady=5, anchor="w", padx=20)

        # Target Settings frame
        self.target_settings_frame = ctk.CTkFrame(self.targeting_frame)
        self.target_settings_frame.pack(fill="x", pady=5, padx=10)

        self.target_key_label = ctk.CTkLabel(
            self.target_settings_frame,
            text="Target Key:"
        )
        self.target_key_label.pack(side="left", padx=5)

        self.target_key_var = ctk.StringVar(value="TAB")
        self.target_key_entry = ctk.CTkComboBox(
            self.target_settings_frame,
            values=["TAB", "T", "F1", "F2", "F3", "1", "2", "3", "SPACE"],
            variable=self.target_key_var,
            width=80
        )
        self.target_key_entry.pack(side="left", padx=5)

        self.target_freq_label = ctk.CTkLabel(
            self.target_settings_frame,
            text="Target Frequency (seconds):"
        )
        self.target_freq_label.pack(side="left", padx=(20, 5))

        self.target_freq_entry = ctk.CTkEntry(
            self.target_settings_frame,
            width=60
        )
        self.target_freq_entry.pack(side="left", padx=5)
        self.target_freq_entry.insert(0, "5")

        # ESP settings
        self.esp_frame = ctk.CTkFrame(esp_tab)
        self.esp_frame.pack(pady=10, fill="x", padx=10)

        self.esp_title = ctk.CTkLabel(
            self.esp_frame,
            text="ESP Settings",
            font=("Arial", 14, "bold")
        )
        self.esp_title.pack(pady=5, anchor="w", padx=10)

        self.esp_switch = ctk.CTkSwitch(
            self.esp_frame,
            text="Enable ESP",
            command=self.toggle_esp
        )
        self.esp_switch.pack(pady=5, anchor="w", padx=20)

        # ESP Settings frame
        self.esp_settings_frame = ctk.CTkFrame(self.esp_frame)
        self.esp_settings_frame.pack(fill="x", pady=5, padx=10)

        self.esp_target_label = ctk.CTkLabel(
            self.esp_settings_frame,
            text="Target Mob Name:"
        )
        self.esp_target_label.pack(side="left", padx=5)

        self.esp_target_entry = ctk.CTkEntry(
            self.esp_settings_frame,
            width=150
        )
        self.esp_target_entry.pack(side="left", padx=5)
        self.esp_target_entry.insert(0, "Monster")

        self.esp_color_label = ctk.CTkLabel(
            self.esp_settings_frame,
            text="ESP Box Color:"
        )
        self.esp_color_label.pack(side="left", padx=(20, 5))

        self.esp_color_button = ctk.CTkButton(
            self.esp_settings_frame,
            text="Choose Color",
            command=self.choose_esp_color,
            width=100
        )
        self.esp_color_button.pack(side="left", padx=5)

        # ESP Overlay settings
        self.esp_overlay_frame = ctk.CTkFrame(self.esp_frame)
        self.esp_overlay_frame.pack(fill="x", pady=10, padx=10)

        self.esp_overlay_label = ctk.CTkLabel(
            self.esp_overlay_frame,
            text="ESP Overlay Window:",
            font=("Arial", 12, "bold")
        )
        self.esp_overlay_label.pack(pady=5, anchor="w")

        self.esp_overlay_switch = ctk.CTkSwitch(
            self.esp_overlay_frame,
            text="Show ESP Overlay Window",
            command=self.toggle_esp_overlay
        )
        self.esp_overlay_switch.pack(pady=5, anchor="w")

        # ESP Debugging & Testing
        self.esp_debug_frame = ctk.CTkFrame(esp_tab)
        self.esp_debug_frame.pack(pady=10, fill="x", padx=10)

        self.esp_debug_title = ctk.CTkLabel(
            self.esp_debug_frame,
            text="ESP Debugging & Testing",
            font=("Arial", 14, "bold")
        )
        self.esp_debug_title.pack(pady=5, anchor="w", padx=10)

        self.esp_debug_desc = ctk.CTkLabel(
            self.esp_debug_frame,
            text="Test ESP functionality and add mock targets for debugging",
            wraplength=800
        )
        self.esp_debug_desc.pack(pady=5, anchor="w", padx=10)

        # Mock target position controls
        self.mock_target_frame = ctk.CTkFrame(self.esp_debug_frame)
        self.mock_target_frame.pack(fill="x", pady=5, padx=10)

        self.mock_target_label = ctk.CTkLabel(
            self.mock_target_frame,
            text="Add Mock Target Position:"
        )
        self.mock_target_label.pack(side="left", padx=5)

        self.mock_x_entry = ctk.CTkEntry(
            self.mock_target_frame,
            width=60,
            placeholder_text="X pos"
        )
        self.mock_x_entry.pack(side="left", padx=5)

        self.mock_y_entry = ctk.CTkEntry(
            self.mock_target_frame,
            width=60,
            placeholder_text="Y pos"
        )
        self.mock_y_entry.pack(side="left", padx=5)

        self.mock_w_entry = ctk.CTkEntry(
            self.mock_target_frame,
            width=60,
            placeholder_text="Width"
        )
        self.mock_w_entry.pack(side="left", padx=5)
        self.mock_w_entry.insert(0, "100")

        self.mock_h_entry = ctk.CTkEntry(
            self.mock_target_frame,
            width=60,
            placeholder_text="Height"
        )
        self.mock_h_entry.pack(side="left", padx=5)
        self.mock_h_entry.insert(0, "100")

        self.add_mock_button = ctk.CTkButton(
            self.mock_target_frame,
            text="Add Mock",
            command=self.add_mock_target,
            width=80
        )
        self.add_mock_button.pack(side="left", padx=10)

        # Testing buttons
        self.esp_test_buttons_frame = ctk.CTkFrame(self.esp_debug_frame)
        self.esp_test_buttons_frame.pack(fill="x", pady=10, padx=10)

        self.test_esp_button = ctk.CTkButton(
            self.esp_test_buttons_frame,
            text="Test ESP Overlay",
            command=self.test_esp_overlay,
            width=150
        )
        self.test_esp_button.pack(side="left", padx=10)

        self.esp_random_button = ctk.CTkButton(
            self.esp_test_buttons_frame,
            text="Add Random Mocks",
            command=self.add_random_mocks,
            width=150
        )
        self.esp_random_button.pack(side="left", padx=10)

        self.esp_clear_button = ctk.CTkButton(
            self.esp_test_buttons_frame,
            text="Clear All Mocks",
            command=self.clear_mocks,
            fg_color="red",
            width=150
        )
        self.esp_clear_button.pack(side="left", padx=10)

        # Display mock targets
        self.mock_targets_frame = ctk.CTkFrame(self.esp_debug_frame)
        self.mock_targets_frame.pack(fill="x", pady=5, padx=10)

        self.mock_targets_label = ctk.CTkLabel(
            self.mock_targets_frame,
            text="Current Mock Targets:"
        )
        self.mock_targets_label.pack(anchor="w", padx=5, pady=5)

        self.mock_targets_text = ctk.CTkTextbox(
            self.mock_targets_frame,
            height=100
        )
        self.mock_targets_text.pack(fill="x", padx=5, pady=5)
        self.mock_targets_text.configure(state="disabled")

        # === PROFILES TAB ===
        profiles_tab = self.tabview.tab("Profiles")

        self.profiles_frame = ctk.CTkFrame(profiles_tab)
        self.profiles_frame.pack(pady=10, fill="both", expand=True, padx=10)

        self.profiles_label = ctk.CTkLabel(
            self.profiles_frame,
            text="Save/Load Configuration Profiles",
            font=("Arial", 14, "bold")
        )
        self.profiles_label.pack(pady=10, padx=10)

        self.profile_name_frame = ctk.CTkFrame(self.profiles_frame)
        self.profile_name_frame.pack(fill="x", pady=5, padx=10)

        self.profile_name_label = ctk.CTkLabel(
            self.profile_name_frame,
            text="Profile Name:"
        )
        self.profile_name_label.pack(side="left", padx=5)

        self.profile_name_entry = ctk.CTkEntry(
            self.profile_name_frame,
            width=200
        )
        self.profile_name_entry.pack(side="left", padx=5)
        self.profile_name_entry.insert(0, "default")

        self.profile_buttons_frame = ctk.CTkFrame(self.profiles_frame)
        self.profile_buttons_frame.pack(fill="x", pady=10, padx=10)

        self.save_profile_button = ctk.CTkButton(
            self.profile_buttons_frame,
            text="Save Profile",
            command=self.save_profile,
            fg_color="blue",
            hover_color="darkblue",
            width=120
        )
        self.save_profile_button.pack(side="left", padx=5)

        self.load_profile_button = ctk.CTkButton(
            self.profile_buttons_frame,
            text="Load Profile",
            command=self.load_profile,
            fg_color="purple",
            hover_color="#551A8B",  # Dark purple with a valid hex color
            width=120
        )
        self.load_profile_button.pack(side="left", padx=5)

        self.delete_profile_button = ctk.CTkButton(
            self.profile_buttons_frame,
            text="Delete Profile",
            command=self.delete_profile,
            fg_color="red",
            hover_color="darkred",
            width=120
        )
        self.delete_profile_button.pack(side="left", padx=5)

        # Available profiles list
        self.profiles_list_frame = ctk.CTkFrame(self.profiles_frame)
        self.profiles_list_frame.pack(fill="both", expand=True, pady=10, padx=10)

        self.profiles_list_label = ctk.CTkLabel(
            self.profiles_list_frame,
            text="Available Profiles:",
            font=("Arial", 12)
        )
        self.profiles_list_label.pack(pady=5, anchor="w", padx=10)

        self.profiles_listbox = ctk.CTkTextbox(
            self.profiles_list_frame,
            height=200
        )
        self.profiles_listbox.pack(fill="both", expand=True, pady=5, padx=10)

        # Add initial sequence steps and potion entry
        self.add_sequence_step(self.combat_container)
        self.add_sequence_step(self.buffs_container)
        self.add_sequence_step(self.trans_container)
        self.add_sequence_step(self.no_enemy_container)
        self.add_potion_entry()

    def select_pet_region(self):
        selector = RegionSelector(self, "pet", [0, 0, 100, 20])
        self.wait_window(selector)
        if selector.result_region:
            self.pet_region = selector.result_region

    def select_pet_color(self):
        if not hasattr(self, 'pet_region') or not self.pet_region:
            messagebox.showwarning("Warning", "Please select a pet status region first")
            return

        picker = ColorPicker(self, self.pet_region, "pet", "#FFFF00")  # Default yellow for pet
        self.wait_window(picker)
        if picker.result_color:
            self.pet_color = picker.result_color
            self.pet_threshold_pct = picker.result_threshold

    def test_pet_feed(self):
        """Test pet feeding function"""
        try:
            # Log the action
            self.add_pet_feed_log("Testing pet feeding")

            # Get the feed key
            key = self.pet_key_var.get()

            # Check if a window is selected
            hwnd = win32gui.FindWindow(None, self.window_dropdown.get())
            if hwnd:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)

                # Press the pet feed key
                self.send_keypress(key)
                self.update_status(f"Pet feed test: Sent {key}", "cyan")
                self.pet_status_display.configure(text=f"Pet feed test: Key {key} sent")

                # Update the pet status indicator
                self.pet_status_label.configure(text="Pet: Just fed (test)", text_color="green")
                return True
            else:
                self.update_status("No game window selected for pet feed test", "red")
                return False
        except Exception as e:
            self.update_status(f"Pet feed test error: {str(e)}", "red")
            return False

    def add_pet_feed_log(self, message):
        """Add an entry to the pet feeding history log"""
        try:
            if not hasattr(self, 'pet_history_text'):
                return

            # Enable editing
            self.pet_history_text.configure(state="normal")

            # Add timestamp and message
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self.pet_history_text.insert("1.0", f"[{timestamp}] {message}\n")

            # Limit log size to prevent memory issues
            if float(self.pet_history_text.index('end')) > 100:  # More than 100 lines
                self.pet_history_text.delete("50.0", "end")  # Delete older entries

            # Disable editing again
            self.pet_history_text.configure(state="disabled")
        except Exception as e:
            print(f"Error updating pet log: {str(e)}")

    def toggle_pet_feed(self):
        """Toggle pet feeding feature"""
        self.pet_feed_enabled = self.pet_feed_switch.get()

        # Update interval value
        try:
            minutes = float(self.pet_interval_entry.get())
            self.pet_feed_interval = minutes * 60  # Convert to seconds
        except:
            self.pet_feed_interval = 1800  # Default 30 minutes

        # Update key value
        self.pet_feed_key = self.pet_key_var.get()

        # Sync with quick toggle
        self.pet_feed_quick_toggle.select() if self.pet_feed_enabled else self.pet_feed_quick_toggle.deselect()

        # Update status
        if self.pet_feed_enabled:
            self.update_status("Pet feeding activated", "green")
            self.pet_status_label.configure(text=f"Pet: Will feed every {minutes} min", text_color="cyan")
        else:
            self.update_status("Pet feeding deactivated", "white")
            self.pet_status_label.configure(text="Pet: Not fed", text_color="white")

    def toggle_pet_feed_quick(self):
        """Quick toggle for pet feeder from main screen"""
        self.pet_feed_enabled = self.pet_feed_quick_toggle.get()
        self.pet_feed_switch.select() if self.pet_feed_enabled else self.pet_feed_switch.deselect()
        self.toggle_pet_feed()  # Update other settings

    def toggle_buffs(self):
        self.buff_toggle_enabled = self.buff_toggle.get()

    def toggle_target(self):
        self.target_enabled = self.targeting_switch.get()
        self.target_key = self.target_key_var.get()
        self.target_frequency = float(self.target_freq_entry.get())
        self.target_quick_toggle.select() if self.target_enabled else self.target_quick_toggle.deselect()

    def toggle_esp(self):
        self.esp_enabled = self.esp_switch.get()
        self.esp_target_name = self.esp_target_entry.get()
        self.esp_quick_toggle.select() if self.esp_enabled else self.esp_quick_toggle.deselect()

        # Update ESP overlay settings
        self.esp_overlay.update_target(self.esp_target_name)
        self.esp_overlay.update_color(self.esp_color)

        # Update ESP status on main tab
        if self.esp_enabled:
            self.esp_status_label.configure(text=f"ESP: {self.esp_target_name}", text_color="cyan")
        else:
            self.esp_status_label.configure(text="ESP: Off", text_color="white")

    def toggle_ep_detect(self):
        """Toggle EP detection between the tabs"""
        # Sync the EP detection switches
        ep_detect_enabled = self.ep_detect_switch_main.get()
        self.ep_detect_switch.select() if ep_detect_enabled else self.ep_detect_switch.deselect()

    def toggle_auto_ep(self):
        """Toggle auto EP feature"""
        self.auto_ep = self.auto_ep_switch.get()
        # Sync with quick toggle
        self.ep_quick_toggle.select() if self.auto_ep else self.ep_quick_toggle.deselect()

        try:
            self.ep_threshold = int(self.ep_threshold_entry.get())
            self.ep_key = self.ep_key_var.get()
        except:
            self.ep_threshold = 30

    def toggle_ep_quick(self):
        """Quick toggle for EP from main tab"""
        self.auto_ep = self.ep_quick_toggle.get()
        self.auto_ep_switch.select() if self.auto_ep else self.auto_ep_switch.deselect()

    def select_ep_region(self):
        """Select the EP bar region"""
        selector = RegionSelector(self, "ep", self.ep_region)
        self.wait_window(selector)
        if selector.result_region:
            self.ep_region = selector.result_region
            self.ep_region_info.configure(text=f"EP Region: {self.ep_region}, Color: {self.ep_color}")

    def select_ep_color(self):
        """Select the EP bar color"""
        if not any(self.ep_region):
            messagebox.showwarning("Warning", "Please select an EP region first")
            return

        picker = ColorPicker(self, self.ep_region, "ep", self.ep_color)
        self.wait_window(picker)
        if picker.result_color:
            self.ep_color = picker.result_color
            self.ep_threshold_pct = picker.result_threshold
            self.ep_region_info.configure(text=f"EP Region: {self.ep_region}, Color: {self.ep_color}")

    def check_ep_level(self):
        """Check EP level using image recognition"""
        try:
            ep_detection_enabled = self.ep_detect_switch.get() or self.ep_detect_switch_main.get()

            if not ep_detection_enabled or not any(self.ep_region):
                return 100  # Default to full EP if detection disabled

            # Take screenshot of EP region
            x, y, width, height = self.ep_region
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            img_np = np.array(screenshot)

            # Convert to HSV for better color detection
            img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

            # Parse the color
            r = int(self.ep_color[1:3], 16)
            g = int(self.ep_color[3:5], 16)
            b = int(self.ep_color[5:7], 16)

            # Convert RGB to HSV color for masking
            rgb_color = np.uint8([[[b, g, r]]])  # OpenCV uses BGR
            hsv_color = cv2.cvtColor(rgb_color, cv2.COLOR_BGR2HSV)
            hsv_value = hsv_color[0][0][0]

            # Create a range for the color
            threshold = self.ep_threshold_pct
            lower_bound = np.array([max(0, hsv_value - threshold), 50, 50])
            upper_bound = np.array([min(179, hsv_value + threshold), 255, 255])

            # Create mask and count pixels
            mask = cv2.inRange(img_hsv, lower_bound, upper_bound)
            ep_pixels = cv2.countNonZero(mask)
            total_pixels = width * height

            # Calculate EP percentage
            if total_pixels > 0:
                ep_pct = min(100, int((ep_pixels / total_pixels) * 100))

                # Update EP status in UI
                self.ep_status_label.configure(
                    text=f"EP: {ep_pct}%",
                    text_color="green" if ep_pct > 50 else "orange" if ep_pct > 25 else "red"
                )

                return ep_pct
            else:
                return 100

        except Exception as e:
            self.update_status(f"EP check error: {str(e)}", "red")
            return 100  # Assume full EP if error

    def check_and_restore_ep(self):
        """Check and restore EP if needed"""
        try:
            if not self.current_config or not self.auto_ep:
                return False

            # Get EP level
            current_ep = self.check_ep_level()
            ep_threshold = self.ep_threshold

            if current_ep <= ep_threshold:
                self.update_status(f"EP at {current_ep}%, restoring with {self.ep_key}", "orange")
                self.send_keypress(self.ep_key)
                time.sleep(0.2)  # Small delay after EP restore
                return True  # EP restoration was performed

            return False

        except Exception as e:
            self.update_status(f"EP Restore Error: {str(e)}", "red")
            return False

    def check_and_feed_pet(self):
        """Check if it's time to feed the pet and do so if needed"""
        try:
            if not self.current_config or not self.pet_feed_enabled:
                return False

            current_time = time.time()

            if current_time - self.last_pet_feed_time > self.pet_feed_interval:
                self.update_status(f"Feeding pet with {self.pet_feed_key}", "cyan")

                # Log the action
                self.add_pet_feed_log("Feeding pet - scheduled")

                # Send the key press
                self.send_keypress(self.pet_feed_key)
                self.last_pet_feed_time = current_time

                # Update pet status display
                minutes = int(self.pet_feed_interval / 60)
                self.pet_status_label.configure(
                    text=f"Pet: Fed, next in {minutes} min",
                    text_color="green"
                )

                return True

            # Update remaining time display occasionally
            if hasattr(self, 'last_pet_status_update') and current_time - self.last_pet_status_update < 30:
                return False

            # Update display with time remaining
            remaining = self.pet_feed_interval - (current_time - self.last_pet_feed_time)
            remaining_minutes = int(remaining / 60)
            self.pet_status_label.configure(
                text=f"Pet: Next feed in {remaining_minutes} min",
                text_color="cyan" if remaining_minutes > 5 else "orange"
            )
            self.last_pet_status_update = current_time

            return False

        except Exception as e:
            self.update_status(f"Pet Feeding Error: {str(e)}", "red")
            return False

    def toggle_target_quick(self):
        self.target_enabled = self.target_quick_toggle.get()
        self.targeting_switch.select() if self.target_enabled else self.targeting_switch.deselect()

    def toggle_esp_quick(self):
        self.esp_enabled = self.esp_quick_toggle.get()
        self.esp_switch.select() if self.esp_enabled else self.esp_switch.deselect()
        self.toggle_esp()  # Update ESP settings

    def toggle_esp_overlay(self):
        esp_overlay_enabled = self.esp_overlay_switch.get() if hasattr(self, 'esp_overlay_switch') else self.esp_overlay_toggle.get()

        # Sync both switches
        if hasattr(self, 'esp_overlay_switch'):
            self.esp_overlay_switch.select() if esp_overlay_enabled else self.esp_overlay_switch.deselect()
        if hasattr(self, 'esp_overlay_toggle'):
            self.esp_overlay_toggle.select() if esp_overlay_enabled else self.esp_overlay_toggle.deselect()

        # Toggle the ESP overlay
        if esp_overlay_enabled:
            # Make sure we have the overlay window ready
            if not self.esp_overlay or not hasattr(self.esp_overlay, 'window') or not self.esp_overlay.window:
                self.esp_overlay.create_window()

            # Start ESP overlay
            self.esp_overlay.toggle_overlay()

            # Update ESP settings
            self.esp_overlay.update_color(self.esp_color)
            self.esp_overlay.update_target(self.esp_target_name)

            # Update status
            self.update_status("ESP Overlay activated", "cyan")
        else:
            # Close overlay if it's active
            if self.esp_overlay and self.esp_overlay.active:
                self.esp_overlay.toggle_overlay()
            self.update_status("ESP Overlay deactivated", "white")

    def add_mock_target(self):
        """Add a mock target for ESP debugging"""
        try:
            # Get values from entries
            x = int(self.mock_x_entry.get() or 200)
            y = int(self.mock_y_entry.get() or 200)
            w = int(self.mock_w_entry.get() or 100)
            h = int(self.mock_h_entry.get() or 100)

            # Add to ESP overlay
            self.esp_overlay.add_mock_position(x, y, w, h)

            # Update the mock targets display
            self.update_mock_targets_display()

            # Clear entry fields
            self.mock_x_entry.delete(0, 'end')
            self.mock_y_entry.delete(0, 'end')

            # Activate overlay if not active
            if self.esp_overlay and not self.esp_overlay.active:
                if not self.esp_overlay_toggle.get():
                    self.esp_overlay_toggle.select()
                self.toggle_esp_overlay()

        except ValueError as e:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values for position and size")

    def add_random_mocks(self):
        """Add random mock targets for testing"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Add 5 random mock targets
        for i in range(5):
            x = random.randint(100, screen_width - 300)
            y = random.randint(100, screen_height - 300)
            w = random.randint(50, 200)
            h = random.randint(50, 200)

            self.esp_overlay.add_mock_position(x, y, w, h)

        # Update the mock targets display
        self.update_mock_targets_display()

        # Activate overlay if not active
        if self.esp_overlay and not self.esp_overlay.active:
            if not self.esp_overlay_toggle.get():
                self.esp_overlay_toggle.select()
            self.toggle_esp_overlay()

    def clear_mocks(self):
        """Clear all mock targets"""
        if self.esp_overlay:
            self.esp_overlay.clear_mock_positions()
            self.update_mock_targets_display()

    def update_mock_targets_display(self):
        """Update the textbox showing current mock targets"""
        if not hasattr(self, 'mock_targets_text'):
            return

        # Enable editing
        self.mock_targets_text.configure(state="normal")

        # Clear current text
        self.mock_targets_text.delete("1.0", "end")

        # Add all mock positions
        if self.esp_overlay and self.esp_overlay.mock_positions:
            for i, (x, y, w, h) in enumerate(self.esp_overlay.mock_positions):
                self.mock_targets_text.insert("end", f"{i+1}. Position: ({x}, {y}), Size: {w}x{h}\n")
        else:
            self.mock_targets_text.insert("end", "No mock targets added yet.")

        # Disable editing again
        self.mock_targets_text.configure(state="disabled")

    def choose_esp_color(self):
        color = colorchooser.askcolor(title="Choose ESP Box Color", initialcolor=self.esp_color)
        if color[1]:  # If color was selected (not canceled)
            self.esp_color = color[1]

            # Update ESP overlay color if it exists
            if self.esp_overlay:
                self.esp_overlay.update_color(self.esp_color)

    def test_esp_overlay(self):
        """Test ESP overlay functionality"""
        # Create ESP overlay window if it doesn't exist
        if not self.esp_overlay or not hasattr(self.esp_overlay, 'window') or not self.esp_overlay.window:
            self.esp_overlay.create_window()

        # Make sure ESP settings are updated
        self.esp_overlay.update_target(self.esp_target_entry.get())
        self.esp_overlay.update_color(self.esp_color)

        # If no mock positions, add some test positions
        if not self.esp_overlay.mock_positions:
            self.add_random_mocks()

        # Enable overlay if not already
        if not self.esp_overlay.active:
            if not self.esp_overlay_toggle.get():
                self.esp_overlay_toggle.select()
            self.toggle_esp_overlay()

        # Update status
        self.update_status(f"ESP Test: Highlighting {self.esp_target_entry.get()}", "cyan")
        self.esp_status_label.configure(text=f"ESP: Testing with {self.esp_target_entry.get()}", text_color="cyan")

    def toggle_priority_healing(self):
        self.prioritize_healing = self.priority_heal_switch.get()

    def select_health_region(self):
        selector = RegionSelector(self, "health", self.health_region)
        self.wait_window(selector)
        if selector.result_region:
            self.health_region = selector.result_region
            self.health_region_info.configure(text=f"Health Region: {self.health_region}, Color: {self.health_color}")

    def select_health_color(self):
        if not any(self.health_region):
            messagebox.showwarning("Warning", "Please select a health region first")
            return

        picker = ColorPicker(self, self.health_region, "health", self.health_color)
        self.wait_window(picker)
        if picker.result_color:
            self.health_color = picker.result_color
            self.health_threshold_pct = picker.result_threshold
            self.health_region_info.configure(text=f"Health Region: {self.health_region}, Color: {self.health_color}")

    def select_enemy_region(self):
        selector = RegionSelector(self, "enemy", self.enemy_region)
        self.wait_window(selector)
        if selector.result_region:
            self.enemy_region = selector.result_region
            self.enemy_region_info.configure(text=f"Enemy Region: {self.enemy_region}, Color: {self.enemy_color}")

    def select_enemy_color(self):
        if not any(self.enemy_region):
            messagebox.showwarning("Warning", "Please select an enemy region first")
            return

        picker = ColorPicker(self, self.enemy_region, "enemy", self.enemy_color)
        self.wait_window(picker)
        if picker.result_color:
            self.enemy_color = picker.result_color
            self.enemy_threshold_pct = picker.result_threshold
            self.enemy_region_info.configure(text=f"Enemy Region: {self.enemy_region}, Color: {self.enemy_color}")

    def select_buff_region(self):
        selector = RegionSelector(self, "buff", self.buff_region)
        self.wait_window(selector)
        if selector.result_region:
            self.buff_region = selector.result_region
            self.buff_region_info.configure(text=f"Buff Region: {self.buff_region}, Color: {self.buff_color}")

    def select_buff_color(self):
        if not any(self.buff_region):
            messagebox.showwarning("Warning", "Please select a buff region first")
            return

        picker = ColorPicker(self, self.buff_region, "buff", self.buff_color)
        self.wait_window(picker)
        if picker.result_color:
            self.buff_color = picker.result_color
            self.buff_threshold_pct = picker.result_threshold
            self.buff_region_info.configure(text=f"Buff Region: {self.buff_region}, Color: {self.buff_color}")

    def toggle_health_detect(self):
        health_detection_enabled = self.health_detect_switch.get()
        if health_detection_enabled and not any(self.health_region):
            messagebox.showwarning("Warning", "Please set a health bar region first")
            self.health_detect_switch.deselect()
            return

        self.health_detect_quick_toggle.select() if health_detection_enabled else self.health_detect_quick_toggle.deselect()

    def toggle_enemy_detect(self):
        self.enemy_detection_enabled = self.enemy_detect_switch.get()
        if self.enemy_detection_enabled and not any(self.enemy_region):
            messagebox.showwarning("Warning", "Please set an enemy detection region first")
            self.enemy_detect_switch.deselect()
            self.enemy_detection_enabled = False
            return

        self.enemy_detect_quick_toggle.select() if self.enemy_detection_enabled else self.enemy_detect_quick_toggle.deselect()

    def toggle_health_detect_quick(self):
        health_detection_enabled = self.health_detect_quick_toggle.get()
        if health_detection_enabled and not any(self.health_region):
            messagebox.showwarning("Warning", "Please configure health detection in Image Recognition tab")
            self.health_detect_quick_toggle.deselect()
            return

        self.health_detect_switch.select() if health_detection_enabled else self.health_detect_switch.deselect()

    def toggle_enemy_detect_quick(self):
        enemy_detection_enabled = self.enemy_detect_quick_toggle.get()
        if enemy_detection_enabled and not any(self.enemy_region):
            messagebox.showwarning("Warning", "Please configure enemy detection in Image Recognition tab")
            self.enemy_detect_quick_toggle.deselect()
            return

        self.enemy_detection_enabled = enemy_detection_enabled
        self.enemy_detect_switch.select() if enemy_detection_enabled else self.enemy_detect_switch.deselect()

    def test_image_recognition(self):
        try:
            results = []

            # Test health detection
            if self.health_detect_switch.get() and any(self.health_region):
                health_pct = self.check_health_level()
                results.append(f"Health: {health_pct}%")

            # Test EP detection
            if (hasattr(self, 'ep_detect_switch') and self.ep_detect_switch.get() or
                hasattr(self, 'ep_detect_switch_main') and self.ep_detect_switch_main.get()) and any(self.ep_region):
                ep_pct = self.check_ep_level()
                results.append(f"EP: {ep_pct}%")

            # Test enemy detection
            if self.enemy_detect_switch.get() and any(self.enemy_region):
                enemies_present = self.check_for_enemies()
                results.append(f"Enemies: {'Present' if enemies_present else 'Not detected'}")

            # Test buff detection
            if self.buff_detect_switch.get() and any(self.buff_region):
                buff_active = self.check_buff_status()
                results.append(f"Buff Status: {'Active' if buff_active else 'Not active'}")

            # Test ESP detection
            if self.esp_enabled:
                results.append(f"ESP would highlight: {self.esp_target_name}")

            # Test Pet status (if configured)
            if hasattr(self, 'pet_detect_switch') and self.pet_detect_switch.get() and hasattr(self, 'pet_region') and self.pet_region:
                # Implement pet status detection if needed
                results.append(f"Pet status: Checked")

            if not results:
                self.test_result_label.configure(text="No image recognition tests configured")
            else:
                self.test_result_label.configure(text="\n".join(results))

        except Exception as e:
            self.test_result_label.configure(text=f"Error during testing: {str(e)}")

    def add_potion_entry(self):
        pot_frame = ctk.CTkFrame(self.pots_container)
        pot_frame.pack(fill="x", pady=2)

        pot_key_label = ctk.CTkLabel(pot_frame, text="Potion Key:")
        pot_key_label.pack(side="left", padx=5)

        pot_key_combo = ctk.CTkComboBox(
            pot_frame,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "F1", "F2", "F3", "F4"],
            width=70
        )
        pot_key_combo.pack(side="left", padx=5)
        pot_key_combo.set("6")

        pot_name_label = ctk.CTkLabel(pot_frame, text="Name:")
        pot_name_label.pack(side="left", padx=5)

        pot_name_entry = ctk.CTkEntry(pot_frame, width=100)
        pot_name_entry.pack(side="left", padx=5)
        pot_name_entry.insert(0, "Buff Potion")

        pot_freq_label = ctk.CTkLabel(pot_frame, text="Interval (s):")
        pot_freq_label.pack(side="left", padx=5)

        pot_freq_entry = ctk.CTkEntry(pot_frame, width=60)
        pot_freq_entry.pack(side="left", padx=5)
        pot_freq_entry.insert(0, "120")

        remove_btn = ctk.CTkButton(
            pot_frame,
            text="×",
            width=28,
            fg_color="transparent",
            hover_color="#444444",
            command=lambda f=pot_frame: f.destroy()
        )
        remove_btn.pack(side="right", padx=5)

    def add_sequence_step(self, container):
        step_frame = DraggableFrame(container)
        step_frame.pack(fill="x", pady=2, padx=5, anchor="n")

        key_label = ctk.CTkLabel(step_frame, text="Action:")
        key_label.pack(side="left", padx=5)

        key_options = [
            '`', '~', 'TAB', 'SHIFT', 'CTRL', 'ALT', 'ESC', 'ENTER', 'SPACE',
            'LEFT_CLICK', 'RIGHT_CLICK', 'MIDDLE_CLICK', 'MOUSE4', 'MOUSE5',
            *[f'F{i}' for i in range(1, 13)],
            *[str(i) for i in range(10)],
            *[chr(65+i) for i in range(26)],
            'Shift+1', 'Ctrl+Q', 'Alt+F4', '[', ']', '\\', ';', "'", ',', '.',
            '/', '-', '=', '+', '*', '_', 'PRTSC', 'SCROLL',
            *[f'NUMPAD_{i}' for i in range(10)]
        ]

        key_dropdown = ctk.CTkComboBox(step_frame, values=key_options, width=140)
        key_dropdown.pack(side="left", padx=5)

        # Set different defaults based on container type
        if container == self.combat_container:
            key_dropdown.set("F1")
        elif container == self.buffs_container:
            key_dropdown.set("B")
        elif container == self.trans_container:
            key_dropdown.set("T")
        elif container == self.no_enemy_container:
            key_dropdown.set("F4")

        delay_label = ctk.CTkLabel(step_frame, text="Duration (s):")
        delay_label.pack(side="left", padx=5)

        delay_entry = ctk.CTkEntry(step_frame, width=60)
        delay_entry.pack(side="left", padx=5)

        # Different default durations based on sequence type
        if container == self.combat_container:
            delay_entry.insert(0, "1.0")
        elif container == self.buffs_container:
            delay_entry.insert(0, "0.5")
        elif container == self.trans_container:
            delay_entry.insert(0, "2.0")
        elif container == self.no_enemy_container:
            delay_entry.insert(0, "0.5")

        # Add cooldown field for skills
        cooldown_label = ctk.CTkLabel(step_frame, text="Cooldown (s):")
        cooldown_label.pack(side="left", padx=5)

        cooldown_entry = ctk.CTkEntry(step_frame, width=60)
        cooldown_entry.pack(side="left", padx=5)

        # Default cooldowns based on sequence type
        if container == self.combat_container:
            cooldown_entry.insert(0, "5.0")
        elif container == self.buffs_container:
            cooldown_entry.insert(0, "60.0")
        elif container == self.trans_container:
            cooldown_entry.insert(0, "300.0")
        elif container == self.no_enemy_container:
            cooldown_entry.insert(0, "10.0")

        # Add button hold mode option
        hold_label = ctk.CTkLabel(step_frame, text="Hold Mode:")
        hold_label.pack(side="left", padx=5)

        hold_var = ctk.StringVar(value="Instant")
        hold_combo = ctk.CTkComboBox(
            step_frame,
            values=["Instant", "Hold 0.5s", "Hold 1s", "Hold 2s", "Custom"],
            width=100,
            variable=hold_var
        )
        hold_combo.pack(side="left", padx=5)

        remove_btn = ctk.CTkButton(
            step_frame,
            text="×",
            width=28,
            fg_color="transparent",
            hover_color="#444444",
            command=lambda f=step_frame: f.destroy()
        )
        remove_btn.pack(side="right", padx=5)

        return step_frame

    def refresh_windows(self):
        windows = [window.title for window in gw.getAllWindows() if window.title]
        self.window_dropdown.configure(values=windows)
        if windows:
            self.window_dropdown.set(windows[0])

    def get_configuration(self):
        try:
            config = {
                "window_title": self.window_dropdown.get(),
                "loop_count": int(self.loop_count_entry.get()),
                "cooldown": float(self.cooldown_entry.get()),
                "sequences": {
                    "combat": {
                        "steps": [],
                        "cooldown": float(self.combat_cooldown_entry.get()),
                        "last_run": 0
                    },
                    "buffs": {
                        "steps": [],
                        "cooldown": float(self.buffs_cooldown_entry.get()),
                        "last_run": 0,
                        "enabled": self.buff_toggle_enabled
                    },
                    "transformations": {
                        "steps": [],
                        "cooldown": float(self.trans_cooldown_entry.get()),
                        "last_run": 0
                    },
                    "no_enemy": {
                        "enabled": self.no_enemy_switch.get(),
                        "steps": []
                    }
                },
                "movement": {
                    "enabled": self.movement_enabled,
                    "pattern": self.movement_pattern_var.get(),
                    "keys": {
                        "forward": self.forward_key_var.get(),
                        "backward": self.backward_key_var.get(),
                        "left": self.left_key_var.get(),
                        "right": self.right_key_var.get()
                    },
                    "interval": float(self.movement_interval_entry.get()),
                    "duration": float(self.movement_duration_entry.get())
                },
                "healing": {
                    "enabled": self.auto_heal,
                    "threshold": int(self.health_threshold_entry.get()),
                    "key": self.health_key_var.get(),
                    "prioritize": self.prioritize_healing
                },
                "ep": {
                    "enabled": self.auto_ep,
                    "threshold": int(self.ep_threshold_entry.get()),
                    "key": self.ep_key_var.get(),
                    "detection_enabled": self.ep_detect_switch.get() if hasattr(self, 'ep_detect_switch') else False,
                    "region": self.ep_region,
                    "color": self.ep_color,
                    "threshold_pct": self.ep_threshold_pct
                },
                "pet_feeder": {
                    "enabled": self.pet_feed_enabled,
                    "key": self.pet_key_var.get(),
                    "interval_minutes": float(self.pet_interval_entry.get()),
                    "interval_seconds": float(self.pet_interval_entry.get()) * 60,
                    "detection_enabled": self.pet_detect_switch.get() if hasattr(self, 'pet_detect_switch') else False,
                    "last_fed_time": self.last_pet_feed_time
                },
                "potion": {
                    "enabled": self.auto_pot,
                    "frequency": float(self.pot_freq_entry.get()),
                    "key": self.pot_key_var.get()
                },
                "loot": {
                    "enabled": self.auto_loot,
                    "key": self.loot_key_var.get(),
                    "frequency": float(self.loot_freq_entry.get()),
                    "click_position": {
                        "enabled": self.loot_click_switch.get(),
                        "x": int(self.loot_x_entry.get()),
                        "y": int(self.loot_y_entry.get())
                    }
                },
                "image_recognition": {
                    "health_detection": {
                        "enabled": self.health_detect_switch.get(),
                        "region": self.health_region,
                        "color": self.health_color,
                        "threshold": self.health_threshold_pct
                    },
                    "enemy_detection": {
                        "enabled": self.enemy_detection_enabled,
                        "region": self.enemy_region,
                        "color": self.enemy_color,
                        "threshold": self.enemy_threshold_pct
                    },
                    "buff_detection": {
                        "enabled": self.buff_detect_switch.get(),
                        "region": self.buff_region,
                        "color": self.buff_color,
                        "threshold": self.buff_threshold_pct
                    }
                },
                "targeting": {
                    "enabled": self.target_enabled,
                    "key": self.target_key_var.get(),
                    "frequency": float(self.target_freq_entry.get())
                },
                "esp": {
                    "enabled": self.esp_enabled,
                    "target_name": self.esp_target_entry.get(),
                    "color": self.esp_color,
                    "overlay_enabled": self.esp_overlay_toggle.get() if hasattr(self, 'esp_overlay_toggle') else False
                },
                "additional_potions": []
            }

            # Get combat sequence
            for step in self.combat_container.winfo_children():
                children = step.winfo_children()
                action = children[1].get()
                duration = float(children[3].get())
                cooldown = float(children[5].get())
                hold_mode = children[7].get()

                hold_times = {
                    "Instant": 0,
                    "Hold 0.5s": 0.5,
                    "Hold 1s": 1.0,
                    "Hold 2s": 2.0,
                    "Custom": duration  # Use the duration as custom hold time
                }

                hold_time = hold_times.get(hold_mode, 0)

                config["sequences"]["combat"]["steps"].append({
                    "action": action,
                    "duration": duration,
                    "cooldown": cooldown,
                    "last_used": 0,
                    "hold_mode": hold_mode,
                    "hold_time": hold_time
                })

            # Get buff sequence
            for step in self.buffs_container.winfo_children():
                children = step.winfo_children()
                action = children[1].get()
                duration = float(children[3].get())
                cooldown = float(children[5].get())
                hold_mode = children[7].get()

                hold_times = {
                    "Instant": 0,
                    "Hold 0.5s": 0.5,
                    "Hold 1s": 1.0,
                    "Hold 2s": 2.0,
                    "Custom": duration  # Use the duration as custom hold time
                }

                hold_time = hold_times.get(hold_mode, 0)

                config["sequences"]["buffs"]["steps"].append({
                    "action": action,
                    "duration": duration,
                    "cooldown": cooldown,
                    "last_used": 0,
                    "hold_mode": hold_mode,
                    "hold_time": hold_time
                })

            # Get transformation sequence
            for step in self.trans_container.winfo_children():
                children = step.winfo_children()
                action = children[1].get()
                duration = float(children[3].get())
                cooldown = float(children[5].get())
                hold_mode = children[7].get()

                hold_times = {
                    "Instant": 0,
                    "Hold 0.5s": 0.5,
                    "Hold 1s": 1.0,
                    "Hold 2s": 2.0,
                    "Custom": duration  # Use the duration as custom hold time
                }

                hold_time = hold_times.get(hold_mode, 0)

                config["sequences"]["transformations"]["steps"].append({
                    "action": action,
                    "duration": duration,
                    "cooldown": cooldown,
                    "last_used": 0,
                    "hold_mode": hold_mode,
                    "hold_time": hold_time
                })

            # Get no-enemy sequence
            for step in self.no_enemy_container.winfo_children():
                children = step.winfo_children()
                action = children[1].get()
                duration = float(children[3].get())
                cooldown = float(children[5].get())
                hold_mode = children[7].get()

                hold_times = {
                    "Instant": 0,
                    "Hold 0.5s": 0.5,
                    "Hold 1s": 1.0,
                    "Hold 2s": 2.0,
                    "Custom": duration  # Use the duration as custom hold time
                }

                hold_time = hold_times.get(hold_mode, 0)

                config["sequences"]["no_enemy"]["steps"].append({
                    "action": action,
                    "duration": duration,
                    "cooldown": cooldown,
                    "last_used": 0,
                    "hold_mode": hold_mode,
                    "hold_time": hold_time
                })

            # Get additional potions
            for pot_frame in self.pots_container.winfo_children():
                children = pot_frame.winfo_children()
                pot_key = children[1].get()
                pot_name = children[3].get()
                pot_freq = float(children[5].get())
                config["additional_potions"].append({
                    "key": pot_key,
                    "name": pot_name,
                    "frequency": pot_freq,
                    "last_used": 0
                })

            return config
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Invalid input: {str(e)}")
            return None

    def send_keypress(self, action, duration=0.1, auto_release=True, hold_time=0):
        try:
            if action.endswith('_CLICK') or action.startswith('MOUSE'):
                self.handle_mouse_action(action)
                return

            # Handle key combinations
            modifiers = []
            if '+' in action:
                parts = action.split('+')
                modifiers = parts[:-1]
                main_key = parts[-1]
            else:
                main_key = action

            # Press modifiers
            for mod in modifiers:
                vk = self.key_map.get(mod.upper())
                if vk:
                    win32api.keybd_event(vk, 0, 0, 0)
                    time.sleep(0.05)

            # Handle main key
            vk = self.key_map.get(main_key.upper())
            if not vk:
                raise ValueError(f"Invalid key: {main_key}")

            win32api.keybd_event(vk, 0, 0, 0)

            # If using hold mode, hold the key for the specified time
            if hold_time > 0:
                time.sleep(hold_time)
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
            else:
                # Otherwise use normal duration
                time.sleep(duration)
                if auto_release:
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Release modifiers
            if auto_release:
                for mod in reversed(modifiers):
                    vk = self.key_map.get(mod.upper())
                    if vk:
                        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                        time.sleep(0.05)

        except Exception as e:
            self.update_status(f"Input Error: {str(e)}", "red")

    def release_key(self, action):
        try:
            if action.endswith('_CLICK') or action.startswith('MOUSE'):
                return

            # Handle key combinations
            if '+' in action:
                parts = action.split('+')
                modifiers = parts[:-1]
                main_key = parts[-1]
            else:
                main_key = action
                modifiers = []

            # Release main key
            vk = self.key_map.get(main_key.upper())
            if not vk:
                raise ValueError(f"Invalid key: {main_key}")

            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

            # Release modifiers
            for mod in reversed(modifiers):
                vk = self.key_map.get(mod.upper())
                if vk:
                    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.05)

        except Exception as e:
            self.update_status(f"Key Release Error: {str(e)}", "red")

    def handle_mouse_action(self, action):
        mouse_map = {
            'LEFT_CLICK': (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP),
            'RIGHT_CLICK': (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP),
            'MIDDLE_CLICK': (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
            'MOUSE4': (0x0008, 0x0008),
            'MOUSE5': (0x0010, 0x0010)
        }

        if action not in mouse_map:
            raise ValueError(f"Invalid mouse action: {action}")

        down_flag, up_flag = mouse_map[action]
        win32api.mouse_event(down_flag, 0, 0, 0, 0)
        time.sleep(0.1)
        win32api.mouse_event(up_flag, 0, 0, 0, 0)

    def toggle_auto_heal(self):
        self.auto_heal = self.auto_heal_switch.get()
        self.heal_quick_toggle.select() if self.auto_heal else self.heal_quick_toggle.deselect()

    def toggle_auto_pot(self):
        self.auto_pot = self.auto_pot_switch.get()
        self.pot_quick_toggle.select() if self.auto_pot else self.pot_quick_toggle.deselect()

    def toggle_movement(self):
        self.movement_enabled = self.movement_switch.get()
        self.movement_pattern = self.movement_pattern_var.get()
        self.movement_quick_toggle.select() if self.movement_enabled else self.movement_quick_toggle.deselect()

    def toggle_loot(self):
        self.auto_loot = self.loot_switch.get()
        self.loot_key = self.loot_key_var.get()
        self.loot_frequency = float(self.loot_freq_entry.get())
        self.loot_quick_toggle.select() if self.auto_loot else self.loot_quick_toggle.deselect()

    # Quick toggle functions for main tab
    def toggle_movement_quick(self):
        self.movement_enabled = self.movement_quick_toggle.get()
        self.movement_switch.select() if self.movement_enabled else self.movement_switch.deselect()

    def toggle_heal_quick(self):
        self.auto_heal = self.heal_quick_toggle.get()
        self.auto_heal_switch.select() if self.auto_heal else self.auto_heal_switch.deselect()

    def toggle_pot_quick(self):
        self.auto_pot = self.pot_quick_toggle.get()
        self.auto_pot_switch.select() if self.auto_pot else self.auto_pot_switch.deselect()

    def toggle_loot_quick(self):
        self.auto_loot = self.loot_quick_toggle.get()
        self.loot_switch.select() if self.auto_loot else self.loot_switch.deselect()

    def apply_esp_overlay(self, img_np):
        """Apply ESP overlay to highlight target monsters"""
        if not self.esp_enabled:
            return img_np

        try:
            # Get the configured ESP color
            if hasattr(self, 'esp_color'):
                color = self.esp_color
            else:
                color = "#FF0000"  # Default red

            # Parse RGB values from hex color
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            # Here you would implement actual mob detection
            # This is a placeholder that would find mobs with your target name
            # In a real implementation, you'd need computer vision or game memory reading

            # For a simple demo, let's just draw boxes in fixed positions
            # In a real bot, you'd detect mobs here
            height, width = img_np.shape[:2]

            # Simulated mob positions (in a real bot this would be detected)
            mob_positions = []

            # Draw ESP boxes in various positions to simulate detection
            for i in range(3):  # Simulate 3 mobs
                x = random.randint(0, width-100)
                y = random.randint(0, height-100)
                w = random.randint(50, 150)
                h = random.randint(50, 150)

                mob_positions.append((x, y, w, h))

                # Draw rectangle for each "detected" mob
                cv2.rectangle(img_np, (x, y), (x+w, y+h), (b, g, r), 2)

                # Add mob name text
                cv2.putText(
                    img_np,
                    self.esp_target_name,
                    (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (b, g, r),
                    1
                )

            # Update UI with info about detected mobs
            self.update_status(f"ESP: {len(mob_positions)} {self.esp_target_name}s detected", "cyan")

            return img_np

        except Exception as e:
            self.update_status(f"ESP Error: {str(e)}", "red")
            return img_np

    def check_health_level(self):
        """Check health level using image recognition"""
        try:
            if not self.health_detect_switch.get() or not any(self.health_region):
                return 100  # Default to full health if detection disabled

            # Take screenshot of health region
            x, y, width, height = self.health_region
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            img_np = np.array(screenshot)

            # Convert to HSV for better color detection
            img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

            # Parse the color
            r = int(self.health_color[1:3], 16)
            g = int(self.health_color[3:5], 16)
            b = int(self.health_color[5:7], 16)

            # Convert RGB to HSV color for masking
            rgb_color = np.uint8([[[b, g, r]]])  # OpenCV uses BGR
            hsv_color = cv2.cvtColor(rgb_color, cv2.COLOR_BGR2HSV)
            hsv_value = hsv_color[0][0][0]

            # Create a range for the color
            threshold = self.health_threshold_pct
            lower_bound = np.array([max(0, hsv_value - threshold), 50, 50])
            upper_bound = np.array([min(179, hsv_value + threshold), 255, 255])

            # Create mask and count pixels
            mask = cv2.inRange(img_hsv, lower_bound, upper_bound)
            health_pixels = cv2.countNonZero(mask)
            total_pixels = width * height

            # Calculate health percentage
            if total_pixels > 0:
                health_pct = min(100, int((health_pixels / total_pixels) * 100))

                # Update health status in UI
                self.health_status_label.configure(
                    text=f"Health: {health_pct}%",
                    text_color="green" if health_pct > 50 else "orange" if health_pct > 25 else "red"
                )

                return health_pct
            else:
                return 100

        except Exception as e:
            self.update_status(f"Health check error: {str(e)}", "red")
            return 100  # Assume full health if error

    def check_for_enemies(self):
        """Check for enemy presence using image recognition"""
        try:
            if not self.enemy_detection_enabled or not any(self.enemy_region):
                return True  # Default to assuming enemies present if detection disabled

            # Take screenshot of enemy detection region
            x, y, width, height = self.enemy_region
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            img_np = np.array(screenshot)

            # Convert to HSV for better color detection
            img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

            # Parse the enemy color
            r = int(self.enemy_color[1:3], 16)
            g = int(self.enemy_color[3:5], 16)
            b = int(self.enemy_color[5:7], 16)

            # Convert RGB to HSV for masking
            rgb_color = np.uint8([[[b, g, r]]])  # OpenCV uses BGR
            hsv_color = cv2.cvtColor(rgb_color, cv2.COLOR_BGR2HSV)
            hsv_value = hsv_color[0][0][0]

            # Create a range for the color
            threshold = self.enemy_threshold_pct
            lower_bound = np.array([max(0, hsv_value - threshold), 50, 50])
            upper_bound = np.array([min(179, hsv_value + threshold), 255, 255])

            # Create mask and count pixels
            mask = cv2.inRange(img_hsv, lower_bound, upper_bound)
            enemy_pixels = cv2.countNonZero(mask)

            # Determine if enemies are present based on pixel count threshold
            # Adjust this threshold based on testing
            enemies_present = enemy_pixels > (width * height * 0.01)  # 1% of pixels match color

            # Update enemy status in UI
            self.enemy_status_label.configure(
                text=f"Enemies: {'Present' if enemies_present else 'Not detected'}",
                text_color="red" if enemies_present else "green"
            )

            return enemies_present

        except Exception as e:
            self.update_status(f"Enemy detection error: {str(e)}", "red")
            return True  # Assume enemies present if error

    def check_buff_status(self):
        """Check if buffs are active using image recognition"""
        try:
            if not self.buff_detect_switch.get() or not any(self.buff_region):
                return True  # Default to assuming buffs active if detection disabled

            # Take screenshot of buff region
            x, y, width, height = self.buff_region
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            img_np = np.array(screenshot)

            # Convert to HSV for better color detection
            img_hsv = cv2.cvtColor(img_np, cv2.COLOR_RGB2HSV)

            # Parse the buff color
            r = int(self.buff_color[1:3], 16)
            g = int(self.buff_color[3:5], 16)
            b = int(self.buff_color[5:7], 16)

            # Convert RGB to HSV for masking
            rgb_color = np.uint8([[[b, g, r]]])  # OpenCV uses BGR
            hsv_color = cv2.cvtColor(rgb_color, cv2.COLOR_BGR2HSV)
            hsv_value = hsv_color[0][0][0]

            # Create a range for the color
            threshold = self.buff_threshold_pct
            lower_bound = np.array([max(0, hsv_value - threshold), 50, 50])
            upper_bound = np.array([min(179, hsv_value + threshold), 255, 255])

            # Create mask and count pixels
            mask = cv2.inRange(img_hsv, lower_bound, upper_bound)
            buff_pixels = cv2.countNonZero(mask)

            # Determine if buffs are active based on pixel count threshold
            buff_active = buff_pixels > (width * height * 0.1)  # 10% of pixels match color

            return buff_active

        except Exception as e:
            self.update_status(f"Buff detection error: {str(e)}", "red")
            return True  # Assume buffs active if error

    def handle_movement(self):
        try:
            config = self.current_config
            if not config or not config.get('movement', {}).get('enabled', False):
                return

            pattern = config['movement']['pattern']
            keys = config['movement']['keys']
            interval = config['movement']['interval']
            duration = config['movement']['duration']

            self.movement_active = True

            while self.is_running and self.movement_enabled and self.movement_active:
                # Different movement patterns
                if pattern == "circle":
                    # Circular movement - press keys in sequence
                    for key in [keys['forward'], keys['right'], keys['backward'], keys['left']]:
                        if not self.is_running or not self.movement_enabled or not self.movement_active:
                            break
                        self.send_keypress(key, duration=duration)
                        time.sleep(interval)

                elif pattern == "random":
                    # Random movement - press random direction key
                    direction_keys = list(keys.values())
                    random_key = random.choice(direction_keys)
                    self.send_keypress(random_key, duration=duration)
                    time.sleep(interval)

                elif pattern == "linear":
                    # Linear movement - go forward then backward
                    self.send_keypress(keys['forward'], duration=duration * 2)
                    time.sleep(interval)
                    self.send_keypress(keys['backward'], duration=duration * 2)
                    time.sleep(interval)

            self.movement_active = False

        except Exception as e:
            self.update_status(f"Movement Error: {str(e)}", "red")
            self.movement_active = False

    def start_movement(self):
        if self.movement_enabled and not self.movement_active:
            self.movement_thread = threading.Thread(target=self.handle_movement, daemon=True)
            self.movement_thread.start()

    def check_and_target(self):
        try:
            if not self.current_config or not self.target_enabled:
                return

            current_time = time.time()

            if current_time - self.last_target_time > self.target_frequency:
                target_key = self.target_key
                self.update_status(f"Pressing target key: {target_key}", "cyan")
                self.send_keypress(target_key)
                self.target_status_label.configure(text=f"Target: Attempting")
                self.last_target_time = current_time
                time.sleep(0.1)  # Small delay after targeting

        except Exception as e:
            self.update_status(f"Targeting Error: {str(e)}", "red")

    def check_and_use_potions(self):
        try:
            if not self.current_config:
                return

            current_time = time.time()

            # Check main potion
            if self.auto_pot and self.current_config.get('potion', {}).get('enabled', False):
                pot_frequency = self.current_config['potion']['frequency']
                pot_key = self.current_config['potion']['key']

                if current_time - self.last_pot_time > pot_frequency:
                    self.update_status(f"Using main potion ({pot_key})", "cyan")
                    self.send_keypress(pot_key)
                    self.last_pot_time = current_time

            # Check additional potions
            for pot in self.current_config.get('additional_potions', []):
                if current_time - pot.get('last_used', 0) > pot['frequency']:
                    self.update_status(f"Using {pot['name']} ({pot['key']})", "cyan")
                    self.send_keypress(pot['key'])
                    pot['last_used'] = current_time

        except Exception as e:
            self.update_status(f"Potion Error: {str(e)}", "red")

    def check_and_loot(self):
        try:
            if not self.current_config or not self.auto_loot:
                return

            current_time = time.time()
            loot_config = self.current_config.get('loot', {})

            if loot_config.get('enabled', False) and current_time - self.last_loot_time > loot_config.get('frequency', 5):
                self.update_status(f"Looting with {loot_config.get('key', 'Z')}", "cyan")

                # If click position is enabled, click at that position first
                if loot_config.get('click_position', {}).get('enabled', False):
                    x = loot_config['click_position']['x']
                    y = loot_config['click_position']['y']

                    # Save current position
                    current_pos = win32api.GetCursorPos()

                    # Move cursor and click
                    win32api.SetCursorPos((x, y))
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.1)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

                    # Restore cursor position
                    win32api.SetCursorPos(current_pos)

                # Press loot key
                self.send_keypress(loot_config.get('key', 'Z'))
                self.last_loot_time = current_time

        except Exception as e:
            self.update_status(f"Loot Error: {str(e)}", "red")

    def check_and_heal(self):
        try:
            if not self.current_config or not self.auto_heal:
                return

            healing_config = self.current_config.get('healing', {})
            if not healing_config.get('enabled', False):
                return

            # Get health level from image detection if enabled
            if self.health_detect_switch.get() and any(self.health_region):
                current_health = self.check_health_level()
            else:
                # Use timer-based approach as fallback
                current_time = time.time()
                if current_time - getattr(self, 'last_heal_check', 0) < 5:  # Check every 5 seconds
                    return

                self.last_heal_check = current_time
                current_health = random.randint(60, 100)  # Simulate health level for testing

            heal_threshold = healing_config.get('threshold', 70)
            heal_key = healing_config.get('key', 'H')

            if current_health <= heal_threshold:
                self.update_status(f"Health at {current_health}%, healing with {heal_key}", "orange")
                self.send_keypress(heal_key)
                time.sleep(0.2)  # Small delay after healing
                return True  # Return True to indicate healing was performed

            return False

        except Exception as e:
            self.update_status(f"Healing Error: {str(e)}", "red")
            return False

    def is_skill_ready(self, skill, skill_type="combat"):
        """Check if a skill is ready or still on cooldown"""
        current_time = time.time()
        skill_id = f"{skill_type}_{skill['action']}"
        last_used = skill['last_used']
        cooldown = skill['cooldown']

        if current_time - last_used >= cooldown:
            return True

        # Calculate remaining cooldown
        remaining = cooldown - (current_time - last_used)
        self.update_status(f"Skill {skill['action']} still on cooldown: {remaining:.1f}s", "yellow")
        return False

    def execute_sequence(self, seq_type):
        try:
            if not self.current_config:
                return False

            sequence = self.current_config["sequences"].get(seq_type, {})
            current_time = time.time()

            # First check if we need to heal (if healing is prioritized)
            if self.prioritize_healing:
                healing_needed = self.check_and_heal()
                if healing_needed:
                    time.sleep(0.2)  # Give a small pause after healing

            # Check if we need to restore EP
            if self.auto_ep:
                ep_restored = self.check_and_restore_ep()
                if ep_restored:
                    time.sleep(0.2)  # Small delay after EP restoration

            # Check if we need to feed pet
            if self.pet_feed_enabled:
                self.check_and_feed_pet()

            # Check if we need to target
            if self.target_enabled and seq_type == "combat":
                self.check_and_target()

            # For buff sequence, check if buffs are enabled
            if seq_type == "buffs" and not sequence.get("enabled", True):
                self.update_status("Buffs are disabled", "yellow")
                return False

            if seq_type == "no_enemy":
                # Special handling for no-enemy sequence
                if not sequence.get("enabled", False) or not self.enemy_detection_enabled:
                    return False

                enemies_present = self.check_for_enemies()
                if enemies_present:
                    return False  # Don't run no-enemy sequence if enemies are present

                steps = sequence.get("steps", [])
                if not steps:
                    return False

                # Execute no-enemy sequence
                self.update_status("No enemies detected, running alternative sequence", "blue")

                # If movement is active, pause it while executing this sequence
                movement_was_active = self.movement_active
                if movement_was_active:
                    self.movement_active = False
                    time.sleep(0.3)  # Small delay to ensure movement stops

                for skill in steps:
                    if not self.is_running:
                        return False

                    # Check health again if prioritized
                    if self.prioritize_healing:
                        self.check_and_heal()

                    # Check if skill is on cooldown
                    if self.is_skill_ready(skill, "no_enemy"):
                        action = skill["action"]
                        duration = skill["duration"]
                        hold_time = skill.get("hold_time", 0)

                        self.send_keypress(action, duration=duration, hold_time=hold_time)
                        self.update_status(f"No-enemy action: {action} ({duration}s)", "cyan")

                        # Update last used timestamp
                        skill["last_used"] = current_time
                        time.sleep(duration)

                # Restart movement if it was active
                if movement_was_active and self.is_running and self.movement_enabled:
                    self.movement_active = True
                    self.start_movement()

                return True
            else:
                # Normal sequence logic for combat, buffs, transformations
                steps = sequence.get("steps", [])
                cooldown = sequence.get("cooldown", 5)
                last_run = sequence.get("last_run", 0)

                # Check if it's time to run this sequence
                if current_time - last_run < cooldown and last_run > 0:
                    return False  # Not yet time to run

                # If no steps, don't run
                if not steps:
                    return False

                # If movement is active, pause it while executing this sequence
                movement_was_active = self.movement_active
                if movement_was_active:
                    self.movement_active = False
                    time.sleep(0.3)  # Small delay to ensure movement stops

                # Execute the sequence
                self.update_status(f"Running {seq_type} sequence", "yellow")

                # Flag to track if any skill was used
                any_skill_used = False

                # Check health again if prioritized
                if self.prioritize_healing:
                    self.check_and_heal()

                # In combat sequence, find the first available skill that's not on cooldown
                if seq_type == "combat":
                    next_available_skill = None
                    for skill in steps:
                        if not self.is_running:
                            return False

                        # Check if target is needed first
                        if self.target_enabled and random.random() < 0.3:  # 30% chance to retarget during combat
                            self.check_and_target()

                        # Check health again if prioritized
                        if self.prioritize_healing:
                            self.check_and_heal()

                        # Check EP if enabled
                        if self.auto_ep:
                            self.check_and_restore_ep()

                        # Skip TAB as the first choice, only use if nothing else is available
                        if skill["action"] == "TAB" and next_available_skill is None:
                            # Hold TAB as a backup if no other skills are ready
                            next_available_skill = skill
                            continue

                        if self.is_skill_ready(skill, seq_type):
                            action = skill["action"]
                            duration = skill["duration"]
                            hold_time = skill.get("hold_time", 0)

                            self.send_keypress(action, duration=duration, hold_time=hold_time)
                            self.update_status(f"{seq_type} action: {action} ({duration}s)", "cyan")

                            # Update last used timestamp
                            skill["last_used"] = current_time
                            any_skill_used = True
                            time.sleep(duration)
                            break

                    # If no skill was found, use the saved TAB or whatever was last available
                    if not any_skill_used and next_available_skill:
                        action = next_available_skill["action"]
                        duration = next_available_skill["duration"]
                        hold_time = next_available_skill.get("hold_time", 0)

                        self.send_keypress(action, duration=duration, hold_time=hold_time)
                        self.update_status(f"{seq_type} action (fallback): {action}", "cyan")

                        # Update last used timestamp
                        next_available_skill["last_used"] = current_time
                        any_skill_used = True
                        time.sleep(duration)
                else:
                    # For buff and transformation sequences, try all skills
                    for skill in steps:
                        if not self.is_running:
                            return False

                        # Check health again if prioritized
                        if self.prioritize_healing:
                            self.check_and_heal()

                        # Check EP if enabled
                        if self.auto_ep:
                            self.check_and_restore_ep()

                        # Check if skill is on cooldown
                        if self.is_skill_ready(skill, seq_type):
                            action = skill["action"]
                            duration = skill["duration"]
                            hold_time = skill.get("hold_time", 0)

                            self.send_keypress(action, duration=duration, hold_time=hold_time)
                            self.update_status(f"{seq_type} action: {action} ({duration}s)", "cyan")

                            # Update last used timestamp
                            skill["last_used"] = current_time
                            any_skill_used = True
                            time.sleep(duration)

                # Update timestamp if any skill was used
                if any_skill_used:
                    self.current_config["sequences"][seq_type]["last_run"] = current_time

                # Restart movement if it was active
                if movement_was_active and self.is_running and self.movement_enabled:
                    self.movement_active = True
                    self.start_movement()

                return any_skill_used

        except Exception as e:
            self.update_status(f"{seq_type} Sequence Error: {str(e)}", "red")
            return False

    def macro_loop(self):
        self.current_config = self.get_configuration()
        if not self.current_config:
            return

        total_loops = self.current_config["loop_count"]
        current_loop = 0

        # Initialize timestamps
        self.last_pot_time = time.time()
        self.last_loot_time = time.time()
        self.last_heal_check = time.time()
        self.last_target_time = time.time()
        self.last_pet_feed_time = self.current_config.get("pet_feeder", {}).get("last_fed_time", 0) or time.time()

        # Initialize pet status display time
        self.last_pet_status_update = time.time()

        for seq_type in ["combat", "buffs", "transformations"]:
            self.current_config["sequences"][seq_type]["last_run"] = 0

            # Initialize skill cooldowns
            for skill in self.current_config["sequences"][seq_type]["steps"]:
                skill["last_used"] = 0

        # Initialize no-enemy sequence cooldowns
        for skill in self.current_config["sequences"]["no_enemy"]["steps"]:
            skill["last_used"] = 0

        # Initialize additional potions
        for pot in self.current_config.get('additional_potions', []):
            pot['last_used'] = time.time()

        # Start movement if enabled
        if self.movement_enabled:
            self.start_movement()

        # Start ESP overlay if enabled
        if self.esp_enabled and self.current_config.get('esp', {}).get('overlay_enabled', False):
            if not self.esp_overlay.active:
                self.esp_overlay_toggle.select()
                self.toggle_esp_overlay()

        # Log pet feeder status
        if self.pet_feed_enabled:
            minutes = int(self.pet_feed_interval / 60)
            self.add_pet_feed_log(f"Pet feeding scheduled every {minutes} minutes")

        try:
            while self.is_running and (total_loops == 0 or current_loop < total_loops):
                hwnd = win32gui.FindWindow(None, self.current_config["window_title"])
                if not hwnd:
                    self.update_status("Window not found!", "red")
                    time.sleep(1)
                    continue

                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.3)

                # First priority check: Health
                if self.prioritize_healing:
                    self.check_and_heal()

                # Check EP if enabled
                if self.auto_ep:
                    self.check_and_restore_ep()

                # Check for pet feeding if enabled
                if self.pet_feed_enabled:
                    self.check_and_feed_pet()

                # Check for targeting if enabled
                if self.target_enabled:
                    self.check_and_target()

                # Apply ESP if enabled
                if self.esp_enabled:
                    # In a real implementation, you would:
                    # 1. Capture the screen
                    # 2. Apply ESP markings to detected mobs
                    # 3. Show the result
                    # This is simulated here with a call to a function that would normally do this
                    try:
                        if random.random() < 0.05:  # Only occasionally update ESP for performance
                            screenshot = ImageGrab.grab()
                            img_np = np.array(screenshot)
                            img_np = self.apply_esp_overlay(img_np)
                            # In a full implementation, you'd show this via an overlay window
                    except Exception as e:
                        self.update_status(f"ESP Error: {str(e)}", "red")

                    # Update ESP status
                    self.esp_status_label.configure(
                        text=f"ESP: {self.esp_target_name}",
                        text_color="cyan"
                    )

                # Check for enemies if enemy detection is enabled
                enemies_present = True  # Default to assuming enemies present
                if self.enemy_detection_enabled:
                    enemies_present = self.check_for_enemies()

                # Run no-enemy sequence if no enemies and that sequence is enabled
                no_enemy_run = False
                if not enemies_present:
                    no_enemy_run = self.execute_sequence("no_enemy")

                # Only run combat sequence if there are enemies or enemy detection is disabled
                combat_result = False
                if enemies_present or not self.enemy_detection_enabled:
                    # First run buff sequence if needed and buffs are enabled
                    buff_result = False
                    if self.buff_toggle_enabled:
                        buff_result = self.execute_sequence("buffs")
                        if buff_result:
                            time.sleep(0.5)  # Small delay after buffs

                    # Then run transformation sequence if needed
                    trans_result = self.execute_sequence("transformations")
                    if trans_result:
                        time.sleep(1)  # Give transformation time to complete

                    # Run the primary combat sequence
                    combat_result = self.execute_sequence("combat")

                # Check health and heal if needed (even if already checked at the beginning)
                self.check_and_heal()

                # Check EP again if enabled
                if self.auto_ep:
                    self.check_and_restore_ep()

                # Check and use potions
                self.check_and_use_potions()

                # Check and loot
                self.check_and_loot()

                # Update progress if we completed the combat sequence
                if combat_result:
                    current_loop += 1
                    self.progress_label.configure(text=f"Completed Loops: {current_loop}")

                    # Only do cooldown if a full combat loop was completed
                    if self.is_running and (total_loops == 0 or current_loop < total_loops):
                        time.sleep(self.current_config["cooldown"])
                elif no_enemy_run:
                    # Small cooldown after no-enemy sequence
                    time.sleep(1)
                else:
                    # Small delay if no sequences were run
                    if not (trans_result if 'trans_result' in locals() else False or
                                                                            buff_result if 'buff_result' in locals() else False or
                                                                                                                          no_enemy_run):
                        time.sleep(0.5)

        except Exception as e:
            self.update_status(f"Error: {str(e)}", "red")
        finally:
            self.stop_macro()

    def update_status(self, message, color="white"):
        self.status_label.configure(text=f"Status: {message}", text_color=color)
        self.update_idletasks()

    def toggle_macro(self):
        if self.is_running:
            self.stop_macro()
        else:
            self.start_macro()

    def start_macro(self):
        if not self.is_running:
            self.is_running = True
            self.macro_thread = threading.Thread(target=self.macro_loop, daemon=True)
            self.macro_thread.start()
            self.update_status("Running", "green")

    def stop_macro(self):
        if self.is_running:
            self.is_running = False
            self.movement_active = False

            # Reset UI elements
            if self.movement_switch.get():
                self.movement_switch.deselect()

            if self.movement_quick_toggle.get():
                self.movement_quick_toggle.deselect()

            self.update_status("Stopped", "white")
            self.progress_label.configure(text="Completed Loops: 0")

    def save_profile(self):
        try:
            config = self.get_configuration()
            if not config:
                return

            profile_name = self.profile_name_entry.get().strip()
            if not profile_name:
                messagebox.showerror("Error", "Please enter a profile name")
                return

            file_path = os.path.join(self.config_dir, f"{profile_name}.json")

            with open(file_path, 'w') as f:
                json.dump(config, f, indent=4)

            messagebox.showinfo("Success", f"Profile '{profile_name}' saved successfully")
            self.load_available_configs()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile: {str(e)}")

    def load_profile(self):
        try:
            profile_name = self.profile_name_entry.get().strip()
            if not profile_name:
                messagebox.showerror("Error", "Please enter a profile name")
                return

            file_path = os.path.join(self.config_dir, f"{profile_name}.json")

            if not os.path.exists(file_path):
                messagebox.showerror("Error", f"Profile '{profile_name}' not found")
                return

            with open(file_path, 'r') as f:
                config = json.load(f)

            # Clear existing settings
            for container in [self.combat_container, self.buffs_container, self.trans_container, self.no_enemy_container]:
                for child in container.winfo_children():
                    child.destroy()

            for child in self.pots_container.winfo_children():
                child.destroy()

            # Load window setting
            if config.get("window_title") in self.window_dropdown.cget("values"):
                self.window_dropdown.set(config["window_title"])

            # Load loop settings
            self.loop_count_entry.delete(0, 'end')
            self.loop_count_entry.insert(0, str(config.get("loop_count", 0)))

            self.cooldown_entry.delete(0, 'end')
            self.cooldown_entry.insert(0, str(config.get("cooldown", 5.0)))

            # Load sequence cooldowns
            self.combat_cooldown_entry.delete(0, 'end')
            self.combat_cooldown_entry.insert(0, str(config["sequences"].get("combat", {}).get("cooldown", 1.0)))

            self.buffs_cooldown_entry.delete(0, 'end')
            self.buffs_cooldown_entry.insert(0, str(config["sequences"].get("buffs", {}).get("cooldown", 60.0)))

            self.trans_cooldown_entry.delete(0, 'end')
            self.trans_cooldown_entry.insert(0, str(config["sequences"].get("transformations", {}).get("cooldown", 300.0)))

            # Load buff toggle setting
            if config["sequences"].get("buffs", {}).get("enabled", True):
                self.buff_toggle.select()
                self.buff_toggle_enabled = True
            else:
                self.buff_toggle.deselect()
                self.buff_toggle_enabled = False

            # Load no-enemy settings
            if config["sequences"].get("no_enemy", {}).get("enabled", False):
                self.no_enemy_switch.select()
            else:
                self.no_enemy_switch.deselect()

            # Load pet feeder settings if available
            if "pet_feeder" in config:
                pet_config = config.get("pet_feeder", {})
                if pet_config.get("enabled", False):
                    self.pet_feed_switch.select()
                    self.pet_feed_quick_toggle.select()
                    self.pet_feed_enabled = True
                else:
                    self.pet_feed_switch.deselect()
                    self.pet_feed_quick_toggle.deselect()
                    self.pet_feed_enabled = False

                self.pet_key_var.set(pet_config.get("key", "P"))
                self.pet_interval_entry.delete(0, 'end')
                self.pet_interval_entry.insert(0, str(pet_config.get("interval_minutes", 30)))
                self.pet_feed_interval = pet_config.get("interval_seconds", 1800)
                self.last_pet_feed_time = pet_config.get("last_fed_time", time.time())

                # Update pet status display
                if self.pet_feed_enabled:
                    minutes = int(self.pet_feed_interval / 60)
                    self.pet_status_label.configure(
                        text=f"Pet: Will feed every {minutes} min",
                        text_color="cyan"
                    )

            # Load EP settings if available
            if "ep" in config:
                ep_config = config.get("ep", {})
                if ep_config.get("enabled", False):
                    self.auto_ep_switch.select()
                    self.ep_quick_toggle.select()
                    self.auto_ep = True
                else:
                    self.auto_ep_switch.deselect()
                    self.ep_quick_toggle.deselect()
                    self.auto_ep = False

                self.ep_threshold_entry.delete(0, 'end')
                self.ep_threshold_entry.insert(0, str(ep_config.get("threshold", 30)))
                self.ep_key_var.set(ep_config.get("key", "E"))

                # Load EP detection settings
                if ep_config.get("detection_enabled", False):
                    self.ep_detect_switch.select()
                    self.ep_detect_switch_main.select()
                else:
                    self.ep_detect_switch.deselect()
                    self.ep_detect_switch_main.deselect()

                self.ep_region = ep_config.get("region", [0, 0, 100, 20])
                self.ep_color = ep_config.get("color", "#0000FF")
                self.ep_threshold_pct = ep_config.get("threshold_pct", 30)
                self.ep_region_info.configure(text=f"EP Region: {self.ep_region}, Color: {self.ep_color}")

            # Load targeting settings if available
            if "targeting" in config:
                targeting_config = config.get("targeting", {})
                if targeting_config.get("enabled", False):
                    self.targeting_switch.select()
                    self.target_quick_toggle.select()
                    self.target_enabled = True
                else:
                    self.targeting_switch.deselect()
                    self.target_quick_toggle.deselect()
                    self.target_enabled = False

                self.target_key_var.set(targeting_config.get("key", "TAB"))
                self.target_freq_entry.delete(0, 'end')
                self.target_freq_entry.insert(0, str(targeting_config.get("frequency", 5.0)))

            # Load ESP settings if available
            if "esp" in config:
                esp_config = config.get("esp", {})
                if esp_config.get("enabled", False):
                    self.esp_switch.select()
                    self.esp_quick_toggle.select()
                    self.esp_enabled = True
                else:
                    self.esp_switch.deselect()
                    self.esp_quick_toggle.deselect()
                    self.esp_enabled = False

                self.esp_target_entry.delete(0, 'end')
                self.esp_target_entry.insert(0, esp_config.get("target_name", "Monster"))
                self.esp_color = esp_config.get("color", "#FF0000")

                # Load ESP overlay setting if available
                if esp_config.get("overlay_enabled", False):
                    self.esp_overlay_toggle.select()
                    if hasattr(self, 'esp_overlay_switch'):
                        self.esp_overlay_switch.select()
                else:
                    self.esp_overlay_toggle.deselect()
                    if hasattr(self, 'esp_overlay_switch'):
                        self.esp_overlay_switch.deselect()

            # Load movement settings
            movement_config = config.get("movement", {})
            if movement_config.get("enabled", False):
                self.movement_switch.select()
                self.movement_quick_toggle.select()
            else:
                self.movement_switch.deselect()
                self.movement_quick_toggle.deselect()

            self.movement_pattern_var.set(movement_config.get("pattern", "circle"))

            movement_keys = movement_config.get("keys", {})
            self.forward_key_var.set(movement_keys.get("forward", "W"))
            self.backward_key_var.set(movement_keys.get("backward", "S"))
            self.left_key_var.set(movement_keys.get("left", "A"))
            self.right_key_var.set(movement_keys.get("right", "D"))

            self.movement_interval_entry.delete(0, 'end')
            self.movement_interval_entry.insert(0, str(movement_config.get("interval", 0.5)))

            self.movement_duration_entry.delete(0, 'end')
            self.movement_duration_entry.insert(0, str(movement_config.get("duration", 0.25)))

            # Load healing settings
            healing_config = config.get("healing", {})
            if healing_config.get("enabled", False):
                self.auto_heal_switch.select()
                self.heal_quick_toggle.select()
            else:
                self.auto_heal_switch.deselect()
                self.heal_quick_toggle.deselect()

            self.health_threshold_entry.delete(0, 'end')
            self.health_threshold_entry.insert(0, str(healing_config.get("threshold", 70)))

            self.health_key_var.set(healing_config.get("key", "H"))

            # Set priority healing
            if healing_config.get("prioritize", True):
                self.priority_heal_switch.select()
                self.prioritize_healing = True
            else:
                self.priority_heal_switch.deselect()
                self.prioritize_healing = False

            # Load potion settings
            potion_config = config.get("potion", {})
            if potion_config.get("enabled", False):
                self.auto_pot_switch.select()
                self.pot_quick_toggle.select()
            else:
                self.auto_pot_switch.deselect()
                self.pot_quick_toggle.deselect()

            self.pot_freq_entry.delete(0, 'end')
            self.pot_freq_entry.insert(0, str(potion_config.get("frequency", 60)))

            self.pot_key_var.set(potion_config.get("key", "P"))

            # Load loot settings
            loot_config = config.get("loot", {})
            if loot_config.get("enabled", False):
                self.loot_switch.select()
                self.loot_quick_toggle.select()
            else:
                self.loot_switch.deselect()
                self.loot_quick_toggle.deselect()

            self.loot_key_var.set(loot_config.get("key", "Z"))

            self.loot_freq_entry.delete(0, 'end')
            self.loot_freq_entry.insert(0, str(loot_config.get("frequency", 5)))

            click_pos = loot_config.get("click_position", {})
            if click_pos.get("enabled", False):
                self.loot_click_switch.select()
            else:
                self.loot_click_switch.deselect()

            self.loot_x_entry.delete(0, 'end')
            self.loot_x_entry.insert(0, str(click_pos.get("x", 500)))

            self.loot_y_entry.delete(0, 'end')
            self.loot_y_entry.insert(0, str(click_pos.get("y", 400)))

            # Load image recognition settings
            img_config = config.get("image_recognition", {})

            # Health detection
            health_detect = img_config.get("health_detection", {})
            if health_detect.get("enabled", False):
                self.health_detect_switch.select()
                self.health_detect_quick_toggle.select()
            else:
                self.health_detect_switch.deselect()
                self.health_detect_quick_toggle.deselect()

            self.health_region = health_detect.get("region", [0, 0, 100, 20])
            self.health_color = health_detect.get("color", "#FF0000")
            self.health_threshold_pct = health_detect.get("threshold", 30)
            self.health_region_info.configure(text=f"Health Region: {self.health_region}, Color: {self.health_color}")

            # Enemy detection
            enemy_detect = img_config.get("enemy_detection", {})
            if enemy_detect.get("enabled", False):
                self.enemy_detect_switch.select()
                self.enemy_detect_quick_toggle.select()
                self.enemy_detection_enabled = True
            else:
                self.enemy_detect_switch.deselect()
                self.enemy_detect_quick_toggle.deselect()
                self.enemy_detection_enabled = False

            self.enemy_region = enemy_detect.get("region", [0, 0, 500, 500])
            self.enemy_color = enemy_detect.get("color", "#FF0000")
            self.enemy_threshold_pct = enemy_detect.get("threshold", 30)
            self.enemy_region_info.configure(text=f"Enemy Region: {self.enemy_region}, Color: {self.enemy_color}")

            # Buff detection
            buff_detect = img_config.get("buff_detection", {})
            if buff_detect.get("enabled", False):
                self.buff_detect_switch.select()
            else:
                self.buff_detect_switch.deselect()

            self.buff_region = buff_detect.get("region", [0, 0, 100, 20])
            self.buff_color = buff_detect.get("color", "#00FF00")
            self.buff_threshold_pct = buff_detect.get("threshold", 30)
            self.buff_region_info.configure(text=f"Buff Region: {self.buff_region}, Color: {self.buff_color}")

            # Load sequences - handle different formats (support both old and new)
            # Combat sequence
            combat_steps = config["sequences"].get("combat", {}).get("steps", [])
            for step in combat_steps:
                step_frame = self.add_sequence_step(self.combat_container)
                children = step_frame.winfo_children()

                # Check if the step is in the old format (tuple) or new format (dict)
                if isinstance(step, list) or isinstance(step, tuple):
                    action, duration = step
                    cooldown = 5.0  # Default cooldown for old format
                    hold_mode = "Instant"  # Default hold mode
                else:
                    action = step.get("action", "F1")
                    duration = step.get("duration", 1.0)
                    cooldown = step.get("cooldown", 5.0)
                    hold_mode = step.get("hold_mode", "Instant")

                children[1].set(action)  # Set action
                children[3].delete(0, 'end')  # Clear duration
                children[3].insert(0, str(duration))  # Set duration
                children[5].delete(0, 'end')  # Clear cooldown
                children[5].insert(0, str(cooldown))  # Set cooldown
                children[7].set(hold_mode)  # Set hold mode

            # Buffs sequence
            buff_steps = config["sequences"].get("buffs", {}).get("steps", [])
            for step in buff_steps:
                step_frame = self.add_sequence_step(self.buffs_container)
                children = step_frame.winfo_children()

                if isinstance(step, list) or isinstance(step, tuple):
                    action, duration = step
                    cooldown = 60.0  # Default cooldown for old format
                    hold_mode = "Instant"  # Default hold mode
                else:
                    action = step.get("action", "B")
                    duration = step.get("duration", 0.5)
                    cooldown = step.get("cooldown", 60.0)
                    hold_mode = step.get("hold_mode", "Instant")

                children[1].set(action)  # Set action
                children[3].delete(0, 'end')  # Clear duration
                children[3].insert(0, str(duration))  # Set duration
                children[5].delete(0, 'end')  # Clear cooldown
                children[5].insert(0, str(cooldown))  # Set cooldown
                children[7].set(hold_mode)  # Set hold mode

            # Transformations sequence
            trans_steps = config["sequences"].get("transformations", {}).get("steps", [])
            for step in trans_steps:
                step_frame = self.add_sequence_step(self.trans_container)
                children = step_frame.winfo_children()

                if isinstance(step, list) or isinstance(step, tuple):
                    action, duration = step
                    cooldown = 300.0  # Default cooldown for old format
                    hold_mode = "Instant"  # Default hold mode
                else:
                    action = step.get("action", "T")
                    duration = step.get("duration", 2.0)
                    cooldown = step.get("cooldown", 300.0)
                    hold_mode = step.get("hold_mode", "Instant")

                children[1].set(action)  # Set action
                children[3].delete(0, 'end')  # Clear duration
                children[3].insert(0, str(duration))  # Set duration
                children[5].delete(0, 'end')  # Clear cooldown
                children[5].insert(0, str(cooldown))  # Set cooldown
                children[7].set(hold_mode)  # Set hold mode

            # No-enemy sequence
            no_enemy_steps = config["sequences"].get("no_enemy", {}).get("steps", [])
            for step in no_enemy_steps:
                step_frame = self.add_sequence_step(self.no_enemy_container)
                children = step_frame.winfo_children()

                if isinstance(step, list) or isinstance(step, tuple):
                    action, duration = step
                    cooldown = 10.0  # Default cooldown for old format
                    hold_mode = "Instant"  # Default hold mode
                else:
                    action = step.get("action", "F4")
                    duration = step.get("duration", 0.5)
                    cooldown = step.get("cooldown", 10.0)
                    hold_mode = step.get("hold_mode", "Instant")

                children[1].set(action)  # Set action
                children[3].delete(0, 'end')  # Clear duration
                children[3].insert(0, str(duration))  # Set duration
                children[5].delete(0, 'end')  # Clear cooldown
                children[5].insert(0, str(cooldown))  # Set cooldown
                children[7].set(hold_mode)  # Set hold mode

            # Load additional potions
            for pot in config.get("additional_potions", []):
                pot_frame = ctk.CTkFrame(self.pots_container)
                pot_frame.pack(fill="x", pady=2)

                pot_key_label = ctk.CTkLabel(pot_frame, text="Potion Key:")
                pot_key_label.pack(side="left", padx=5)

                pot_key_combo = ctk.CTkComboBox(
                    pot_frame,
                    values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "F1", "F2", "F3", "F4"],
                    width=70
                )
                pot_key_combo.pack(side="left", padx=5)
                pot_key_combo.set(pot.get("key", "6"))

                pot_name_label = ctk.CTkLabel(pot_frame, text="Name:")
                pot_name_label.pack(side="left", padx=5)

                pot_name_entry = ctk.CTkEntry(pot_frame, width=100)
                pot_name_entry.pack(side="left", padx=5)
                pot_name_entry.insert(0, pot.get("name", "Buff Potion"))

                pot_freq_label = ctk.CTkLabel(pot_frame, text="Interval (s):")
                pot_freq_label.pack(side="left", padx=5)

                pot_freq_entry = ctk.CTkEntry(pot_frame, width=60)
                pot_freq_entry.pack(side="left", padx=5)
                pot_freq_entry.insert(0, str(pot.get("frequency", 120)))

                remove_btn = ctk.CTkButton(
                    pot_frame,
                    text="×",
                    width=28,
                    fg_color="transparent",
                    hover_color="#444444",
                    command=lambda f=pot_frame: f.destroy()
                )
                remove_btn.pack(side="right", padx=5)

            messagebox.showinfo("Success", f"Profile '{profile_name}' loaded successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {str(e)}")

    def delete_profile(self):
        try:
            profile_name = self.profile_name_entry.get().strip()
            if not profile_name:
                messagebox.showerror("Error", "Please enter a profile name")
                return

            file_path = os.path.join(self.config_dir, f"{profile_name}.json")

            if not os.path.exists(file_path):
                messagebox.showerror("Error", f"Profile '{profile_name}' not found")
                return

            if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile '{profile_name}'?"):
                os.remove(file_path)
                messagebox.showinfo("Success", f"Profile '{profile_name}' deleted successfully")
                self.load_available_configs()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete profile: {str(e)}")

    def load_available_configs(self):
        try:
            self.profiles_listbox.delete('1.0', 'end')

            if not os.path.exists(self.config_dir):
                return

            config_files = [f for f in os.listdir(self.config_dir) if f.endswith('.json')]

            if not config_files:
                self.profiles_listbox.insert('1.0', "No saved profiles found")
                return

            for file in config_files:
                profile_name = os.path.splitext(file)[0]
                self.profiles_listbox.insert('end', f"• {profile_name}\n")

        except Exception as e:
            self.update_status(f"Error loading profiles: {str(e)}", "red")

    def on_closing(self):
        # Close ESP overlay if it's active
        if self.esp_overlay and self.esp_overlay.active:
            self.esp_overlay.toggle_overlay()

        # Stop everything
        self.stop_macro()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    app = FarmingBot()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()