// Comprehensive Kotlin Resilience Patterns Test File

// ENHANCEMENT 1: Import detection
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import io.github.resilience4j.kotlin.retry.retry
import io.github.resilience4j.kotlin.circuitbreaker.circuitBreaker
import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.features.*
import io.ktor.client.request.*
import kotlinx.coroutines.*
import java.util.concurrent.TimeUnit

// ENHANCEMENT 2: OkHttp with timeout configuration
class OkHttpClientExample {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()
    
    fun fetchData(url: String): String? {
        try {
            val request = Request.Builder()
                .url(url)
                .build()
            
            client.newCall(request).execute().use { response ->
                if (response.code == 200) {
                    return response.body?.string()
                } else {
                    throw Exception("HTTP ${response.code}")
                }
            }
        } catch (e: Exception) {
            println("Request failed: ${e.message}")
            return null
        }
    }
}

// ENHANCEMENT 3: Retrofit with timeout
class RetrofitClientExample {
    private val okHttpClient = OkHttpClient.Builder()
        .callTimeout(60, TimeUnit.SECONDS)
        .build()
    
    private val retrofit = Retrofit.Builder()
        .baseUrl("https://api.example.com")
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
    
    suspend fun fetchUser(userId: String): User? {
        return try {
            val response = api.getUser(userId).execute()
            
            if (response.isSuccessful && response.code() == 200) {
                response.body()
            } else {
                null
            }
        } catch (e: Exception) {
            println("Error: ${e.message}")
            null
        }
    }
}

// ENHANCEMENT 4: Resilience4j Retry Pattern
class Resilience4jRetryExample {
    suspend fun fetchWithRetry(url: String): String? {
        return retry {
            fetchData(url)
        }
    }
    
    suspend fun fetchWithRetryConfig(url: String): String? {
        return retry(
            maxAttempts = 3,
            waitDuration = 1000L
        ) {
            fetchData(url)
        }
    }
    
    private suspend fun fetchData(url: String): String {
        // Fetch logic
        return "data"
    }
}

// ENHANCEMENT 5: Resilience4j Circuit Breaker
class Resilience4jCircuitBreakerExample {
    suspend fun fetchWithCircuitBreaker(url: String): String? {
        return circuitBreaker {
            fetchData(url)
        }
    }
    
    private suspend fun fetchData(url: String): String {
        // Fetch logic
        return "data"
    }
}

// ENHANCEMENT 6: Coroutine withTimeout
class CoroutineTimeoutExample {
    suspend fun fetchWithTimeout(url: String): String? {
        return try {
            withTimeout(5000) {
                fetchData(url)
            }
        } catch (e: TimeoutCancellationException) {
            println("Request timed out")
            null
        }
    }
    
    suspend fun fetchWithTimeoutOrNull(url: String): String? {
        return withTimeoutOrNull(5000) {
            fetchData(url)
        }
    }
    
    private suspend fun fetchData(url: String): String {
        delay(1000)
        return "data"
    }
}

// ENHANCEMENT 7: Ktor Client with timeout and retry
class KtorClientExample {
    private val client = HttpClient(CIO) {
        install(HttpTimeout) {
            requestTimeoutMillis = 5000
            connectTimeoutMillis = 3000
            socketTimeoutMillis = 5000
        }
        
        install(HttpRequestRetry) {
            maxRetries = 3
            retryOnExceptionIf { _, cause ->
                cause is java.net.SocketTimeoutException
            }
            exponentialDelay()
        }
    }
    
    suspend fun fetchUser(userId: String): User? {
        return try {
            val response: String = client.get("https://api.example.com/users/$userId")
            // Parse response
            null
        } catch (e: Exception) {
            println("Error: ${e.message}")
            null
        }
    }
}

// ENHANCEMENT 8: Manual retry with exponential backoff
class ManualRetryExample {
    suspend fun fetchWithManualRetry(url: String, maxRetries: Int = 3): String? {
        var lastException: Exception? = null
        var backoff = 1000L
        
        repeat(maxRetries) { attempt ->
            try {
                val result = fetchData(url)
                
                if (result.statusCode == 200) {
                    return result.body
                } else if (result.statusCode >= 500) {
                    // Retry on server errors
                    throw Exception("Server error: ${result.statusCode}")
                } else {
                    // Don't retry client errors
                    return null
                }
            } catch (e: Exception) {
                lastException = e
                
                if (attempt < maxRetries - 1) {
                    delay(backoff)
                    backoff *= 2  // Exponential backoff
                }
            }
        }
        
        println("All retry attempts failed: ${lastException?.message}")
        return null
    }
    
    private suspend fun fetchData(url: String): Response {
        // Fetch implementation
        return Response(200, "data")
    }
    
    data class Response(val statusCode: Int, val body: String)
}

// ENHANCEMENT 9: Custom extension function with retry
suspend fun <T> withRetry(
    times: Int = 3,
    initialDelay: Long = 1000,
    maxDelay: Long = 10000,
    factor: Double = 2.0,
    block: suspend () -> T
): T {
    var currentDelay = initialDelay
    repeat(times - 1) { attempt ->
        try {
            return block()
        } catch (e: Exception) {
            println("Attempt ${attempt + 1} failed: ${e.message}")
            delay(currentDelay)
            currentDelay = (currentDelay * factor).toLong().coerceAtMost(maxDelay)
        }
    }
    return block() // Last attempt
}

// ENHANCEMENT 10: Circuit breaker implementation
class CustomCircuitBreaker(
    private val threshold: Int = 5,
    private val timeout: Long = 60000
) {
    private var failureCount = 0
    private var lastFailureTime = 0L
    private var state = State.CLOSED
    
    enum class State {
        CLOSED, OPEN, HALF_OPEN
    }
    
    suspend fun <T> execute(block: suspend () -> T): T {
        when (state) {
            State.OPEN -> {
                if (System.currentTimeMillis() - lastFailureTime > timeout) {
                    state = State.HALF_OPEN
                } else {
                    throw Exception("Circuit breaker is OPEN")
                }
            }
            else -> {}
        }
        
        return try {
            val result = block()
            onSuccess()
            result
        } catch (e: Exception) {
            onFailure()
            throw e
        }
    }
    
    private fun onSuccess() {
        failureCount = 0
        state = State.CLOSED
    }
    
    private fun onFailure() {
        failureCount++
        lastFailureTime = System.currentTimeMillis()
        
        if (failureCount >= threshold) {
            state = State.OPEN
        }
    }
}

// ENHANCEMENT 11: Rate limiting with semaphore
class RateLimiter(maxConcurrent: Int) {
    private val semaphore = kotlinx.coroutines.sync.Semaphore(maxConcurrent)
    
    suspend fun <T> execute(block: suspend () -> T): T {
        semaphore.acquire()
        return try {
            block()
        } finally {
            semaphore.release()
        }
    }
}

// ENHANCEMENT 12: Supervisor scope for error isolation
class SupervisorExample {
    suspend fun fetchMultipleUsers(userIds: List<String>): List<User?> {
        return supervisorScope {
            userIds.map { userId ->
                async {
                    try {
                        withTimeout(5000) {
                            fetchUser(userId)
                        }
                    } catch (e: Exception) {
                        println("Failed to fetch user $userId: ${e.message}")
                        null
                    }
                }
            }.awaitAll()
        }
    }
    
    private suspend fun fetchUser(userId: String): User {
        // Fetch implementation
        return User(userId, "Name")
    }
}

// Data classes
data class User(val id: String, val name: String)