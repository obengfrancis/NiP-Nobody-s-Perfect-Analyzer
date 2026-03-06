![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Java](https://img.shields.io/badge/Java-11+-007396?style=for-the-badge&logo=java&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-4.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![C#](https://img.shields.io/badge/C%23-6.0+-239120?style=for-the-badge&logo=c-sharp&logoColor=white)
![Go](https://img.shields.io/badge/Go-1.16+-00ADD8?style=for-the-badge&logo=go&logoColor=white)
![Ruby](https://img.shields.io/badge/Ruby-2.7+-CC342D?style=for-the-badge&logo=ruby&logoColor=white)
![Kotlin](https://img.shields.io/badge/Kotlin-1.5+-7F52FF?style=for-the-badge&logo=kotlin&logoColor=white)
![Swift](https://img.shields.io/badge/Swift-5.5+-FA7343?style=for-the-badge&logo=swift&logoColor=white)

-----------------------------------------------------------------------------------------------------------------------
# WebServFH aka Nobody's Perfect (NiP for short).
-----------------------------------------------------------------------------------------------------------------------

**WebServFH** is a Python-based static analysis tool designed to automatically detect and classify exception handling, detect HTTP library uasge, and detect resilience patterns in web service client repositories across nine programming languages.

> **Note:** In our research paper, this tool is referred to as **NiP** (Noboody's Perfect) for brevity.

-----------------------------------------------------------------------------------------------------------------------
## Overview
-----------------------------------------------------------------------------------------------------------------------

WebServFH performs comprehensive analysis of exception handling strategies in web service clients by:
- **Parsing source code** using language-specific Abstract Syntax Tree (AST) parsers
- **Classifying repositories** into four categories: None, Basic, Mixed, and Advanced
- **Identifying HTTP library usage** across 9 programming languages
- **Detecting resilience patterns** including timeouts, retries, circuit breakers, exponential backoff, and status checks
- **Generating detailed reports** with pattern prevalence and adoption metrics

-----------------------------------------------------------------------------------------------------------------------
## Features
-----------------------------------------------------------------------------------------------------------------------
### Core Capabilities
-  **Multi-language support**: Analyzes 9 programming languages
-  **AST-based parsing**: Language-specific Abstract Syntax Tree analysis
-  **HTTP library detection**: Identifies 50+ HTTP client libraries
-  **Resilience pattern detection**: Identifies 6 advanced fault-handling patterns
-  **Comprehensive logging**: System and process-level logging for debugging
-  **Configurable execution**: INI-based configuration for easy customization
-  **Batch processing**: Handles large datasets with automatic chunking
-  **Temporary file management**: Secure and clean parsing execution
-  **Parser fallback mechanisms**: Regex-based detection when AST parsing fails

-----------------------------------------------------------------------------------------------------------------------
## Supported Languages
-----------------------------------------------------------------------------------------------------------------------

WebServFH analyzes source code in the following languages:

| Language | Parser | Version Required |
|----------|--------|------------------|
| **Python** | AST (built-in) | Python 3.10+ |
| **Java** | JavaParser (JAR) | Java 11+ |
| **JavaScript** | Esprima | Node.js 14+ |
| **TypeScript** | TypeScript Compiler | TypeScript 4.0+ |
| **C#** | Roslyn | .NET 6.0+ |
| **Go** | go/parser | Go 1.16+ |
| **Ruby** | parser gem | Ruby 2.7+ |
| **Kotlin** | kotlinc | Kotlin 1.5+ |
| **Swift** | SwiftSyntax | Swift 5.5+ |

> ** Important:** All languages and their compilers/interpreters must be installed on the machine running WebServFH.

-----------------------------------------------------------------------------------------------------------------------
## Classification Taxonomy
-----------------------------------------------------------------------------------------------------------------------

WebServFH classifies repositories into **four categories** based on detected patterns:

| Category | Definition | Patterns Detected |
|----------|-----------|-------------------|
| **None** | No exception handling detected | No try-catch, no patterns |
| **Basic** | Only try-catch and/or status checks | Try-catch, HTTP status checks |
| **Advanced** | Advanced patterns only (no try-catch) | Timeout, Retry, Circuit Breaker, Backoff |
| **Mixed** | Both basic and advanced patterns | Try-catch/or status checks + any advanced pattern |


-----------------------------------------------------------------------------------------------------------------------
## HTTP Library Detection
-----------------------------------------------------------------------------------------------------------------------

WebServFH automatically detects HTTP client library usage across all supported languages. This enables analysis of framework-specific resilience patterns and ecosystem-level practices.

### Supported HTTP Libraries by Language (Python and Java)
<summary><b>📘 Python (10+ libraries)</b></summary>

| Library | Detection Method | Common Patterns |
|---------|-----------------|-----------------|
| **requests** | `import requests` | Retry adapters, timeout parameters |
| **httpx** | `import httpx` | Async/await, built-in retries |
| **aiohttp** | `import aiohttp` | Async sessions, timeout configs |
| **urllib3** | `import urllib3` | Retry strategies, timeout |
| **http.client** | `import http.client` | Standard library HTTP |
| **tornado** | `import tornado.httpclient` | Async HTTP client |
| **treq** | `import treq` | Twisted-based HTTP |
| **requests-futures** | `import requests_futures` | Async requests wrapper |
| **grequests** | `import grequests` | Gevent-based async |
| **urllib** | `from urllib import request` | Standard library (legacy) |


<summary><b>☕ Java (8+ libraries)</b></summary>

| Library | Detection Method | Common Patterns |
|---------|-----------------|-----------------|
| **HttpClient (Java 11+)** | `java.net.http.HttpClient` | Built-in timeout, async |
| **OkHttp** | `okhttp3.OkHttpClient` | Interceptors, retry |
| **Apache HttpClient** | `org.apache.http.client` | Retry handlers, timeout |
| **RestTemplate** | `org.springframework.web.client.RestTemplate` | Spring integration |
| **WebClient** | `org.springframework.web.reactive.function.client.WebClient` | Reactive, retry |
| **Retrofit** | `retrofit2.Retrofit` | Annotation-based |
| **Jersey Client** | `javax.ws.rs.client.Client` | JAX-RS standard |
| **AsyncHttpClient** | `org.asynchttpclient.AsyncHttpClient` | Async operations |


-----------------------------------------------------------------------------------------------------------------------
## Resilience Patterns Detected
-----------------------------------------------------------------------------------------------------------------------
WebServFH identifies **six resilience patterns** commonly used in web service clients:

| Pattern | Description |
|--------|-------------|
| `Has Try-Catch` | Boolean: Try-catch blocks detected |
| `Has Timeout` | Boolean: Timeout pattern detected |
| `Has Retry` | Boolean: Retry pattern detected |
| `Has Circuit Breaker` | Boolean: Circuit breaker detected |
| `Has Backoff` | Boolean: Exponential backoff detected |
| `Has Status Check` | Boolean: HTTP status check detected |



-----------------------------------------------------------------------------------------------------------------------
## Installation
-----------------------------------------------------------------------------------------------------------------------
### Prerequisites
Ensure all supported languages and their compilers are installed:
```bash
#IDE
VSCode preferred for running "python WebServFH.py" 
# Python
python --version  # 3.10+

# Java
java --version    # 11+

# Node.js (for JavaScript/TypeScript)
node --version    # 14+

# Go
go version        # 1.16+

# Ruby
ruby --version    # 2.7+

# Kotlin
kotlinc -version  # 1.5+

# Swift
swift --version   # 5.5+

# .NET (for C#)
dotnet --version  # 6.0+
```

### Setup Steps

1. **Create project directory:**
```bash
   mkdir NEW_AST_WEBSERVFH
   cd NEW_AST_WEBSERVFH
```

2. **Clone the repository:**
```bash
   git clone https://github.com/obengfrancis/NiP-Nobody-s-Perfect-Analyzer.git
```

3. **Install Python dependencies:**
```bash
   pip install -r requirements.txt
```

4. **Install language-specific dependencies:**
```bash
   # JavaScript/TypeScript
   npm install esprima
   npm install typescript

   # Ruby
   gem install parser

   # Kotlin (if not using system kotlinc)
   # Download from https://kotlinlang.org/
```

5. **Configure paths in `config.ini`:**
```ini
   [paths]
   input_csv_file_path = /path/to/your/input.csv
   output_csv_file_path = /path/to/your/output.csv
   clone_dir = /path/to/your/clones
   cache_file = /path/to/your/cache.pkl
   log_dir = /path/to/your/logs
```

   > **Note:** Paths in `create_config_file()` must match `update_config_file()`


-----------------------------------------------------------------------------------------------------------------------
## Usage/Running
-----------------------------------------------------------------------------------------------------------------------
### Basic Execution
```bash
python WebServFH.py
```

-----------------------------------------------------------------------------------------------------------------------
### Input Format
-----------------------------------------------------------------------------------------------------------------------

Your input CSV must contain a `repo_url` column:
```csv
repo_url,other metedata
https://github.com/user/repo1, 
https://github.com/user/repo2,
```

-----------------------------------------------------------------------------------------------------------------------
### Output Format
-----------------------------------------------------------------------------------------------------------------------
WebServFH generates a detailed CSV with the following columns:

| Column | Description |
|--------|-------------|
| `repo_url` | GitHub repository URL |
| `Languages` | Detected programming language(s) |
| `Exception Type` | Classification (None/Basic/Mixed/Advanced) |
| `HTTP_Libraries` | Detected HTTP client libraries (comma-separated) |
| `Has Try-Catch` | Boolean: Try-catch blocks detected |
| `Has Timeout` | Boolean: Timeout pattern detected |
| `Has Retry` | Boolean: Retry pattern detected |
| `Has Circuit Breaker` | Boolean: Circuit breaker detected |
| `Has Backoff` | Boolean: Exponential backoff detected |
| `Has Status Check` | Boolean: HTTP status check detected |
| `Parser Success Rate` | Percentage of successfully parsed files |
| `Total Files Analyzed` | Count of analyzed files |
| `Error Details` | Any parsing errors encountered |

-----------------------------------------------------------------------------------------------------------------------
## Processing Large Datasets
-----------------------------------------------------------------------------------------------------------------------
For large datasets (e.g., 10,000+ repositories):
1. **Divide input into chunks:**
```bash
   # Split into batches of 1,000-2,000 repositories, and modify input file path
    1. input_csv_file_path = /path/to/your/input.csv
    2. python WebServFH.py 
```

-----------------------------------------------------------------------------------------------------------------------
## Dependencies
-----------------------------------------------------------------------------------------------------------------------

### Python Packages (requirements.txt)
- pip install requirements.txt
```
pandas>=1.3.0
requests>=2.26.0
GitPython>=3.1.18
configparser>=5.0.2
esprima>=4.0.1
```

### External Tools
- **Java:** JavaParser JAR (included in project)
- **Node.js:** esprima, typescript
- **Ruby:** parser gem
- **Others:** System-installed compilers


-----------------------------------------------------------------------------------------------------------------------
## Logging
-----------------------------------------------------------------------------------------------------------------------
WebServFH provides comprehensive logging:
```
logs/
├── webservfh_YYYYMMDD_HHMMSS.log  # Main execution log
├── processing.log                 # Parsing failures
└── processing_warnings.log         # Summary statistics
```

**Log levels:**
- `INFO`: Normal execution progress
- `WARNING`: Non-critical issues (e.g., parser fallback)
- `ERROR`: Parsing failures, missing dependencies
- `CRITICAL`: Fatal errors requiring intervention


-----------------------------------------------------------------------------------------------------------------------
## Troubleshooting
-----------------------------------------------------------------------------------------------------------------------
### Common Issues

**1. Parser Failures (0.00% success rate):**
- Verify language compilers are installed
- Check file permissions in clone directory
- Review `processing.log`, and `processing_warnings.log` for details

**2. Missing Dependencies:**
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

**3. Java Parser Not Found:**
```bash
# Rebuild JavaParser JAR
cd parsers/java
mvn clean package
```

**4. Memory Issues (Large Datasets):**
- Process in smaller chunks (1000-2000 repos)
- Increase system memory allocation
- Enable disk-based caching in `config.ini`



-----------------------------------------------------------------------------------------------------------------------
## License
-----------------------------------------------------------------------------------------------------------------------
[MIT Licence.........]


-----------------------------------------------------------------------------------------------------------------------
## Contributing
-----------------------------------------------------------------------------------------------------------------------

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with detailed description


-----------------------------------------------------------------------------------------------------------------------
## Contact
-----------------------------------------------------------------------------------------------------------------------
For questions, issues, or feature requests:
- **GitHub Issues:** https://github.com/WebServFH/nip-analyzer-project/issues
- **Email:** [my-email@domain.com]


-----------------------------------------------------------------------------------------------------------------------
## Acknowledgments
-----------------------------------------------------------------------------------------------------------------------
This tool was developed as part of research on exception handling and resilience patterns in web service client application. Special thanks to the open-source community for language parser libraries.
