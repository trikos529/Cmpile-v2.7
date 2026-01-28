import re

# Simple mapping of common headers to vcpkg package names
# This is non-exhaustive and will need updates.
HEADER_MAPPING = {
    "nlohmann/json.hpp": "nlohmann-json",
    "fmt/core.h": "fmt",
    "fmt/format.h": "fmt",
    "spdlog/spdlog.h": "spdlog",
    "sqlite3.h": "sqlite3",
    "curl/curl.h": "curl",
    "gtest/gtest.h": "gtest",
    "GL/glew.h": "glew",
    "GLFW/glfw3.h": "glfw3",
    "glm/glm.hpp": "glm",
    "zlib.h": "zlib",
    "openssl/ssl.h": "openssl",
    "boost/asio.hpp": "boost-asio",
    "raylib.h": "raylib",
    "imgui.h": "imgui",
    "assimp/scene.h": "assimp",
    "eigen3/Eigen/Dense": "eigen3",
    "yaml-cpp/yaml.h": "yaml-cpp",
    "miniaudio/miniaudio.h": "miniaudio",
    "absent/absent.h": "absent",
    "vulkan/vulkan.h": "vulkan",
    "anyrpc/anyrpc.h": "anyrpc",
    "adios2/adios2.h": "adios2",
    "aom/aom.h": "aom",
    "aom/aom_codec.h": "aom",
    "openfbx/fbx.h": "openfbx",
    "ffmpeg/avformat.h": "ffmpeg",
    "ffmpeg/avcodec.h": "ffmpeg",
    "ffmpeg/avutil.h": "ffmpeg",
    "audiofile/audiofile.h": "audiofile",
    "utf8.h": "utf8",
    "SDL2/SDL.h": "sdl2",
    "QApplication": "qtbase",
    "QDebug": "qtbase",
    "QString": "qtbase",
}

# Mapping of package names to specific library names (for linking)
# This is used when the package name doesn't match the library name directly.
PACKAGE_LIBS = {
    "qtbase": ["Qt6Widgets", "Qt6Gui", "Qt6Core", "Qt6Network"],
    "sdl2": ["SDL2main", "SDL2"],
}

def find_includes(file_path):
    """
    Scans a C/C++ file for #include directives.
    Returns a set of included files (strings).
    """
    includes = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Regex for #include <path> or #include "path"
                match = re.search(r'^\s*#include\s*[<"]([^>"]+)[>"]', line)
                if match:
                    includes.add(match.group(1))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return includes

def find_github_fetches(file_path):
    """
    Scans a C/C++ file for @fetch directives.
    Format: // @fetch https://github.com/user/repo [version]
    Returns a list of tuples (repo_url, version).
    """
    fetches = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Regex for // @fetch <url> [version]
                match = re.search(r'//\s*@fetch\s+(https://github\.com/[^\s@]+)(?:\s*@?\s*([^\s]+))?', line)
                if match:
                    repo_url = match.group(1).strip()
                    version = match.group(2).strip() if match.group(2) else "main"
                    fetches.append((repo_url, version))
    except Exception as e:
        print(f"Error reading {file_path} for fetches: {e}")
    return fetches

def map_includes_to_packages(includes):
    """
    Maps a list of include paths to potential vcpkg package names.
    Returns a set of package names.
    """
    packages = set()
    for inc in includes:
        # Check exact match in mapping
        if inc in HEADER_MAPPING:
            packages.add(HEADER_MAPPING[inc])
            continue
        
        # Check heuristics
        # Logic: if include is "foo/bar.h", try mapping "foo" if it's not standard
        # Identifying standard libs is hard without a list, but we can try ignoring them?
        # For now, minimal heuristics to avoid false positives on std libs (iostream, vector, etc)
        # Assuming vcpkg packages usually live in subdirs or have known headers.
        
        # We can detect if it looks like a library (has a slash)
        if '/' in inc:
            parts = inc.split('/')
            root = parts[0]
            
            # Special handling for Qt
            # Maps QtWidgets, QtCore, QtNetwork, etc. to 'qtbase' (Qt6 default in vcpkg)
            if root.startswith("Qt") and root[2:].isalnum():
                packages.add("qtbase")
                continue
            
            # Heuristic: map the root folder if it matches a known pattern?
            # actually commonly libs match the folder name: generic usage
            if root.isalnum():
                packages.add(root.lower())
            
    return packages
