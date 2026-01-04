import os
import requests
import zipfile
import subprocess
import shutil
import threading
import stat
import time
import download_script

import json

# Use a dedicated directory for extensions
EXTENSIONS_DIR = os.path.join(os.getcwd(), "extensions")
CUSTOM_EXTENSIONS_FILE = os.path.join(EXTENSIONS_DIR, "custom_extensions.json")

class Extension:
    def __init__(self, name):
        self.name = name
        self.path = None
        self.installed = False

    def is_installed(self):
        raise NotImplementedError

    def install(self, progress_callback=None):
        raise NotImplementedError

    def get_include_path(self):
        raise NotImplementedError

    def get_lib_path(self):
        raise NotImplementedError

    def get_link_flags(self):
        raise NotImplementedError

class RaylibExtension(Extension):
    def __init__(self):
        super().__init__("raylib")
        self.version = "5.0"
        self.download_url = f"https://github.com/raysan5/raylib/archive/refs/tags/{self.version}.zip"
        self.zip_filename = f"raylib-{self.version}.zip"
        self.extract_folder_name = f"raylib-{self.version}"
        self.install_dir = os.path.join(EXTENSIONS_DIR, "raylib")
        
        self.include_path = None
        self.lib_path = None

        # Check if already installed in default location
        if self.check_default_install():
            self.path = self.install_dir
            self.installed = True
            # Default structure from source build
            self.include_path = os.path.join(self.install_dir, "src")
            self.lib_path = os.path.join(self.install_dir, "src")

    def is_installed(self):
        return self.installed

    def check_default_install(self):
        # Basic check: look for include/raylib.h and lib/libraylib.a
        return os.path.exists(os.path.join(self.install_dir, "src", "raylib.h")) and \
               os.path.exists(os.path.join(self.install_dir, "src", "libraylib.a"))

    def set_manual_path(self, path):
        if not os.path.isdir(path): return False
        
        # Detect include path
        found_inc = False
        potential_inc_paths = [
            os.path.join(path, "src"),
            os.path.join(path, "include"),
            path
        ]
        for p in potential_inc_paths:
            if os.path.exists(os.path.join(p, "raylib.h")):
                self.include_path = p
                found_inc = True
                break
        
        # Detect lib path
        found_lib = False
        potential_lib_paths = [
            os.path.join(path, "src"),
            os.path.join(path, "lib"),
            path
        ]
        for p in potential_lib_paths:
            if os.path.exists(os.path.join(p, "libraylib.a")):
                self.lib_path = p
                found_lib = True
                break
            
        if found_inc: # Allow if at least headers are found
             self.path = path
             self.installed = True
             if not self.lib_path: self.lib_path = self.include_path
             return True
             
        return False

    def _on_rm_error(self, func, path, exc_info):
        # Error handler for shutil.rmtree to remove read-only files
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def install(self, progress_callback=None):
        if self.installed:
            if progress_callback: progress_callback("Raylib already installed.")
            return

        if not os.path.exists(EXTENSIONS_DIR):
            os.makedirs(EXTENSIONS_DIR)

        try:
            # Check for make
            make_cmd = "make"
            if shutil.which("mingw32-make"):
                make_cmd = "mingw32-make"
            elif not shutil.which("make"):
                 if progress_callback: progress_callback("Warning: 'make' not found. Compilation might fail.")

            # 1. Download
            if progress_callback: progress_callback(f"Downloading {self.zip_filename}...")
            zip_path = os.path.join(EXTENSIONS_DIR, self.zip_filename)
            
            # Use stream=True to avoid reading large file into memory
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 2. Extract
            if progress_callback: progress_callback("Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(EXTENSIONS_DIR)
            
            # Rename/Move
            extracted_path = os.path.join(EXTENSIONS_DIR, self.extract_folder_name)
            
            # Robust removal of existing dir
            if os.path.exists(self.install_dir):
                if progress_callback: progress_callback("Removing old version...")
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
                time.sleep(0.5)

            # Robust move with retry
            max_retries = 3
            for i in range(max_retries):
                try:
                    if progress_callback: progress_callback("Moving files...")
                    shutil.move(extracted_path, self.install_dir)
                    break 
                except Exception as e:
                    if i == max_retries - 1:
                        raise e
                    if progress_callback: progress_callback(f"Move failed (attempt {i+1}), retrying...")
                    time.sleep(1.0)
            
            try:
                os.remove(zip_path)
            except:
                pass

            # 3. Compile
            if progress_callback: progress_callback("Compiling Raylib (this may take a while)...")
            src_dir = os.path.join(self.install_dir, "src")
            
            # We use subprocess with cwd
            cmd = [make_cmd, "PLATFORM=PLATFORM_DESKTOP", "RAYLIB_LIBTYPE=STATIC"]
            
            # Capture output
            result = subprocess.run(cmd, cwd=src_dir, capture_output=True, text=True)
            if result.returncode != 0:
                if progress_callback: progress_callback(f"Compilation failed:\n{result.stderr}")
                raise Exception(f"Raylib compilation failed: {result.stderr}")

            if progress_callback: progress_callback("Raylib installed successfully.")
            self.path = self.install_dir
            self.installed = True
            self.include_path = src_dir
            self.lib_path = src_dir

        except Exception as e:
            if progress_callback: progress_callback(f"Error: {e}")
            raise e

    def get_include_path(self):
        return self.include_path

    def get_lib_path(self):
        return self.lib_path

    def get_link_flags(self):
        # -lraylib -lgdi32 -lwinmm etc for windows
        flags = ["-lraylib"]
        if os.name == 'nt':
            flags.extend(["-lgdi32", "-lwinmm", "-lopengl32"])
        else:
            flags.extend(["-lGL", "-lm", "-lpthread", "-ldl", "-lrt", "-lX11"])
        return flags

class OpenCVExtension(Extension):
    def __init__(self):
        super().__init__("opencv")
        self.version = "4.10.0" 
        self.download_url = f"https://github.com/opencv/opencv/archive/refs/tags/{self.version}.zip"
        self.zip_filename = f"opencv-{self.version}.zip"
        self.extract_folder_name = f"opencv-{self.version}"
        self.install_dir = os.path.join(EXTENSIONS_DIR, "opencv")
        
        self.include_path = None
        self.lib_path = None

        if self.check_default_install():
            self.path = self.install_dir
            self.installed = True
            # Defaults for local build
            # Usually install/include and install/x64/mingw/lib or similar
            # We will use valid paths after install
            self.include_path = os.path.join(self.install_dir, "build", "install", "include")
            self.lib_path = os.path.join(self.install_dir, "build", "install", "x64", "mingw", "lib")
            # fallback for simple builds
            if not os.path.exists(self.lib_path):
                 self.lib_path = os.path.join(self.install_dir, "build", "lib")

    def is_installed(self):
        return self.installed

    def check_default_install(self):
        # Check for build/install folder
        install_p = os.path.join(self.install_dir, "build", "install")
        return os.path.exists(os.path.join(install_p, "include", "opencv4", "opencv2", "opencv.hpp"))

    def set_manual_path(self, path):
         if not os.path.isdir(path): return False
         # Logic to find opencv paths in a custom directory is complex due to variations
         # Search for include
         found_inc = False
         for root, dirs, files in os.walk(path):
             if "opencv2" in dirs and "opencv.hpp" in files: 
                  # This likely is opencv2/opencv.hpp, so root is include/opencv4 or include
                  # But we need the root include dir that 'contains' opencv2 or opencv4
                  pass
             if "opencv.hpp" in files:
                  # Found it. verify if parent is opencv2
                  if os.path.basename(root) == "opencv2":
                       # The include path is the parent of 'opencv2' (if #include <opencv2/...>)
                       # or parent of parent if (#include <opencv4/...>)
                       self.include_path = os.path.dirname(root) # include/
                       found_inc = True
                       break
         
         if found_inc:
             self.path = path
             self.installed = True
             # Try to find lib
             self.lib_path = self.include_path # fallback
             for root, dirs, files in os.walk(path):
                 if any(f.endswith(".a") or f.endswith(".lib") for f in files):
                     if "libopencv_core" in " ".join(files):
                         self.lib_path = root
                         break
             return True
         return False

    def install(self, progress_callback=None):
        if self.installed:
            if progress_callback: progress_callback("OpenCV already installed.")
            return

        # Check CMake
        cmake_cmd = "cmake"
        import download_script
        if not shutil.which("cmake"):
             # checks internal path
             cmake_internal = os.path.join(download_script.CMAKE_DIR, "bin", "cmake.exe")
             if not os.path.exists(cmake_internal):
                  if progress_callback: progress_callback("CMake not found. Downloading portable CMake...")
                  try:
                       download_script.install_cmake(log_func=lambda m, s="": progress_callback(m) if progress_callback else None)
                  except Exception as e:
                       raise Exception(f"Failed to install CMake: {e}")
             
             if os.path.exists(cmake_internal):
                  # Add to path for this session so subprocess finds it
                  os.environ["PATH"] = os.path.dirname(cmake_internal) + os.pathsep + os.environ["PATH"]
             else:
                  raise Exception("CMake is required but could not be installed.")

        if not os.path.exists(EXTENSIONS_DIR):
            os.makedirs(EXTENSIONS_DIR)

        try:
            # 1. Download
            if progress_callback: progress_callback(f"Downloading {self.zip_filename}...")
            zip_path = os.path.join(EXTENSIONS_DIR, self.zip_filename)
            
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 2. Extract
            if progress_callback: progress_callback("Extracting OpenCV source...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(EXTENSIONS_DIR)
            
            extracted_path = os.path.join(EXTENSIONS_DIR, self.extract_folder_name)
            
            # Remove old
            if os.path.exists(self.install_dir):
                if progress_callback: progress_callback("Removing old version...")
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
                time.sleep(0.5)

            # Move
            shutil.move(extracted_path, self.install_dir)
            try: os.remove(zip_path); 
            except: pass

            # 3. Build with CMake
            if progress_callback: progress_callback("Configuring OpenCV with CMake...")
            build_dir = os.path.join(self.install_dir, "build")
            if not os.path.exists(build_dir): os.makedirs(build_dir)
            
            # Configure
            # We force MinGW Makefiles if on Windows to ensure compatibility with Cmpile's likely environment
            # effectively 'cmake -S .. -B . -G "MinGW Makefiles" -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF'
            cmake_args = [
                "cmake", "-S", "..", "-B", ".",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DBUILD_TESTS=OFF",
                "-DBUILD_PERF_TESTS=OFF",
                "-DBUILD_EXAMPLES=OFF",
                "-DBUILD_JAVA=OFF",
                "-DBUILD_PYTHON=OFF",
                "-DCMAKE_INSTALL_PREFIX=./install"
            ]
            
            if os.name == 'nt' and shutil.which("mingw32-make"):
                 cmake_args.extend(["-G", "MinGW Makefiles"])

            result = subprocess.run(cmake_args, cwd=build_dir, capture_output=True, text=True)
            if result.returncode != 0:
                 raise Exception(f"CMake Configuration Failed:\n{result.stderr}")

            # Build
            if progress_callback: progress_callback("Building OpenCV (This WILL take 10-30 minutes)...")
            build_cmd = ["cmake", "--build", ".", "--config", "Release", "--target", "install"]
            
            # This is the long part
            # Streaming output strictly is hard with subprocess.run capture_output, 
            # ideally we just let it run or use Popen to stream updates.
            # For simplicity/stability we wait, but user gets no partial progress bar for the compilation itself.
            result = subprocess.run(build_cmd, cwd=build_dir, capture_output=True, text=True)
            if result.returncode != 0:
                 raise Exception(f"OpenCV Build Failed:\n{result.stderr}")

            if progress_callback: progress_callback("OpenCV installed successfully.")
            self.installed = True
            self.path = self.install_dir
            self.include_path = os.path.join(build_dir, "install", "include")
            # Lib path - try to find where .a files went
            self.lib_path = os.path.join(build_dir, "install", "x64", "mingw", "lib")
            if not os.path.exists(self.lib_path):
                self.lib_path = os.path.join(build_dir, "install", "lib")

        except Exception as e:
            if progress_callback: progress_callback(f"Error: {e}")
            raise e
    
    def _on_rm_error(self, func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def get_include_path(self):
        return self.include_path

    def get_lib_path(self):
        return self.lib_path

    def get_link_flags(self):
        # OpenCV requires many libs
        # Just linking core, imgproc, imgcodecs, highgui usually enough for basic stuff
        # But order matters and there are many dependencies (zlib, etc).
        # We'll return a wildcard or list all known modules?
        # A static build of OpenCV is heavy on deps.
        # Best guess list:
        libs = ["-lopencv_highgui4100", "-lopencv_imgcodecs4100", "-lopencv_imgproc4100", "-lopencv_core4100"]
        # If headers are different version, libs names change.
        # We need to scan lib_path for actual names?
        if self.lib_path and os.path.exists(self.lib_path):
             files = os.listdir(self.lib_path)
             # Basic auto-discovery of main modules
             found_libs = []
             priority = ["highgui", "imgcodecs", "videoio", "imgproc", "core"]
             # We need to strip lib prefix and extension
             for p in priority:
                  for f in files:
                       if p in f and (f.endswith(".a") or f.endswith(".lib")) and "main" not in f:
                            # libopencv_core4100.a -> -lopencv_core4100
                            name = os.path.splitext(f)[0]
                            if name.startswith("lib"): name = name[3:]
                            flag = f"-l{name}"
                            if flag not in found_libs:
                                 found_libs.append(flag)
             
             # Add others not in priority but present? 
             # For now return the priority list + extensive system libs
             libs = found_libs
        
        if os.name == 'nt':
             libs.extend(["-lgdi32", "-lcomdlg32", "-lole32", "-luuid"])
        return libs

class CustomExtension(Extension):
    def __init__(self, name, include_path, lib_path, flags):
        super().__init__(name)
        self.include_path = include_path
        self.lib_path = lib_path
        self.flags = flags  # List of flags
        self.path = include_path # Rough approximation
        self.installed = True # Custom extensions are assumed installed

    def is_installed(self):
        return os.path.isdir(self.include_path) and os.path.isdir(self.lib_path)

    def install(self, progress_callback=None):
        if progress_callback: progress_callback(f"Custom extension '{self.name}' is manually managed.")

    def get_include_path(self):
        return self.include_path

    def get_lib_path(self):
        return self.lib_path
    
    def get_link_flags(self):
        return self.flags

    def to_dict(self):
        return {
            "name": self.name,
            "include_path": self.include_path,
            "lib_path": self.lib_path,
            "flags": self.flags
        }

    @staticmethod
    def from_dict(data):
        return CustomExtension(
            data["name"],
            data["include_path"],
            data["lib_path"],
            data["flags"]
        )

class ExtensionManager:
    def __init__(self):
        self.extensions = {
            "raylib": RaylibExtension(),
            "opencv": OpenCVExtension()
        }
        self.load_custom_extensions()

    def load_custom_extensions(self):
        if os.path.exists(CUSTOM_EXTENSIONS_FILE):
            try:
                with open(CUSTOM_EXTENSIONS_FILE, 'r') as f:
                    data = json.load(f)
                    for ext_data in data:
                        ext = CustomExtension.from_dict(ext_data)
                        self.extensions[ext.name] = ext
            except Exception as e:
                print(f"Failed to load custom extensions: {e}")

    def save_custom_extensions(self):
        custom_exts = [
            ext.to_dict() for ext in self.extensions.values() 
            if isinstance(ext, CustomExtension)
        ]
        if not os.path.exists(EXTENSIONS_DIR):
            os.makedirs(EXTENSIONS_DIR)
            
        try:
            with open(CUSTOM_EXTENSIONS_FILE, 'w') as f:
                json.dump(custom_exts, f, indent=4)
        except Exception as e:
            print(f"Failed to save custom extensions: {e}")

    def add_extension(self, extension):
        self.extensions[extension.name] = extension
        if isinstance(extension, CustomExtension):
            self.save_custom_extensions()

    def get_extension(self, name):
        return self.extensions.get(name)

    def get_all_extensions(self):
        return self.extensions.values()

    def install_all(self, progress_callback=None):
        for ext in self.extensions.values():
            if not ext.is_installed(): 
                ext.install(progress_callback)
