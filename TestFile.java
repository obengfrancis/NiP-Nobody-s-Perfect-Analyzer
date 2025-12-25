import io.github.resilience4j.retry.annotation.Retry;

public class TestFile {
    
    @Retry(name = "backend")
    public String callExternalService() {
        try {
            return performHttpCall();
        } catch (Exception e) {
            throw new RuntimeException("Failed to call service", e);
        }
    }
    
    private String performHttpCall() throws Exception {
        // Simulated HTTP call
        return "result";
    }
}