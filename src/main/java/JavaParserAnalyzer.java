import java.io.File;
import java.io.FileNotFoundException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import org.json.JSONObject;

import com.github.javaparser.StaticJavaParser;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.ImportDeclaration;
import com.github.javaparser.ast.body.ClassOrInterfaceDeclaration;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.expr.AnnotationExpr;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.ast.expr.ObjectCreationExpr;
import com.github.javaparser.ast.stmt.CatchClause;
import com.github.javaparser.ast.stmt.ThrowStmt;
import com.github.javaparser.ast.stmt.TryStmt;
import com.github.javaparser.ast.visitor.VoidVisitorAdapter;
import com.github.javaparser.ParserConfiguration;

/**
 * Enhanced JavaParser Analyzer for Exception Handling Detection
 * 
 * Detects:
 * - Basic exception handling: try-catch, throw, throws, finally
 * - Advanced patterns: retry, timeout, circuit breaker, backoff
 * - Java resilience libraries: Resilience4j, Hystrix, Spring Retry, Failsafe
 * - Annotation-based patterns: @Retry, @HystrixCommand, @CircuitBreaker, etc.
 * - Class-based patterns: RetryConfig, CircuitBreakerRegistry, etc.
 * 
 * @version 2.0 - Enhanced for comprehensive resilience pattern detection
 */
public class JavaParserAnalyzer {
    private static boolean hasBasicHandling = false;
    private static boolean hasAdvancedHandling = false;
    
    // Track individual patterns for detailed analysis
    private static Map<String, Boolean> patterns = new HashMap<>();
    
    // Track detected resilience libraries
    private static Set<String> resilienceLibraries = new HashSet<>();

    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Please provide a file path");
            System.exit(1);
        }

        // Initialize pattern tracking
        initializePatterns();

        // Configure parser for maximum compatibility
        ParserConfiguration config = new ParserConfiguration();
        config.setLanguageLevel(ParserConfiguration.LanguageLevel.RAW);
        StaticJavaParser.setConfiguration(config);

        String filePath = args[0];
        try {
            CompilationUnit cu = StaticJavaParser.parse(new File(filePath));
            cu.accept(new ErrorHandlingVisitor(), null);

            // Output enhanced JSON result
            JSONObject result = new JSONObject();
            result.put("hasBasicHandling", hasBasicHandling);
            result.put("hasAdvancedHandling", hasAdvancedHandling);
            
            // Add detailed pattern information
            JSONObject patternsJson = new JSONObject();
            for (Map.Entry<String, Boolean> entry : patterns.entrySet()) {
                patternsJson.put(entry.getKey(), entry.getValue());
            }
            result.put("patterns", patternsJson);
            
            // Add detected libraries
            if (!resilienceLibraries.isEmpty()) {
                result.put("resilience_libraries", resilienceLibraries);
            }
            
            System.out.println(result.toString());
            
        } catch (FileNotFoundException e) {
            System.err.println("File not found: " + filePath);
            System.exit(1);
        } catch (Exception e) {
            // Output safe JSON even on parse errors
            JSONObject errorResult = new JSONObject();
            errorResult.put("hasBasicHandling", hasBasicHandling);
            errorResult.put("hasAdvancedHandling", hasAdvancedHandling);
            errorResult.put("parse_error", e.getMessage());
            System.out.println(errorResult.toString());
            System.exit(0);  // Exit 0 so Python can parse the partial result
        }
    }

    private static void initializePatterns() {
        patterns.put("try_catch", false);
        patterns.put("timeout", false);
        patterns.put("retry", false);
        patterns.put("circuit_breaker", false);
        patterns.put("exponential_backoff", false);
        patterns.put("status_check", false);
    }

    /**
     * Enhanced Visitor that detects both basic and advanced exception handling patterns
     */
    private static class ErrorHandlingVisitor extends VoidVisitorAdapter<Void> {
        
        /**
         *  Detect resilience library imports
         * Catches: Resilience4j, Hystrix, Spring Retry, Failsafe
         */
        @Override
        public void visit(ImportDeclaration n, Void arg) {
            super.visit(n, arg);
            String importName = n.getNameAsString();
            
            // Resilience4j patterns
            if (importName.startsWith("io.github.resilience4j")) {
                resilienceLibraries.add("Resilience4j");
                hasAdvancedHandling = true;
                
                if (importName.contains("retry")) {
                    patterns.put("retry", true);
                } else if (importName.contains("circuitbreaker")) {
                    patterns.put("circuit_breaker", true);
                } else if (importName.contains("timelimiter")) {
                    patterns.put("timeout", true);
                } else if (importName.contains("bulkhead")) {
                    hasAdvancedHandling = true;
                } else if (importName.contains("ratelimiter")) {
                    hasAdvancedHandling = true;
                }
            }
            
            // Hystrix patterns
            else if (importName.startsWith("com.netflix.hystrix")) {
                resilienceLibraries.add("Hystrix");
                hasAdvancedHandling = true;
                patterns.put("circuit_breaker", true);
            }
            
            // Spring Retry patterns
            else if (importName.startsWith("org.springframework.retry")) {
                resilienceLibraries.add("Spring Retry");
                hasAdvancedHandling = true;
                patterns.put("retry", true);
                
                if (importName.contains("backoff") || importName.contains("BackOff")) {
                    patterns.put("exponential_backoff", true);
                }
            }
            
            // Failsafe patterns
            else if (importName.startsWith("dev.failsafe") || importName.startsWith("net.jodah.failsafe")) {
                resilienceLibraries.add("Failsafe");
                hasAdvancedHandling = true;
                patterns.put("retry", true);
                patterns.put("circuit_breaker", true);
            }
            
            // Guava Retry patterns
            else if (importName.contains("guava.retrying") || importName.contains("github.rholder.retry")) {
                resilienceLibraries.add("Guava Retry");
                hasAdvancedHandling = true;
                patterns.put("retry", true);
            }
        }
        
        /**
         * Detect annotation-based patterns
         * Catches: @Retry, @HystrixCommand, @CircuitBreaker, @TimeLimiter, etc.
         */
        @Override
        public void visit(MethodDeclaration n, Void arg) {
            // Check for throws declarations (basic handling)
            if (!n.getThrownExceptions().isEmpty()) {
                hasBasicHandling = true;
            }
            
            // Check for resilience annotations (advanced handling)
            for (AnnotationExpr annotation : n.getAnnotations()) {
                String annotationName = annotation.getNameAsString();
                
                // Spring Retry annotations
                if (annotationName.equals("Retryable") || annotationName.equals("Retry")) {
                    hasAdvancedHandling = true;
                    patterns.put("retry", true);
                }
                else if (annotationName.equals("Backoff")) {
                    hasAdvancedHandling = true;
                    patterns.put("exponential_backoff", true);
                }
                else if (annotationName.equals("Recover")) {
                    hasAdvancedHandling = true;
                }
                
                // Hystrix annotations
                else if (annotationName.equals("HystrixCommand")) {
                    hasAdvancedHandling = true;
                    patterns.put("circuit_breaker", true);
                }
                else if (annotationName.equals("HystrixCollapser")) {
                    hasAdvancedHandling = true;
                }
                
                // Resilience4j annotations
                else if (annotationName.equals("CircuitBreaker")) {
                    hasAdvancedHandling = true;
                    patterns.put("circuit_breaker", true);
                }
                else if (annotationName.equals("RateLimiter")) {
                    hasAdvancedHandling = true;
                }
                else if (annotationName.equals("Bulkhead")) {
                    hasAdvancedHandling = true;
                }
                else if (annotationName.equals("TimeLimiter")) {
                    hasAdvancedHandling = true;
                    patterns.put("timeout", true);
                }
            }
            
            super.visit(n, arg);
        }
        
        /**
         *  Detect class-based patterns
         * Catches: RetryConfig, CircuitBreakerRegistry, HystrixCommand, etc.
         */
        @Override
        public void visit(ObjectCreationExpr n, Void arg) {
            super.visit(n, arg);
            String className = n.getType().getNameAsString();
            
            // Resilience4j Config/Registry patterns
            if (className.equals("RetryConfig") || className.contains("RetryRegistry")) {
                hasAdvancedHandling = true;
                patterns.put("retry", true);
            }
            else if (className.equals("CircuitBreakerConfig") || className.contains("CircuitBreakerRegistry")) {
                hasAdvancedHandling = true;
                patterns.put("circuit_breaker", true);
            }
            else if (className.equals("TimeLimiterConfig") || className.contains("TimeLimiterRegistry")) {
                hasAdvancedHandling = true;
                patterns.put("timeout", true);
            }
            else if (className.contains("BulkheadConfig") || className.contains("BulkheadRegistry")) {
                hasAdvancedHandling = true;
            }
            else if (className.contains("RateLimiterConfig") || className.contains("RateLimiterRegistry")) {
                hasAdvancedHandling = true;
            }
            
            // Hystrix patterns
            else if (className.contains("HystrixCommand")) {
                hasAdvancedHandling = true;
                patterns.put("circuit_breaker", true);
            }
            else if (className.contains("HystrixObservableCommand")) {
                hasAdvancedHandling = true;
                patterns.put("circuit_breaker", true);
            }
            
            // Spring Retry patterns
            else if (className.equals("RetryTemplate")) {
                hasAdvancedHandling = true;
                patterns.put("retry", true);
            }
            else if (className.contains("BackOffPolicy") || className.contains("ExponentialBackOff")) {
                hasAdvancedHandling = true;
                patterns.put("exponential_backoff", true);
            }
            else if (className.contains("FixedBackOff") || className.contains("UniformRandomBackOff")) {
                hasAdvancedHandling = true;
                patterns.put("exponential_backoff", true);
            }
            
            // Failsafe patterns
            else if (className.equals("RetryPolicy") || className.equals("CircuitBreaker") || 
                     className.equals("Timeout") || className.equals("Fallback")) {
                hasAdvancedHandling = true;
            }
        }
        
        /**
         * Detect classes extending resilience patterns
         */
        @Override
        public void visit(ClassOrInterfaceDeclaration n, Void arg) {
            super.visit(n, arg);
            
            // Check if class extends HystrixCommand
            n.getExtendedTypes().forEach(type -> {
                String typeName = type.getNameAsString();
                if (typeName.contains("HystrixCommand") || typeName.contains("HystrixObservableCommand")) {
                    hasAdvancedHandling = true;
                    patterns.put("circuit_breaker", true);
                }
            });
            
            // Check class-level annotations
            for (AnnotationExpr annotation : n.getAnnotations()) {
                String annotationName = annotation.getNameAsString();
                if (annotationName.equals("CircuitBreaker") || 
                    annotationName.equals("Retry") ||
                    annotationName.equals("RateLimiter") ||
                    annotationName.equals("Bulkhead")) {
                    hasAdvancedHandling = true;
                }
            }
        }
        
        /**
         * Enhanced method call detection
         * Detects: .retry(), Retry.of(), .withTimeout(), etc.
         */
        @Override
        public void visit(MethodCallExpr n, Void arg) {
            String methodName = n.getNameAsString().toLowerCase();
            
            // Retry patterns
            if (methodName.contains("retry") || methodName.equals("retryif") || 
                methodName.equals("retrywhen") || methodName.equals("withretry")) {
                hasAdvancedHandling = true;
                patterns.put("retry", true);
            }
            
            // Timeout patterns
            else if (methodName.contains("timeout") || methodName.contains("timelimit") ||
                     methodName.equals("withtimeout") || methodName.equals("settimeout")) {
                hasAdvancedHandling = true;
                patterns.put("timeout", true);
            }
            
            // Circuit breaker patterns
            else if (methodName.contains("circuitbreaker") || methodName.contains("breaker") ||
                     methodName.equals("withcircuitbreaker")) {
                hasAdvancedHandling = true;
                patterns.put("circuit_breaker", true);
            }
            
            // Backoff patterns
            else if (methodName.contains("backoff") || methodName.contains("exponential") ||
                     methodName.equals("withbackoff") || methodName.contains("waitstrategy")) {
                hasAdvancedHandling = true;
                patterns.put("exponential_backoff", true);
            }
            
            // Bulkhead patterns
            else if (methodName.contains("bulkhead")) {
                hasAdvancedHandling = true;
            }
            
            // Rate limiter patterns
            else if (methodName.contains("ratelimit") || methodName.contains("throttle")) {
                hasAdvancedHandling = true;
            }
            
            // Fallback patterns
            else if (methodName.contains("fallback") || methodName.equals("withfallback")) {
                hasAdvancedHandling = true;
            }
            
            // Status code checks (basic handling)
            else if (methodName.equals("statuscode") || methodName.equals("getstatuscode")) {
                hasBasicHandling = true;
                patterns.put("status_check", true);
            }
            
            super.visit(n, arg);
        }
        
        /**
         * Basic exception handling: Try-catch blocks
         */
        @Override
        public void visit(TryStmt n, Void arg) {
            hasBasicHandling = true;
            patterns.put("try_catch", true);
            
            if (n.getFinallyBlock().isPresent()) {
                hasBasicHandling = true;
            }
            super.visit(n, arg);
        }
        
        /**
         * Basic exception handling: Catch clauses
         */
        @Override
        public void visit(CatchClause n, Void arg) {
            hasBasicHandling = true;
            patterns.put("try_catch", true);
            
            // Check for status code checks in catch blocks
            String catchBody = n.getBody().toString().toLowerCase();
            if (catchBody.contains("statuscode") || catchBody.contains("status_code") ||
                catchBody.contains("getstatuscode")) {
                patterns.put("status_check", true);
            }
            
            super.visit(n, arg);
        }
        
        /**
         * Basic exception handling: Throw statements
         */
        @Override
        public void visit(ThrowStmt n, Void arg) {
            hasBasicHandling = true;
            super.visit(n, arg);
        }
    }
}