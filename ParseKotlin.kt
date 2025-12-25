import java.io.File
import com.google.gson.Gson

// ============================================================================
//  Data Classes for JSON Output
// ============================================================================

data class ParseResult(
    val hasBasicHandling: Boolean,
    val hasAdvancedHandling: Boolean,
    val patterns: Map<String, Boolean>,
    val resilienceLibraries: List<String>
)

// ============================================================================
//  Resilience Library Definitions
// ============================================================================

val RESILIENCE_LIBRARIES = mapOf(
    // HTTP Clients
    "okhttp3" to mapOf("patterns" to listOf("timeout"), "type" to "http_client"),
    "com.squareup.okhttp3" to mapOf("patterns" to listOf("timeout"), "type" to "http_client"),
    "retrofit2" to mapOf("patterns" to listOf("timeout"), "type" to "http_client"),
    "com.squareup.retrofit2" to mapOf("patterns" to listOf("timeout"), "type" to "http_client"),
    "io.ktor.client" to mapOf("patterns" to listOf("timeout", "retry"), "type" to "http_client"),
    "com.github.kittinunf.fuel" to mapOf("patterns" to listOf("timeout"), "type" to "http_client"),
    
    // Resilience4j
    "io.github.resilience4j" to mapOf("patterns" to listOf("retry", "circuit_breaker", "timeout"), "type" to "resilience"),
    "io.github.resilience4j.retry" to mapOf("patterns" to listOf("retry"), "type" to "retry"),
    "io.github.resilience4j.circuitbreaker" to mapOf("patterns" to listOf("circuit_breaker"), "type" to "circuit_breaker"),
    "io.github.resilience4j.kotlin" to mapOf("patterns" to listOf("retry", "circuit_breaker"), "type" to "resilience"),
    
    // Coroutines
    "kotlinx.coroutines" to mapOf("patterns" to listOf("timeout"), "type" to "coroutines"),
    
    // Java standard
    "java.net.http" to mapOf("patterns" to listOf("timeout"), "type" to "http_client")
)

// ============================================================================
//  Kotlin Code Analyzer
// ============================================================================

class KotlinCodeAnalyzer(private val code: String) {
    private var hasBasicHandling = false
    private var hasAdvancedHandling = false
    private val patterns = mutableMapOf(
        "try_catch" to false,
        "timeout" to false,
        "retry" to false,
        "circuit_breaker" to false,
        "exponential_backoff" to false,
        "status_check" to false,
        "rate_limiting" to false,
        "coroutine_timeout" to false
    )
    private val resilienceLibraries = mutableSetOf<String>()

    fun analyze(): ParseResult {
        // Detect import statements
        detectImports()
        
        // Detect try-catch blocks
        detectTryCatch()
        
        // Detect timeout patterns
        detectTimeoutPatterns()
        
        // Detect retry patterns
        detectRetryPatterns()
        
        // Detect circuit breaker patterns
        detectCircuitBreakerPatterns()
        
        // Detect status checks
        detectStatusChecks()
        
        //  Detect coroutine patterns
        detectCoroutinePatterns()
        
        // Detect configuration patterns
        detectConfigurationPatterns()
        
        return ParseResult(
            hasBasicHandling = hasBasicHandling,
            hasAdvancedHandling = hasAdvancedHandling,
            patterns = patterns,
            resilienceLibraries = resilienceLibraries.toList().sorted()
        )
    }

    //  Import detection
    private fun detectImports() {
        val importPattern = Regex("""^\s*import\s+([\w.]+)""", RegexOption.MULTILINE)
        
        importPattern.findAll(code).forEach { match ->
            val importPath = match.groupValues[1]
            
            // Check against known resilience libraries
            RESILIENCE_LIBRARIES.forEach { (libPattern, libInfo) ->
                if (importPath.startsWith(libPattern)) {
                    // Add canonical library name
                    val libraryName = when {
                        libPattern.contains("okhttp3") -> "OkHttp"
                        libPattern.contains("retrofit2") -> "Retrofit"
                        libPattern.contains("ktor.client") -> "Ktor Client"
                        libPattern.contains("fuel") -> "Fuel"
                        libPattern.contains("resilience4j") -> "Resilience4j"
                        libPattern.contains("kotlinx.coroutines") -> "Kotlinx Coroutines"
                        else -> libPattern
                    }
                    
                    resilienceLibraries.add(libraryName)
                    hasAdvancedHandling = true
                    
                    // Set pattern flags based on library
                    @Suppress("UNCHECKED_CAST")
                    val patternsList = libInfo["patterns"] as? List<String> ?: emptyList()
                    patternsList.forEach { pattern ->
                        patterns[pattern] = true
                    }
                }
            }
        }
    }

    // Try-catch detection
    private fun detectTryCatch() {
        // Pattern: try { ... } catch
        val tryCatchPattern = Regex("""\btry\s*\{[^}]*\}\s*catch\b""")
        
        if (tryCatchPattern.containsMatchIn(code)) {
            hasBasicHandling = true
            patterns["try_catch"] = true
        }
    }

    // Timeout patterns detection
    private fun detectTimeoutPatterns() {
        val timeoutPatterns = listOf(
            // Coroutine withTimeout
            Regex("""\bwithTimeout\s*\("""),
            Regex("""\bwithTimeoutOrNull\s*\("""),
            
            // OkHttp timeout
            Regex("""\b(connectTimeout|readTimeout|writeTimeout|callTimeout)\s*\("""),
            
            // Retrofit timeout
            Regex("""\b(timeout|readTimeout|writeTimeout)\s*\("""),
            
            // Ktor timeout
            Regex("""\binstall\s*\(\s*HttpTimeout\s*\)"""),
            Regex("""\brequestTimeoutMillis\s*="""),
            
            // Configuration object
            Regex("""\btimeout\s*[:=]"""),
            
            // Timeout class usage
            Regex("""\bTimeout\s*\.""")
        )
        
        timeoutPatterns.forEach { pattern ->
            if (pattern.containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["timeout"] = true
                return
            }
        }
    }

    // Retry patterns detection
    private fun detectRetryPatterns() {
        val retryPatterns = listOf(
            // Resilience4j retry
            Regex("""\bretry\s*\{"""),
            Regex("""\bRetry\.of"""),
            Regex("""\bRetry\.ofDefaults"""),
            Regex("""\bretryAsync\s*\{"""),
            
            // Ktor retry
            Regex("""\binstall\s*\(\s*HttpRequestRetry\s*\)"""),
            
            // Function names containing retry
            Regex("""\bfun\s+\w*[Rr]etry\w*\s*\("""),
            
            // Retry configuration
            Regex("""\bretries\s*[:=]"""),
            Regex("""\bmaxRetries\s*[:=]"""),
            Regex("""\bretryCount\s*[:=]"""),
            
            // Loop-based retry
            Regex("""\brepeat\s*\("""),
            Regex("""\bwhile\s*\([^)]*retry""", RegexOption.IGNORE_CASE)
        )
        
        retryPatterns.forEach { pattern ->
            if (pattern.containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["retry"] = true
                
                // Check for exponential backoff
                if (Regex("""exponential|backoff""", RegexOption.IGNORE_CASE).containsMatchIn(code)) {
                    patterns["exponential_backoff"] = true
                }
                return
            }
        }
    }

    // Circuit breaker patterns detection
    private fun detectCircuitBreakerPatterns() {
        val circuitBreakerPatterns = listOf(
            // Resilience4j circuit breaker
            Regex("""\bcircuitBreaker\s*\{"""),
            Regex("""\bCircuitBreaker\.of"""),
            Regex("""\bCircuitBreaker\.ofDefaults"""),
            
            // Class names
            Regex("""\bclass\s+\w*CircuitBreaker\w*""", RegexOption.IGNORE_CASE),
            
            // Variable declarations
            Regex("""\bval\s+\w*[Cc]ircuit\w*\s*="""),
            Regex("""\bvar\s+\w*[Bb]reaker\w*\s*=""")
        )
        
        circuitBreakerPatterns.forEach { pattern ->
            if (pattern.containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["circuit_breaker"] = true
                return
            }
        }
    }

    // Status check patterns detection
    private fun detectStatusChecks() {
        val statusCheckPatterns = listOf(
            // Response code checks
            Regex("""\b(response|result)\s*\.\s*code\s*\(\s*\)"""),
            Regex("""\b(response|result)\s*\.\s*statusCode"""),
            Regex("""\b(response|result)\s*\.\s*status"""),
            
            // HTTP status comparisons
            Regex("""\b(code|status|statusCode)\s*==\s*\d+"""),
            Regex("""\bisSuccessful\s*\(\s*\)"""),
            Regex("""\b(is2xxSuccessful|is4xxClientError|is5xxServerError)""")
        )
        
        statusCheckPatterns.forEach { pattern ->
            if (pattern.containsMatchIn(code)) {
                hasBasicHandling = true
                patterns["status_check"] = true
                return
            }
        }
    }

    // Coroutine  detection
    private fun detectCoroutinePatterns() {
        val coroutinePatterns = listOf(
            // Timeout
            Regex("""\bwithTimeout\s*\("""),
            Regex("""\bwithTimeoutOrNull\s*\("""),
            
            // Supervisors (error handling)
            Regex("""\bSupervisorJob\s*\("""),
            Regex("""\bsupervisorScope\s*\{"""),
            
            // Error handlers
            Regex("""\bCoroutineExceptionHandler\s*\{""")
        )
        
        coroutinePatterns.forEach { pattern ->
            if (pattern.containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["coroutine_timeout"] = true
                patterns["timeout"] = true
                return
            }
        }
    }

    // Configuration patterns detection
    private fun detectConfigurationPatterns() {
        // OkHttp Builder configuration
        val okHttpConfigPattern = Regex("""\bOkHttpClient\.Builder\s*\(\s*\)""")
        if (okHttpConfigPattern.containsMatchIn(code)) {
            resilienceLibraries.add("OkHttp")
            
            // Check for specific configurations
            if (Regex("""\b(connectTimeout|readTimeout|writeTimeout)\s*\(""").containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["timeout"] = true
            }
        }
        
        // Retrofit Builder configuration
        val retrofitConfigPattern = Regex("""\bRetrofit\.Builder\s*\(\s*\)""")
        if (retrofitConfigPattern.containsMatchIn(code)) {
            resilienceLibraries.add("Retrofit")
            
            if (Regex("""\bcallTimeout\s*\(""").containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["timeout"] = true
            }
        }
        
        // Ktor Client configuration
        val ktorConfigPattern = Regex("""\bHttpClient\s*\{""")
        if (ktorConfigPattern.containsMatchIn(code)) {
            resilienceLibraries.add("Ktor Client")
            
            if (Regex("""\binstall\s*\(\s*HttpTimeout\s*\)""").containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["timeout"] = true
            }
            
            if (Regex("""\binstall\s*\(\s*HttpRequestRetry\s*\)""").containsMatchIn(code)) {
                hasAdvancedHandling = true
                patterns["retry"] = true
            }
        }
        
        // Rate limiting patterns
        if (Regex("""\b(rateLimit|throttle|semaphore)\s*\(""", RegexOption.IGNORE_CASE).containsMatchIn(code)) {
            hasAdvancedHandling = true
            patterns["rate_limiting"] = true
        }
    }
}

// ============================================================================
//  Main Execution
// ============================================================================

fun main(args: Array<String>) {
    try {
        if (args.isEmpty()) {
            val errorResult = ParseResult(
                hasBasicHandling = false,
                hasAdvancedHandling = false,
                patterns = emptyMap(),
                resilienceLibraries = emptyList()
            )
            println(Gson().toJson(errorResult))
            return
        }

        val filePath = args[0]
        val file = File(filePath)
        
        if (!file.exists()) {
            val errorResult = ParseResult(
                hasBasicHandling = false,
                hasAdvancedHandling = false,
                patterns = emptyMap(),
                resilienceLibraries = emptyList()
            )
            println(Gson().toJson(errorResult))
            return
        }

        val kotlinCode = file.readText()
        val analyzer = KotlinCodeAnalyzer(kotlinCode)
        val result = analyzer.analyze()
        
        // Output JSON
        println(Gson().toJson(result))
        
    } catch (e: Exception) {
        System.err.println("Error processing Kotlin file: ${e.message}")
        e.printStackTrace()
        
        val errorResult = ParseResult(
            hasBasicHandling = false,
            hasAdvancedHandling = false,
            patterns = emptyMap(),
            resilienceLibraries = emptyList()
        )
        println(Gson().toJson(errorResult))
    }
}