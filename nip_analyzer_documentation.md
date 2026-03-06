# NiP Analyzer: Network Incident Parser System Documentation

## Executive Summary

**NiP Analyzer** is a sophisticated multi-language code analysis framework designed to assess exception handling, strategies, resilience patterns and HTTP library usage across distributed repositories. It processes repositories in parallel batches, performs language-specific AST/bytecode parsing, and generates detailed resilience pattern reports.

---

## 1. System Architecture Overview

### 1.1 High-Level Pipeline

```
Input (CSV) → Configuration → Batch Processing → Repository Cloning → 
Code Analysis → Language-Specific Parsers → Pattern Detection → 
Output (CSV) + Caching + Logging
```

### 1.2 Core Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **Config Manager** | Load/update configuration | ConfigParser (.ini) |
| **Repository Manager** | Clone & validate repos | Git with retry logic |
| **Batch Processor** | Manage parallel processing | Python Multiprocessing (4 workers) |
| **Parser Router** | Dispatch to language parsers | Language-specific detection |
| **HTTP Detector** | Identify HTTP clients | AST + Regex analysis |
| **Pattern Analyzer** | Extract resilience patterns | Language-specific visitors |
| **Logger System** | Concurrent logging | QueueHandler + RotatingFileHandler |
| **Cache Manager** | Incremental result storage | Pickle (binary) |

---

## 2. Data Flow Architecture

### 2.1 Input Stage
- **Format**: CSV file with `repo_url` column
- **Default**: `input_csv_file_19.csv`
- **Processing**: Batch reading (50 repositories per batch)

### 2.2 Configuration Management
```
config.ini
├── paths.input_csv_file_path
├── paths.output_csv_file_path
├── paths.clone_dir (cloned_repos)
└── paths.cache_file (analysis_cache.pkl)
```

### 2.3 Processing Pipeline

**Step 1: Repository Cloning**
- Uses `git clone --depth 1` (shallow clone for speed)
- Retry logic: 2 attempts with exponential backoff
- Timeout: 120 seconds per clone
- Permanent error detection (404, 403, auth failures)
- Cleanup: Removes directory after analysis

**Step 2: Code Discovery**
- Walks repository directory tree
- Skips: `.git`, `dist`, `build`, `node_modules`, `__pycache__`, etc.
- Collects files by language extension:
  - Python (`.py`)
  - Java (`.java`)
  - JavaScript (`.js`)
  - TypeScript (`.ts`)
  - Go (`.go`)
  - Ruby (`.rb`)
  - C# (`.cs`)
  - Kotlin (`.kt`)
  - Swift (`.swift`)

**Step 3: Language-Specific Analysis**
Each language has dedicated parser returning:
```python
(error_handling_type: str, patterns: dict or None)

# error_handling_type values:
# - "None" (no handling detected)
# - "Basic" (try-catch/basic error handling)
# - "Advanced" (retry, timeout, circuit breaker)
# - "Mixed" (both basic and advanced)

# patterns dict structure:
{
    "try_catch": bool,
    "timeout": bool,
    "retry": bool,
    "circuit_breaker": bool,
    "exponential_backoff": bool,
    "status_check": bool
}
```

**Step 4: HTTP Library Detection**
- Router function: `detect_http_libraries_enhanced(code, language)`
- Returns: `(has_http_library: bool, libraries_found: List[str])`
- Supported libraries per language documented in `HTTP_LIBRARIES` dict

**Step 5: Aggregation**
- Combines results across all files in repository
- Counts pattern occurrences
- Identifies all languages used
- Calculates parser success rate

**Step 6: Human Textual Recommendation Generation (It is not a recommender system)**
```python
Mixed      → "The codebase has basic and advanced exception handling."
Advanced   → "The codebase has advanced exception handling."
Basic      → "Basic exception handling detected. Consider enhancements."
None       → "No exception handling detected. Consider adding exception handling."
```

### 2.4 Output Stage

**CSV Columns**:
```
repo_url, Exception Type, Recommendation, Languages, HTTP Libraries, 
Parser Success Rate, Has Try-Catch, Has Timeout, Has Retry, 
Has Circuit Breaker, Has Backoff, Has Status Check
```

**Cache File**: `analysis_cache.pkl`
- Pickled dictionary: `{repo_url: result_dict}`
- Enables resumable processing
- Saved incrementally (batch_size=1000)

---

## 3. Language-Specific Parsers

### 3.1 Python Parser

**Method**: AST (Abstract Syntax Tree) parsing
- Detects imports: `tenacity`, `pybreaker`, `backoff`, `retry`, `circuit_breaker`
- Visitor pattern for:
  - `Try/ExceptHandler` nodes → try_catch
  - Function calls: `timeout()`, `retry()`, `circuitbreaker()`
  - Method calls: `.retry()`, `.timeout()`, `.with_backoff()`
  - Decorators: `@retry`, `@timeout`, `@circuitbreaker`
  - Context managers: `with timeout():`

**Error Handling**: SyntaxError recovery logs and returns `("None", [])`

### 3.2 Java Parser

**Method**: Subprocess call to JAR-based analyzer
- Preprocesses code for Unicode/encoding issues
- Fallback regex detection:
  - Annotations: `@Retry`, `@HystrixCommand`, `@CircuitBreaker`, `@TimeLimiter`
  - Classes: `RetryConfig`, `CircuitBreakerRegistry`, `TimeLimiterConfig`
  - Imports: Resilience4j, Hystrix, Spring Retry, Failsafe
  - Method calls: `.retry()`, `Retry.of()`, `CircuitBreaker.of()`

**Timeout**: 30 seconds per file
**Fallback**: Regex-based pattern detection when JAR fails

### 3.3 JavaScript/TypeScript Parser

**Method**: Node.js subprocess with Babel plugins
- Parse JavaScript/TypeScript file with Babel
- Babel plugins: `jsx`, `typescript`, `classProperties`, `objectRestSpread`
- Detects import/require patterns:
  - ES6: `import ... from "module"`
  - CommonJS: `require("module")`
- Timeout: 30 seconds

### 3.4 Go Parser

**Method**: Binary executable (`./parse_go_code/parse_go_code`)
- Parses Go import blocks (single and multi-import)
- Output format: JSON (enhanced) or CSV (legacy)
- Timeout: 30 seconds

### 3.5 Ruby Parser

**Method**: Ruby script subprocess (`parse_ruby.rb`)
- Detects: `require`, `require_relative` statements
- Matches against Ruby HTTP libraries
- Standard library detection: `Net::HTTP` via regex
- Output: JSON (enhanced) or CSV (legacy)
- Timeout: 30 seconds

### 3.6 C# Parser

**Method**: .NET DLL subprocess (`CSharpParser.dll`)
- Executes via: `dotnet C_SHARP_PARSER_PATH file.cs`
- Parses using statements
- Output format: JSON (enhanced) or CSV (legacy)
- Timeout: 30 seconds
- Path: `/Users/francisobeng/Developer/Web_Services/.../CSharpParser.dll`

### 3.7 Kotlin Parser

**Method**: JAR-based analyzer (`parse_kotlin.jar`)
- Prerequisite: Java runtime available
- Parses import statements
- Output format: JSON (enhanced) or CSV (legacy)
- Timeout: 30 seconds

### 3.8 Swift Parser

**Method**: Python script (`parse_swift.py`)
- Parses import statements
- Detects: `URLSession`, `URLRequest`, `Alamofire`, `Moya`, `AsyncHTTPClient`
- Output: JSON format
- Timeout: 30 seconds

---

## 4. HTTP Library Detection System

### 4.1 Supported Libraries by Language

**Python** (12 libraries):
- Standard: `http.client`, `urllib`, `urllib2`, `httplib`
- Third-party: `requests`, `httpx`, `aiohttp`, `tornado.httpclient`, `treq`, `urllib3`, `httplib2`

**Java** (11 libraries):
- Standard: `HttpClient`, `HttpURLConnection`
- Apache: `org.apache.http`, `org.apache.httpcomponents`
- Popular: OkHttp3, Spring RestTemplate/WebClient, Feign, Jersey, AsyncHttpClient

**JavaScript/TypeScript** (14 libraries):
- Standard: `fetch`, Node.js `http`/`https`
- Popular: `axios`, `node-fetch`, `superagent`, `request`, `got`, `undici`, `ky`, `wretch`, `needle`

**Go** (6 libraries):
- Standard: `net/http`
- Popular: `go-resty`, `fasthttp`, `sling`, `gorequest`, `gentleman`

**C#** (6 libraries):
- Standard: `HttpClient`, `WebClient`, `HttpWebRequest`
- Popular: `RestSharp`, `Flurl`, `Refit`

**Ruby** (10 libraries):
- Standard: `net/http`, `open-uri`
- Popular: `httparty`, `rest-client`, `faraday`, `typhoeus`, `curb`, `excon`, `http.rb`

**Kotlin** (8 libraries):
- Standard: `HttpClient`
- Popular: OkHttp, Retrofit, Fuel, Ktor, http4k

**Swift** (7 libraries):
- Standard: `URLSession`, `URLRequest`, `NWConnection`
- Popular: `Alamofire`, `Moya`, `AsyncHTTPClient`

### 4.2 Detection Methods

| Language | Method | Advantage |
|----------|--------|-----------|
| Python | AST parsing | Avoids comments/strings |
| Java | Regex import matching | Fast, handles complex packages |
| JS/TS | Regex patterns | Handles ES6 and CommonJS |
| Go | Import block regex | Supports multi-import syntax |
| Ruby | require() regex | Pattern-based detection |
| C# | using statement regex | Namespace-based detection |
| Kotlin | Import regex | Same as Java approach |
| Swift | import statement regex | Straightforward detection |

---

## 5. Pattern Tracking & Detection

### 5.1 Resilience Patterns

| Pattern | Detection Method |
|---------|------------------|
| **try_catch** | Try/Except/Catch blocks |
| **timeout** | Timeout library imports, decorator calls, context managers |
| **retry** | Retry library imports, decorator calls, method patterns |
| **circuit_breaker** | CircuitBreaker imports, annotations, class instantiation |
| **exponential_backoff** | Backoff library imports, exponential backoff method calls |
| **status_check** | HTTP status code checking methods (`.status_code`, `.raise_for_status()`) |

### 5.2 Aggregation Logic

```python
# Per repository:
detailed_patterns = {
    "try_catch": count_of_files_with_pattern,
    "timeout": count_of_files_with_pattern,
    "retry": count_of_files_with_pattern,
    "circuit_breaker": count_of_files_with_pattern,
    "exponential_backoff": count_of_files_with_pattern,
    "status_check": count_of_files_with_pattern
}

# Overall error_handling_type:
if both_basic_and_advanced:
    type = "Mixed"
elif has_advanced:
    type = "Advanced"
elif has_basic:
    type = "Basic"
else:
    type = "None"
```

---

## 6. Concurrency & Performance

### 6.1 Multiprocessing Architecture

```python
Batch (50 repos)
├── Worker 1: Process repos
├── Worker 2: Process repos
├── Worker 3: Process repos
└── Worker 4: Process repos
```

- **Process Pool**: 4 workers (capped, not using all cores)
- **Process Pool Size Calc**: `min(4, os.cpu_count() or 1)`
- **Initializer**: `worker_init()` sets up per-worker logging

### 6.2 Logging Strategy

**Queue-Based Multiprocessing Logging**:
```python
Main Process
├── QueueListener (handles write ops)
└── Log Queue ← [Worker 1 QueueHandler, Worker 2 QueueHandler, ...]
```

**Rotating File Handler**:
- Max file size: 100 KB
- Backup count: 2 files
- Files:
  - `processing.log` (main)
  - `processing_warnings.log` (warnings)

### 6.3 System Monitoring

Functions periodically call:
- `log_system_stats()`: Disk usage, memory %, process count
- `check_disk_usage()`: Free/total disk space

---

## 7. Error Handling & Resilience

### 7.1 Repository Cloning

**Retry Logic**:
```
Attempt 1 → Fail (retriable) → Wait 5s
Attempt 2 → Fail (retriable) → Wait 10s (backoff)
Attempt 3 → Fail or succeed

Permanent errors (immediate fail):
- "repository not found"
- "authentication failed"
- "404 Not Found"
- "403 Forbidden"
```

### 7.2 Code Parsing

**Encoding Handling**:
```python
encodings = [
    'utf-8', 'latin1', 'iso-8859-1', 'ascii', 
    'utf-16', 'utf-32', 'cp1252', 'cp850', 'mac_roman'
]
# Tries each until successful or raises UnicodeDecodeError
```

**Java Preprocessing**:
- Remove BOM (`\ufeff`)
- Normalize Unicode (NFKC)
- Standardize quotes
- Remove invalid control characters
- Escape special characters

**Parser Failures**:
- Tracked separately (counts as 0% success if all fail)
- Logged with file path
- Continue processing other files

### 7.3 Subprocess Timeouts

All external parsers have 30-second timeout:
- Python: AST parse timeout
- Java: Subprocess timeout
- JS/TS: Node.js timeout
- Go: Binary timeout
- Ruby: Script timeout
- C#: Dotnet timeout
- Kotlin: JAR timeout
- Swift: Script timeout

---

## 8. Caching & Resumability

### 8.1 Cache Structure
```python
cache = {
    "https://github.com/owner/repo": {
        "repo_url": "...",
        "Exception Type": "Mixed",
        "Languages": "python; java",
        "HTTP Libraries": "requests; okhttp",
        ...
    },
    ...
}
```

### 8.2 Incremental Saving

```python
save_cache_incrementally(cache, "analysis_cache.pkl", batch_size=1000)
# Saves every 1000 items to avoid memory overflow
```

### 8.3 Resumability

- Load existing cache at startup
- Skip already-processed repos if desired
- Append new results incrementally

---

## 9. Configuration System

### 9.1 Default Config (auto-created)

```ini
[paths]
input_csv_file_path = input_csv_file_19.csv
output_csv_file_path = analyze_error_handling_output.csv
clone_dir = cloned_repos
cache_file = analysis_cache.pkl
```

### 9.2 Update Logic

- Checks for existing `config.ini`
- If missing: creates with defaults
- If exists: updates with fallback values

---

## 10. Output Specification

### 10.1 CSV Output Schema

```csv
repo_url,Exception Type,Recommendation,Languages,HTTP Libraries,Parser Success Rate,
Has Try-Catch,Has Timeout,Has Retry,Has Circuit Breaker,Has Backoff,Has Status Check
```

### 10.2 Example Output Row

```csv
https://github.com/owner/repo,
Mixed,
"The codebase has basic and advanced exception handling.",
"python; java",
"requests; okhttp3",
95.50%,
TRUE,TRUE,TRUE,FALSE,FALSE,TRUE
```

---

## 11. Key Features & Innovations

### 11.1 Advanced Detection

**AST-based parsing** (Python) - Avoids false positives in comments
**Multi-language support** (8 languages + imports)
**HTTP library fingerprinting** - Identifies specific client libraries
**Pattern tracking** - Counts specific resilience patterns across codebase
**Parallel processing** - 4-worker pool for 50-repo batches
**Incremental caching** - Resumable, fault-tolerant analysis

### 11.2 Robustness

**Encoding handling** - Supports 9 character encodings
**Subprocess timeouts** - 30-second limits prevent hanging
**Retry logic** - Exponential backoff for git clone
**Directory cleanup** - Removes cloned repos after analysis
**Logging** - Queue-based multiprocessing-safe logging
**Error recovery** - Continues on parser failures

---

## 12. Runtime Configuration

### 12.1 Customizable Parameters

```python
batch_size = 50                    # Repos per batch
num_procs = min(4, os.cpu_count()) # Worker processes
timeout = 120                      # Git clone timeout (seconds)
clone_depth = 1                    # Shallow clone
retries = 2                        # Clone retry attempts
```

### 12.2 System Limits

```python
sys.setrecursionlimit(1500)        # Python recursion limit
```

---

## 13. File Structure

```
Project Root
├── WebServFH.py (main script)
├── config.ini (configuration)
├── input_csv_file_19.csv (input repositories)
├── analyze_error_handling_output.csv (results)
├── analysis_cache.pkl (cached results)
├── processing.log (main log)
├── processing_warnings.log (warnings)
├── cloned_repos/ (temporary clones)
├── parse_javascript.js (Node.js parser)
├── parse_typescript.js (Node.js parser)
├── parse_ruby.rb (Ruby parser)
├── parse_swift.py (Python parser for Swift)
├── parse_go_code/ (Go binary)
│   └── parse_go_code (executable)
├── parse_kotlin.jar (JAR file)
├── target/your-artifact-id-1.0-SNAPSHOT.jar (Java parser)
└── CSharpParser.dll (C# parser .NET)
```

---

## 14. Usage Instructions

### 14.1 Basic Execution

```bash
python3 WebServFH.py
```

### 14.2 Expected Workflow

1. Check/create `config.ini`
2. Read `input_csv_file_19.csv` # modify to specific location of your input file. 
3. Process repositories in batches of 50
4. Write results to `analyze_error_handling_output.csv`
5. Cache results in `analysis_cache.pkl`
6. Log operations to `processing.log` and `processing_warnings.log`

### 14.3 Resuming Processing

- Keep existing `analysis_cache.pkl`
- Re-run script (will skip cached repos)
- Or clear cache to reprocess all

---

## 15. Performance Metrics

| Metric | Value |
|--------|-------|
| Worker Processes | 4 |
| Batch Size | 50 repositories |
| Clone Timeout | 120 seconds |
| Parser Timeout | 30 seconds |
| HTTP Libraries Tracked | ~60 per language family |
| Supported Languages | 8 |
| Resilience Patterns | 6 |

---

## 16. Known Limitations & Future Improvements

### Current Limitations
- Java parser JAR may timeout on very large files
- Regex-based detection may miss obscured imports
- No support for dynamic imports (require/import statements)
- Pattern counting limited to file-level granularity

### Potential Enhancements
- Streaming parser for large repositories
- Machine learning pattern classification
- Dynamic import tracking
- Cross-method call graph analysis
- Distributed processing across machines

---

## 17. Contributing & Extension

### 17.1 Adding a New Language

1. Create parser function: `parse_<language>_code(code) → (type, patterns)`
2. Add to `language_parsers` dict
3. Add extension mapping: `.ext → language`
4. Add HTTP libraries to `HTTP_LIBRARIES` dict
5. Add detection function: `detect_<language>_http_libraries(code)`

### 17.2 Adding a New Pattern

1. Add to `detailed_patterns` dict initialization
2. Update parser visitors to detect pattern
3. Add to output CSV schema
4. Update recommendation logic if needed

---

## Conclusion

NiP Analyzer is a production-ready, multi-language code analysis framework designed to scale across thousands of repositories while maintaining accuracy through language-specific parsing strategies. Its modular architecture enables easy extension and customization for emerging languages and patterns.

