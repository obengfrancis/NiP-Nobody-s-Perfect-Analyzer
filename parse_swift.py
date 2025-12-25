#!/usr/bin/env python3
"""
Swift Parser for Exception Handling and Resilience Patterns
Outputs JSON format consistent with other enhanced parsers
No external dependencies - works on any platform
"""

import sys
import json
import re
from typing import Dict, List, Set, Tuple

# ============================================================================
#  Swift Resilience Libraries
# ============================================================================

RESILIENCE_LIBRARIES = {
    # HTTP Clients
    'Alamofire': {'patterns': ['timeout', 'retry'], 'type': 'http_client'},
    'Moya': {'patterns': ['timeout'], 'type': 'http_client'},
    'AFNetworking': {'patterns': ['timeout'], 'type': 'http_client'},
    
    # Async/Promise Libraries
    'PromiseKit': {'patterns': ['retry', 'timeout'], 'type': 'async'},
    'Combine': {'patterns': ['retry', 'timeout'], 'type': 'async'},
    'RxSwift': {'patterns': ['retry', 'timeout'], 'type': 'async'},
    
    # Retry Libraries
    'Retry': {'patterns': ['retry', 'exponential_backoff'], 'type': 'retry'},
    'SwiftRetry': {'patterns': ['retry'], 'type': 'retry'},
    
    # Network/Resilience
    'AsyncHTTPClient': {'patterns': ['timeout'], 'type': 'http_client'},
    'URLSession': {'patterns': ['timeout'], 'type': 'http_client'},
    
    # Utilities
    'SwiftyTimer': {'patterns': ['timeout'], 'type': 'timeout'},
}

# ============================================================================
#  Enhanced Swift Code Analyzer
# ============================================================================

class SwiftCodeAnalyzer:
    def __init__(self, code: str):
        self.code = code
        self.has_basic_handling = False
        self.has_advanced_handling = False
        self.patterns = {
            'do_catch': False,
            'result_type': False,
            'async_throws': False,
            'timeout': False,
            'retry': False,
            'circuit_breaker': False,
            'exponential_backoff': False,
            'status_check': False,
        }
        self.resilience_libraries: Set[str] = set()

    def analyze(self) -> Dict:
        """Analyze Swift code for resilience patterns."""
        # ENHANCEMENT 1: Detect import statements
        self._detect_imports()
        
        # ENHANCEMENT 2: Detect do-catch blocks
        self._detect_do_catch()
        
        # ENHANCEMENT 3: Detect Result type
        self._detect_result_type()
        
        # ENHANCEMENT 4: Detect async/await patterns
        self._detect_async_await()
        
        # ENHANCEMENT 5: Detect timeout patterns
        self._detect_timeout_patterns()
        
        # ENHANCEMENT 6: Detect retry patterns
        self._detect_retry_patterns()
        
        # ENHANCEMENT 7: Detect status checks
        self._detect_status_checks()
        
        # ENHANCEMENT 8: Detect circuit breaker patterns
        self._detect_circuit_breaker_patterns()
        
        return {
            'hasBasicHandling': self.has_basic_handling,
            'hasAdvancedHandling': self.has_advanced_handling,
            'patterns': self.patterns,
            'resilienceLibraries': sorted(list(self.resilience_libraries))
        }

    # ENHANCEMENT 1: Import detection
    def _detect_imports(self):
        """Detect import statements for resilience libraries."""
        import_pattern = re.compile(r'^\s*import\s+(\w+)', re.MULTILINE)
        
        for match in import_pattern.finditer(self.code):
            module = match.group(1)
            
            if module in RESILIENCE_LIBRARIES:
                self.resilience_libraries.add(module)
                self.has_advanced_handling = True
                
                # Set pattern flags based on library
                lib_info = RESILIENCE_LIBRARIES[module]
                for pattern in lib_info['patterns']:
                    self.patterns[pattern] = True

    # ENHANCEMENT 2: Do-catch detection
    def _detect_do_catch(self):
        """Detect do-catch blocks (Swift's try-catch equivalent)."""
        # Pattern: do { ... } catch { ... }
        do_catch_pattern = re.compile(r'\bdo\s*\{[^}]*\}\s*catch\b', re.DOTALL)
        
        if do_catch_pattern.search(self.code):
            self.has_basic_handling = True
            self.patterns['do_catch'] = True

    # ENHANCEMENT 3: Result type detection
    def _detect_result_type(self):
        """Detect Swift Result type usage (most common Swift error handling)."""
        result_patterns = [
            re.compile(r'->\s*Result\s*<'),  # -> Result<Success, Failure>
            re.compile(r':\s*Result\s*<'),   # : Result<Success, Failure>
            re.compile(r'\bResult\s*<\w+,\s*Error>'),  # Result<T, Error>
            re.compile(r'\bResult\s*<\w+,\s*\w+Error>'),  # Result<T, NetworkError>
        ]
        
        for pattern in result_patterns:
            if pattern.search(self.code):
                self.has_basic_handling = True
                self.patterns['result_type'] = True
                return

    # ENHANCEMENT 4: Async/await detection
    def _detect_async_await(self):
        """Detect async/await and throws patterns."""
        async_patterns = [
            re.compile(r'\basync\s+throws\b'),  # async throws
            re.compile(r'\btry\s+await\b'),     # try await
            re.compile(r'\basync\s*\{'),        # async { }
            re.compile(r'func\s+\w+\([^)]*\)\s+async\b'),  # async function
        ]
        
        for pattern in async_patterns:
            if pattern.search(self.code):
                self.has_basic_handling = True
                self.patterns['async_throws'] = True
                return

    # ENHANCEMENT 5: Timeout patterns
    def _detect_timeout_patterns(self):
        """Detect timeout configurations and patterns."""
        timeout_patterns = [
            # URLSession timeout configuration
            re.compile(r'timeoutIntervalForRequest\s*='),
            re.compile(r'timeoutIntervalForResource\s*='),
            re.compile(r'\.timeoutInterval\s*='),
            
            # Alamofire timeout
            re.compile(r'\.timeout\('),
            re.compile(r'timeoutInterval:\s*\d+'),
            
            # PromiseKit timeout
            re.compile(r'\.timeout\(seconds:'),
            
            # Combine timeout
            re.compile(r'\.timeout\(\.seconds\('),
            
            # RxSwift timeout
            re.compile(r'\.timeout\('),
            
            # Generic timeout usage
            re.compile(r'\btimeout\s*:\s*\d+'),
            re.compile(r'withTimeout\('),
        ]
        
        for pattern in timeout_patterns:
            if pattern.search(self.code):
                self.has_advanced_handling = True
                self.patterns['timeout'] = True
                return

    # ENHANCEMENT 6: Retry patterns
    def _detect_retry_patterns(self):
        """Detect retry logic patterns."""
        retry_patterns = [
            # Alamofire retry
            re.compile(r'\.retry\('),
            re.compile(r'\.retryPolicy\('),
            re.compile(r'RetryPolicy\('),
            
            # PromiseKit retry
            re.compile(r'\.retry\(\d+\)'),
            re.compile(r'firstly.*\.retry', re.DOTALL),
            
            # RxSwift retry
            re.compile(r'\.retry\('),
            re.compile(r'\.retryWhen\('),
            
            # Custom retry functions
            re.compile(r'func\s+\w*[Rr]etry\w*\s*\('),
            re.compile(r'withRetry\('),
            
            # Retry configuration
            re.compile(r'\bretries\s*:\s*\d+'),
            re.compile(r'\bmaxRetries\s*:\s*\d+'),
            re.compile(r'\bretryCount\s*='),
            
            # Loop-based retry
            re.compile(r'for\s+_\s+in\s+\d+\.\.\.retries'),
        ]
        
        for pattern in retry_patterns:
            if pattern.search(self.code):
                self.has_advanced_handling = True
                self.patterns['retry'] = True
                
                # Check for exponential backoff
                if re.search(r'exponential|backoff', self.code, re.IGNORECASE):
                    self.patterns['exponential_backoff'] = True
                return

    # ENHANCEMENT 7: Status check patterns
    def _detect_status_checks(self):
        """Detect HTTP status code checks."""
        status_patterns = [
            # HTTPURLResponse status checks
            re.compile(r'\.statusCode\s*==\s*\d+'),
            re.compile(r'statusCode\s*==\s*200'),
            re.compile(r'response\.statusCode'),
            
            # Alamofire validation
            re.compile(r'\.validate\(\)'),
            re.compile(r'\.validate\(statusCode:'),
            
            # Status code ranges
            re.compile(r'200\.\.\.299'),
            re.compile(r'statusCode\s*>=\s*200'),
            
            # Guard statements with status
            re.compile(r'guard.*statusCode.*else', re.DOTALL),
        ]
        
        for pattern in status_patterns:
            if pattern.search(self.code):
                self.has_basic_handling = True
                self.patterns['status_check'] = True
                return

    # ENHANCEMENT 8: Circuit breaker patterns
    def _detect_circuit_breaker_patterns(self):
        """Detect circuit breaker implementations."""
        circuit_breaker_patterns = [
            re.compile(r'CircuitBreaker', re.IGNORECASE),
            re.compile(r'class\s+\w*CircuitBreaker'),
            re.compile(r'struct\s+\w*CircuitBreaker'),
            re.compile(r'enum\s+CircuitState'),
            re.compile(r'\bcircuit\s*:\s*CircuitBreaker'),
        ]
        
        for pattern in circuit_breaker_patterns:
            if pattern.search(self.code):
                self.has_advanced_handling = True
                self.patterns['circuit_breaker'] = True
                return

# ============================================================================
#  Main Execution
# ============================================================================

def main():
    if len(sys.argv) < 2:
        error_result = {
            'hasBasicHandling': False,
            'hasAdvancedHandling': False,
            'patterns': {},
            'resilienceLibraries': [],
            'error': 'No Swift code file provided'
        }
        print(json.dumps(error_result))
        sys.exit(1)

    file_path = sys.argv[1]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            swift_code = f.read()
        
        analyzer = SwiftCodeAnalyzer(swift_code)
        result = analyzer.analyze()
        
        # Output JSON
        print(json.dumps(result))
        
    except FileNotFoundError:
        error_result = {
            'hasBasicHandling': False,
            'hasAdvancedHandling': False,
            'patterns': {},
            'resilienceLibraries': [],
            'error': f'File not found: {file_path}'
        }
        print(json.dumps(error_result))
        sys.exit(1)
    except Exception as e:
        error_result = {
            'hasBasicHandling': False,
            'hasAdvancedHandling': False,
            'patterns': {},
            'resilienceLibraries': [],
            'error': f'Error processing file: {str(e)}'
        }
        print(json.dumps(error_result))
        sys.exit(1)

if __name__ == '__main__':
    main()