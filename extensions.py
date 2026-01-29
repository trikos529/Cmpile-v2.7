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

    def get_version(self):
        return "N/A"

    def install(self, progress_callback=None):
        raise NotImplementedError

    def uninstall(self, progress_callback=None):
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
        self.version = "5.5"
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
        if self.path == self.install_dir:
            if not self.check_default_install():
                self.installed = False
                self.path = None
        elif self.path: # manual path
             if not os.path.isdir(self.path):
                 self.installed = False
                 self.path = None
        else: # not installed, check defaulted
            if self.check_default_install():
                self.set_manual_path(self.install_dir)
        return self.installed

    def check_default_install(self):
        # Basic check: look for src/raylib.h and src/libraylib.a
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

    def uninstall(self, progress_callback=None):
        if not self.installed:
            if progress_callback: progress_callback("Raylib is not installed.")
            return
        
        try:
            if progress_callback: progress_callback("Uninstalling Raylib...")
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            self.installed = False
            self.path = None
            self.include_path = None
            self.lib_path = None
            if progress_callback: progress_callback("Raylib uninstalled successfully.")
        except Exception as e:
            if progress_callback: progress_callback(f"Error uninstalling Raylib: {e}")
            raise e

    def get_version(self):
        return f"v{self.version}"

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
        self.version = "4.13.0"
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
        if self.path == self.install_dir:
            if not self.check_default_install():
                self.installed = False
                self.path = None
        elif self.path: # manual path
             if not os.path.isdir(self.path):
                 self.installed = False
                 self.path = None
        else: # not installed, check defaulted
            if self.check_default_install():
                 # For OpenCV, set_manual_path is complex, we just set paths here if default found
                 self.path = self.install_dir
                 self.installed = True
                 self.include_path = os.path.join(self.install_dir, "build", "install", "include")
                 self.lib_path = os.path.join(self.install_dir, "build", "install", "x64", "mingw", "lib")
                 if not os.path.exists(self.lib_path):
                      self.lib_path = os.path.join(self.install_dir, "build", "lib")
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
    
    def uninstall(self, progress_callback=None):
        if not self.installed:
            if progress_callback: progress_callback("OpenCV is not installed.")
            return
        
        try:
            if progress_callback: progress_callback("Uninstalling OpenCV...")
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            self.installed = False
            self.path = None
            self.include_path = None
            self.lib_path = None
            if progress_callback: progress_callback("OpenCV uninstalled successfully.")
        except Exception as e:
            if progress_callback: progress_callback(f"Error uninstalling OpenCV: {e}")
            raise e

    def get_version(self):
        return f"v{self.version}"

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

class MiniaudioExtension(Extension):
    def __init__(self):
        super().__init__("miniaudio")
        self.version = "0.11.23"
        self.download_url = f"https://github.com/mackron/miniaudio/archive/refs/tags/{self.version}.zip"
        self.zip_filename = f"miniaudio-{self.version}.zip"
        self.extract_folder_name = f"miniaudio-{self.version}"
        self.install_dir = os.path.join(EXTENSIONS_DIR, "miniaudio")
        
        if self.is_installed():
            self.path = self.install_dir
            self.installed = True

    def is_installed(self):
        if self.path == self.install_dir:
            if not self.check_default_install():
                self.installed = False
                self.path = None
        else:
            if self.check_default_install():
                self.path = self.install_dir
                self.installed = True
        return self.installed

    def check_default_install(self):
        return os.path.exists(os.path.join(self.install_dir, "miniaudio.h"))

    def install(self, progress_callback=None):
        if self.installed:
            if progress_callback: progress_callback("miniaudio already installed.")
            return

        if not os.path.exists(EXTENSIONS_DIR):
            os.makedirs(EXTENSIONS_DIR)

        try:
            if progress_callback: progress_callback(f"Downloading {self.zip_filename}...")
            zip_path = os.path.join(EXTENSIONS_DIR, self.zip_filename)
            
            response = requests.get(self.download_url, stream=True)
            response.raise_for_status()
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if progress_callback: progress_callback("Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(EXTENSIONS_DIR)
            
            extracted_path = os.path.join(EXTENSIONS_DIR, self.extract_folder_name)
            
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            shutil.move(extracted_path, self.install_dir)
            
            try: os.remove(zip_path)
            except: pass

            if progress_callback: progress_callback("miniaudio installed successfully.")
            self.path = self.install_dir
            self.installed = True

        except Exception as e:
            if progress_callback: progress_callback(f"Error: {e}")
            raise e

    def uninstall(self, progress_callback=None):
        if not self.installed:
            if progress_callback: progress_callback("miniaudio is not installed.")
            return
        
        try:
            if progress_callback: progress_callback("Uninstalling miniaudio...")
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            self.installed = False
            self.path = None
            if progress_callback: progress_callback("miniaudio uninstalled successfully.")
        except Exception as e:
            if progress_callback: progress_callback(f"Error uninstalling miniaudio: {e}")
            raise e

    def get_version(self):
        return f"v{self.version}"

    def _on_rm_error(self, func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def get_include_path(self):
        return self.install_dir

    def get_lib_path(self):
        return None

    def get_link_flags(self):
        if os.name == 'nt':
            return []
        return ["-lpthread", "-lm", "-ldl"]

class TinyXMLExtension(Extension):
    def __init__(self):
        super().__init__("tinyxml")
        self.version = "11.0.0"
        self.download_url = f"https://github.com/leethomason/tinyxml2/archive/refs/tags/{self.version}.zip"
        self.zip_filename = f"tinyxml2-{self.version}.zip"
        self.extract_folder_name = f"tinyxml2-{self.version}"
        self.install_dir = os.path.join(EXTENSIONS_DIR, "tinyxml2")
        
        self.include_path = None
        self.lib_path = None

        if self.check_default_install():
            self.path = self.install_dir
            self.installed = True
            self.include_path = self.install_dir
            self.lib_path = os.path.join(self.install_dir, "build")
        else:
            self.path = None
            self.installed = False

    def is_installed(self):
        if self.path == self.install_dir:
            if not self.check_default_install():
                self.installed = False
                self.path = None
        elif self.path: # manual path
             if not os.path.isdir(self.path):
                 self.installed = False
                 self.path = None
        else: # not installed, check defaulted
            if self.check_default_install():
                self.path = self.install_dir
                self.installed = True
                self.include_path = self.install_dir
                self.lib_path = os.path.join(self.install_dir, "build")
        return self.installed

    def check_default_install(self):
        # Look for tinyxml2.h in install_dir and libtinyxml2.a in build
        # Windows might have .lib instead of .a
        return os.path.exists(os.path.join(self.install_dir, "tinyxml2.h")) and \
               (os.path.exists(os.path.join(self.install_dir, "build", "libtinyxml2.a")) or \
                os.path.exists(os.path.join(self.install_dir, "build", "tinyxml2.lib")))

    def install(self, progress_callback=None):
        if self.installed:
            if progress_callback: progress_callback("TinyXML2 already installed.")
            return

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
            if progress_callback: progress_callback("Extracting TinyXML2 source...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(EXTENSIONS_DIR)
            
            extracted_path = os.path.join(EXTENSIONS_DIR, self.extract_folder_name)
            
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            shutil.move(extracted_path, self.install_dir)
            
            try: os.remove(zip_path)
            except: pass

            # 3. Build with CMake
            if progress_callback: progress_callback("Configuring TinyXML2 with CMake...")
            build_dir = os.path.join(self.install_dir, "build")
            if not os.path.exists(build_dir): os.makedirs(build_dir)
            
            # We use common CMake flags for static build
            cmake_args = [
                "cmake", "..", 
                "-DBUILD_SHARED_LIBS=OFF", 
                "-DBUILD_TESTS=OFF"
            ]
            
            if os.name == 'nt' and shutil.which("mingw32-make"):
                 cmake_args.extend(["-G", "MinGW Makefiles"])

            result = subprocess.run(cmake_args, cwd=build_dir, capture_output=True, text=True)
            if result.returncode != 0:
                 raise Exception(f"TinyXML2 CMake Configuration Failed:\n{result.stderr}")

            # Build
            if progress_callback: progress_callback("Building TinyXML2...")
            build_cmd = ["cmake", "--build", ".", "--config", "Release"]
            
            result = subprocess.run(build_cmd, cwd=build_dir, capture_output=True, text=True)
            if result.returncode != 0:
                 raise Exception(f"TinyXML2 Build Failed:\n{result.stderr}")

            if progress_callback: progress_callback("TinyXML2 installed successfully.")
            self.installed = True
            self.path = self.install_dir
            self.include_path = self.install_dir
            self.lib_path = build_dir

        except Exception as e:
            if progress_callback: progress_callback(f"Error: {e}")
            raise e

    def uninstall(self, progress_callback=None):
        if not self.installed:
            if progress_callback: progress_callback("TinyXML2 is not installed.")
            return
        
        try:
            if progress_callback: progress_callback("Uninstalling TinyXML2...")
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            self.installed = False
            self.path = None
            self.include_path = None
            self.lib_path = None
            if progress_callback: progress_callback("TinyXML2 uninstalled successfully.")
        except Exception as e:
            if progress_callback: progress_callback(f"Error uninstalling TinyXML2: {e}")
            raise e

    def get_version(self):
        return f"v{self.version}"

    def _on_rm_error(self, func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def get_include_path(self):
        return self.include_path

    def get_lib_path(self):
        return self.lib_path

    def get_link_flags(self):
        return ["-ltinyxml2"]

class MinizExtension(Extension):
    def __init__(self):
        super().__init__("miniz")
        self.version = "3.1.0"
        self.download_url = f"https://github.com/richgel999/miniz/archive/refs/tags/{self.version}.zip"
        self.zip_filename = f"miniz-{self.version}.zip"
        self.extract_folder_name = f"miniz-{self.version}"
        self.install_dir = os.path.join(EXTENSIONS_DIR, "miniz")
        
        self.include_path = None
        self.lib_path = None

        if self.check_default_install():
            self.path = self.install_dir
            self.installed = True
            self.include_path = self.install_dir
            self.lib_path = os.path.join(self.install_dir, "build")
        else:
            self.path = None
            self.installed = False

    def is_installed(self):
        if self.path == self.install_dir:
            if not self.check_default_install():
                self.installed = False
                self.path = None
        elif self.path: # manual path
             if not os.path.isdir(self.path):
                 self.installed = False
                 self.path = None
        else: # not installed, check defaulted
            if self.check_default_install():
                self.path = self.install_dir
                self.installed = True
                self.include_path = self.install_dir
                self.lib_path = os.path.join(self.install_dir, "build")
        return self.installed

    def check_default_install(self):
        return os.path.exists(os.path.join(self.install_dir, "miniz.h")) and \
               (os.path.exists(os.path.join(self.install_dir, "build", "libminiz.a")) or \
                os.path.exists(os.path.join(self.install_dir, "build", "miniz.lib")))

    def install(self, progress_callback=None):
        if self.installed:
            if progress_callback: progress_callback("miniz already installed.")
            return

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
            if progress_callback: progress_callback("Extracting miniz source...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(EXTENSIONS_DIR)
            
            extracted_path = os.path.join(EXTENSIONS_DIR, self.extract_folder_name)
            
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            shutil.move(extracted_path, self.install_dir)
            
            try: os.remove(zip_path)
            except: pass

            # 3. Build with CMake
            if progress_callback: progress_callback("Configuring miniz with CMake...")
            build_dir = os.path.join(self.install_dir, "build")
            if not os.path.exists(build_dir): os.makedirs(build_dir)
            
            cmake_args = [
                "cmake", "..", 
                "-DBUILD_SHARED_LIBS=OFF", 
                "-DMINIZ_BUILD_EXAMPLES=OFF",
                "-DMINIZ_BUILD_UNIT_TESTS=OFF"
            ]
            
            if os.name == 'nt' and shutil.which("mingw32-make"):
                 cmake_args.extend(["-G", "MinGW Makefiles"])

            result = subprocess.run(cmake_args, cwd=build_dir, capture_output=True, text=True)
            if result.returncode != 0:
                 raise Exception(f"miniz CMake Configuration Failed:\n{result.stderr}")

            # Build
            if progress_callback: progress_callback("Building miniz...")
            build_cmd = ["cmake", "--build", ".", "--config", "Release"]
            
            result = subprocess.run(build_cmd, cwd=build_dir, capture_output=True, text=True)
            if result.returncode != 0:
                 raise Exception(f"miniz Build Failed:\n{result.stderr}")

            if progress_callback: progress_callback("miniz installed successfully.")
            self.installed = True
            self.path = self.install_dir
            self.include_path = self.install_dir
            self.lib_path = build_dir

        except Exception as e:
            if progress_callback: progress_callback(f"Error: {e}")
            raise e

    def uninstall(self, progress_callback=None):
        if not self.installed:
            if progress_callback: progress_callback("miniz is not installed.")
            return
        
        try:
            if progress_callback: progress_callback("Uninstalling miniz...")
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            self.installed = False
            self.path = None
            self.include_path = None
            self.lib_path = None
            if progress_callback: progress_callback("miniz uninstalled successfully.")
        except Exception as e:
            if progress_callback: progress_callback(f"Error uninstalling miniz: {e}")
            raise e

    def get_version(self):
        return f"v{self.version}"

    def _on_rm_error(self, func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def get_include_path(self):
        return self.include_path

    def get_lib_path(self):
        return self.lib_path

    def get_link_flags(self):
        return ["-lminiz"]

class EnttExtension(Extension):
    def __init__(self):
        super().__init__("entt")
        self.version = "3.16.0"
        self.download_url = f"https://github.com/skypjack/entt/archive/refs/tags/v{self.version}.zip"
        self.zip_filename = f"entt-{self.version}.zip"
        self.extract_folder_name = f"entt-{self.version}"
        self.install_dir = os.path.join(EXTENSIONS_DIR, "entt")
        
        self.include_path = None

        if self.check_default_install():
            self.path = self.install_dir
            self.installed = True
            self.include_path = os.path.join(self.install_dir, "single_include")
        else:
            self.path = None
            self.installed = False

    def is_installed(self):
        if self.path == self.install_dir:
            if not self.check_default_install():
                self.installed = False
                self.path = None
        elif self.path: # manual path
             if not os.path.isdir(self.path):
                 self.installed = False
                 self.path = None
        else: # not installed, check defaulted
            if self.check_default_install():
                self.path = self.install_dir
                self.installed = True
                self.include_path = os.path.join(self.install_dir, "single_include")
        return self.installed

    def check_default_install(self):
        return os.path.exists(os.path.join(self.install_dir, "single_include", "entt", "entt.hpp"))

    def install(self, progress_callback=None):
        if self.installed:
            if progress_callback: progress_callback("EnTT already installed.")
            return

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
            if progress_callback: progress_callback("Extracting EnTT source...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(EXTENSIONS_DIR)
            
            extracted_path = os.path.join(EXTENSIONS_DIR, self.extract_folder_name)
            
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            shutil.move(extracted_path, self.install_dir)
            
            try: os.remove(zip_path)
            except: pass

            if progress_callback: progress_callback("EnTT installed successfully (Header-only).")
            self.installed = True
            self.path = self.install_dir
            self.include_path = os.path.join(self.install_dir, "single_include")

        except Exception as e:
            if progress_callback: progress_callback(f"Error: {e}")
            raise e

    def uninstall(self, progress_callback=None):
        if not self.installed:
            if progress_callback: progress_callback("EnTT is not installed.")
            return
        
        try:
            if progress_callback: progress_callback("Uninstalling EnTT...")
            if os.path.exists(self.install_dir):
                shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
            
            self.installed = False
            self.path = None
            self.include_path = None
            if progress_callback: progress_callback("EnTT uninstalled successfully.")
        except Exception as e:
            if progress_callback: progress_callback(f"Error uninstalling EnTT: {e}")
            raise e

    def get_version(self):
        return f"v{self.version}"

    def _on_rm_error(self, func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def get_include_path(self):
        return self.include_path

    def get_lib_path(self):
        return None

    def get_link_flags(self):
        return []

class GitHubFetchExtension(Extension):
    def __init__(self, repo_url, version="main"):
        # repo_url: https://github.com/user/repo
        self.repo_url = repo_url.rstrip('/')
        self.repo_name = self.repo_url.split('/')[-1]
        super().__init__(self.repo_name)
        self.version = version
        
        # We'll use a specific subdir for fetched content
        self.fetch_dir = os.path.join(EXTENSIONS_DIR, "fetched")
        self.install_dir = os.path.join(self.fetch_dir, self.repo_name)
        
        # For GitHub zips: https://github.com/user/repo/archive/refs/heads/main.zip
        # or tags: https://github.com/user/repo/archive/refs/tags/v1.0.0.zip
        if version.startswith('v') and any(char.isdigit() for char in version):
             self.download_url = f"{self.repo_url}/archive/refs/tags/{version}.zip"
        else:
             # Try tags first if it looks like a version, otherwise heads
             if any(char.isdigit() for char in version):
                 self.download_url = f"{self.repo_url}/archive/refs/tags/{version}.zip"
             else:
                 self.download_url = f"{self.repo_url}/archive/refs/heads/{version}.zip"
             
        self.zip_filename = f"{self.repo_name}-{version}.zip"
        
        self.include_path = None
        self.lib_path = None
        self.link_flags = []

        if self.is_installed():
            self.auto_detect_paths()

    def is_installed(self):
        return os.path.exists(os.path.join(self.install_dir)) and os.path.isdir(self.install_dir)

    def auto_detect_paths(self):
        # Search for include dir
        # Priority 1: Standard include directories (prefer installed artifacts)
        potential_includes = [
            os.path.join(self.install_dir, "install", "include"),
            os.path.join(self.install_dir, "include"),
            os.path.join(self.install_dir, "single_include"),
        ]
        
        found_inc = False
        for p in potential_includes:
            if os.path.isdir(p):

                # Check if it contains headers
                has_headers = False
                for root, dirs, files in os.walk(p):
                    if any(f.endswith(('.h', '.hpp', '.hxx')) for f in files):
                        has_headers = True
                        break
                if has_headers:
                    self.include_path = p
                    found_inc = True
                    break
        
        # Priority 2: Recursive search for any 'include' directory
        if not found_inc:
             candidates = []
             for root, dirs, files in os.walk(self.install_dir):
                 if "include" in dirs:
                     p = os.path.join(root, "include")
                     # Check if it actually has headers (recursively count)
                     header_count = 0
                     for r, d, f in os.walk(p):
                         header_count += sum(1 for x in f if x.endswith(('.h', '.hpp', '.hxx')))
                     
                     if header_count > 0:
                         candidates.append((p, header_count))
             
             if candidates:
                 # Pick the one with the most headers
                 candidates.sort(key=lambda x: x[1], reverse=True)
                 self.include_path = candidates[0][0]
                 found_inc = True

        # Priority 3: 'src' directory
        if not found_inc:
            p = os.path.join(self.install_dir, "src")
            if os.path.isdir(p):
                has_headers = False
                for root, dirs, files in os.walk(p):
                    if any(f.endswith(('.h', '.hpp', '.hxx')) for f in files):
                        has_headers = True
                        break
                if has_headers:
                    self.include_path = p
                    found_inc = True

        # Priority 4: Root directory
        if not found_inc:
             # Check if root has headers
             if any(f.endswith(('.h', '.hpp', '.hxx')) for f in os.listdir(self.install_dir)):
                 self.include_path = self.install_dir
                 found_inc = True
             # Or if root contains headers in subdirs (last resort, old behavior)
             elif any(f.endswith(('.h', '.hpp', '.hxx')) for root, dirs, files in os.walk(self.install_dir) for f in files):
                 self.include_path = self.install_dir
                 found_inc = True
        
        # Search for lib dir
        potential_libs = [
            os.path.join(self.install_dir, "install", "lib"),
            os.path.join(self.install_dir, "lib"),
            os.path.join(self.install_dir, "build"),
            os.path.join(self.install_dir, "bin"),
            self.install_dir
        ]

        for p in potential_libs:
            if os.path.isdir(p):
                if any(f.endswith(('.a', '.lib')) for root, dirs, files in os.walk(p) for f in files):
                    self.lib_path = p
                    break
        
        # If no lib path found, but it's a header-only lib, just use include_path
        if not self.lib_path:
            self.lib_path = self.include_path
        
        self.installed = found_inc

    def install(self, progress_callback=None):
        if self.is_installed():
             if progress_callback: progress_callback(f"'{self.name}' already fetched.")
             self.auto_detect_paths()
             return

        if not os.path.exists(self.fetch_dir):
            os.makedirs(self.fetch_dir)

        try:
            if progress_callback: progress_callback(f"Fetching {self.repo_url} ({self.version})...")
            zip_path = os.path.join(self.fetch_dir, self.zip_filename)
            
            response = requests.get(self.download_url, stream=True)
            if response.status_code != 200:
                # Try fallback for version naming (sometimes tags don't have 'v' or do)
                alt_version = self.version[1:] if self.version.startswith('v') else f"v{self.version}"
                alt_url = f"{self.repo_url}/archive/refs/tags/{alt_version}.zip"
                if progress_callback: progress_callback(f"Trying alternative URL: {alt_url}")
                response = requests.get(alt_url, stream=True)
                
            response.raise_for_status()
            
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            if progress_callback: progress_callback("Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # The first folder in the zip is usually the root of the repo
                namelist = zip_ref.namelist()
                if not namelist:
                    raise Exception("Downloaded zip is empty")
                    
                top_dir = namelist[0].split('/')[0]
                zip_ref.extractall(self.fetch_dir)
                
                extracted_path = os.path.join(self.fetch_dir, top_dir)
                if os.path.exists(self.install_dir):
                    shutil.rmtree(self.install_dir, onerror=self._on_rm_error)
                shutil.move(extracted_path, self.install_dir)

            try: os.remove(zip_path)
            except: pass

            self.auto_detect_paths()
            self.installed = True
            if progress_callback: progress_callback(f"'{self.name}' fetched and analyzed.")
            
            # 4. Auto-Build (CMake)
            if os.path.exists(os.path.join(self.install_dir, "CMakeLists.txt")):
                try:
                    if progress_callback: progress_callback(f"CMakeLists.txt found. Attempting to build {self.name}...")
                    build_dir = os.path.join(self.install_dir, "build")
                    install_dir = os.path.join(self.install_dir, "install")
                    if not os.path.exists(build_dir): os.makedirs(build_dir)
                    
                    # Configure
                    cmake_cmd = [
                        "cmake", "-S", self.install_dir, "-B", build_dir,
                        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
                        "-DBUILD_SHARED_LIBS=OFF",
                        "-DBUILD_TESTS=OFF",
                        "-DBUILD_EXAMPLES=OFF"
                    ]
                    
                    if os.name == 'nt' and shutil.which("mingw32-make"):
                         cmake_cmd.extend(["-G", "MinGW Makefiles"])
                         
                    if progress_callback: progress_callback("Configuring with CMake...")
                    subprocess.run(cmake_cmd, check=True, cwd=build_dir, capture_output=True)
                    
                    # Build & Install
                    if progress_callback: progress_callback("Building and Installing...")
                    build_cmd = ["cmake", "--build", build_dir, "--target", "install", "--config", "Release"]
                    subprocess.run(build_cmd, check=True, cwd=build_dir, capture_output=True)
                    
                    if progress_callback: progress_callback(f"Build successful. Artifacts installed to {install_dir}")
                    
                    # Re-detect paths to find the new install artifacts
                    self.auto_detect_paths()
                    
                except Exception as e:
                    if progress_callback: progress_callback(f"Warning: Automatic build failed: {e}. Continuing with source-only...")


        except Exception as e:
            if progress_callback: progress_callback(f"Error fetching {self.name}: {e}")
            raise e

    def _on_rm_error(self, func, path, exc_info):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def get_include_path(self):
        return self.include_path

    def get_lib_path(self):
        return self.lib_path

    def get_link_flags(self):
        flags = []
        # Auto-detect libs in the lib_path
        if self.lib_path and os.path.exists(self.lib_path):
            for f in os.listdir(self.lib_path):
                if f.endswith(('.a', '.lib')):
                    name = os.path.splitext(f)[0]
                    if name.startswith('lib'): name = name[3:]
                    # Avoid duplicates and common system libs if they somehow got here
                    flag = f"-l{name}"
                    if flag not in flags:
                        flags.append(flag)
        
        # Special case for webview on Windows
        if self.repo_name == "webview" and os.name == 'nt':
             sys_libs = ["-lole32", "-lshlwapi", "-lversion", "-luser32", "-ladvapi32", "-lshell32"]
             for lib in sys_libs:
                 if lib not in flags:
                     flags.append(lib)

        return flags

    def to_dict(self):
        return {
            "type": "github",
            "repo_url": self.repo_url,
            "version": self.version
        }

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

    def uninstall(self, progress_callback=None):
         if progress_callback: progress_callback(f"Custom extension '{self.name}' can be removed from the list.")

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
            "opencv": OpenCVExtension(),
            "miniaudio": MiniaudioExtension(),
            "tinyxml": TinyXMLExtension(),
            "miniz": MinizExtension(),
            "entt": EnttExtension()
        }
        self.load_custom_extensions()

    def load_custom_extensions(self):
        if os.path.exists(CUSTOM_EXTENSIONS_FILE):
            try:
                with open(CUSTOM_EXTENSIONS_FILE, 'r') as f:
                    data = json.load(f)
                    for ext_data in data:
                        if ext_data.get("type") == "github":
                            ext = GitHubFetchExtension(ext_data["repo_url"], ext_data["version"])
                        else:
                            ext = CustomExtension.from_dict(ext_data)
                        self.extensions[ext.name] = ext
            except Exception as e:
                print(f"Failed to load custom extensions: {e}")

    def save_custom_extensions(self):
        custom_exts = []
        for ext in self.extensions.values():
            if isinstance(ext, CustomExtension):
                custom_exts.append(ext.to_dict())
            elif isinstance(ext, GitHubFetchExtension):
                custom_exts.append(ext.to_dict())
                
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

    def remove_extension(self, name):
        if name in self.extensions:
            del self.extensions[name]
            self.save_custom_extensions()

    def get_extension(self, name):
        return self.extensions.get(name)

    def get_all_extensions(self):
        return self.extensions.values()

    def install_all(self, progress_callback=None):
        for ext in self.extensions.values():
            if not ext.is_installed(): 
                ext.install(progress_callback)