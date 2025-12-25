using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

class Program
{
    static void Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.WriteLine("Please provide a C# file to parse.");
            return;
        }

        try
        {
            string code = File.ReadAllText(args[0]);
            var analyzer = new ExceptionHandlingAnalyzer();
            var result = analyzer.Analyze(code);

            // Output JSON for detailed analysis
            var json = JsonSerializer.Serialize(result, new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
                WriteIndented = false
            });
            Console.WriteLine(json);
        }
        catch (Exception ex)
        {
            // Fallback output on error
            var errorResult = new AnalysisResult
            {
                HasBasicHandling = false,
                HasAdvancedHandling = false,
                ParseError = ex.Message
            };
            var json = JsonSerializer.Serialize(errorResult, new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.CamelCase
            });
            Console.WriteLine(json);
        }
    }
}

class AnalysisResult
{
    public bool HasBasicHandling { get; set; }
    public bool HasAdvancedHandling { get; set; }
    public Dictionary<string, bool> Patterns { get; set; } = new();
    public List<string> ResilienceLibraries { get; set; } = new();
    public string ParseError { get; set; }
}

class ExceptionHandlingAnalyzer
{
    private bool hasBasicHandling = false;
    private bool hasAdvancedHandling = false;
    private Dictionary<string, bool> patterns = new()
    {
        ["try_catch"] = false,
        ["timeout"] = false,
        ["retry"] = false,
        ["circuit_breaker"] = false,
        ["exponential_backoff"] = false,
        ["status_check"] = false
    };
    private HashSet<string> resilienceLibraries = new();

    public AnalysisResult Analyze(string code)
    {
        SyntaxTree tree = CSharpSyntaxTree.ParseText(code);
        var root = tree.GetRoot() as CompilationUnitSyntax;

        // ENHANCEMENT 1: Analyze using directives (imports)
        AnalyzeUsings(root);

        // ENHANCEMENT 2: Analyze all nodes
        foreach (var node in root.DescendantNodes())
        {
            AnalyzeNode(node);
        }

        return new AnalysisResult
        {
            HasBasicHandling = hasBasicHandling,
            HasAdvancedHandling = hasAdvancedHandling,
            Patterns = patterns,
            ResilienceLibraries = resilienceLibraries.ToList()
        };
    }

    // ENHANCEMENT 1: Detect resilience library imports
    private void AnalyzeUsings(CompilationUnitSyntax root)
    {
        foreach (var usingDirective in root.Usings)
        {
            var name = usingDirective.Name.ToString();

            // Polly library (most popular C# resilience library)
            if (name.StartsWith("Polly"))
            {
                resilienceLibraries.Add("Polly");
                hasAdvancedHandling = true;

                if (name.Contains("Retry"))
                    patterns["retry"] = true;
                if (name.Contains("CircuitBreaker"))
                    patterns["circuit_breaker"] = true;
                if (name.Contains("Timeout"))
                    patterns["timeout"] = true;
                if (name.Contains("Fallback"))
                    hasAdvancedHandling = true;
            }

            // Microsoft.Extensions.Http.Resilience (modern approach)
            if (name.Contains("Microsoft.Extensions.Http.Resilience") ||
                name.Contains("Microsoft.Extensions.Http.Polly"))
            {
                resilienceLibraries.Add("Microsoft.Extensions.Http.Resilience");
                hasAdvancedHandling = true;
                patterns["retry"] = true;
                patterns["circuit_breaker"] = true;
            }

            // Other resilience libraries
            if (name.Contains("Steeltoe.CircuitBreaker"))
            {
                resilienceLibraries.Add("Steeltoe.CircuitBreaker");
                hasAdvancedHandling = true;
                patterns["circuit_breaker"] = true;
            }
        }
    }

    private void AnalyzeNode(SyntaxNode node)
    {
        switch (node)
        {
            case TryStatementSyntax _:
                AnalyzeTryStatement();
                break;
            case InvocationExpressionSyntax invocation:
                AnalyzeInvocation(invocation);
                break;
            case ObjectCreationExpressionSyntax creation:
                AnalyzeObjectCreation(creation);
                break;
            case ClassDeclarationSyntax classDecl:
                AnalyzeClassDeclaration(classDecl);
                break;
            case MethodDeclarationSyntax methodDecl:
                AnalyzeMethodDeclaration(methodDecl);
                break;
        }
    }

    // BASIC: Try-catch detection
    private void AnalyzeTryStatement()
    {
        hasBasicHandling = true;
        patterns["try_catch"] = true;
    }

    // ENHANCEMENT 2: Comprehensive invocation analysis
    private void AnalyzeInvocation(InvocationExpressionSyntax invocation)
    {
        var expression = invocation.Expression.ToString().ToLower();

        // Status code checks (basic)
        if (expression.Contains("statuscode"))
        {
            hasBasicHandling = true;
            patterns["status_check"] = true;
        }

        // Timeout patterns (advanced) - case-insensitive
        if (expression.Contains("timeout") || expression.Contains("withtimeout"))
        {
            hasAdvancedHandling = true;
            patterns["timeout"] = true;
        }

        // Retry patterns (advanced)
        if (expression.Contains("retry") || expression.Contains("retryasync") ||
            expression.Contains("waitandretry"))
        {
            hasAdvancedHandling = true;
            patterns["retry"] = true;
        }

        // Circuit breaker patterns (advanced)
        if (expression.Contains("circuitbreaker") || expression.Contains("breaker"))
        {
            hasAdvancedHandling = true;
            patterns["circuit_breaker"] = true;
        }

        // Backoff patterns (advanced)
        if (expression.Contains("backoff") || expression.Contains("exponentialbackoff"))
        {
            hasAdvancedHandling = true;
            patterns["exponential_backoff"] = true;
        }

        // Polly-specific patterns
        if (expression.Contains("executeasync") || expression.Contains("executeandcapture"))
        {
            hasAdvancedHandling = true;
        }

        // Fallback patterns
        if (expression.Contains("fallback"))
        {
            hasAdvancedHandling = true;
        }
    }

    // ENHANCEMENT 3: Detect object creation patterns
    private void AnalyzeObjectCreation(ObjectCreationExpressionSyntax creation)
    {
        var typeName = creation.Type.ToString();

        // Polly policy creation
        if (typeName.Contains("Policy") || typeName.Contains("RetryPolicy") ||
            typeName.Contains("CircuitBreakerPolicy"))
        {
            hasAdvancedHandling = true;
        }

        // Circuit breaker instances
        if (typeName.Contains("CircuitBreaker"))
        {
            hasAdvancedHandling = true;
            patterns["circuit_breaker"] = true;
        }

        // Retry configuration
        if (typeName.Contains("Retry"))
        {
            hasAdvancedHandling = true;
            patterns["retry"] = true;
        }

        // Timeout configuration
        if (typeName.Contains("Timeout"))
        {
            hasAdvancedHandling = true;
            patterns["timeout"] = true;
        }

        // CancellationTokenSource (often used for timeouts)
        if (typeName.Contains("CancellationTokenSource"))
        {
            hasAdvancedHandling = true;
            patterns["timeout"] = true;
        }

        // Resilience pipeline builder (modern Polly v8+)
        if (typeName.Contains("ResiliencePipeline"))
        {
            hasAdvancedHandling = true;
        }
    }

    // ENHANCEMENT 4: Detect custom class implementations
    private void AnalyzeClassDeclaration(ClassDeclarationSyntax classDecl)
    {
        var className = classDecl.Identifier.Text;

        // Custom circuit breaker implementations
        if (className.Contains("CircuitBreaker"))
        {
            hasAdvancedHandling = true;
            patterns["circuit_breaker"] = true;
        }

        // Custom retry implementations
        if (className.Contains("Retry") || className.Contains("RetryPolicy"))
        {
            hasAdvancedHandling = true;
            patterns["retry"] = true;
        }

        // Timeout implementations
        if (className.Contains("Timeout"))
        {
            hasAdvancedHandling = true;
            patterns["timeout"] = true;
        }
    }

    // ENHANCEMENT 5: Detect method names suggesting patterns
    private void AnalyzeMethodDeclaration(MethodDeclarationSyntax methodDecl)
    {
        var methodName = methodDecl.Identifier.Text.ToLower();

        // Methods with "retry" in name often implement retry logic
        if (methodName.Contains("retry") || methodName.Contains("retries"))
        {
            // Don't automatically mark as advanced - might just be a helper method
            // But look for actual retry logic in the method body
            var hasRetryLogic = methodDecl.DescendantNodes()
                .OfType<WhileStatementSyntax>()
                .Any() || methodDecl.DescendantNodes()
                .OfType<ForStatementSyntax>()
                .Any();

            if (hasRetryLogic)
            {
                hasAdvancedHandling = true;
                patterns["retry"] = true;
            }
        }

        // Methods with "timeout" in name
        if (methodName.Contains("timeout"))
        {
            // Check for CancellationToken parameter
            var hasCancellationToken = methodDecl.ParameterList.Parameters
                .Any(p => p.Type.ToString().Contains("CancellationToken"));

            if (hasCancellationToken)
            {
                hasAdvancedHandling = true;
                patterns["timeout"] = true;
            }
        }
    }
}