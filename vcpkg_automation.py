import os
import subprocess

class VcpkgManager:
    def __init__(self, internal_downloads_path, log_func=print):
        self.vcpkg_root = os.path.join(internal_downloads_path, "vcpkg")
        self.vcpkg_exe = os.path.join(self.vcpkg_root, "vcpkg.exe")
        self.triplet = "x64-mingw-dynamic"
        self.log_func = log_func

    def is_installed(self):
        return os.path.exists(self.vcpkg_exe)

    def is_package_installed(self, package_name):
        """Checks if a package is already installed by looking for its share directory."""
        # This is much faster than running 'vcpkg list'
        share_dir = os.path.join(self.get_installed_path(), "share", package_name)
        return os.path.isdir(share_dir)

    def install_package(self, package_name):
        if not self.is_installed():
            self.log_func("vcpkg not found. Please run caching/download script first.", "bold red")
            return False

        self.log_func(f"Installing {package_name} for {self.triplet}...")
        try:
            # Capture output to log it, providing feedback without printing directly
            process = subprocess.Popen(
                [self.vcpkg_exe, "install", f"{package_name}:{self.triplet}", f"--host-triplet={self.triplet}"],
                cwd=self.vcpkg_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # Stream stdout
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if line.strip():
                        self.log_func(line.strip())

            process.wait()

            if process.returncode != 0:
                stderr_output = process.stderr.read() if process.stderr else "No stderr output."
                self.log_func(f"Failed to install {package_name}.", "bold red")
                if stderr_output.strip():
                    self.log_func(f"Stderr:\n{stderr_output.strip()}", "bold red")
                return False

            self.log_func(f"Successfully installed {package_name}.", "bold green")
            return True
        except Exception as e:
            self.log_func(f"An exception occurred while installing {package_name}: {e}", "bold red")
            return False

    def get_installed_path(self):
        return os.path.join(self.vcpkg_root, "installed", self.triplet)

    def get_include_path(self):
        return os.path.join(self.get_installed_path(), "include")

    def get_lib_path(self):
        return os.path.join(self.get_installed_path(), "lib")

    def get_bin_path(self):
        return os.path.join(self.get_installed_path(), "bin")
