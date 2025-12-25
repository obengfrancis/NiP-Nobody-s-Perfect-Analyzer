# Dependencies Documentation

## Python Dependencies (requirements.txt)

Install with:
```bash
pip install -r requirements.txt
```

Current packages:
- javalang==0.13.0 (for Java parsing)
- esprima==4.0.1 (for JavaScript parsing, if used)
- tree-sitter (for AST parsing)
- Other utilities (matplotlib, numpy, tqdm, psutil, etc.)

---

## External Runtime Dependencies

### Required Language Runtimes:

1. **Python 3.8+** (main application)
   ```bash
   python3 --version
   ```

2. **Java Runtime (JRE/JDK)** (for Kotlin parser)
   ```bash
   java -version
   ```

3. **Node.js** (for JavaScript/TypeScript parsers)
   ```bash
   node --version
   ```

4. **Ruby** (for Ruby parser)
   ```bash
   ruby --version
   ```

5. **Go** (for Go parser - if not using compiled binary)
   ```bash
   go version
   ```

6. **Mono/.NET** (for C# parser - if not using compiled binary)
   ```bash
   mono --version
   # or
   dotnet --version
   ```

---

## Language-Specific Parser Dependencies

### Ruby Parser:
```bash
gem install parser
```

### Kotlin Parser:
Requires the `parse_kotlin.jar` file (pre-built)
- Dependencies bundled in JAR (Gson, Kotlin stdlib)

### JavaScript/TypeScript Parsers:
No additional packages needed (pure Node.js)

### Swift Parser:
Pure Python - no additional dependencies!

### Go Parser:
Compiled binary - no additional dependencies!

### C# Parser:
Compiled binary - no additional dependencies!

---

## Quick Dependency Check Script

```bash
#!/bin/bash
echo "Checking dependencies..."

echo -n "Python 3: "
python3 --version 2>/dev/null || echo "❌ Not found"

echo -n "Java: "
java -version 2>&1 | head -1 || echo "❌ Not found"

echo -n "Node.js: "
node --version 2>/dev/null || echo "❌ Not found"

echo -n "Ruby: "
ruby --version 2>/dev/null || echo "❌ Not found"

echo -n "Go: "
go version 2>/dev/null || echo "❌ Not found"

echo -n "Mono/.NET: "
mono --version 2>/dev/null | head -1 || dotnet --version 2>/dev/null || echo "❌ Not found"

echo -n "Ruby parser gem: "
gem list parser | grep "^parser " || echo "❌ Not installed"

echo ""
echo "Parser files:"
ls -1 parse_*.py parse_*.js parse_*.jar parse_*.rb 2>/dev/null | sed 's/^/  ✓ /'
```

---

## Installation Guide

### macOS (Homebrew):
```bash
# Install runtimes
brew install python node ruby openjdk go mono

# Install Ruby gem
gem install parser

# Install Python packages
pip3 install -r requirements.txt
```

### Ubuntu/Debian:
```bash
# Install runtimes
sudo apt-get update
sudo apt-get install python3 python3-pip nodejs ruby-full openjdk-11-jdk golang mono-complete

# Install Ruby gem
gem install parser

# Install Python packages
pip3 install -r requirements.txt
```

---

## Minimal Setup (Analysis Only)

If you only need to analyze the dataset and all parsers are pre-compiled:

**Required:**
- Python 3.8+
- Java (for parse_kotlin.jar)
- Node.js (for parse_javascript.js, parse_typescript.js)
- Ruby + parser gem (for parse_ruby.rb)

**Optional (if using pre-compiled binaries):**
- Go compiler (not needed if parse_go_code is compiled)
- C# compiler (not needed if parse_csharp_code is compiled)