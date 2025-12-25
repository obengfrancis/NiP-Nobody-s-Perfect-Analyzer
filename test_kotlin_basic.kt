// Basic Error Handling Only - No Advanced Patterns

import okhttp3.OkHttpClient
import okhttp3.Request

class BasicAPIClient {
    private val client = OkHttpClient()
    
    fun fetchUser(userId: String): User? {
        return try {
            val request = Request.Builder()
                .url("https://api.example.com/users/$userId")
                .build()
            
            client.newCall(request).execute().use { response ->
                if (response.code == 200) {
                    // Parse response
                    User(userId, "Name")
                } else {
                    println("HTTP error: ${response.code}")
                    null
                }
            }
        } catch (e: Exception) {
            println("Request failed: ${e.message}")
            null
        }
    }
    
    fun updateUser(userId: String, data: Map<String, String>): Boolean {
        try {
            val request = Request.Builder()
                .url("https://api.example.com/users/$userId")
                .put(/* body */)
                .build()
            
            val response = client.newCall(request).execute()
            
            return response.isSuccessful
        } catch (e: Exception) {
            println("Update failed: ${e.message}")
            return false
        }
    }
}

data class User(val id: String, val name: String)