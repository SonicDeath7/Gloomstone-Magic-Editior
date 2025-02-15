import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageOps, ImageFilter, ImageEnhance
import numpy as np
import threading
import pygame
import time


class GothicEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Gloomstone_Magic_Editior 0.1.0")
        self.root.geometry("1280x1024")
        self.set_gothic_theme()

        # Инициализация переменных
        self.filters = [
            "Dithering - Floyd-Steinberg",
            "Dithering - Pattern",
            "Sepia",
            "Invert",
            "Blur",
            "Contour",
            "Grayscale"
        ]

        # Параметры обработки
        self.brightness_var = tk.DoubleVar(value=1.0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        self.pixelation_var = tk.IntVar(value=0)
        self.saturation_var = tk.DoubleVar(value=1.0)

        self.base_image = None
        self.processed_image = None
        self.preview_size = (400, 400)
        self.last_update = None
        self.update_delay = 350
        self.lock = threading.Lock()

        self.create_widgets()
        self.setup_layout()

        # Инициализация pygame для музыки
        pygame.mixer.init()
        self.background_music_playing = False
        self.root.bind("<<ProcessingComplete>>", self.on_processing_complete)

    def set_gothic_theme(self):
        self.root.configure(bg='#0a0a0a')
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Настройка стилей
        self.style.configure('TFrame', background='#1a1a1a')
        self.style.configure('TLabel', background='#1a1a1a', foreground='#8b0000', font=('Garamond', 10))
        self.style.configure('TButton', background='#2d2d2d', foreground='#8b0000',
                             font=('Garamond', 10, 'bold'), borderwidth=3)
        self.style.map('TButton', background=[('active', '#3d3d3d')])
        self.style.configure('TScale', background='#1a1a1a', troughcolor='#2d2d2d')
        self.style.configure('TCombobox', fieldbackground='#2d2d2d', foreground='#8b0000')

    def create_widgets(self):
        self.control_frame = ttk.Frame(self.root, width=300)
        self.image_frame = ttk.Frame(self.root)
        self.create_buttons()
        self.create_sliders()
        self.create_filter_selector()

    def create_buttons(self):
        button_style = {
            'bg': '#2d2d2d',
            'fg': '#8b0000',
            'activebackground': '#3d3d3d',
            'relief': tk.GROOVE,
            'font': ('Garamond', 12, 'bold'),
            'borderwidth': 3
        }

        buttons = [
            ("Open Image", self.open_image),
            ("Apply Effects", self.apply_effects),
            ("Save Image", self.save_image),
            ("🎵 Toggle Music", self.toggle_music)
        ]

        for text, command in buttons:
            btn = tk.Button(
                self.control_frame,
                text=text,
                command=command,
                **button_style
            )
            btn.pack(pady=10, fill=tk.X, padx=5)

    def create_sliders(self):
        sliders = [
            ("Brightness", self.brightness_var, 0.1, 3.0),
            ("Contrast", self.contrast_var, 0.1, 3.0),
            ("Pixelation", self.pixelation_var, 0, 50),
            ("Saturation", self.saturation_var, 0.0, 2.0)
        ]

        for label, var, from_, to in sliders:
            frame = ttk.Frame(self.control_frame)
            ttk.Label(frame, text=label, style='TLabel').pack(side=tk.LEFT)
            ttk.Scale(
                frame,
                variable=var,
                from_=from_,
                to=to,
                command=lambda v, lbl=label: self.on_slider_change(lbl)
            ).pack(side=tk.RIGHT, fill=tk.X, expand=True)
            frame.pack(pady=8, fill=tk.X, padx=5)

    def create_filter_selector(self):
        ttk.Label(self.control_frame, text="Select Filter:").pack(pady=10)
        self.filter_combo = ttk.Combobox(
            self.control_frame,
            values=self.filters,
            state="readonly",
            style='TCombobox'
        )
        self.filter_combo.current(0)
        self.filter_combo.pack(fill=tk.X, pady=10, padx=5)

    def setup_layout(self):
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.image_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=10, pady=10)

        self.original_label = ttk.Label(self.image_frame, text="Original Image", style='TLabel')
        self.original_label.pack(side=tk.LEFT, padx=20, pady=10)

        self.processed_label = ttk.Label(self.image_frame, text="Processed Image", style='TLabel')
        self.processed_label.pack(side=tk.RIGHT, padx=20, pady=10)

    def open_image(self):
        file_types = [("Image files", "*.jpg;*.jpeg;*.png;*.bmp")]
        path = filedialog.askopenfilename(filetypes=file_types)

        if path:
            try:
                self.base_image = Image.open(path).convert("RGB")
                self.processed_image = self.base_image.copy()
                self.show_images()
            except Exception as e:
                self.show_error(f"Error loading image: {str(e)}")

    def show_images(self):
        if not hasattr(self, 'original_preview'):
            self.original_preview = None
            self.processed_preview = None

        resize_method = (
            Image.Resampling.BILINEAR
            if self.pixelation_var.get() > 5
            else Image.Resampling.LANCZOS
        )

        if self.base_image:
            original_preview = self.base_image.resize(self.preview_size, resize_method)
            self.original_preview = ImageTk.PhotoImage(original_preview)
            self.original_label.configure(image=self.original_preview)

        if self.processed_image:
            processed_preview = self.processed_image.resize(self.preview_size, resize_method)
            self.processed_preview = ImageTk.PhotoImage(processed_preview)
            self.processed_label.configure(image=self.processed_preview)

    def on_slider_change(self, label):
        if self.base_image and not self.last_update:
            self.last_update = self.root.after(self.update_delay, self.debounced_update)

    def debounced_update(self):
        if self.base_image:
            threading.Thread(target=self.apply_effects).start()
        self.last_update = None

    def apply_base_effects(self, img):
        try:
            if self.brightness_var.get() != 1.0:
                img = ImageEnhance.Brightness(img).enhance(self.brightness_var.get())
            if self.contrast_var.get() != 1.0:
                img = ImageEnhance.Contrast(img).enhance(self.contrast_var.get())

            pixel_size = self.pixelation_var.get()
            if pixel_size > 1:
                w, h = img.size
                img = img.resize((w // pixel_size, h // pixel_size), Image.Resampling.NEAREST)
                img = img.resize((w, h), Image.Resampling.NEAREST)

            if self.saturation_var.get() != 1.0:
                img = ImageEnhance.Color(img).enhance(self.saturation_var.get())

            return img
        except Exception as e:
            self.show_error(str(e))
            return img

    def apply_filter(self, img):
        selected_filter = self.filter_combo.get()
        try:
            if "Floyd-Steinberg" in selected_filter:
                return self.vectorized_floyd_steinberg(img)
            elif "Pattern" in selected_filter:
                return self.pattern_dither(img)
            elif selected_filter == "Sepia":
                return self.apply_sepia(img)
            elif selected_filter == "Invert":
                return ImageOps.invert(img)
            elif selected_filter == "Blur":
                return img.filter(ImageFilter.GaussianBlur(5))
            elif selected_filter == "Contour":
                return img.filter(ImageFilter.CONTOUR)
            elif selected_filter == "Grayscale":
                return img.convert("L").convert("RGB")
            return img
        except Exception as e:
            self.show_error(str(e))
            return img

    def apply_effects(self):
        with self.lock:
            try:
                preview_img = self.base_image.copy().resize(self.preview_size, Image.Resampling.LANCZOS)
                processed_preview = self.apply_base_effects(preview_img)
                processed_preview = self.apply_filter(processed_preview)

                self.processed_preview = ImageTk.PhotoImage(processed_preview)
                self.processed_label.configure(image=self.processed_preview)

                threading.Thread(target=self.process_full_image).start()
            except Exception as e:
                self.show_error(str(e))

    def process_full_image(self):
        try:
            with self.lock:
                full_processed = self.apply_base_effects(self.base_image.copy())
                full_processed = self.apply_filter(full_processed)
                self.processed_image = full_processed
        except Exception as e:
            self.show_error(f"Processing error: {str(e)}")
        finally:
            self.root.event_generate("<<ProcessingComplete>>")

    def vectorized_floyd_steinberg(self, image):
        try:
            img = image.convert("L")
            pixels = np.array(img, dtype=np.float32) / 255.0
            h, w = pixels.shape

            errors = np.zeros((h + 1, w + 2), dtype=np.float32)

            for y in range(h):
                for x in range(w):
                    old_val = pixels[y, x] + errors[y, x + 1]
                    new_val = np.round(old_val)
                    quant_error = old_val - new_val

                    pixels[y, x] = new_val

                    # Распределение ошибки
                    errors[y, x + 2] += quant_error * 7 / 16
                    errors[y + 1, x] += quant_error * 3 / 16
                    errors[y + 1, x + 1] += quant_error * 5 / 16
                    errors[y + 1, x + 2] += quant_error * 1 / 16

            return Image.fromarray((np.clip(pixels, 0, 1) * 255).astype(np.uint8))
        except Exception as e:
            self.show_error(str(e))
            return image

    def pattern_dither(self, image):
        try:
            img = image.convert("L")
            pixels = np.array(img)
            pattern = np.array([[0, 128], [192, 64]])

            h, w = pixels.shape
            threshold = np.tile(pattern, (h // 2 + 1, w // 2 + 1))[:h, :w]
            pixels = np.where(pixels < threshold, 0, 255)

            return Image.fromarray(pixels.astype(np.uint8))
        except Exception as e:
            self.show_error(str(e))
            return image

    def apply_sepia(self, img):
        sepia_filter = np.array([[0.393, 0.769, 0.189],
                                 [0.349, 0.686, 0.168],
                                 [0.272, 0.534, 0.131]])

        img = np.array(img)
        img = img.dot(sepia_filter.T)
        img = np.clip(img, 0, 255).astype(np.uint8)

        return Image.fromarray(img)

    def toggle_music(self):
        if self.background_music_playing:
            pygame.mixer.music.pause()
        else:
            if not pygame.mixer.music.get_busy():
                try:
                    pygame.mixer.music.load("music.mp3")
                    pygame.mixer.music.play(-1)
                except Exception as e:
                    self.show_error(f"Music error: {str(e)}")
                    return
            else:
                pygame.mixer.music.unpause()
        self.background_music_playing = not self.background_music_playing

    def on_processing_complete(self, event=None):
        pass  # Можно добавить уведомление или логирование

    def show_error(self, message):
        messagebox.showerror("Error", message)

    def save_image(self):
        if self.processed_image:
            file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
            if file_path:
                self.processed_image.save(file_path)


if __name__ == "__main__":
    root = tk.Tk()
    app = GothicEditor(root)
    root.mainloop()


