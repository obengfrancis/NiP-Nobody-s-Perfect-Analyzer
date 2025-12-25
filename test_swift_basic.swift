// Basic Error Handling Only - No Advanced Patterns

import Foundation

class BasicAPIClient {
    func fetchUser(id: String) -> Result<User, Error> {
        do {
            let url = URL(string: "https://api.example.com/users/\(id)")!
            let data = try Data(contentsOf: url)
            let user = try JSONDecoder().decode(User.self, from: data)
            return .success(user)
        } catch {
            return .failure(error)
        }
    }
    
    func fetchData(from url: URL) async throws -> Data {
        let (data, response) = try await URLSession.shared.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }
        
        return data
    }
}

struct User: Codable {
    let id: String
    let name: String
}

enum APIError: Error {
    case invalidResponse
}