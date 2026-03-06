# NiP (Nobody Is Perfect) - Detection Rules (Language-Specific)

This document is part of the replication package.
It specifies the **operational rules** used by NiP to:

1. classify each repository into one of four categories (**None**, **Basic**, **Advanced**, **Mixed**), and
2. emit per-pattern indicator flags (**try_catch**, **status_check**, **timeout**, **retry**, **exponential_backoff**, **circuit_breaker**).

NiP is a multi-language analyzer. The main driver (Python) orchestrates cloning, file selection, and per-language analysis. Each language analyzer reports file-level detections; NiP aggregates them to a repository label and a CSV row.

---

## 1) Taxonomy and aggregation rules

### 1.1 File-level category
A file is categorized as:

- **None**   : no basic or advanced signals detected
- **Basic**  : at least one **basic** signal detected and no **advanced** signal detected
- **Advanced**: at least one **advanced** signal detected and no **basic** signal detected
- **Mixed**  : both basic and advanced signals detected, irrespective of proportion.

Notes:
- In practice, some ecosystems commonly combine basic handlers with advanced mechanisms; therefore **Mixed** is expected to occur frequently.
- Some per-language parsers may choose to categorize at the file level differently (e.g., treat any advanced detection as Advanced even when try/catch exists). If so, the parser must still emit the canonical flags above; NiP's repository aggregation remains consistent.

### 1.2 Repository-level classification (aggregation)
NiP aggregates file-level categories to a single repository label:

- Initialize `repo_label = None`.
- For each file label `file_label`:
  - If `repo_label` is `None`, set `repo_label = file_label`.
  - If `repo_label` is `Basic` and `file_label` is `Advanced`, set `repo_label = Mixed`.
  - If `repo_label` is `Advanced` and `file_label` is `Basic`, set `repo_label = Mixed`.
  - Otherwise keep the current `repo_label`.

NiP also aggregates pattern flags by counting how many files in the repository triggered each flag.

### 1.3 Parser success rate and exclusions
NiP tracks parser failures at the file level and reports:

- `Parser Success Rate = (total_files - parser_failures) / total_files`

Repositories with **0% parser success rate** are excluded from downstream analysis to avoid conflating "None" with "could not parse".

---

## 2) HTTP client library detection (metadata)

NiP performs separate HTTP client library detection for each file and aggregates detected libraries to the repository level. This signal is reported as the CSV field `HTTP Libraries` as metadata.

Important: HTTP library detection is **independent** of exception-handling detection. NiP does **not** restrict exception-handling detection to code that is syntactically co-located with HTTP call sites.

### 2.1 HTTP library catalog
NiP maintains a catalog of HTTP client libraries per language (`HTTP_LIBRARIES` in the Python driver). Detection is implemented via:

- AST import analysis (Python)
- import/require analysis and lightweight regex matching (Java, JS/TS)
- import/use detection in the corresponding language parser for other languages

Below is the catalog as shipped in this replication package.

#### Python
- Standard: `http.client`, `urllib`, `urllib.request`, `urllib2`, `httplib`
- Third-party: `urllib3`, `httplib2`, `requests`, `httpx`, `aiohttp`, `tornado.httpclient`, `treq`

#### Java
- Standard: `java.net.http.HttpClient`, `java.net.HttpURLConnection`
- Apache: `org.apache.http`, `org.apache.httpcomponents`
- Third-party: `okhttp3.OkHttpClient`, `com.squareup.okhttp`,
  `org.springframework.web.client.RestTemplate`, `org.springframework.web.reactive.function.client.WebClient`,
  `feign.Client`, `com.netflix.feign`, `org.glassfish.jersey.client`, `com.ning.http.client`

#### JavaScript
`axios`, `fetch`, `node-fetch`, `isomorphic-fetch`, `cross-fetch`, `superagent`, `request`, `got`,
`undici`, `ky`, `wretch`, `needle`, `http`, `https`, `node:http`, `node:https`

#### TypeScript
`axios`, `fetch`, `node-fetch`, `isomorphic-fetch`, `cross-fetch`, `superagent`, `got`, `undici`,
`ky`, `wretch`, `http`, `https`, `node:http`, `node:https`

#### Go
- Standard: `net/http`
- Third-party: `github.com/go-resty/resty`, `github.com/valyala/fasthttp`, `github.com/dghubble/sling`,
  `github.com/parnurzeal/gorequest`, `gopkg.in/h2non/gentleman`

#### C#
- Standard: `System.Net.Http.HttpClient`, `System.Net.WebClient`, `System.Net.HttpWebRequest`
- Third-party: `RestSharp`, `Flurl.Http`, `Refit`

#### Ruby
- Standard: `net/http`, `Net::HTTP`, `open-uri`
- Third-party: `httparty`, `rest-client`, `faraday`, `typhoeus`, `curb`, `excon`, `http.rb`

#### Kotlin
`okhttp3.OkHttpClient`, `com.squareup.okhttp`, `retrofit2`, `com.squareup.retrofit2`, `fuel`,
`com.github.kittinunf.fuel`, `io.ktor.client`, `org.http4k`, `java.net.http.HttpClient`

#### Swift
- Standard: `URLSession`, `Foundation.URLSession`, `URLRequest`, `NWConnection`
- Third-party: `Alamofire`, `Moya`, `AsyncHTTPClient`

===============================================================================================
### 3 Canonical pattern flags
Each language parser reports a `patterns` dictionary containing boolean flags:

- `try_catch`            : presence of native exception-handling constructs
- `status_check`         : explicit response status/error checks (or equivalent)
- `timeout`              : explicit timeout configuration or timeout mechanism
- `retry`                : explicit retry logic or retry framework usage
- `exponential_backoff`  : explicit backoff/delay strategy (including exponential backoff)
- `circuit_breaker`      : explicit circuit breaker usage

A parser may optionally also report `resilienceLibraries` (or `resilience_libraries`) as metadata.

## 4) Pattern detection rules by language
=====================================================================================
This section documents how each parser maps source code to the canonical pattern flags. The goal is to be explicit about the operationalization, while keeping the full implementation in code.

### 4.1 Python (AST-based)
Implementation: `parse_python_code()` in the Python driver.

**Basic signals**
- `try_catch`:
  - AST nodes: `ast.Try`, `ast.ExceptHandler`
- `status_check`:
  - attribute/method access with names `status_code` or `raise_for_status` in a call expression

**Advanced signals**
Python advanced detection is context-aware: NiP only counts a keyword when it is used as a **function/method call**, a **context manager**, a **decorator**, or a known **resilience import**.

- Resilience imports (set advanced flag):
  - `tenacity`, `pybreaker`, `backoff`, `retry`, `circuit_breaker`
  - from-import modules also include: `urllib3.util.retry`, `requests.adapters`

- `timeout`:
  - direct call: `timeout(...)`
  - attribute call: `.timeout(...)`, `.with_timeout(...)`
  - context manager: `with timeout(...):`
  - decorator: `@timeout` or `@timeout(...)`

- `retry`:
  - direct call: `retry(...)`
  - attribute call: `.retry(...)`, `.with_retry(...)`
  - context manager: `with retry(...):`
  - decorator: `@retry` or `@retry(...)`

- `circuit_breaker`:
  - direct call: `circuitbreaker(...)` or `circuit_breaker(...)`
  - context manager: `with circuitbreaker(...):`
  - decorator: `@circuitbreaker` / `@circuit_breaker`

- `exponential_backoff`:
  - direct call: `backoff(...)`
  - attribute call: `.with_backoff(...)`, `.exponential_backoff(...)`

### 4.2 Java (JavaParser + regex fallback)
Implementation: `parse_java_code()` in the Python driver.

NiP invokes a JavaParser-based analyzer (packaged as a JAR) that emits:
- `hasBasicHandling`, `hasAdvancedHandling`, and optionally `patterns`.

If the JAR does not detect advanced handling, NiP applies a regex fallback to detect common Java resilience mechanisms.

**Regex fallback: advanced signals**
- Resilience library imports (also recorded as metadata):
  - Resilience4j: `import io.github.resilience4j...`
  - Hystrix: `import com.netflix.hystrix...`
  - Spring Retry: `import org.springframework.retry...`
  - Failsafe: `import dev.failsafe...` or `import net.jodah.failsafe...`

- `retry`:
  - annotations: `@Retryable`, `@Retry`
  - class names: `RetryConfig`, `RetryRegistry`, `RetryTemplate`
  - method patterns: `.retry(`, `.withRetry(`, `Retry.of(`

- `circuit_breaker`:
  - annotations: `@HystrixCommand`, `@CircuitBreaker`
  - class names: `CircuitBreakerConfig`, `CircuitBreakerRegistry`, `HystrixCommand`
  - method patterns: `CircuitBreaker.of(`, `.circuitBreaker(`

- `timeout`:
  - annotations: `@TimeLimiter`
  - class names: `TimeLimiterConfig`, `TimeLimiterRegistry`
  - method patterns: `TimeLimiter.of(`, `.timeout(`

- `exponential_backoff`:
  - annotations: `@Backoff`
  - class names: `ExponentialBackOff`, `BackOffPolicy`

### 4.3 JavaScript
Implementation: `parse_javascript.js` (Node-based parser).

The JavaScript parser returns `hasBasicHandling`, `hasAdvancedHandling`, `patterns`, and optionally `resilienceLibraries`.

**Basic signals (expected)**
- `try_catch`: `try { ... } catch (e) { ... }`
- `status_check`: explicit response status checks, e.g., `response.status`, `response.statusCode`, `response.ok`, `res.statusCode`

**Advanced signals (expected)**
- `timeout`: explicit timeout configuration, e.g., `axios({ timeout: ... })`, `AbortController` timeouts, client config fields containing `timeout`
- `retry`: explicit retry logic or retry libraries (e.g., library/module names containing `retry`, `axios-retry`, `promise-retry`), or loops that re-issue requests under failure
- `exponential_backoff`: identifiers containing `backoff` / `exponential` combined with delayed retry (`setTimeout`, `sleep` polyfills)
- `circuit_breaker`: circuit breaker libraries (e.g., `opossum`) or identifiers containing `circuit` in breaker context

The authoritative implementation is the parser code in `parse_javascript.js`.

### 4.4 TypeScript
Implementation: `parse_typescript.js` (Node-based parser).

Same output contract as JavaScript.

**Basic signals (expected)**
- `try_catch`: `try/catch`
- `status_check`: response status checks in common client code

**Advanced signals (expected)**
- `timeout`: axios/fetch timeout configuration, AbortController patterns
- `retry`, `exponential_backoff`, `circuit_breaker`: same as JavaScript

The authoritative implementation is the parser code in `parse_typescript.js`.

### 4.5 Go
Implementation: `parse_go_code/parse_go_code` (Go-based parser/binary).

The Go parser returns JSON with `hasBasicHandling`, `hasAdvancedHandling`, `patterns`, and optionally `resilience_libraries`. (Older versions may return CSV with only basic/advanced booleans.)

**Basic signals (expected)**
- `try_catch`: Go does not have try/catch; basic handling is operationalized via error returns and panic recovery, e.g.:
  - `if err != nil { ... }` checks
  - `defer func(){ if r := recover(); r != nil { ... } }()`
- `status_check`: checks on HTTP response status, e.g., `resp.StatusCode`, `resp.Status`

**Advanced signals (expected)**
- `timeout`: `http.Client{Timeout: ...}`, `context.WithTimeout(...)`, request contexts with deadlines
- `retry`: explicit retry loops; or libraries such as `go-retryablehttp` (if present in the replication package rule list)
- `exponential_backoff`: libraries/identifiers containing `backoff`, usage of `time.Sleep(...)` in retry loops
- `circuit_breaker`: libraries/identifiers containing `breaker` / `circuit` (e.g., gobreaker)

The authoritative implementation is the Go parser sources in `parse_go_code/`.

### 4.6 Ruby
Implementation: `parse_ruby.rb`.

The Ruby parser returns JSON with `hasBasicHandling`, `hasAdvancedHandling`, `patterns`, and optionally `resilienceLibraries`. (Older versions may return CSV with only basic/advanced booleans.)

**Basic signals (expected)**
- `try_catch`: `begin ... rescue ... end`, `rescue` modifier
- `status_check`: response status checks such as `response.code`, `response.status`

**Advanced signals (expected)**
- `timeout`: `Timeout.timeout(...)` or HTTP client timeout options
- `retry`: Ruby `retry` keyword in rescue blocks, or retry middleware/gems
- `exponential_backoff`: backoff/delay identifiers and `sleep` in retry loops
- `circuit_breaker`: breaker gems/middleware (e.g., circuitbox) or breaker identifiers

The authoritative implementation is the parser code in `parse_ruby.rb`.

### 4.7 C#
Implementation: `CSharpParser` (dotnet parser).

The C# parser returns JSON with `hasBasicHandling`, `hasAdvancedHandling`, `patterns`, and optionally `resilienceLibraries`. (Older versions may return CSV with only basic/advanced booleans.)

**Basic signals (expected)**
- `try_catch`: `try { ... } catch (Exception e) { ... }`
- `status_check`: checks on `HttpResponseMessage.StatusCode`, `IsSuccessStatusCode`

**Advanced signals (expected)**
- `timeout`: `HttpClient.Timeout = ...`, request cancellation tokens with timeouts
- `retry` / `exponential_backoff` / `circuit_breaker`: resilience libraries such as Polly (Retry/WaitAndRetry/CircuitBreaker) when present in imports/usages

The authoritative implementation is the C# parser project shipped in the replication package.

### 4.8 Kotlin
Implementation: `parse_kotlin.jar`.

The Kotlin parser returns JSON with `hasBasicHandling`, `hasAdvancedHandling`, `patterns`, and optionally `resilienceLibraries`. (Older versions may return CSV with only basic/advanced booleans.)

**Basic signals (expected)**
- `try_catch`: `try { ... } catch (e: Exception) { ... }`
- `status_check`: status checks on common client responses

**Advanced signals (expected)**
- `timeout`: coroutine timeouts (`withTimeout`, `withTimeoutOrNull`) and HTTP client timeout configuration
- `retry` / `exponential_backoff` / `circuit_breaker`: Resilience4j usage (if present) or explicit retry/backoff constructs

The authoritative implementation is the Kotlin parser sources/JAR shipped in the replication package.

### 4.9 Swift
Implementation: `parse_swift.py`.

The Swift parser returns JSON with `hasBasicHandling`, `hasAdvancedHandling`, `patterns`, and optionally `resilienceLibraries`.

**Basic signals (expected)**
- `try_catch`: Swift `do { ... } catch { ... }` and error-handling keywords (`try`, `try?`, `try!`) as implemented in the parser
- `status_check`: `HTTPURLResponse.statusCode` checks

**Advanced signals (expected)**
- `timeout`: `URLSessionConfiguration.timeoutIntervalForRequest/Resource`, request timeout parameters in common client frameworks
- `retry` / `exponential_backoff`: retry loops and delayed retries (e.g., `DispatchQueue.asyncAfter`, `Task.sleep`) when present
- `circuit_breaker`: breaker identifiers or library usage if present

The authoritative implementation is `parse_swift.py` shipped in the replication package.

---

## 5) Known limitations

- Several languages rely on lexical matching and/or library-name matching for advanced patterns. This can:
  - miss framework-driven idioms (annotation-based, configuration-only, code generation), and
  - occasionally flag unrelated identifiers.
- NiP does not restrict exception-handling detection to code syntactically co-located with HTTP call sites. The study scope is: exception-handling practices in repositories that primarily function as Web-service clients.
- "None" means "no signals detected in parsed files"; repositories with 0% parser success rate are excluded rather than counted as "None".

---

## 6) How to update / extend the rules

1. Update the appropriate language parser implementation (Python driver or per-language parser).
2. If you add or rename pattern flags, update:
   - Section 1.1 (canonical flag list)
   - repository aggregation logic
   - the CSV schema emitted by the driver
3. If you add HTTP client libraries, update `HTTP_LIBRARIES` and Section 2.1.

