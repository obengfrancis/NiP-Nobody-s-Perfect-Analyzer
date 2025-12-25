public class TestBasicOnly {
    
    public String processData() {
        try {
            return doWork();
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            throw e;
        } finally {
            cleanup();
        }
    }
    
    public String doWork() throws Exception {
        return "result";
    }
    
    public void cleanup() {
        // cleanup code
    }
}