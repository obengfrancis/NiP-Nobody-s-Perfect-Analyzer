import ast
import csv
import functools
import io
import json
import logging
import os
import pickle
import random
import re
import shutil
import subprocess
from hashlib import md5
from subprocess import CalledProcessError, TimeoutExpired
import sys
import tempfile
import time
import unicodedata
import warnings
from configparser import ConfigParser
from contextlib import contextmanager
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from multiprocessing import Manager, Pool
from pathlib import Path
import babel
import psutil
import timeout_decorator
from tqdm import tqdm
from typing import Tuple, List, Set

# Increase recursion limit if necessary
sys.setrecursionlimit(1500)


# Function to suppress warnings temporarily during progress bar updates
def suppress_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)


# Function to redirect logs to file
def redirect_logs_to_file(log_file="processing_warnings.log"):
    # Setting up logging to file
    handler = RotatingFileHandler(log_file, maxBytes=100 * 1024, backupCount=2)
    logging.getLogger().addHandler(handler)


# Disk monitoring function
def check_disk_usage():
    usage = shutil.disk_usage("/")
    logging.info(
        f"Disk usage: {usage.free / (1024 ** 3):.2f} GB free of {usage.total / (1024 ** 3):.2f} GB"
    )


# MonitorSystem stats logging function
def log_system_stats():
    disk_usage = psutil.disk_usage("/")
    logging.info(
        f"Disk usage: {disk_usage.free / (1024 ** 3):.2f} GB free"
    )

    memory_info = psutil.virtual_memory()
    logging.info(f"Memory usage: {memory_info.percent}% used")

    process_count = len(psutil.pids())
    logging.info(f"Number of running processes: {process_count}")


def setup_logging():
    manager = Manager()
    log_queue = manager.Queue()
    # This log rotation to avoid large log files
    handler = RotatingFileHandler(
        "processing.log", maxBytes=100 * 1024, backupCount=2
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    listener = QueueListener(log_queue, handler)
    listener.start()

    logging.basicConfig(level=logging.INFO, handlers=[QueueHandler(log_queue)])

    return log_queue, listener


def worker_init(log_queue):
    queue_handler = QueueHandler(log_queue)
    logger = logging.getLogger()
    logger.addHandler(queue_handler)
    logger.setLevel(logging.INFO)


def global_exception_handler(exc_type, exc_value, exc_traceback):
    logging.error(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def create_config_file():
    config = ConfigParser()
    config["paths"] = {
        "input_csv_file_path": "input_csv_file_1.csv",  # Replace with the actual input path
        "output_csv_file_path": "analyze_error_handling_output.csv",
        "clone_dir": "cloned_repos",
        "cache_file": "analysis_cache.pkl",
    }
    with open("config.ini", "w") as configfile:
        config.write(configfile)


def update_config_file():
    config = ConfigParser()
    config.read("config.ini")
    if "paths" not in config:
        config["paths"] = {}
    config["paths"]["input_csv_file_path"] = config.get(
        "paths", "input_csv_file_path", fallback="input_csv_file_1.csv" # Replace with the actual input path
    )
    config["paths"]["output_csv_file_path"] = config.get(
        "paths",
        "output_csv_file_path",
        fallback="analyze_error_handling_output.csv",
    )
    config["paths"]["clone_dir"] = config.get(
        "paths", "clone_dir", fallback="cloned_repos",
    )
    config["paths"]["cache_file"] = config.get(
        "paths", "cache_file", fallback="analysis_cache.pkl",
    )
    with open("config.ini", "w") as configfile:
        config.write(configfile)


def load_configuration():
    config = ConfigParser()
    config.read("config.ini")
    return config


@contextmanager
def open_file(file_path):
    encodings = [
        'utf-8',
        'latin1',
        'iso-8859-1',
        'ascii',
        'utf-16',
        'utf-32',
        'cp1252',
        'cp850',
        'mac_roman',
    ]
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                yield f
            return  # If successful, exit the context manager
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        f"Unable to decode {file_path} with any of the attempted encodings"
    )



"""
This module provides AST-based detection of HTTP client libraries across
multiple languages. Unlike simple string matching, this approach:
- Avoids false positives from comments/strings
- Detects actual import statements
- Consistent with enhanced resilience parsers
"""

# ============================================================================
#  HTTP Library Definitions
# ============================================================================

HTTP_LIBRARIES = {
    "python": {
        # Standard library
        "http.client": "standard",
        "urllib": "standard",
        "urllib.request": "standard",
        "urllib2": "standard",
        "urllib3": "third_party",
        "httplib": "standard",
        "httplib2": "third_party",
        
        # Popular third-party
        "requests": "third_party",
        "httpx": "third_party",
        "aiohttp": "third_party",
        "tornado.httpclient": "third_party",
        "treq": "third_party",
    },
    
    "java": {
        # Standard library
        "java.net.http.HttpClient": "standard",
        "java.net.HttpURLConnection": "standard",
        
        # Apache
        "org.apache.http": "apache_httpclient",
        "org.apache.httpcomponents": "apache_httpclient",
        
        # Popular third-party
        "okhttp3.OkHttpClient": "okhttp",
        "com.squareup.okhttp": "okhttp",
        "org.springframework.web.client.RestTemplate": "spring",
        "org.springframework.web.reactive.function.client.WebClient": "spring",
        "feign.Client": "feign",
        "com.netflix.feign": "feign",
        "org.glassfish.jersey.client": "jersey",
        "com.ning.http.client": "async_http_client",
    },
    
    "javascript": {
        "axios": "axios",
        "fetch": "standard",
        "node-fetch": "node_fetch",
        "isomorphic-fetch": "isomorphic_fetch",
        "cross-fetch": "cross_fetch",
        "superagent": "superagent",
        "request": "request",
        "got": "got",
        "undici": "undici",
        "ky": "ky",
        "wretch": "wretch",
        "needle": "needle",
        "http": "standard",
        "https": "standard",
        "node:http": "standard",
        "node:https": "standard",
    },
    
    "typescript": {
        "axios": "axios",
        "fetch": "standard",
        "node-fetch": "node_fetch",
        "isomorphic-fetch": "isomorphic_fetch",
        "cross-fetch": "cross_fetch",
        "superagent": "superagent",
        "got": "got",
        "undici": "undici",
        "ky": "ky",
        "wretch": "wretch",
        "http": "standard",
        "https": "standard",
        "node:http": "standard",
        "node:https": "standard",
    },
    
    "go": {
        "net/http": "standard",
        "github.com/go-resty/resty": "resty",
        "github.com/valyala/fasthttp": "fasthttp",
        "github.com/dghubble/sling": "sling",
        "github.com/parnurzeal/gorequest": "gorequest",
        "gopkg.in/h2non/gentleman": "gentleman",
    },
    
    "csharp": {
        "System.Net.Http.HttpClient": "standard",
        "System.Net.WebClient": "standard",
        "System.Net.HttpWebRequest": "standard",
        "RestSharp": "restsharp",
        "Flurl.Http": "flurl",
        "Refit": "refit",
    },
    
    "ruby": {
        "net/http": "standard",
        "Net::HTTP": "standard",
        "httparty": "httparty",
        "rest-client": "rest_client",
        "faraday": "faraday",
        "typhoeus": "typhoeus",
        "open-uri": "standard",
        "curb": "curb",
        "excon": "excon",
        "http.rb": "http_rb",
    },
    
    "kotlin": {
        "okhttp3.OkHttpClient": "okhttp",
        "com.squareup.okhttp": "okhttp",
        "retrofit2": "retrofit",
        "com.squareup.retrofit2": "retrofit",
        "fuel": "fuel",
        "com.github.kittinunf.fuel": "fuel",
        "io.ktor.client": "ktor",
        "org.http4k": "http4k",
        "java.net.http.HttpClient": "standard",
    },
    
    "swift": {
        "URLSession": "standard",
        "Foundation.URLSession": "standard",
        "Alamofire": "alamofire",
        "Moya": "moya",
        "URLRequest": "standard",
        "NWConnection": "standard",
        "AsyncHTTPClient": "async_http_client",
    }
}


# ============================================================================
#  Python HTTP Library Detection (AST-based)
# ============================================================================

def detect_python_http_libraries(code: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in Python code using AST parsing.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            # Import statements: import requests
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module in HTTP_LIBRARIES["python"]:
                        found_libraries.add(module)
                    # Check full path: urllib.request
                    if alias.name in HTTP_LIBRARIES["python"]:
                        found_libraries.add(alias.name)
            
            # From imports: from http.client import HTTPConnection
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in HTTP_LIBRARIES["python"]:
                        found_libraries.add(module)
                    # Check full module path
                    if node.module in HTTP_LIBRARIES["python"]:
                        found_libraries.add(node.module)
    
    except SyntaxError as e:
        logging.debug(f"Python AST parse error (may be invalid Python): {e}")
        return False, []
    except Exception as e:
        logging.warning(f"Error parsing Python for HTTP libraries: {e}")
        return False, []
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  Java HTTP Library Detection (Import-based)
# ============================================================================

def detect_java_http_libraries(code: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in Java code using import statement analysis.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    # Pattern to match import statements
    import_pattern = r'^\s*import\s+(?:static\s+)?([a-zA-Z0-9_.]+(?:\.\*)?)\s*;'
    
    for line in code.split('\n'):
        match = re.match(import_pattern, line)
        if match:
            import_path = match.group(1)
            
            # Check against known HTTP libraries
            for lib_pattern, lib_name in HTTP_LIBRARIES["java"].items():
                if import_path.startswith(lib_pattern):
                    # Add the canonical library name
                    if lib_name == "okhttp":
                        found_libraries.add("OkHttp")
                    elif lib_name == "spring":
                        if "RestTemplate" in import_path:
                            found_libraries.add("RestTemplate")
                        elif "WebClient" in import_path:
                            found_libraries.add("WebClient")
                    elif lib_name == "apache_httpclient":
                        found_libraries.add("Apache HttpClient")
                    elif lib_name == "feign":
                        found_libraries.add("Feign")
                    elif lib_name == "jersey":
                        found_libraries.add("Jersey")
                    elif lib_name == "async_http_client":
                        found_libraries.add("AsyncHttpClient")
                    elif lib_name == "standard":
                        if "HttpClient" in import_path:
                            found_libraries.add("HttpClient")
                        elif "HttpURLConnection" in import_path:
                            found_libraries.add("HttpURLConnection")
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  JavaScript/TypeScript HTTP Library Detection (Import-based)
# ============================================================================

def detect_js_ts_http_libraries(code: str, language: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in JavaScript/TypeScript code using import analysis.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    # Patterns for ES6 imports and require statements
    patterns = [
        r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', 
        r'import\s+[\'"]([^\'"]+)[\'"]',               
        r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',     
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, code):
            module = match.group(1)
            
            # Check if it's an HTTP library
            if module in HTTP_LIBRARIES[language]:
                found_libraries.add(module)
            
            # Also check package scope: @scope/package
            base_module = module.split('/')[0]
            if base_module in HTTP_LIBRARIES[language]:
                found_libraries.add(base_module)
    
    # Check for fetch API usage (standard but worth noting)
    if re.search(r'\bfetch\s*\(', code):
        found_libraries.add("fetch")
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  Go HTTP Library Detection (Import-based)
# ============================================================================

def detect_go_http_libraries(code: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in Go code using import analysis.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    # Pattern for Go imports
    # Single: import "net/http"
    # Multiple: import ( ... )
    
    # Single import
    single_pattern = r'import\s+"([^"]+)"'
    for match in re.finditer(single_pattern, code):
        import_path = match.group(1)
        if import_path in HTTP_LIBRARIES["go"]:
            found_libraries.add(import_path)
    
    # Multiple imports
    multi_pattern = r'import\s*\(\s*((?:[^)]*\n)*)\s*\)'
    for match in re.finditer(multi_pattern, code, re.MULTILINE):
        import_block = match.group(1)
        for line in import_block.split('\n'):
            import_match = re.search(r'"([^"]+)"', line)
            if import_match:
                import_path = import_match.group(1)
                if import_path in HTTP_LIBRARIES["go"]:
                    found_libraries.add(import_path)
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  C# HTTP Library Detection (Using-based)
# ============================================================================

def detect_csharp_http_libraries(code: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in C# code using using statement analysis.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    # Pattern for using statements
    using_pattern = r'^\s*using\s+(?:static\s+)?([a-zA-Z0-9_.]+)\s*;'
    
    for line in code.split('\n'):
        match = re.match(using_pattern, line)
        if match:
            namespace = match.group(1)
            
            # Check against known HTTP libraries
            for lib_pattern, lib_name in HTTP_LIBRARIES["csharp"].items():
                if namespace.startswith(lib_pattern.split('.')[0]):
                    if lib_name == "standard":
                        if "HttpClient" in namespace:
                            found_libraries.add("HttpClient")
                        elif "WebClient" in namespace:
                            found_libraries.add("WebClient")
                        elif "HttpWebRequest" in namespace:
                            found_libraries.add("HttpWebRequest")
                    else:
                        found_libraries.add(lib_pattern)
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  Ruby HTTP Library Detection (Require-based)
# ============================================================================

def detect_ruby_http_libraries(code: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in Ruby code using require statement analysis.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    # Patterns for Ruby require/require_relative statements
    patterns = [
        r'require\s+[\'"]([^\'"]+)[\'"]',           # require 'httparty'
        r'require_relative\s+[\'"]([^\'"]+)[\'"]',  # require_relative 'http_client'
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, code):
            module = match.group(1)
            
            # Check if it's an HTTP library
            if module in HTTP_LIBRARIES["ruby"]:
                found_libraries.add(module)
            
            # Also check base module name (e.g., 'net/http' -> 'net/http')
            for lib in HTTP_LIBRARIES["ruby"]:
                if module.startswith(lib.replace('-', '_')):
                    found_libraries.add(lib)
    
    # Check for standard library usage
    if re.search(r'\bNet::HTTP\b', code):
        found_libraries.add("net/http")
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  Kotlin HTTP Library Detection (Import-based)
# ============================================================================

def detect_kotlin_http_libraries(code: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in Kotlin code using import statement analysis.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    # Pattern to match Kotlin import statements
    import_pattern = r'^\s*import\s+([a-zA-Z0-9_.]+(?:\.\*)?)'
    
    for line in code.split('\n'):
        match = re.match(import_pattern, line)
        if match:
            import_path = match.group(1)
            
            # Check against known HTTP libraries
            for lib_pattern, lib_name in HTTP_LIBRARIES["kotlin"].items():
                if import_path.startswith(lib_pattern.split('.')[0]):
                    # Add the canonical library name
                    if lib_name == "okhttp":
                        found_libraries.add("OkHttp")
                    elif lib_name == "retrofit":
                        found_libraries.add("Retrofit")
                    elif lib_name == "fuel":
                        found_libraries.add("Fuel")
                    elif lib_name == "ktor":
                        found_libraries.add("ktor")
                    elif lib_name == "http4k":
                        found_libraries.add("http4k")
                    elif lib_name == "standard":
                        if "HttpClient" in import_path:
                            found_libraries.add("java.net.http.HttpClient")
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  Swift HTTP Library Detection (Import-based)
# ============================================================================

def detect_swift_http_libraries(code: str) -> Tuple[bool, List[str]]:
    """
    Detect HTTP libraries in Swift code using import statement analysis.
    Returns: (has_http_library: bool, libraries_found: list)
    """
    found_libraries = set()
    
    # Pattern to match Swift import statements
    import_pattern = r'^\s*import\s+([a-zA-Z0-9_.]+)'
    
    for line in code.split('\n'):
        match = re.match(import_pattern, line)
        if match:
            module = match.group(1)
            
            # Check if it's an HTTP library
            for lib_pattern, lib_name in HTTP_LIBRARIES["swift"].items():
                if module == lib_pattern.split('.')[0]:
                    # Add the canonical library name
                    if lib_name == "standard":
                        if module == "Foundation":
                            found_libraries.add("URLSession")
                    elif lib_name == "alamofire":
                        found_libraries.add("Alamofire")
                    elif lib_name == "moya":
                        found_libraries.add("Moya")
                    elif lib_name == "async_http_client":
                        found_libraries.add("AsyncHTTPClient")
    
    # Check for URLSession usage (standard but often used without explicit import)
    if re.search(r'\bURLSession\b', code):
        found_libraries.add("URLSession")
    
    # Check for URLRequest
    if re.search(r'\bURLRequest\b', code):
        found_libraries.add("URLRequest")
    
    return len(found_libraries) > 0, sorted(list(found_libraries))


# ============================================================================
#  Main Detection Function (Language Router)
# ============================================================================

def detect_http_libraries_enhanced(code: str, language: str) -> Tuple[bool, List[str]]:
    """
    This function uses language-specific parsers to accurately detect HTTP
    client libraries by analyzing import statements rather than simple string
    matching. This eliminates false positives from comments and strings.
    
    Args:
        code: Source code to analyze
        language: Programming language (lowercase)
    
    Returns:
        Tuple of (has_http_library: bool, libraries_found: List[str])
    
    Example:
        >>> code = 'import requests\\nresponse = requests.get(url)'
        >>> has_http, libs = detect_http_libraries_enhanced(code, 'python')
        >>> print(has_http, libs)
        True ['requests']
    """
    language = language.lower()
    
    try:
        if language == "python":
            return detect_python_http_libraries(code)
        
        elif language == "java":
            return detect_java_http_libraries(code)
        
        elif language in ["javascript", "typescript"]:
            return detect_js_ts_http_libraries(code, language)
        
        elif language == "go":
            return detect_go_http_libraries(code)
        
        elif language == "csharp":
            return detect_csharp_http_libraries(code)
        
        elif language == "ruby":
            return detect_ruby_http_libraries(code)
        
        elif language == "kotlin":
            return detect_kotlin_http_libraries(code)
        
        elif language == "swift":
            return detect_swift_http_libraries(code)
        
        else:
            logging.warning(f"HTTP library detection not implemented for language: {language}")
            return False, []
    
    except Exception as e:
        logging.error(f"Error in HTTP library detection for {language}: {e}")
        return False, []


# ============================================================================
#  Backward Compatibility Wrapper
# ============================================================================

def detect_http_libraries(code: str, language: str) -> Tuple[bool, List[str]]:
    """
    Backward compatible wrapper for detect_http_libraries_enhanced.
    """
    return detect_http_libraries_enhanced(code, language)


# ============================================================================
#  Python Parser with Context-Aware Detection
#  Manual implementation detection
# ============================================================================
def parse_python_code(code):
    """
    Enhanced Python parser with:
    - Context-aware keyword detection (reduces false positives)
    - Import detection for resilience libraries
    - Detailed pattern tracking
    """
    error_handling_type = "None"
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        logging.error(
            f"SyntaxError: Invalid Python code. Detail: {str(e)}"
        )
        return error_handling_type, None  # Return None to indicate parser failure

    class ErrorHandlingVisitor(ast.NodeVisitor):
        def __init__(self):
            self.has_basic_handling = False
            self.has_advanced_handling = False
            # Track specific patterns for detailed taxonomy.
            self.patterns = {
                "try_catch": False,
                "timeout": False,
                "retry": False,
                "circuit_breaker": False,
                "exponential_backoff": False,
                "status_check": False,
            }
            # Track imports for better detection
            self.resilience_imports = set()

        def visit_Import(self, node):
            """Detect imports of resilience libraries"""
            for alias in node.names:
                if alias.name in {
                    "tenacity",
                    "pybreaker",
                    "backoff",
                    "retry",
                    "circuit_breaker",
                }:
                    self.resilience_imports.add(alias.name)
                    self.has_advanced_handling = True
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            """Detect from-imports of resilience libraries"""
            if node.module in {
                "tenacity",
                "pybreaker",
                "backoff",
                "retry",
                "urllib3.util.retry",
                "requests.adapters",
            }:
                self.resilience_imports.add(node.module)
                self.has_advanced_handling = True
            self.generic_visit(node)

        def visit_Try(self, node):
            self.has_basic_handling = True
            self.patterns["try_catch"] = True
            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            self.has_basic_handling = True
            self.patterns["try_catch"] = True
            self.generic_visit(node)

        def visit_Call(self, node):
            """Enhanced call detection with context awareness"""
            # Check for function calls (not variables)
            if isinstance(node.func, ast.Name):
                func_name = node.func.id.lower()
                # Only count as advanced if it's a FUNCTION CALL
                if func_name == "timeout":
                    self.has_advanced_handling = True
                    self.patterns["timeout"] = True
                elif func_name == "retry":
                    self.has_advanced_handling = True
                    self.patterns["retry"] = True
                elif func_name in {"circuitbreaker", "circuit_breaker"}:
                    self.has_advanced_handling = True
                    self.patterns["circuit_breaker"] = True
                elif func_name == "backoff":
                    self.has_advanced_handling = True
                    self.patterns["exponential_backoff"] = True

            elif isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr.lower()
                # HTTP status checks (basic)
                if attr_name in {"status_code", "raise_for_status"}:
                    self.has_basic_handling = True
                    self.patterns["status_check"] = True
                # Method-based retry/timeout patterns (advanced)
                elif attr_name in {"retry", "with_retry"}:
                    self.has_advanced_handling = True
                    self.patterns["retry"] = True
                elif attr_name in {"timeout", "with_timeout"}:
                    self.has_advanced_handling = True
                    self.patterns["timeout"] = True
                elif attr_name in {"with_backoff", "exponential_backoff"}:
                    self.has_advanced_handling = True
                    self.patterns["exponential_backoff"] = True

            self.generic_visit(node)

        def visit_With(self, node):
            """Detect context managers for timeout/retry"""
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    if isinstance(item.context_expr.func, ast.Name):
                        func_name = item.context_expr.func.id.lower()
                        if func_name == "timeout":
                            self.has_advanced_handling = True
                            self.patterns["timeout"] = True
                        elif func_name == "retry":
                            self.has_advanced_handling = True
                            self.patterns["retry"] = True
                        elif func_name in {"circuitbreaker", "circuit_breaker"}:
                            self.has_advanced_handling = True
                            self.patterns["circuit_breaker"] = True
                        elif func_name == "backoff":
                            self.has_advanced_handling = True
                            self.patterns["exponential_backoff"] = True
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            """Detect decorator-based patterns"""
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    dec_name = decorator.id.lower()
                    if dec_name == "retry":
                        self.has_advanced_handling = True
                        self.patterns["retry"] = True
                    elif dec_name == "timeout":
                        self.has_advanced_handling = True
                        self.patterns["timeout"] = True
                    elif dec_name in {"circuitbreaker", "circuit_breaker"}:
                        self.has_advanced_handling = True
                        self.patterns["circuit_breaker"] = True
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name):
                        dec_name = decorator.func.id.lower()
                        if dec_name == "retry":
                            self.has_advanced_handling = True
                            self.patterns["retry"] = True
                        elif dec_name == "timeout":
                            self.has_advanced_handling = True
                            self.patterns["timeout"] = True
            self.generic_visit(node)

    visitor = ErrorHandlingVisitor()
    visitor.visit(tree)

    if visitor.has_basic_handling and visitor.has_advanced_handling:
        error_handling_type = "Mixed"
    elif visitor.has_advanced_handling:
        error_handling_type = "Advanced"
    elif visitor.has_basic_handling:
        error_handling_type = "Basic"

    return error_handling_type, visitor.patterns


def preprocess_java_code(code):
    """
    Preprocess Java code to handle common parsing issues:
    - Remove BOM and normalize Unicode
    - Handle problematic annotations
    - Normalize line endings
    - Remove invalid control characters
    - Standardize quotes and escape sequences

    This preprocessing improves JavaParser's ability to parse real-world
    code that may have encoding issues, non-standard formatting, or
    platform-specific line endings.
    """
    # Remove BOM and normalize Unicode
    code = code.replace("\ufeff", "")
    code = unicodedata.normalize("NFKC", code)
    code = code.encode("utf-16", "surrogatepass").decode("utf-16")

    # Additional preprocessing to handle problematic annotations
    code = re.sub(
        r"@(\w+)\s*(\([^)]*\))?\s*(?=class|interface|enum|@interface)",
        r"/* @\1\2 */",
        code,
    )

    # Normalize line endings
    code = code.replace("\r\n", "\n").replace("\r", "\n")
    code = code.replace("\u2028", "\n").replace("\u2029", "\n")

    # Remove invalid control characters
    code = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", code)

    # Standardize quote characters (normalize curly quotes to straight)
    code = code.replace("’", "'").replace("“", '"').replace("”", '"')

    code = re.sub(r'("(?:[^"\\]|\\.)*$)', r'\1"', code)  # Close unclosed double quotes
    code = re.sub(r"('(?:[^'\\]|\\.)*$)", r"\1'", code)  # Close unclosed single quotes

    # Handle hash selectively (e.g., color codes)
    code = re.sub(
        r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?!\w)", r"COLOR_\1", code
    )

    # Escape special characters and balance quotes
    code = re.sub(
        r"\\u([0-9A-Fa-f]{4})",
        lambda m: "\\u" + m.group(1).upper(),
        code,
    )  # Normalize Unicode escapes to uppercase
    code = re.sub(
        r'"(.*?)"',
        lambda m: '"'
        + m.group(1).replace("#", "\\#").replace("\n", "\\n")
        + '"',
        code,
    )
    code = re.sub(
        r'(\\*)"', lambda m: "@@QUOTE@@" if len(m.group(1)) % 2 == 0 else m.group(0), code
    )
    code = re.sub(
        r"(\\*)'",
        lambda m: "@@SINGLE_QUOTE@@"
        if len(m.group(1)) % 2 == 0
        else m.group(0),
        code,
    )
    code = re.sub(r"(\\+)", r"\\\\", code)

    # Handle emojis and symbols
    code = re.sub(
        r"[^\x00-\x7F]",
        lambda x: f"\\u{ord(x.group(0)):04x}",
        code,
    )

    # Normalize block comments
    code = re.sub(r"/\*.*?\*/", "/* */", code, flags=re.DOTALL)
    code = re.sub(r"/\*.*$", "/* */", code, flags=re.DOTALL)

    # Remove line comments
    code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)

    # Handle unescaped line breaks in strings
    def replace_newlines(match):
        return (
            match.group(1)
            + match.group(2)
            + match.group(3).replace("\n", "\\n")
            + match.group(4)
            + match.group(2)
        )

    code = re.sub(
        r'([^\\])(["\'`])(.*?)\n(.*?)\2',
        replace_newlines,
        code,
        flags=re.DOTALL,
    )

    # Remove unwanted symbols (e.g., "So" category in Unicode)
    code = re.sub(r"[^\w\s#@,\"'(){}\[\]<>;.:*/+=-]", "", code)

    # Ensure the code ends with a newline
    if not code.endswith("\n"):
        code += "\n"

    return code


# ============================================================================
# Enhanced Java Parser with Debug Logging
# Addresses Java zero Advanced/Mixed detection issue
# ============================================================================
def detect_java_resilience_patterns_fallback(code):
    """
    Fallback regex-based detection for Java resilience patterns.
    Detects: Resilience4j, Hystrix, Spring Retry libraries
    Annotations: @Retry, @HystrixCommand, @CircuitBreaker, etc.
    Class names: RetryConfig, CircuitBreakerRegistry, etc.

    This supplements JAR-based parsing when it misses Java-specific patterns.
    """
    patterns = {
        "retry": False,
        "circuit_breaker": False,
        "timeout": False,
        "exponential_backoff": False,
    }

    libraries_found = []

    # Detect resilience library imports
    import_patterns = {
        "Resilience4j": r"import\s+io\.github\.resilience4j",
        "Hystrix": r"import\s+com\.netflix\.hystrix",
        "Spring Retry": r"import\s+org\.springframework\.retry",
        "Failsafe": r"import\s+(dev\.failsafe|net\.jodah\.failsafe)",
    }

    for lib_name, pattern in import_patterns.items():
        if re.search(pattern, code):
            libraries_found.append(lib_name)

    # Detect annotation-based patterns
    if re.search(r"@(Retryable|Retry)\b", code):
        patterns["retry"] = True
    if re.search(r"@(HystrixCommand|CircuitBreaker)", code):
        patterns["circuit_breaker"] = True
    if re.search(r"@TimeLimiter", code):
        patterns["timeout"] = True
    if re.search(r"@Backoff", code):
        patterns["exponential_backoff"] = True

    # Detect capitalized class name patterns
    if re.search(r"\b(RetryConfig|RetryRegistry|RetryTemplate)\b", code):
        patterns["retry"] = True
    if re.search(
        r"\b(CircuitBreakerConfig|CircuitBreakerRegistry|HystrixCommand)\b",
        code,
    ):
        patterns["circuit_breaker"] = True
    if re.search(r"\b(TimeLimiterConfig|TimeLimiterRegistry)\b", code):
        patterns["timeout"] = True
    if re.search(r"\b(ExponentialBackOff|BackOffPolicy)\b", code):
        patterns["exponential_backoff"] = True

    # Detect method call patterns
    if re.search(r"\.(retry|withRetry)\(|Retry\.of\(", code):
        patterns["retry"] = True
    if re.search(r"CircuitBreaker\.of\(|\.circuitBreaker\(", code):
        patterns["circuit_breaker"] = True
    if re.search(r"TimeLimiter\.of\(|\.timeout\(", code):
        patterns["timeout"] = True

    has_advanced = any(patterns.values()) or len(libraries_found) > 0

    return has_advanced, patterns, libraries_found


def parse_java_code(code):
    """
    Enhanced Java parser with:
    - Code preprocessing to handle encoding issues
    - Timeout protection
    - Debug logging for zero detection issue
    - Regex fallback for Java-specific resilience patterns
    - Better error handling
    """
    error_handling_type = "None"
    patterns = None
    temp_file_path = None

    try:
        # Preprocess Java code to handle encoding and syntax issues
        preprocessed_code = preprocess_java_code(code)

        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".java", delete=False
        ) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(preprocessed_code)

        jar_path = Path("target/your-artifact-id-1.0-SNAPSHOT.jar").resolve()

        # Add timeout to prevent hanging
        result = subprocess.run(
            ["java", "-jar", str(jar_path), temp_file_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,  # 30 second timeout
        )

        # Debug logging for Java parser output
        logging.debug(
            f"Java parser raw output: {result.stdout[:200]}"
        )  # Log first 200 chars

        parsed_output = json.loads(result.stdout)
        has_basic_handling = parsed_output.get("hasBasicHandling", False)
        has_advanced_handling = parsed_output.get("hasAdvancedHandling", False)

        # Debug logging for detection results
        logging.debug(
            f"Java detection - Basic: {has_basic_handling}, Advanced: {has_advanced_handling}"
        )

        # Regex fallback for Java-specific resilience patterns
        # If JAR doesn't detect advanced patterns, try regex-based detection
        if not has_advanced_handling:
            (
                has_advanced_fallback,
                fallback_patterns,
                libraries,
            ) = detect_java_resilience_patterns_fallback(preprocessed_code)

            if has_advanced_fallback:
                logging.info(
                    f"Regex fallback detected Java resilience patterns: {fallback_patterns}"
                )
                logging.info(
                    f"Java resilience libraries found: {libraries}"
                )
                has_advanced_handling = True

                # Initialize patterns dict if not present
                if "patterns" not in parsed_output:
                    parsed_output["patterns"] = {}

                # Merge fallback patterns
                for pattern_name, detected in fallback_patterns.items():
                    if detected:
                        parsed_output["patterns"][pattern_name] = True

        if has_basic_handling and has_advanced_handling:
            error_handling_type = "Mixed"
        elif has_basic_handling:
            error_handling_type = "Basic"
        elif has_advanced_handling:
            error_handling_type = "Advanced"

        # Extract pattern details if available
        patterns = parsed_output.get("patterns", {})

    except subprocess.TimeoutExpired:
        logging.error("Java parsing timed out after 30 seconds")
        return error_handling_type, None  # Indicate parser failure
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running JavaParser analyzer: {e.stderr}")
        if e.stdout:
            try:
                parsed_output = json.loads(e.stdout)
                has_basic_handling = parsed_output.get("hasBasicHandling", False)
                has_advanced_handling = parsed_output.get(
                    "hasAdvancedHandling", False
                )
                if has_basic_handling and has_advanced_handling:
                    error_handling_type = "Mixed"
                elif has_basic_handling:
                    error_handling_type = "Basic"
                elif has_advanced_handling:
                    error_handling_type = "Advanced"
                patterns = parsed_output.get("patterns", {})
            except json.JSONDecodeError:
                logging.error("Failed to parse partial results")
                return error_handling_type, None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JavaParser output: {e}")
        return error_handling_type, None
    except Exception as e:
        logging.error(f"Unexpected error during Java parsing: {str(e)}")
        return error_handling_type, None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logging.error(
                    f"Error removing temporary file: {str(e)}"
                )

    return error_handling_type, patterns


# Additional Babel plugins for parsing javascript code
BABEL_PLUGINS = ["jsx", "typescript", "classProperties", "objectRestSpread"]


def parse_javascript_code(code):
    """
    Enhanced JavaScript parser that extracts exception handling patterns.
    
    Returns:
        tuple: (error_handling_type: str, patterns: dict or None)
    """
    error_handling_type = "None"
    patterns = None
    temp_file_path = None

    try:
        # Create temporary JavaScript file
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".js", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(code)

        # Run JavaScript parser
        result = subprocess.run(
            ["node", "parse_javascript.js", temp_file_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        # Parse JSON output
        parsed_output = json.loads(result.stdout)
        has_basic_handling = parsed_output.get("hasBasicHandling", False)
        has_advanced_handling = parsed_output.get("hasAdvancedHandling", False)
        patterns = parsed_output.get("patterns", {})
        resilience_libraries = parsed_output.get("resilienceLibraries", [])
        
        # Debug logging
        logging.debug(f"JS parser - Basic: {has_basic_handling}, Advanced: {has_advanced_handling}")
        logging.debug(f"JS parser - Patterns: {patterns}")
        logging.debug(f"JS parser - Libraries: {resilience_libraries}")

        # Determine error handling type.
        if has_basic_handling and has_advanced_handling:
            error_handling_type = "Mixed"  
        elif has_basic_handling:
            error_handling_type = "Basic"
        elif has_advanced_handling:
            error_handling_type = "Advanced"

    except subprocess.TimeoutExpired:
        logging.error("JavaScript parsing timed out after 30 seconds")
        return error_handling_type, None
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running JavaScript parser: {e.stderr}")
        return error_handling_type, None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON output: {e}")
        logging.error(f"Raw output: {result.stdout if 'result' in locals() else 'N/A'}")
        return error_handling_type, None
    except Exception as e:
        logging.error(f"Unexpected error in JavaScript parsing: {str(e)}")
        return error_handling_type, None
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logging.error(f"Error removing temporary file: {str(e)}")

    return error_handling_type, patterns

def parse_typescript_code(code):
    error_handling_type = "None"
    patterns = None
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".ts", delete=False
        ) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(code)

        result = subprocess.run(
            ["node", "parse_typescript.js", temp_file_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        parsed_output = json.loads(result.stdout)
        has_basic_handling = parsed_output.get("hasBasicHandling", False)
        has_advanced_handling = parsed_output.get(
            "hasAdvancedHandling", False
        )

        if has_basic_handling and has_advanced_handling:
            error_handling_type = "Mixed"
        elif has_basic_handling:
            error_handling_type = "Basic"
        elif has_advanced_handling:
            error_handling_type = "Advanced"

        patterns = parsed_output.get("patterns", {})

    except subprocess.TimeoutExpired:
        logging.error("TypeScript parsing timed out after 30 seconds")
        return error_handling_type, None
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running TypeScript parser: {e.stderr}")
        if e.stdout:
            logging.error(f"Parser stdout: {e.stdout}")
        return error_handling_type, None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON output: {e}")
        logging.error(f"Raw output: {result.stdout}")
        return error_handling_type, None
    except Exception as e:
        logging.error(f"Unexpected error in TypeScript parsing: {str(e)}")
        return error_handling_type, None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logging.error(
                    f"Error removing temporary file: {str(e)}"
                )

    return error_handling_type, patterns


def parse_go_code(code):
    """
    Enhanced Go parser that handles both JSON (new) and CSV (old) output formats.
    
    Returns:
        tuple: (error_handling_type: str, patterns: dict or None)
    """
    error_handling_type = "None"
    patterns = None
    temp_file_path = None

    try:
        temp_file_path = os.path.join("integration_test", "temp_go_code.go")
        with open(temp_file_path, "w") as f:
            f.write(code)

        logging.info(f"Temp Go file created at: {temp_file_path}")
        if not os.path.exists(temp_file_path):
            logging.error("Temp Go file was not created.")
            return error_handling_type, None

        result = subprocess.run(
            ["./parse_go_code/parse_go_code", temp_file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()

        logging.info(f"Go parser output: {output}")

        if not output:
            logging.error("Go parser returned empty output.")
            return error_handling_type, None

        # Try JSON format first (enhanced parser)
        try:
            parsed_output = json.loads(output)
            
            # Extract values from JSON
            has_basic_handling = parsed_output.get('hasBasicHandling', False)
            has_advanced_handling = parsed_output.get('hasAdvancedHandling', False)
            patterns = parsed_output.get('patterns', {})
            resilience_libraries = parsed_output.get('resilience_libraries', [])
            
            logging.debug(f"Go parser - Basic: {has_basic_handling}, Advanced: {has_advanced_handling}")
            logging.debug(f"Go parser - Patterns: {patterns}")
            logging.debug(f"Go parser - Libraries: {resilience_libraries}")
            
            # Determine error handling type
            if has_basic_handling and has_advanced_handling:
                error_handling_type = "Mixed"
            elif has_basic_handling:
                error_handling_type = "Basic"
            elif has_advanced_handling:
                error_handling_type = "Advanced"
                
        except json.JSONDecodeError:
            # Fallback to CSV format (old parser for backward compatibility)
            logging.info("Go parser output is not JSON, trying CSV format")
            try:
                has_basic_handling_str, has_advanced_handling_str = output.split(",")
                has_basic_handling = has_basic_handling_str.lower() == "true"
                has_advanced_handling = has_advanced_handling_str.lower() == "true"
                
                # Determine error handling type
                if has_basic_handling and has_advanced_handling:
                    error_handling_type = "Mixed"
                elif has_basic_handling:
                    error_handling_type = "Basic"
                elif has_advanced_handling:
                    error_handling_type = "Advanced"
                    
                # No patterns available in CSV format
                patterns = None
                
            except ValueError:
                logging.error(f"Unexpected output format from Go parser: {output}")
                return error_handling_type, None

    except subprocess.TimeoutExpired:
        logging.error("Go parsing timed out after 30 seconds")
        return error_handling_type, None
    except Exception as e:
        logging.error(f"Go parsing failed: {e}")
        return error_handling_type, None

    return error_handling_type, patterns



# Ruby parsing
def parse_ruby_code(code):
    """
    Enhanced Ruby parser that extracts exception handling patterns.
    
    Returns:
        tuple: (error_handling_type: str, patterns: dict or None)
    """
    error_handling_type = "None"
    patterns = None
    temp_file_path = None

    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".rb", delete=False
    ) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(code)

    try:
        result = subprocess.run(
            ["ruby", "parse_ruby.rb", temp_file_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        output = result.stdout.strip()
        if not output:
            logging.error("Ruby parsing failed: No output from parser")
            return error_handling_type, None

        # ENHANCEMENT: Parse JSON output from enhanced parser
        try:
            parsed_output = json.loads(output)
            
            # Extract values from JSON
            has_basic_handling = parsed_output.get("hasBasicHandling", False)
            has_advanced_handling = parsed_output.get("hasAdvancedHandling", False)
            patterns = parsed_output.get("patterns", {})
            resilience_libraries = parsed_output.get("resilienceLibraries", [])
            
            # Debug logging
            logging.debug(f"Ruby parser - Basic: {has_basic_handling}, Advanced: {has_advanced_handling}")
            logging.debug(f"Ruby parser - Patterns: {patterns}")
            logging.debug(f"Ruby parser - Libraries: {resilience_libraries}")
            
            # Determine error handling type (use "Mixed" for consistency)
            if has_basic_handling and has_advanced_handling:
                error_handling_type = "Mixed"
            elif has_basic_handling:
                error_handling_type = "Basic"
            elif has_advanced_handling:
                error_handling_type = "Advanced"
                
        except json.JSONDecodeError as e:
            # BACKWARD COMPATIBILITY: Fallback to CSV parsing for old parser
            logging.debug(f"JSON parsing failed, trying CSV format: {e}")
            
            try:
                has_basic_handling, has_advanced_handling = output.split(",")
                
                if has_basic_handling == "true" and has_advanced_handling == "true":
                    error_handling_type = "Mixed"
                elif has_basic_handling == "true":
                    error_handling_type = "Basic"
                elif has_advanced_handling == "true":
                    error_handling_type = "Advanced"
                    
            except ValueError as csv_error:
                logging.error(f"Failed to parse Ruby output as CSV: {csv_error}")
                logging.error(f"Raw output: {output}")
                return error_handling_type, None

    except subprocess.TimeoutExpired:
        logging.error("Ruby parsing timed out after 30 seconds")
        return error_handling_type, None
    except subprocess.CalledProcessError as e:
        logging.error(
            f"Ruby parsing failed with exit code {e.returncode}. STDERR: {e.stderr.strip()}"
        )
        return error_handling_type, None
    except Exception as e:
        logging.error(f"Ruby parsing failed: {str(e)}")
        return error_handling_type, None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logging.warning(
                    f"Failed to remove temporary Ruby file {temp_file_path}: {str(e)}"
                )

    return error_handling_type, patterns


# Add a global flag to set the csharp parser path
# Path to C# parser
C_SHARP_PARSER_PATH = os.path.abspath(
    "/Users/francisobeng/Developer/Web_Services/Web_Services/NEW_AST_WEBSERVFH/CSharpParser/bin/Release/net8.0/CSharpParser.dll"
)

def parse_csharp_code(code):
    """
    Enhanced C# parser that handles both JSON (new) and CSV (old) output formats.
    
    Returns:
        tuple: (error_handling_type: str, patterns: dict or None)
    """
    error_handling_type = "None"
    patterns = None
    temp_file_path = None

    if not os.path.exists(C_SHARP_PARSER_PATH):
        logging.error(f"C# parsing failed: '{C_SHARP_PARSER_PATH}' not found.")
        return error_handling_type, None

    try:
        # Create temporary C# file
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".cs", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(code)

        # Run C# parser
        result = subprocess.run(
            ["dotnet", C_SHARP_PARSER_PATH, temp_file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logging.error(f"C# parsing failed with exit code {result.returncode}")
            logging.error(f"STDERR: {result.stderr.strip()}")
            return error_handling_type, None

        output = result.stdout.strip()
        
        if not output:
            logging.error("C# parser returned empty output")
            return error_handling_type, None

        # Try JSON format first (enhanced parser)
        try:
            parsed_output = json.loads(output)
            
            # Extract values from JSON
            has_basic_handling = parsed_output.get('hasBasicHandling', False)
            has_advanced_handling = parsed_output.get('hasAdvancedHandling', False)
            patterns = parsed_output.get('patterns', {})
            resilience_libraries = parsed_output.get('resilienceLibraries', [])
            
            logging.debug(f"C# parser - Basic: {has_basic_handling}, Advanced: {has_advanced_handling}")
            logging.debug(f"C# parser - Patterns: {patterns}")
            logging.debug(f"C# parser - Libraries: {resilience_libraries}")
            
            # Determine error handling type
            if has_basic_handling and has_advanced_handling:
                error_handling_type = "Mixed"  
            elif has_basic_handling:
                error_handling_type = "Basic"
            elif has_advanced_handling:
                error_handling_type = "Advanced"
                
        except json.JSONDecodeError:
            # Fallback to CSV format (old parser for backward compatibility)
            logging.info("C# parser output is not JSON, trying CSV format")
            
            if "," not in output:
                logging.error(f"Unexpected output format from C# parser: {output}")
                return error_handling_type, None
            
            try:
                has_basic_handling_str, has_advanced_handling_str = output.split(",")
                has_basic_handling = has_basic_handling_str.lower() == "true"
                has_advanced_handling = has_advanced_handling_str.lower() == "true"
                
                # Determine error handling type
                if has_basic_handling and has_advanced_handling:
                    error_handling_type = "Mixed"  
                elif has_basic_handling:
                    error_handling_type = "Basic"
                elif has_advanced_handling:
                    error_handling_type = "Advanced"
                
                # No patterns available in CSV format
                patterns = None
                
            except ValueError:
                logging.error(f"Failed to parse CSV output: {output}")
                return error_handling_type, None

    except subprocess.TimeoutExpired:
        logging.error("C# parsing timed out after 30 seconds")
        return error_handling_type, None
    except Exception as e:
        logging.error(f"C# parsing failed: {e}")
        return error_handling_type, None
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logging.error(f"Error removing C# temporary file: {str(e)}")

    return error_handling_type, patterns


# Add a global flag to track if the Kotlin compiler was already checked
JAVA_COMPILER_AVAILABLE = shutil.which("java") is not None

def parse_kotlin_code(code):
    """
    Enhanced Kotlin parser that extracts exception handling patterns.
    
    Returns:
        tuple: (error_handling_type: str, patterns: dict or None)
    """
    global JAVA_COMPILER_AVAILABLE
    error_handling_type = "None"
    patterns = None
    temp_file_path = None
    jar_path = os.path.abspath("parse_kotlin.jar")

    if not os.path.exists(jar_path):
        logging.error(f"parse_kotlin.jar not found at {jar_path}")
        return error_handling_type, None

    if not JAVA_COMPILER_AVAILABLE:
        logging.error(
            "Java not found. Please ensure Java is installed and accessible."
        )
        return error_handling_type, None

    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".kt", delete=False
    ) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(code)
        temp_file.close()

    try:
        result = subprocess.run(
            ["java", "-jar", jar_path, temp_file_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        output = result.stdout.strip()
        if not output:
            logging.error("Kotlin parsing failed: No output from parser")
            return error_handling_type, None

        # Parse JSON output from enhanced parser
        try:
            parsed_output = json.loads(output)
            
            # Extract values from JSON
            has_basic_handling = parsed_output.get("hasBasicHandling", False)
            has_advanced_handling = parsed_output.get("hasAdvancedHandling", False)
            patterns = parsed_output.get("patterns", {})
            resilience_libraries = parsed_output.get("resilienceLibraries", [])
            
            # Debug logging
            logging.debug(f"Kotlin parser - Basic: {has_basic_handling}, Advanced: {has_advanced_handling}")
            logging.debug(f"Kotlin parser - Patterns: {patterns}")
            logging.debug(f"Kotlin parser - Libraries: {resilience_libraries}")
            
            # Determine error handling type
            if has_basic_handling and has_advanced_handling:
                error_handling_type = "Mixed"
            elif has_basic_handling:
                error_handling_type = "Basic"
            elif has_advanced_handling:
                error_handling_type = "Advanced"
                
        except json.JSONDecodeError as e:
            # BACKWARD COMPATIBILITY: Fallback to CSV parsing for old parser
            logging.debug(f"JSON parsing failed, trying CSV format: {e}")
            
            try:
                values = output.split(",")
                if len(values) != 2:
                    logging.error(
                        f"Kotlin parsing failed: Expected 2 values, but got {len(values)}: '{output}'"
                    )
                    return error_handling_type, None

                has_basic_handling, has_advanced_handling = values

                if has_basic_handling == "true" and has_advanced_handling == "true":
                    error_handling_type = "Mixed"
                elif has_basic_handling == "true":
                    error_handling_type = "Basic"
                elif has_advanced_handling == "true":
                    error_handling_type = "Advanced"
                    
            except ValueError as csv_error:
                logging.error(f"Failed to parse Kotlin output as CSV: {csv_error}")
                logging.error(f"Raw output: {output}")
                return error_handling_type, None

    except subprocess.TimeoutExpired:
        logging.error("Kotlin parsing timed out after 30 seconds")
        return error_handling_type, None
    except subprocess.CalledProcessError as e:
        logging.error(
            f"Kotlin parsing failed with exit code {e.returncode}"
        )
        logging.error(f"STDERR: {e.stderr.strip()}")
        logging.error(f"STDOUT: {e.stdout.strip()}")
        return error_handling_type, None
    except Exception as e:
        logging.error(f"Kotlin parsing failed: {e}")
        return error_handling_type, None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logging.error(
                    f"Error removing Kotlin temporary file: {str(e)}"
                )

    return error_handling_type, patterns

# Swift parsing
def parse_swift_code(code):
    """
    Enhanced Swift parser that extracts exception handling patterns.
    Uses parse_swift.py (Python-based) instead of SourceKitten.
    
    Returns:
        tuple: (error_handling_type: str, patterns: dict or None)
    """
    error_handling_type = "None"
    patterns = None
    temp_file_path = None
    swift_parser_path = os.path.abspath("parse_swift.py")

    # Check if swift parser exists
    if not os.path.exists(swift_parser_path):
        logging.error(f"parse_swift.py not found at {swift_parser_path}")
        return error_handling_type, None

    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".swift", delete=False
    ) as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(code)
        temp_file.flush()

    try:
        result = subprocess.run(
            ["python3", swift_parser_path, temp_file_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        output = result.stdout.strip()
        if not output:
            logging.error("Swift parsing failed: No output from parser")
            return error_handling_type, None

        # Parse JSON output from enhanced parser
        try:
            parsed_output = json.loads(output)
            
            # Extract values from JSON
            has_basic_handling = parsed_output.get("hasBasicHandling", False)
            has_advanced_handling = parsed_output.get("hasAdvancedHandling", False)
            patterns = parsed_output.get("patterns", {})
            resilience_libraries = parsed_output.get("resilienceLibraries", [])
            
            # Debug logging
            logging.debug(f"Swift parser - Basic: {has_basic_handling}, Advanced: {has_advanced_handling}")
            logging.debug(f"Swift parser - Patterns: {patterns}")
            logging.debug(f"Swift parser - Libraries: {resilience_libraries}")
            
            # Determine error handling type.
            if has_basic_handling and has_advanced_handling:
                error_handling_type = "Mixed"
            elif has_basic_handling:
                error_handling_type = "Basic"
            elif has_advanced_handling:
                error_handling_type = "Advanced"
                
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse Swift JSON output: {e}")
            logging.error(f"Raw output: {output}")
            return error_handling_type, None

    except subprocess.TimeoutExpired:
        logging.error("Swift parsing timed out after 30 seconds")
        return error_handling_type, None
    except subprocess.CalledProcessError as e:
        logging.error(
            f"Swift parsing failed with exit code {e.returncode}"
        )
        logging.error(f"STDERR: {e.stderr.strip()}")
        logging.error(f"STDOUT: {e.stdout.strip()}")
        return error_handling_type, None
    except Exception as e:
        logging.error(f"Swift parsing failed: {e}")
        return error_handling_type, None
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logging.warning(
                    f"Failed to remove temporary Swift file {temp_file_path}: {e}"
                )
    return error_handling_type, patterns




def get_clone_path(repo_url: str, clone_dir: str) -> str:
    # Generate a unique clone directory path for a repository.
    # Extract owner and repo name
    parts = repo_url.rstrip("/").replace(".git", "").split("/")
    owner = parts[-2] if len(parts) >= 2 else "unknown"
    name = parts[-1] if len(parts) >= 1 else "unknown"

    safe_name = f"{owner}__{name}"
    
    return os.path.join(clone_dir, safe_name)



# Repository cloning
#@functools.lru_cache(maxsize=128)
def clone_repo(repo_url, clone_path, retries=3, delay=5, backoff_factor=2, timeout=180):
    """
    Clone a repository with timeout and retry logic.
    Args:
        timeout: Clone timeout in seconds (default 180s = 3 minutes)
        retries: Number of retry attempts (default 3)
    Returns:
        bool: True if clone successful, False otherwise
    """
    start_time = time.time()
    attempt = 0
    
    while attempt < retries:
        try:
            # Clean up existing directory if present
            if os.path.exists(clone_path):
                cleanup_clone(clone_path)

            logging.info(
                f"Cloning repository {repo_url}, attempt {attempt + 1}/{retries}, timeout={timeout}s"
            )
            
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, clone_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            elapsed = time.time() - start_time
            logging.info(f"Successfully cloned {repo_url} in {elapsed:.1f}s")
            return True

        except TimeoutExpired:
            logging.error(
                f"Timeout cloning repository {repo_url} after {timeout}s "
                f"(attempt {attempt + 1}/{retries})"
            )
            
        except CalledProcessError as e:
            logging.error(
                f"Error cloning repository {repo_url}: {e.stderr.strip()} "
                f"(attempt {attempt + 1}/{retries})"
            )

        # Shared backoff for both error types
        attempt += 1
        if attempt < retries:
            sleep_time = delay + (random.uniform(0, 1) * backoff_factor)
            logging.info(f"Retrying in {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            delay *= backoff_factor

    elapsed = time.time() - start_time
    logging.error(
        f"Failed to clone repository {repo_url} after {retries} attempts ({elapsed:.1f}s total)."
    )
    return False

# ============================================================================
# Enhanced analyze_code with Better Metrics
# Addresses concern about distinguishing parser failures from "None"
# ============================================================================
def analyze_code(repo_path):
    """
    Enhanced code analysis with:
    - HTTP library detection
    - Parser failure tracking
    - Detailed pattern tracking
    - Success rate calculation
    """
    error_handling_type = "None"
    exception_files = set()
    languages_used = set()
    http_libraries_found = set()
    parser_failures = []
    detailed_patterns = {
        "try_catch": 0,
        "timeout": 0,
        "retry": 0,
        "circuit_breaker": 0,
        "exponential_backoff": 0,
        "status_check": 0,
    }

    extension_to_language = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".rb": "ruby",
        ".cs": "csharp",
        ".kt": "kotlin",
        ".swift": "swift",
    }

    language_parsers = {
        "python": parse_python_code,
        "java": parse_java_code,
        "javascript": parse_javascript_code,
        "typescript": parse_typescript_code,
        "go": parse_go_code,
        "ruby": parse_ruby_code,
        "csharp": parse_csharp_code,
        "kotlin": parse_kotlin_code,
        "swift": parse_swift_code,
    }

    files_to_analyze = [
        os.path.join(root, file)
        for root, _, files in os.walk(repo_path)
        for file in files
        if any(file.endswith(ext) for ext in extension_to_language.keys())
    ]

    for file_path in files_to_analyze:
        if not os.path.exists(file_path):
            logging.warning(f"File not found: {file_path}")
            continue

        try:
            with open_file(file_path) as f:
                code = f.read()
                file_extension = os.path.splitext(file_path)[1]
                language = extension_to_language.get(
                    file_extension, "Unknown"
                )

                # HTTP library detection
                has_http, libs = detect_http_libraries(code, language)
                if has_http:
                    http_libraries_found.update(libs)

                parser = language_parsers.get(language)

                if parser:
                    # Enhanced parsing with pattern detection
                    languages_used.add(language)
                    result = parser(code)

                    # Handle parser result tuple (error_handling_type, patterns)
                    if isinstance(result, tuple):
                        result_type, patterns = result

                        # Check for parser failure (patterns is None)
                        if patterns is None:
                            parser_failures.append(file_path)
                            continue

                        # Aggregate pattern counts
                        if patterns and isinstance(patterns, dict):
                            for pattern_name, detected in patterns.items():
                                if detected:
                                    detailed_patterns[pattern_name] = (
                                        detailed_patterns.get(
                                            pattern_name, 0
                                        )
                                        + 1
                                    )
                    else:
                        # Backward compatibility for parsers returning only string
                        result_type = result

                    if result_type != "None":
                        exception_files.add(file_path)
                        #languages_used.add(language)
                        if error_handling_type == "None":
                            error_handling_type = result_type
                        elif (
                            error_handling_type == "Basic"
                            and result_type == "Advanced"
                        ):
                            error_handling_type = "Mixed"
                        elif (
                            error_handling_type == "Advanced"
                            and result_type == "Basic"
                        ):
                            error_handling_type = "Mixed"

        except FileNotFoundError:
            logging.warning(
                f"File not found when trying to open: {file_path}"
            )
            parser_failures.append(file_path)
            continue
        except UnicodeDecodeError:
            logging.warning(
                f"Skipping file due to encoding issues: {file_path}"
            )
            parser_failures.append(file_path)
            continue
        except Exception as e:
            logging.error(
                f"Unexpected error processing file {file_path}: {str(e)}"
            )
            parser_failures.append(file_path)
            continue

    # Calculate success rate
    total_files = len(files_to_analyze)
    success_rate = (
        (total_files - len(parser_failures)) / total_files
        if total_files > 0
        else 0
    )

    return {
        "error_handling_type": error_handling_type,
        "exception_files": list(exception_files),
        "languages_used": list(languages_used),
        "http_libraries": list(http_libraries_found),
        "parser_failures": len(parser_failures),
        "total_files": total_files,
        "success_rate": success_rate,
        "detailed_patterns": detailed_patterns,
    }

# Processing repositories
def process_repo(row, clone_dir):
    """
    Process a single repository: clone, analyze, and return results.
    Now uses unique clone paths to prevent directory collisions.
    """
    try:
        log_system_stats()
        check_disk_usage()

        repo_url = row["repo_url"]
        
        # FIXED: Use unique clone path
        clone_path = get_clone_path(repo_url, clone_dir)
        
        logging.info(f"Processing repository {repo_url}...")
        logging.debug(f"Clone path: {clone_path}")
        
        if clone_repo(repo_url, clone_path, retries=3, delay=5, backoff_factor=2, timeout=180):
            if not os.listdir(clone_path):
                logging.error(f"Clone repository {clone_path} is empty")
                return None

            logging.info(f"Analyzing repository at {clone_path}...")
            analysis_result = analyze_code(clone_path)

            error_handling_type = analysis_result["error_handling_type"]
            languages_used = analysis_result["languages_used"]
            http_libraries = analysis_result["http_libraries"]
            success_rate = analysis_result["success_rate"]
            detailed_patterns = analysis_result["detailed_patterns"]

            recommendation = get_recommendation(error_handling_type)
            languages_str = "; ".join(languages_used)
            http_libs_str = (
                "; ".join(http_libraries)
                if http_libraries
                else "None detected"
            )

            cleanup_clone(clone_path)

            return {
                "repo_url": repo_url,
                "Exception Type": error_handling_type,
                "Recommendation": recommendation,
                "Languages": languages_str,
                "HTTP Libraries": http_libs_str,
                "Parser Success Rate": f"{success_rate:.2%}",
                "Has Try-Catch": detailed_patterns.get("try_catch", 0) > 0,
                "Has Timeout": detailed_patterns.get("timeout", 0) > 0,
                "Has Retry": detailed_patterns.get("retry", 0) > 0,
                "Has Circuit Breaker": detailed_patterns.get("circuit_breaker", 0) > 0,
                "Has Backoff": detailed_patterns.get("exponential_backoff", 0) > 0,
                "Has Status Check": detailed_patterns.get("status_check", 0) > 0,
            }
        else:
            logging.error(f"Failed to clone repository: {repo_url}")
            return None
            
    except Exception as e:
        logging.exception(
            f"Error processing repository {row['repo_url']}: {str(e)}"
        )
        return None

# Generating textual recommendations
def get_recommendation(error_handling_type):
    if error_handling_type == "Mixed":
        return "The codebase has basic and advanced exception handling."
    elif error_handling_type == "Advanced":
        return "The codebase has advanced exception handling."
    elif error_handling_type == "Basic":
        return "Basic exception handling detected. Consider enhancements."
    else:
        return "No exception handling detected. Consider adding exception handling."


def cleanup_clone(clone_path):
    try:
        shutil.rmtree(clone_path)
        logging.info(f"Successfully removed directory {clone_path}")
    except Exception as e:
        logging.error(
            f"Failed to remove directory {clone_path}: {str(e)}"
        )

# Incrementally saving analyzed output
def save_cache_incrementally(cache, cache_file, batch_size=1000):
    temp_cache = {}
    for i, (key, value) in enumerate(cache.items()):
        temp_cache[key] = value
        if (i + 1) % batch_size == 0:
            try:
                with open(cache_file, "ab") as f:
                    pickle.dump(temp_cache, f)
                temp_cache.clear()
            except OSError as e:
                logging.error(f"Failed to save cache batch: {e}")

    if temp_cache:
        try:
            with open(cache_file, "ab") as f:
                pickle.dump(temp_cache, f)
        except OSError as e:
            logging.error(f"Failed to save final cache batch: {e}")

# Processing repositories in batches
def batch_process_repositories(rows, batch_size, log_queue, clone_dir):
    total_batches = (len(rows) + batch_size - 1) // batch_size

    redirect_logs_to_file() # Redirect logs to file to avoid distracting progress bar
    suppress_warnings() # Suppress specific warnings during processing

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        logging.info(
            f"Processing batch {i // batch_size + 1}/{total_batches}..."
        )

        log_system_stats()

        with Pool(
            processes=os.cpu_count(),
            initializer=worker_init,
            initargs=(log_queue,),
        ) as pool:
            results = list(
                tqdm(
                    pool.imap_unordered(
                        functools.partial(
                            process_repo, clone_dir=clone_dir
                        ),
                        batch,
                    ),
                    total=len(batch),
                    desc=f"Processing batch {i // batch_size + 1}/{total_batches}",
                )
            )
        yield results


def main():
    log_queue, listener = setup_logging()
    sys.excepthook = global_exception_handler

    config = load_configuration()
    input_csv_file_path = config.get("paths", "input_csv_file_path")
    output_csv_file_path = config.get("paths", "output_csv_file_path")
    clone_dir = config.get("paths", "clone_dir")
    cache_file = config.get("paths", "cache_file")

    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                cache = pickle.load(f)
        except (EOFError, pickle.UnpicklingError):
            logging.warning(
                f"Cache file {cache_file} is corrupted. Starting with an empty cache."
            )
            cache = {}
    else:
        cache = {}

    try:
        with open(
            input_csv_file_path,
            mode="r",
            newline="",
            encoding="utf-8",
        ) as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)
    except Exception as e:
        logging.error(f"Failed to read input CSV file: {e}")
        listener.stop()
        sys.exit(1)

    total_repos = len(rows)
    logging.info(f"Total repositories in input CSV: {total_repos}")

    batch_size = 50 #batch size is set to 50 per a batch.

    # Enhanced field names for detailed output
    fieldnames = [
        "repo_url",
        "Exception Type",
        "Recommendation",
        "Languages",
        "HTTP Libraries",
        "Parser Success Rate",
        "Has Try-Catch",
        "Has Timeout",
        "Has Retry",
        "Has Circuit Breaker",
        "Has Backoff",
        "Has Status Check",
    ]

    try:
        with open(
            output_csv_file_path,
            mode="w",
            newline="",
            encoding="utf-8",
        ) as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    except Exception as e:
        logging.error(f"Failed to write to output CSV file: {e}")
        listener.stop()
        sys.exit(1)

    for batch_results in batch_process_repositories(
        rows, batch_size, log_queue, clone_dir
    ):
        successful_ops = sum(
            1 for result in batch_results if result is not None
        )
        failed_ops = len(batch_results) - successful_ops

        logging.info(
            f"Successful operations in batch: {successful_ops}"
        )
        logging.info(f"Failed operations in batch: {failed_ops}")

        for result in batch_results:
            if result:
                cache[result["repo_url"]] = result

        save_cache_incrementally(cache, cache_file)

        try:
            with open(
                output_csv_file_path,
                mode="a",
                newline="",
                encoding="utf-8",
            ) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerows(
                    result for result in batch_results if result
                )
        except Exception as e:
            logging.error(f"Error writing to the CSV file: {e}")

    logging.info(f"Total repositories processed: {total_repos}")
    logging.info(f"Repositories in output CSV: {len(cache)}")

    listener.stop()


if __name__ == "__main__":
    if not os.path.exists("config.ini"):
        create_config_file()
    else:
        update_config_file()

    main()
