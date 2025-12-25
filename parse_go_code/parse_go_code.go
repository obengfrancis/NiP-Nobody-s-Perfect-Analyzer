package main

import (
    "encoding/json"
    "fmt"
    "go/ast"
    "go/parser"
    "go/token"
    "os"
    "strings"
)

// Result represents the analysis output
type Result struct {
    HasBasicHandling    bool              `json:"hasBasicHandling"`
    HasAdvancedHandling bool              `json:"hasAdvancedHandling"`
    Patterns            map[string]bool   `json:"patterns"`
    ResilienceLibraries []string          `json:"resilience_libraries,omitempty"`
    ParseError          string            `json:"parse_error,omitempty"`
}

// Analyzer holds the state during AST traversal
type Analyzer struct {
    hasBasicHandling    bool
    hasAdvancedHandling bool
    patterns            map[string]bool
    resilienceLibraries map[string]bool
    imports             map[string]string // alias -> import path
}

func newAnalyzer() *Analyzer {
    return &Analyzer{
        patterns: map[string]bool{
            "error_check":         false,
            "defer_recover":       false,
            "timeout":             false,
            "retry":               false,
            "circuit_breaker":     false,
            "exponential_backoff": false,
            "status_check":        false,
        },
        resilienceLibraries: make(map[string]bool),
        imports:             make(map[string]string),
    }
}

func main() {
    result := Result{
        HasBasicHandling:    false,
        HasAdvancedHandling: false,
        Patterns:            make(map[string]bool),
    }

    if len(os.Args) < 2 {
        outputJSON(result)
        return
    }

    filePath := os.Args[1]
    fset := token.NewFileSet()

    node, err := parser.ParseFile(fset, filePath, nil, parser.AllErrors)
    if err != nil {
        result.ParseError = err.Error()
        outputJSON(result)
        return
    }

    analyzer := newAnalyzer()
    analyzer.analyze(node)

    result.HasBasicHandling = analyzer.hasBasicHandling
    result.HasAdvancedHandling = analyzer.hasAdvancedHandling
    result.Patterns = analyzer.patterns

    // Convert resilience libraries map to slice
    for lib := range analyzer.resilienceLibraries {
        result.ResilienceLibraries = append(result.ResilienceLibraries, lib)
    }

    outputJSON(result)
}

func outputJSON(result Result) {
    jsonBytes, err := json.Marshal(result)
    if err != nil {
        // Fallback to simple format for backward compatibility
        fmt.Printf("%t,%t\n", result.HasBasicHandling, result.HasAdvancedHandling)
        return
    }
    fmt.Println(string(jsonBytes))
}

func (a *Analyzer) analyze(node *ast.File) {
    // First pass: collect imports
    a.analyzeImports(node)

    // Second pass: analyze code
    ast.Inspect(node, func(n ast.Node) bool {
        switch x := n.(type) {
        case *ast.IfStmt:
            a.analyzeIfStmt(x)
        case *ast.CallExpr:
            a.analyzeCallExpr(x)
        case *ast.DeferStmt:
            a.analyzeDeferStmt(x)
        case *ast.FuncLit:
            a.analyzeFuncLit(x)
        case *ast.CompositeLit:
            a.analyzeCompositeLit(x)
        }
        return true
    })
}

// ENHANCEMENT 1: Detect resilience library imports
func (a *Analyzer) analyzeImports(node *ast.File) {
    for _, imp := range node.Imports {
        importPath := strings.Trim(imp.Path.Value, `"`)
        
        // Store import with alias
        var alias string
        if imp.Name != nil {
            alias = imp.Name.Name
        } else {
            // Extract package name from path
            parts := strings.Split(importPath, "/")
            alias = parts[len(parts)-1]
        }
        a.imports[alias] = importPath

        // Detect resilience libraries
        switch {
        // Retry libraries
        case strings.Contains(importPath, "cenkalti/backoff"):
            a.resilienceLibraries["backoff"] = true
            a.hasAdvancedHandling = true
            a.patterns["exponential_backoff"] = true
        case strings.Contains(importPath, "avast/retry-go"):
            a.resilienceLibraries["retry-go"] = true
            a.hasAdvancedHandling = true
            a.patterns["retry"] = true
        case strings.Contains(importPath, "hashicorp/go-retryablehttp"):
            a.resilienceLibraries["go-retryablehttp"] = true
            a.hasAdvancedHandling = true
            a.patterns["retry"] = true

        // Circuit breaker libraries
        case strings.Contains(importPath, "sony/gobreaker"):
            a.resilienceLibraries["gobreaker"] = true
            a.hasAdvancedHandling = true
            a.patterns["circuit_breaker"] = true
        case strings.Contains(importPath, "rubyist/circuitbreaker"):
            a.resilienceLibraries["circuitbreaker"] = true
            a.hasAdvancedHandling = true
            a.patterns["circuit_breaker"] = true

        // Resilience libraries
        case strings.Contains(importPath, "eapache/go-resiliency"):
            a.resilienceLibraries["go-resiliency"] = true
            a.hasAdvancedHandling = true
            a.patterns["retry"] = true
            a.patterns["circuit_breaker"] = true
        }
    }
}

// ENHANCEMENT 2: Comprehensive error checking detection
func (a *Analyzer) analyzeIfStmt(x *ast.IfStmt) {
    // Pattern 1: if err != nil
    if cond, ok := x.Cond.(*ast.BinaryExpr); ok {
        if a.isErrorCheck(cond) {
            a.hasBasicHandling = true
            a.patterns["error_check"] = true
        }
    }

    // Pattern 2: if err := someFunc(); err != nil
    if x.Init != nil {
        if assign, ok := x.Init.(*ast.AssignStmt); ok {
            for _, lhs := range assign.Lhs {
                if ident, ok := lhs.(*ast.Ident); ok && ident.Name == "err" {
                    a.hasBasicHandling = true
                    a.patterns["error_check"] = true
                }
            }
        }
    }
}

func (a *Analyzer) isErrorCheck(expr *ast.BinaryExpr) bool {
    // Check if it's comparing err with nil
    if expr.Op == token.NEQ || expr.Op == token.EQL {
        // err != nil or err == nil
        if ident, ok := expr.X.(*ast.Ident); ok {
            if ident.Name == "err" {
                if yIdent, ok := expr.Y.(*ast.Ident); ok && yIdent.Name == "nil" {
                    return true
                }
            }
        }
        // nil != err or nil == err
        if ident, ok := expr.Y.(*ast.Ident); ok {
            if ident.Name == "err" {
                if xIdent, ok := expr.X.(*ast.Ident); ok && xIdent.Name == "nil" {
                    return true
                }
            }
        }
    }
    return false
}

// ENHANCEMENT 3: Detect defer/recover patterns
func (a *Analyzer) analyzeDeferStmt(x *ast.DeferStmt) {
    a.hasBasicHandling = true

    // Check if defer contains recover()
    ast.Inspect(x.Call, func(n ast.Node) bool {
        if call, ok := n.(*ast.CallExpr); ok {
            if ident, ok := call.Fun.(*ast.Ident); ok {
                if ident.Name == "recover" {
                    a.patterns["defer_recover"] = true
                }
            }
        }
        return true
    })
}

func (a *Analyzer) analyzeFuncLit(x *ast.FuncLit) {
    // Check for recover() in function literals (often used in goroutines)
    ast.Inspect(x.Body, func(n ast.Node) bool {
        if call, ok := n.(*ast.CallExpr); ok {
            if ident, ok := call.Fun.(*ast.Ident); ok {
                if ident.Name == "recover" {
                    a.hasBasicHandling = true
                    a.patterns["defer_recover"] = true
                }
            }
        }
        return true
    })
}

// ENHANCEMENT 4: Comprehensive call expression analysis
func (a *Analyzer) analyzeCallExpr(x *ast.CallExpr) {
    switch fun := x.Fun.(type) {
    case *ast.SelectorExpr:
        a.analyzeSelectorExpr(fun)
    case *ast.Ident:
        a.analyzeIdentCall(fun)
    }
}

func (a *Analyzer) analyzeSelectorExpr(sel *ast.SelectorExpr) {
    methodName := sel.Sel.Name
    methodNameLower := strings.ToLower(methodName)

    // Check package qualifier
    var pkgName string
    if ident, ok := sel.X.(*ast.Ident); ok {
        pkgName = ident.Name
    }

    // Status code checks (basic)
    if methodName == "StatusCode" || methodName == "Code" || methodName == "Status" {
        a.hasBasicHandling = true
        a.patterns["status_check"] = true
    }

    // Context timeout/deadline patterns (advanced)
    if pkgName == "context" {
        switch methodName {
        case "WithTimeout", "WithDeadline":
            a.hasAdvancedHandling = true
            a.patterns["timeout"] = true
        case "WithCancel":
            a.hasAdvancedHandling = true
        }
    }

    // Time-based timeout patterns
    if pkgName == "time" && (methodName == "After" || methodName == "NewTimer") {
        a.hasAdvancedHandling = true
        a.patterns["timeout"] = true
    }

    // Backoff library patterns
    if strings.Contains(pkgName, "backoff") || strings.Contains(methodNameLower, "backoff") {
        a.hasAdvancedHandling = true
        a.patterns["exponential_backoff"] = true
    }

    // Retry patterns
    if strings.Contains(methodNameLower, "retry") || strings.Contains(methodNameLower, "retryable") {
        a.hasAdvancedHandling = true
        a.patterns["retry"] = true
    }

    // Circuit breaker patterns
    if strings.Contains(methodNameLower, "circuitbreaker") || 
       strings.Contains(methodNameLower, "breaker") ||
       methodName == "Call" && strings.Contains(pkgName, "breaker") {
        a.hasAdvancedHandling = true
        a.patterns["circuit_breaker"] = true
    }

    // Timeout patterns
    if strings.Contains(methodNameLower, "timeout") || strings.Contains(methodNameLower, "deadline") {
        a.hasAdvancedHandling = true
        a.patterns["timeout"] = true
    }

    // Failover patterns
    if strings.Contains(methodNameLower, "failover") {
        a.hasAdvancedHandling = true
    }
}

func (a *Analyzer) analyzeIdentCall(ident *ast.Ident) {
    name := strings.ToLower(ident.Name)

    // Direct function calls
    if strings.Contains(name, "retry") {
        a.hasAdvancedHandling = true
        a.patterns["retry"] = true
    }
    if strings.Contains(name, "backoff") {
        a.hasAdvancedHandling = true
        a.patterns["exponential_backoff"] = true
    }
}

// ENHANCEMENT 5: Detect configuration structs
func (a *Analyzer) analyzeCompositeLit(x *ast.CompositeLit) {
    if typ, ok := x.Type.(*ast.SelectorExpr); ok {
        typeName := typ.Sel.Name
        typeNameLower := strings.ToLower(typeName)

        // Backoff configuration structs
        if strings.Contains(typeNameLower, "backoff") {
            a.hasAdvancedHandling = true
            a.patterns["exponential_backoff"] = true
        }

        // Circuit breaker configuration structs
        if strings.Contains(typeNameLower, "breaker") || strings.Contains(typeNameLower, "settings") {
            if pkgIdent, ok := typ.X.(*ast.Ident); ok {
                if strings.Contains(strings.ToLower(pkgIdent.Name), "breaker") {
                    a.hasAdvancedHandling = true
                    a.patterns["circuit_breaker"] = true
                }
            }
        }

        // Retry configuration structs
        if strings.Contains(typeNameLower, "retry") || strings.Contains(typeNameLower, "policy") {
            a.hasAdvancedHandling = true
            a.patterns["retry"] = true
        }
    }
}