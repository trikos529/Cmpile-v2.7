import os
import sys
import shutil
import zipfile
import subprocess
import requests
import time
import errno
from rich.console import Console
from rich.progress import Progress

console = Console()

def is_tool_on_path(name):
    """Check whether `name` is on PATH and marked as executable."""
    return shutil.which(name) is not None

def _default_log(message, style=""):
    # Helper for standalone script running
    console.print(f"[{style}]{message}[/{style}]" if style else message)

if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INTERNAL_DOWNLOADS = os.path.join(BASE_DIR, "internal_downloads")
GCC_DIR = os.path.join(INTERNAL_DOWNLOADS, "gcc")
VCPKG_DIR = os.path.join(INTERNAL_DOWNLOADS, "vcpkg")

# LLVM-MinGW (UCRT, 64-bit)
# Provides Clang/LLD with MinGW-w64 runtime.
GCC_URL = "https://github.com/mstorsjo/llvm-mingw/releases/download/20251216/llvm-mingw-20251216-ucrt-x86_64.zip"
# MinGit
GIT_URL = "https://github.com/git-for-windows/git/releases/download/v2.53.0.windows.1/MinGit-2.53.0-64-bit.zip"

GIT_DIR = os.path.join(INTERNAL_DOWNLOADS, "git")

def download_file(url, target_path, log_func=_default_log):
    # If a custom log_func is provided, we avoid using the Rich progress bar
    # as it's not suitable for GUI logs.
    use_progress = (log_func == _default_log) and sys.stdout is not None and getattr(sys.stdout, 'isatty', lambda: False)()

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))

            if use_progress:
                with Progress(console=console) as progress:
                    task = progress.add_task(f"Downloading {os.path.basename(target_path)}...", total=total_size)
                    with open(target_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
            else:
                log_func(f"Downloading {os.path.basename(target_path)} ({total_size / 1024 / 1024:.2f} MB)...")
                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                log_func("Download complete.")

    except Exception as e:
        log_func(f"Failed to download {url}: {e}", "bold red")
        raise e

def install_git(log_func=_default_log):
    if is_tool_on_path("git"):
        log_func("Git is already available on PATH.", "bold blue")
        return
    if os.path.exists(GIT_DIR) and os.path.exists(os.path.join(GIT_DIR, "cmd", "git.exe")):
         return

    os.makedirs(INTERNAL_DOWNLOADS, exist_ok=True)
    zip_path = os.path.join(INTERNAL_DOWNLOADS, "git.zip")

    if not os.path.exists(zip_path):
        log_func(f"Downloading MinGit from {GIT_URL}...")
        try:
            download_file(GIT_URL, zip_path, log_func=log_func)
        except Exception as e:
            log_func(f"Failed to download Git: {e}", "bold red")
            return

    log_func("Extracting Git...")
    try:
        os.makedirs(GIT_DIR, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(GIT_DIR)

        log_func("Git installed successfully.", "bold green")
        os.remove(zip_path)
    except Exception as e:
         log_func(f"Failed to extract Git: {e}", "bold red")

def install_gcc(log_func=_default_log):
    if is_tool_on_path("clang") or is_tool_on_path("gcc"):
        log_func("An existing C/C++ compiler (clang/gcc) was found on PATH.", "bold blue")
        return
    if os.path.exists(GCC_DIR) and os.path.exists(os.path.join(GCC_DIR, "bin", "clang++.exe")):
        return

    os.makedirs(INTERNAL_DOWNLOADS, exist_ok=True)
    zip_path = os.path.join(INTERNAL_DOWNLOADS, "compiler.zip")

    if not os.path.exists(zip_path):
        log_func(f"Downloading LLVM-MinGW from {GCC_URL}...")
        download_file(GCC_URL, zip_path, log_func=log_func)

    log_func("Extracting Compiler...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(INTERNAL_DOWNLOADS)

        extracted_name = None
        for name in os.listdir(INTERNAL_DOWNLOADS):
            if name.startswith("llvm-mingw"):
                extracted_name = name
                break

        if extracted_name:
                extracted_path = os.path.join(INTERNAL_DOWNLOADS, extracted_name)

                max_retries = 5
                for i in range(max_retries):
                    try:
                        if os.path.exists(GCC_DIR):
                            def on_rm_error(func, path, exc_info):
                                os.chmod(path, 0o777)
                                func(path)
                            shutil.rmtree(GCC_DIR, onerror=on_rm_error)

                        time.sleep(0.5)
                        shutil.move(extracted_path, GCC_DIR)
                        break
                    except (PermissionError, OSError) as e:
                        if (isinstance(e, OSError) and e.errno not in [errno.EACCES, errno.ENOTEMPTY]) or i == max_retries - 1:
                            raise
                        time.sleep(1)
        else:
            raise Exception(f"Extraction failed: Could not find llvm-mingw folder in {INTERNAL_DOWNLOADS}")

        log_func("Compiler installed successfully.", "bold green")
        if os.path.exists(zip_path):
            os.remove(zip_path)
    except Exception as e:
        log_func(f"Compiler installation failed: {e}", "bold red")
        raise e

CMAKE_URL = "https://github.com/Kitware/CMake/releases/download/v4.2.3/cmake-4.2.3-windows-x86_64.zip"
CMAKE_DIR = os.path.join(INTERNAL_DOWNLOADS, "cmake")

def install_cmake(log_func=_default_log):
    if is_tool_on_path("cmake"):
        log_func("CMake is already available on PATH.", "bold blue")
        return
    if os.path.exists(CMAKE_DIR) and os.path.exists(os.path.join(CMAKE_DIR, "bin", "cmake.exe")):
         return

    os.makedirs(INTERNAL_DOWNLOADS, exist_ok=True)
    zip_path = os.path.join(INTERNAL_DOWNLOADS, "cmake.zip")

    if not os.path.exists(zip_path):
        log_func(f"Downloading CMake from {CMAKE_URL}...")
        try:
            download_file(CMAKE_URL, zip_path, log_func=log_func)
        except Exception as e:
            log_func(f"Failed to download CMake: {e}", "bold red")
            return

    log_func("Extracting CMake...")
    try:
        if os.path.exists(CMAKE_DIR):
             shutil.rmtree(CMAKE_DIR)
             
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(INTERNAL_DOWNLOADS)
        
        extracted_name = None
        for name in os.listdir(INTERNAL_DOWNLOADS):
            if name.startswith("cmake-") and name.endswith("windows-x86_64"):
                extracted_name = name
                break
        
        if extracted_name:
             shutil.move(os.path.join(INTERNAL_DOWNLOADS, extracted_name), CMAKE_DIR)
        else:
             raise Exception("Could not find extracted CMake folder")

        log_func("CMake installed successfully.", "bold green")
        os.remove(zip_path)
    except Exception as e:
         log_func(f"Failed to extract CMake: {e}", "bold red")

def install_vcpkg(git_path_env=None, log_func=_default_log):
    if is_tool_on_path("vcpkg"):
        log_func("vcpkg is already available on PATH.", "bold blue")
        return
    if os.path.exists(VCPKG_DIR) and os.path.exists(os.path.join(VCPKG_DIR, "vcpkg.exe")):
         return

    log_func("Cloning vcpkg...")
    env = os.environ.copy()
    if git_path_env:
        env["PATH"] = git_path_env + os.pathsep + env["PATH"]

    if os.path.exists(VCPKG_DIR):
        shutil.rmtree(VCPKG_DIR)

    try:
        subprocess.run(["git", "clone", "https://github.com/microsoft/vcpkg.git", VCPKG_DIR], check=True, env=env, capture_output=True, text=True)

        log_func("Bootstrapping vcpkg...")
        bootstrap_script = os.path.join(VCPKG_DIR, "bootstrap-vcpkg.bat")
        subprocess.run([bootstrap_script], cwd=VCPKG_DIR, check=True, shell=True, env=env, capture_output=True, text=True)

        log_func("vcpkg installed successfully.", "bold green")
    except subprocess.CalledProcessError as e:
        log_func(f"vcpkg installation failed: {e.stderr}", "bold red")
        raise e

if __name__ == "__main__":
    _default_log("Checking dependencies...", "bold blue")
    install_git(log_func=_default_log)
    install_gcc(log_func=_default_log)
    install_cmake(log_func=_default_log)

    git_cmd_path = os.path.join(GIT_DIR, "cmd")
    install_vcpkg(git_path_env=git_cmd_path, log_func=_default_log)

    _default_log("Dependencies check complete.", "bold blue")