import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading
from pathlib import Path
import atexit
from math import ceil

from script_data import FFMPEG_BIN, FFPROBE_BIN, ICON_BIN
import tempfile
import shutil

FFMPEG_PATH = None
FFPROBE_PATH = None
ICON_PATH = None
TEMP_FILES = []

DEFAULT_ASPECT_RATIO = 16/9
DEFAULT_RESOLUTION = "420x333"
DEFAULT_FRAMERATE = 24

def cleanup_temp_files():
    """Cleanup temporary binaries"""
    for temp_file in TEMP_FILES:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception:
            pass

atexit.register(cleanup_temp_files)

def setup_binaries():
    """Install temporary binaries if doesn't exists"""
    global FFMPEG_PATH, FFPROBE_PATH, ICON_PATH
    
    if shutil.which("ffmpeg.exe"):
        FFMPEG_PATH = "ffmpeg.exe"
    else:
        fd, FFMPEG_PATH = tempfile.mkstemp(suffix='.exe')
        os.close(fd)
        with open(FFMPEG_PATH, 'wb') as f:
            f.write(FFMPEG_BIN)
        TEMP_FILES.append(FFMPEG_PATH)
        os.chmod(FFMPEG_PATH, 0o755)

    if shutil.which("ffprobe.exe"):
        FFPROBE_PATH = "ffprobe.exe"
    else:
        fd, FFPROBE_PATH = tempfile.mkstemp(suffix='.exe')
        os.close(fd)
        with open(FFPROBE_PATH, 'wb') as f:
            f.write(FFPROBE_BIN)
        TEMP_FILES.append(FFPROBE_PATH)
        os.chmod(FFPROBE_PATH, 0o755)

    fd, ICON_PATH = tempfile.mkstemp(suffix='.ico')
    os.close(fd)
    with open(ICON_PATH, 'wb') as f:
        f.write(ICON_BIN)
    TEMP_FILES.append(ICON_PATH)

class VideoToGIFConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Video to GIF Converter")
        self.root.geometry("720x600")
        self.root.resizable(True, True)
        
        self.input_video = tk.StringVar()
        self.output_gif = tk.StringVar()
        self.fps = tk.StringVar(value=str(DEFAULT_FRAMERATE))
        self.start_time = tk.StringVar()
        self.stop_time = tk.StringVar()
        self.crop_width = tk.StringVar()
        self.crop_height = tk.StringVar()
        self.crop_x = tk.StringVar()
        self.crop_y = tk.StringVar()
        self.use_crop = tk.BooleanVar(value=False)
        
        _width,_height = DEFAULT_RESOLUTION.split("x")
        self.width = tk.StringVar(value=_width)
        self.height = tk.StringVar(value=_height)
        self.lock_aspect = tk.BooleanVar(value=True)
        self.original_aspect = DEFAULT_ASPECT_RATIO
        self.updating = False
        
        self.crop_entries = {}

        self.user_defined_output = False
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        ttk.Label(main_frame, text="Input Video:").grid(row=0, column=0, sticky=tk.W, pady=5)
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        input_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(input_frame, textvariable=self.input_video).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(input_frame, text="Browse", command=self.browse_input).grid(row=0, column=1, padx=(5, 0))
        
        ttk.Label(main_frame, text="Output GIF:").grid(row=1, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        ttk.Entry(output_frame, textvariable=self.output_gif).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(output_frame, text="Browse", command=self.browse_output).grid(row=0, column=1, padx=(5, 0))
        
        res_frame = ttk.LabelFrame(main_frame, text="Output Resolution", padding="5")
        res_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        res_controls_frame = ttk.Frame(res_frame)
        res_controls_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(res_controls_frame, text="Width:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.width_entry = ttk.Entry(res_controls_frame, textvariable=self.width, width=8)
        self.width_entry.grid(row=0, column=1, padx=(0, 15))
        
        ttk.Label(res_controls_frame, text="Height:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.height_entry = ttk.Entry(res_controls_frame, textvariable=self.height, width=8)
        self.height_entry.grid(row=0, column=3, padx=(0, 15))
        
        self.lock_button = ttk.Button(res_controls_frame, text="🔒 Lock", 
                                    command=self.toggle_aspect_lock)
        self.lock_button.grid(row=0, column=4, padx=(0, 15))
        
        ttk.Button(res_controls_frame, text="Reset to Original", 
                  command=self.reset_to_original).grid(row=0, column=5)
        
        self.ar_info = ttk.Label(res_frame, text="Aspect Ratio: 16:9 (1.78:1)", 
                                font=("Arial", 8), foreground="gray")
        self.ar_info.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
        
        presets_frame = ttk.Frame(res_frame)
        presets_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(presets_frame, text="Presets:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        presets = [
            ("360p (480x360)", "480", "360"),
            ("720p (1280x720)", "1280", "720"),
            ("1080p (1920x1080)", "1920", "1080"),
            ("Square (500x500)", "500", "500"),
            ("Instagram (1080x1350)", "1080", "1350"),
            ("Story (1080x1920)", "1080", "1920")
        ]
        
        for i, (label, w, h) in enumerate(presets):
            btn = ttk.Button(presets_frame, text=label, width=15,
                           command=lambda w=w, h=h: self.apply_preset(w, h))
            btn.grid(row=0, column=i+1, padx=(0, 5))
        
        fps_frame = ttk.Frame(main_frame)
        fps_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(fps_frame, text="FPS:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Entry(fps_frame, textvariable=self.fps, width=10).grid(row=0, column=1, sticky=tk.W)
        
        time_frame = ttk.LabelFrame(main_frame, text="Time Settings (Optional)", padding="5")
        time_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        time_frame.columnconfigure(1, weight=1)
        time_frame.columnconfigure(3, weight=1)
        
        ttk.Label(time_frame, text="Start Time:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(time_frame, textvariable=self.start_time, width=15).grid(row=0, column=1, sticky=tk.W, pady=2, padx=(5, 15))
        
        ttk.Label(time_frame, text="Stop Time:").grid(row=0, column=2, sticky=tk.W, pady=2)
        ttk.Entry(time_frame, textvariable=self.stop_time, width=15).grid(row=0, column=3, sticky=tk.W, pady=2, padx=5)
        
        ttk.Label(time_frame, text="Format: HH:MM:SS, MM:SS, or seconds", font=("Arial", 8)).grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))
        
        crop_frame = ttk.LabelFrame(main_frame, text="Crop Settings (Optional)", padding="5")
        crop_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Checkbutton(crop_frame, text="Enable Crop", variable=self.use_crop, 
                       command=self.toggle_crop_fields).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=5)
        
        crop_fields_frame = ttk.Frame(crop_frame)
        crop_fields_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E))
        
        ttk.Label(crop_fields_frame, text="Width:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.crop_entries['width'] = ttk.Entry(crop_fields_frame, textvariable=self.crop_width, width=8, state="disabled")
        self.crop_entries['width'].grid(row=0, column=1, padx=(0, 15))
        
        ttk.Label(crop_fields_frame, text="Height:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.crop_entries['height'] = ttk.Entry(crop_fields_frame, textvariable=self.crop_height, width=8, state="disabled")
        self.crop_entries['height'].grid(row=0, column=3, padx=(0, 15))
        
        ttk.Label(crop_fields_frame, text="X Offset:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.crop_entries['x'] = ttk.Entry(crop_fields_frame, textvariable=self.crop_x, width=8, state="disabled")
        self.crop_entries['x'].grid(row=0, column=5, padx=(0, 15))
        
        ttk.Label(crop_fields_frame, text="Y Offset:").grid(row=0, column=6, sticky=tk.W, padx=(0, 5))
        self.crop_entries['y'] = ttk.Entry(crop_fields_frame, textvariable=self.crop_y, width=8, state="disabled")
        self.crop_entries['y'].grid(row=0, column=7)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=7, column=0, columnspan=3, pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="Convert to GIF", command=self.start_conversion).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.LEFT)
        
        self.input_video.trace_add('write', self.auto_generate_output)
        
        self.width.trace_add('write', self.on_width_change)
        self.height.trace_add('write', self.on_height_change)
        
        self.calculate_aspect_ratio()
        
    def toggle_aspect_lock(self):
        """Toggle lock for aspect ratio sync"""
        self.lock_aspect.set(not self.lock_aspect.get())
        if self.lock_aspect.get():
            self.lock_button.config(text="🔒 Lock")
            try:
                w = int(self.width.get())
                h = int(self.height.get())
                if w > 0 and h > 0:
                    self.original_aspect = w / h
                    self.calculate_aspect_ratio()
            except ValueError:
                pass
        else:
            self.lock_button.config(text="🔓 Unlock")

    def calculate_aspect_ratio(self):
        """Calculate and display current aspect ratio"""
        try:
            w = int(self.width.get())
            h = int(self.height.get())
            if w > 0 and h > 0:
                gcd_val = self.gcd(w, h)
                ratio_w = w // gcd_val
                ratio_h = h // gcd_val
                aspect_ratio = w / h
                
                self.ar_info.config(text=f"Aspect Ratio: {ratio_w}:{ratio_h} ({aspect_ratio:.2f}:1)")
                return aspect_ratio
        except ValueError:
            pass
        return None
    
    def gcd(self, a, b):
        """Calculate greatest common divisor"""
        while b:
            a, b = b, a % b
        return a
    
    def on_width_change(self, *args):
        """Event handler for width width to sync with height"""
        if self.updating:
            return
            
        if self.lock_aspect.get() and self.original_aspect and self.width.get():
            try:
                self.updating = True
                new_width = int(self.width.get())
                new_height = int(round(new_width / self.original_aspect))
                if new_height > 0:
                    self.height.set(str(new_height))
                self.calculate_aspect_ratio()
            except ValueError:
                pass
            finally:
                self.updating = False

    def on_height_change(self, *args):
        """Event handler for width height to sync with width"""
        if self.updating:
            return
            
        if self.lock_aspect.get() and self.original_aspect and self.height.get():
            try:
                self.updating = True
                new_height = int(self.height.get())
                new_width = int(round(new_height * self.original_aspect))
                if new_width > 0:
                    self.width.set(str(new_width))
                self.calculate_aspect_ratio()
            except ValueError:
                pass
            finally:
                self.updating = False

    def apply_preset(self, width, height):
        """Apply a resolution preset"""
        self.updating = True
        try:
            self.width.set(width)
            self.height.set(height)
            if self.lock_aspect.get():
                w = int(width)
                h = int(height)
                if w > 0 and h > 0:
                    self.original_aspect = w / h
            self.calculate_aspect_ratio()
        finally:
            self.updating = False

    def reset_to_original(self):
        """Reset to original video dimensions (if known) or default"""
        self.updating = True
        try:
            if hasattr(self, 'original_video_width') and hasattr(self, 'original_video_height'):
                self.width.set(str(self.original_video_width))
                self.height.set(str(self.original_video_height))
                if self.lock_aspect.get():
                    self.original_aspect = self.original_video_width / self.original_video_height
            else:
                _width, _height = DEFAULT_RESOLUTION.split("x")
                self.width.set(_width)
                self.height.set(_height)
                if self.lock_aspect.get():
                    self.original_aspect = 380 / 214
            self.calculate_aspect_ratio()
        finally:
            self.updating = False

    def browse_input(self):
        """Browse input path using windows's file dialog"""
        file_types = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(title="Select Video File", filetypes=file_types)
        if filename:
            self.input_video.set(filename)
            width, height, fps = self.get_video_dimensions(filename)
            fps = ceil(fps)
            if width and height and fps:
                self.fps.set(str(fps))
                self.original_video_width = width
                self.original_video_height = height
                if self.lock_aspect.get():
                    self.original_aspect = width / height
                self.width.set(str(width))
                self.height.set(str(height))
                self.calculate_aspect_ratio()
                gcd_val = self.gcd(width, height)
                self.ar_info.config(text=f"Aspect Ratio: Original {width}x{height} - {width//gcd_val}:{height//gcd_val}")
            else:
                if self.lock_aspect.get():
                    self.original_aspect = DEFAULT_ASPECT_RATIO
                self.calculate_aspect_ratio()
    
    def get_video_dimensions(self, video_path):
        """Get video dimensions using ffprobe"""
        try:
            cmd = [
                FFPROBE_PATH, '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height,avg_frame_rate', '-of', 'csv=p=0',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            width, height, fpstemp = result.stdout.strip().split(',')
            dividend, divisor = fpstemp.split("/")
            fps = int(dividend) / int(divisor)
            return int(width), int(height), fps
        except Exception as e:
            print(e.with_traceback(None))
            return None, None, None
    
    def toggle_crop_fields(self):
        """Toggle crop function"""
        state = "normal" if self.use_crop.get() else "disabled"
        for entry in self.crop_entries.values():
            entry.config(state=state)
    
    def browse_output(self):
        """Browse output path using windows's file dialog"""
        filename = filedialog.asksaveasfilename(
            title="Save GIF As",
            defaultextension=".gif",
            filetypes=[("GIF files", "*.gif"), ("All files", "*.*")]
        )
        if filename:
            self.output_gif.set(filename)
            self.user_defined_output = True
        else:
            self.user_defined_output = False

    def auto_generate_output(self, *args):
        """Generate output path"""
        if self.input_video.get() and not self.user_defined_output or self.input_video.get() and len(self.output_gif.get()) == 0:
            input_path = Path(self.input_video.get())
            output_path = input_path.with_suffix('.gif')
            self.output_gif.set(str(output_path))
    
    def clear_all(self):
        """Reset everything"""
        _width, _height = DEFAULT_RESOLUTION.split("x")

        self.input_video.set("")
        self.output_gif.set("")
        self.fps.set(str(DEFAULT_FRAMERATE))
        self.start_time.set("")
        self.stop_time.set("")
        self.crop_width.set("")
        self.crop_height.set("")
        self.crop_x.set("")
        self.crop_y.set("")
        self.use_crop.set(False)
        self.width.set(_width)
        self.height.set(_height)
        self.lock_aspect.set(True)
        self.lock_button.config(text="🔒 Lock")
        self.toggle_crop_fields()
        self.calculate_aspect_ratio()
        self.status_label.config(text="Ready")
    
    def parse_time_to_seconds(self, time_str):
        """Parse time in seconds"""
        if not time_str:
            return None
        
        try:
            if ':' not in time_str:
                return float(time_str)
            
            parts = time_str.split(':')
            if len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = parts
                return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
            elif len(parts) == 2:  # MM:SS
                minutes, seconds = parts
                return float(minutes) * 60 + float(seconds)
            else:
                raise ValueError("Invalid time format")
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}")
    
    def get_scale_filter(self):
        """Generate the scale filter with current dimensions"""
        return f"scale={self.width.get()}:{self.height.get()}:flags=lanczos"
    
    def validate_inputs(self):
        """Validate user's input"""
        if not self.input_video.get():
            messagebox.showerror("Error", "Please select an input video file")
            return False
        
        if not self.output_gif.get():
            messagebox.showerror("Error", "Please specify an output GIF file")
            return False
        
        if not os.path.exists(self.input_video.get()):
            messagebox.showerror("Error", "Input video file does not exist")
            return False
        
        try:
            width = int(self.width.get())
            height = int(self.height.get())
            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be positive integers")
                return False
        except ValueError:
            messagebox.showerror("Error", "Width and height must be valid integers")
            return False
        
        try:
            fps = int(self.fps.get())
            if fps <= 0:
                messagebox.showerror("Error", "FPS must be a positive integer")
                return False
        except ValueError:
            messagebox.showerror("Error", "FPS must be a valid integer")
            return False
        
        try:
            start_time = self.parse_time_to_seconds(self.start_time.get()) if self.start_time.get() else None
            stop_time = self.parse_time_to_seconds(self.stop_time.get()) if self.stop_time.get() else None
            
            if start_time is not None and stop_time is not None and stop_time <= start_time:
                messagebox.showerror("Error", "Stop time must be after start time")
                return False
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return False
        
        # Validate crop
        if self.use_crop.get():
            try:
                crop_fields = [self.crop_width.get(), self.crop_height.get(), self.crop_x.get(), self.crop_y.get()]
                if any(not field for field in crop_fields):
                    messagebox.showerror("Error", "All crop fields must be filled when crop is enabled")
                    return False
                
                w, h, x, y = map(int, crop_fields)
                if w <= 0 or h <= 0 or x < 0 or y < 0:
                    messagebox.showerror("Error", "Crop width and height must be positive, offsets non-negative")
                    return False
            except ValueError:
                messagebox.showerror("Error", "Crop values must be valid integers")
                return False
        
        return True
    
    def create_gif(self):
        """Create gif from args"""
        try:
            fps = int(self.fps.get())
            start_time = self.parse_time_to_seconds(self.start_time.get()) if self.start_time.get() else None
            stop_time = self.parse_time_to_seconds(self.stop_time.get()) if self.stop_time.get() else None
            
            crop = None
            if self.use_crop.get():
                crop = (
                    int(self.crop_width.get()),
                    int(self.crop_height.get()),
                    int(self.crop_x.get()),
                    int(self.crop_y.get())
                )
            
            palette_file = "palette.png"
            
            video_filters = []
            
            if crop:
                w, h, x, y = crop
                video_filters.append(f"crop={w}:{h}:{x}:{y}")
            
            video_filters.append(self.get_scale_filter())
            video_filters.append(f"fps={fps}")
            video_filter_str = ','.join(video_filters)
            
            input_options = []
            if start_time is not None:
                input_options.extend(['-ss', str(start_time)])
            if stop_time is not None:
                input_options.extend(['-to', str(stop_time)])
            
            self.update_status("Generating palette...")
            palette_cmd = [FFMPEG_PATH] + input_options + [
                '-i', self.input_video.get(),
                '-vf', f'{video_filter_str},palettegen',
                '-y', palette_file
            ]
            
            subprocess.run(palette_cmd, check=True, capture_output=True)
            
            self.update_status("Creating GIF...")
            gif_cmd = [FFMPEG_PATH] + input_options + [
                '-i', self.input_video.get(),
                '-i', palette_file,
                '-filter_complex', f'{video_filter_str}[x];[x][1:v]paletteuse',
                '-loop', '0', '-y', self.output_gif.get()
            ]
            
            subprocess.run(gif_cmd, check=True, capture_output=True)
            
            if os.path.exists(palette_file):
                os.remove(palette_file)
            
            self.update_status("Conversion completed successfully!")
            messagebox.showinfo("Success", f"GIF created successfully!\n{self.output_gif.get()}")
            
        except subprocess.CalledProcessError as e:
            self.update_status("Error: FFmpeg command failed")
            messagebox.showerror("Error", f"FFmpeg command failed with return code {e.returncode}")
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            self.progress.stop()
            self.root.config(cursor="")
    
    def update_status(self, message):
        """Change the status"""
        def update():
            self.status_label.config(text=message)
        self.root.after(0, update)
    
    def start_conversion(self):
        """Start the conversion"""
        if not self.validate_inputs():
            return
        
        self.root.config(cursor="watch")
        self.progress.start()
        self.update_status("Starting conversion...")
        
        thread = threading.Thread(target=self.create_gif)
        thread.daemon = True
        thread.start()

def main():
    setup_binaries()
    root = tk.Tk()
    app = VideoToGIFConverter(root)
    root.iconbitmap(ICON_PATH)
    root.mainloop()

if __name__ == "__main__":
    main()