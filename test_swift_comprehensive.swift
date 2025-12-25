// Comprehensive Swift Resilience Patterns Test File

// ENHANCEMENT 1: Import detection
import Alamofire
import PromiseKit
import Combine
import Foundation

// ENHANCEMENT 2: URLSession with timeout configuration
class URLSessionExample {
    func fetchWithTimeout(url: URL) async throws -> Data {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        
        let session = URLSession(configuration: config)
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        return data
    }
}

// ENHANCEMENT 3: Alamofire with timeout and retry
class AlamofireExample {
    func fetchUser(id: String) {
        AF.request("https://api.example.com/users/\(id)")
            .validate(statusCode: 200..<300)
            .retry(3)
            .responseDecodable(of: User.self) { response in
                switch response.result {
                case .success(let user):
                    print("User: \(user)")
                case .failure(let error):
                    print("Error: \(error)")
                }
            }
    }
    
    func fetchWithRetryPolicy() {
        let retryPolicy = RetryPolicy(retryLimit: 3)
        
        AF.request("https://api.example.com/data")
            .validate()
            .retry(retryPolicy)
            .response { response in
                // Handle response
            }
    }
}

// ENHANCEMENT 4: Result type pattern
class ResultTypeExample {
    func fetchUser(id: String) -> Result<User, Error> {
        do {
            let data = try Data(contentsOf: URL(string: "https://api.example.com")!)
            let user = try JSONDecoder().decode(User.self, from: data)
            return .success(user)
        } catch {
            return .failure(error)
        }
    }
    
    func fetchData() -> Result<Data, NetworkError> {
        // Implementation
        return .success(Data())
    }
}

// ENHANCEMENT 5: Async/await with do-catch
class AsyncAwaitExample {
    func fetchUser(id: String) async throws -> User {
        let url = URL(string: "https://api.example.com/users/\(id)")!
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        return try JSONDecoder().decode(User.self, from: data)
    }
    
    func fetchMultiple() async throws {
        do {
            let user = try await fetchUser(id: "123")
            print("User: \(user)")
        } catch {
            print("Error: \(error)")
        }
    }
}

// ENHANCEMENT 6: PromiseKit with retry and timeout
class PromiseKitExample {
    func fetchWithRetry(url: String) -> Promise<Data> {
        return firstly {
            URLSession.shared.dataTask(.promise, with: URL(string: url)!)
        }.map { data, response in
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                throw APIError.invalidResponse
            }
            return data
        }.retry(3)
        .timeout(seconds: 30)
        .recover { error -> Promise<Data> in
            // Fallback to cache
            return self.fetchFromCache(url: url)
        }
    }
}

// ENHANCEMENT 7: Combine with timeout and retry
class CombineExample {
    var cancellables = Set<AnyCancellable>()
    
    func fetchWithTimeout(url: URL) {
        URLSession.shared.dataTaskPublisher(for: url)
            .timeout(.seconds(30), scheduler: DispatchQueue.main)
            .retry(3)
            .sink(receiveCompletion: { completion in
                switch completion {
                case .finished:
                    print("Success")
                case .failure(let error):
                    print("Error: \(error)")
                }
            }, receiveValue: { data, response in
                print("Received data: \(data.count) bytes")
            })
            .store(in: &cancellables)
    }
}

// ENHANCEMENT 8: Manual retry with exponential backoff
class ManualRetryExample {
    func fetchWithRetry<T>(
        maxRetries: Int = 3,
        operation: () async throws -> T
    ) async throws -> T {
        var lastError: Error?
        var delay: TimeInterval = 1.0
        
        for attempt in 0..<maxRetries {
            do {
                return try await operation()
            } catch {
                lastError = error
                
                if attempt < maxRetries - 1 {
                    try await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                    delay *= 2  // Exponential backoff
                }
            }
        }
        
        throw lastError ?? APIError.unknownError
    }
}

// ENHANCEMENT 9: Custom retry extension
extension URLSession {
    func dataWithRetry(
        from url: URL,
        retries: Int = 3
    ) async throws -> (Data, URLResponse) {
        var lastError: Error?
        
        for attempt in 0..<retries {
            do {
                return try await self.data(from: url)
            } catch {
                lastError = error
                if attempt < retries - 1 {
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                }
            }
        }
        
        throw lastError ?? APIError.unknownError
    }
}

// ENHANCEMENT 10: Circuit breaker implementation
class CircuitBreaker {
    enum State {
        case closed
        case open
        case halfOpen
    }
    
    private var state: State = .closed
    private var failureCount = 0
    private let threshold = 5
    private var lastFailureTime: Date?
    private let timeout: TimeInterval = 60
    
    func execute<T>(_ operation: () async throws -> T) async throws -> T {
        switch state {
        case .open:
            if let lastFailure = lastFailureTime,
               Date().timeIntervalSince(lastFailure) > timeout {
                state = .halfOpen
            } else {
                throw CircuitBreakerError.circuitOpen
            }
        default:
            break
        }
        
        do {
            let result = try await operation()
            onSuccess()
            return result
        } catch {
            onFailure()
            throw error
        }
    }
    
    private func onSuccess() {
        failureCount = 0
        state = .closed
    }
    
    private func onFailure() {
        failureCount += 1
        lastFailureTime = Date()
        
        if failureCount >= threshold {
            state = .open
        }
    }
}

// ENHANCEMENT 11: Guard statements with status checks
class StatusCheckExample {
    func validateResponse(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }
        
        guard httpResponse.statusCode >= 200 && httpResponse.statusCode < 300 else {
            throw APIError.httpError(statusCode: httpResponse.statusCode)
        }
    }
    
    func fetchData(from url: URL) async throws -> Data {
        let (data, response) = try await URLSession.shared.data(from: url)
        try validateResponse(response)
        return data
    }
}

// Data models
struct User: Codable {
    let id: String
    let name: String
}

enum APIError: Error {
    case invalidResponse
    case httpError(statusCode: Int)
    case unknownError
}

enum NetworkError: Error {
    case timeout
    case noConnection
}

enum CircuitBreakerError: Error {
    case circuitOpen
}