const ts = require('typescript');
const fs = require('fs');

function parseTypeScript(filePath) {
    let code;
    try {
        code = fs.readFileSync(filePath, 'utf8');
    } catch (error) {
        console.error(JSON.stringify({
            error: `Error reading file: ${error.message}`
        }));
        process.exit(1);
    }

    try {
        const sourceFile = ts.createSourceFile(
            filePath,
            code,
            ts.ScriptTarget.Latest,
            true
        );

        // Analysis state
        const state = {
            hasBasicHandling: false,
            hasAdvancedHandling: false,
            patterns: {
                try_catch: false,
                promise_catch: false,
                timeout: false,
                retry: false,
                circuit_breaker: false,
                exponential_backoff: false,
                status_check: false,
                rate_limiting: false,
                decorator: false
            },
            resilienceLibraries: new Set()
        };

        // Resilience library detection (TypeScript + JavaScript)
        const RESILIENCE_LIBRARIES = {
            // TypeScript-first libraries
            'cockatiel': { patterns: ['retry', 'circuit_breaker', 'timeout'], type: 'multi' },
            'ts-retry': { patterns: ['retry'], type: 'retry' },
            'ts-retry-promise': { patterns: ['retry'], type: 'retry' },
            
            // JavaScript libraries with TypeScript support
            'axios-retry': { patterns: ['retry'], type: 'retry' },
            'p-retry': { patterns: ['retry'], type: 'retry' },
            'async-retry': { patterns: ['retry'], type: 'retry' },
            'retry': { patterns: ['retry'], type: 'retry' },
            'node-retry': { patterns: ['retry'], type: 'retry' },
            
            // Circuit breaker libraries
            'opossum': { patterns: ['circuit_breaker'], type: 'circuit_breaker' },
            'brakes': { patterns: ['circuit_breaker'], type: 'circuit_breaker' },
            
            // Rate limiting libraries
            'bottleneck': { patterns: ['rate_limiting'], type: 'rate_limiting' },
            'p-limit': { patterns: ['rate_limiting'], type: 'rate_limiting' },
            'p-throttle': { patterns: ['rate_limiting'], type: 'rate_limiting' },
            'limiter': { patterns: ['rate_limiting'], type: 'rate_limiting' },
            
            // Timeout libraries
            'promise-timeout': { patterns: ['timeout'], type: 'timeout' },
            'p-timeout': { patterns: ['timeout'], type: 'timeout' },
            'timeout-abort-controller': { patterns: ['timeout'], type: 'timeout' },
            
            // Multi-purpose libraries
            'bluebird': { patterns: ['timeout', 'retry'], type: 'multi' },
            'async': { patterns: ['retry'], type: 'multi' },
            'got': { patterns: ['retry', 'timeout'], type: 'http_client' },
            'axios': { patterns: ['timeout'], type: 'http_client' },
            
            // RxJS resilience operators
            'rxjs': { patterns: ['retry', 'timeout'], type: 'reactive' },
            'rxjs/operators': { patterns: ['retry', 'timeout'], type: 'reactive' }
        };

        // Analyze imports
        function analyzeImportDeclaration(node) {
            if (ts.isImportDeclaration(node) && node.moduleSpecifier) {
                const moduleName = node.moduleSpecifier.text;
                
                if (RESILIENCE_LIBRARIES[moduleName]) {
                    state.resilienceLibraries.add(moduleName);
                    state.hasAdvancedHandling = true;
                    
                    const library = RESILIENCE_LIBRARIES[moduleName];
                    library.patterns.forEach(pattern => {
                        state.patterns[pattern] = true;
                    });
                }
            }
        }

        // Analyze decorators (TypeScript-specific!)
        function analyzeDecorators(node) {
            if (!ts.canHaveDecorators(node)) return;
            
            const decorators = ts.getDecorators(node);
            if (!decorators) return;
            
            decorators.forEach(decorator => {
                const expression = decorator.expression;
                let decoratorName = '';
                
                if (ts.isIdentifier(expression)) {
                    decoratorName = expression.escapedText.toLowerCase();
                } else if (ts.isCallExpression(expression) && ts.isIdentifier(expression.expression)) {
                    decoratorName = expression.expression.escapedText.toLowerCase();
                }
                
                if (decoratorName) {
                    state.hasAdvancedHandling = true;
                    state.patterns.decorator = true;
                    
                    // Specific decorator patterns
                    if (decoratorName.includes('retry')) {
                        state.patterns.retry = true;
                    }
                    if (decoratorName.includes('timeout')) {
                        state.patterns.timeout = true;
                    }
                    if (decoratorName.includes('circuitbreaker') || decoratorName.includes('breaker')) {
                        state.patterns.circuit_breaker = true;
                    }
                    if (decoratorName.includes('backoff')) {
                        state.patterns.exponential_backoff = true;
                    }
                    if (decoratorName.includes('ratelimit') || decoratorName.includes('throttle')) {
                        state.patterns.rate_limiting = true;
                    }
                }
            });
        }

        // Analyze call expressions
        function analyzeCallExpression(node) {
            const expression = node.expression;
            
            // Handle: functionName()
            if (ts.isIdentifier(expression)) {
                const name = expression.escapedText.toLowerCase();
                
                // Timeout patterns
                if (name.includes('timeout') || name === 'settimeout') {
                    state.hasAdvancedHandling = true;
                    state.patterns.timeout = true;
                }
                
                // Retry patterns
                if (name.includes('retry')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.retry = true;
                }
                
                // Circuit breaker patterns
                if (name.includes('breaker') || name.includes('circuitbreaker')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.circuit_breaker = true;
                }
                
                // Backoff patterns
                if (name.includes('backoff')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.exponential_backoff = true;
                }
                
                // Rate limiting patterns
                if (name.includes('limit') || name.includes('throttle')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.rate_limiting = true;
                }
            }
            
            // Handle: object.method()
            if (ts.isPropertyAccessExpression(expression)) {
                const propertyName = ts.isIdentifier(expression.name) 
                    ? expression.name.escapedText.toLowerCase() 
                    : '';
                
                const objectName = ts.isIdentifier(expression.expression)
                    ? expression.expression.escapedText.toLowerCase()
                    : '';
                
                // Status checks
                if (propertyName === 'status' || propertyName === 'statuscode') {
                    state.hasBasicHandling = true;
                    state.patterns.status_check = true;
                }
                
                // Promise.race (timeout pattern)
                if (objectName === 'promise' && propertyName === 'race') {
                    state.hasAdvancedHandling = true;
                    state.patterns.timeout = true;
                }
                
                // Promise.catch (error handling)
                if (propertyName === 'catch') {
                    state.hasBasicHandling = true;
                    state.patterns.promise_catch = true;
                }
                
                // Circuit breaker methods
                if (objectName.includes('breaker') || objectName.includes('circuit')) {
                    if (propertyName === 'fire' || propertyName === 'execute' || 
                        propertyName === 'call' || propertyName === 'run') {
                        state.hasAdvancedHandling = true;
                        state.patterns.circuit_breaker = true;
                    }
                }
                
                // Rate limiter methods
                if (objectName.includes('limit') || objectName.includes('throttle') || 
                    objectName === 'bottleneck') {
                    if (propertyName === 'schedule' || propertyName === 'submit' || 
                        propertyName === 'wrap') {
                        state.hasAdvancedHandling = true;
                        state.patterns.rate_limiting = true;
                    }
                }
                
                // Retry library methods
                if (objectName.includes('retry')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.retry = true;
                }
                
                // RxJS operators
                if (propertyName === 'retrywhen' || propertyName === 'retry') {
                    state.hasAdvancedHandling = true;
                    state.patterns.retry = true;
                }
            }
        }

        // Analyze object literal expressions (config objects)
        function analyzeObjectLiteral(node) {
            if (ts.isObjectLiteralExpression(node)) {
                node.properties.forEach(property => {
                    if (ts.isPropertyAssignment(property)) {
                        const name = property.name;
                        let keyName = '';
                        
                        if (ts.isIdentifier(name)) {
                            keyName = name.escapedText.toLowerCase();
                        } else if (ts.isStringLiteral(name)) {
                            keyName = name.text.toLowerCase();
                        }
                        
                        if (keyName) {
                            // Timeout configurations
                            if (keyName === 'timeout') {
                                state.hasAdvancedHandling = true;
                                state.patterns.timeout = true;
                            }
                            
                            // Retry configurations
                            if (keyName === 'retries' || keyName === 'retry' || 
                                keyName === 'maxretries' || keyName === 'maxattempts') {
                                state.hasAdvancedHandling = true;
                                state.patterns.retry = true;
                            }
                            
                            // Backoff configurations
                            if (keyName.includes('backoff') || keyName === 'retrydelay') {
                                state.hasAdvancedHandling = true;
                                state.patterns.exponential_backoff = true;
                            }
                            
                            // Circuit breaker configurations
                            if (keyName.includes('breaker') || keyName === 'threshold' ||
                                keyName === 'errorthreshold') {
                                state.hasAdvancedHandling = true;
                                state.patterns.circuit_breaker = true;
                            }
                        }
                    }
                });
            }
        }

        // Analyze class declarations
        function analyzeClassDeclaration(node) {
            if (ts.isClassDeclaration(node) && node.name) {
                const className = node.name.escapedText.toLowerCase();
                
                // Circuit breaker classes
                if (className.includes('circuitbreaker') || className.includes('breaker')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.circuit_breaker = true;
                }
                
                // Retry classes
                if (className.includes('retry')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.retry = true;
                }
                
                // Rate limiter classes
                if (className.includes('limiter') || className.includes('throttle')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.rate_limiting = true;
                }
            }
        }

        //  Analyze interface/type declarations (TypeScript-specific)
        function analyzeTypeDeclaration(node) {
            let typeName = '';
            
            if (ts.isInterfaceDeclaration(node) && node.name) {
                typeName = node.name.escapedText.toLowerCase();
            } else if (ts.isTypeAliasDeclaration(node) && node.name) {
                typeName = node.name.escapedText.toLowerCase();
            }
            
            if (typeName) {
                // Retry-related types
                if (typeName.includes('retry') || typeName.includes('retrypolicy')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.retry = true;
                }
                
                // Circuit breaker types
                if (typeName.includes('circuitbreaker') || typeName.includes('breaker')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.circuit_breaker = true;
                }
                
                // Timeout types
                if (typeName.includes('timeout')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.timeout = true;
                }
                
                // Backoff types
                if (typeName.includes('backoff')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.exponential_backoff = true;
                }
            }
        }

        // Analyze new expressions
        function analyzeNewExpression(node) {
            if (ts.isNewExpression(node) && ts.isIdentifier(node.expression)) {
                const className = node.expression.escapedText.toLowerCase();
                
                // Circuit breaker instantiation
                if (className.includes('circuitbreaker') || className.includes('breaker')) {
                    state.hasAdvancedHandling = true;
                    state.patterns.circuit_breaker = true;
                }
                
                // Bottleneck (rate limiter)
                if (className === 'bottleneck') {
                    state.hasAdvancedHandling = true;
                    state.patterns.rate_limiting = true;
                }
                
                // AbortController (timeout pattern)
                if (className === 'abortcontroller') {
                    state.hasAdvancedHandling = true;
                    state.patterns.timeout = true;
                }
            }
        }

        // Main visitor function
        function visit(node) {
            // Basic: try-catch
            if (ts.isTryStatement(node)) {
                state.hasBasicHandling = true;
                state.patterns.try_catch = true;
            }
            
            //  Import declarations
            if (ts.isImportDeclaration(node)) {
                analyzeImportDeclaration(node);
            }
            
            //  Decorators (TypeScript-specific)
            analyzeDecorators(node);
            
            //  Call expressions
            if (ts.isCallExpression(node)) {
                analyzeCallExpression(node);
            }
            
            //  Object literals
            if (ts.isObjectLiteralExpression(node)) {
                analyzeObjectLiteral(node);
            }
            
            //  Class declarations
            if (ts.isClassDeclaration(node)) {
                analyzeClassDeclaration(node);
            }
            
            //  Interface/Type declarations
            if (ts.isInterfaceDeclaration(node) || ts.isTypeAliasDeclaration(node)) {
                analyzeTypeDeclaration(node);
            }
            
            // New expressions
            if (ts.isNewExpression(node)) {
                analyzeNewExpression(node);
            }
            
            // Continue traversing
            ts.forEachChild(node, visit);
        }

        // Start traversal
        visit(sourceFile);

        // Output results
        const result = {
            hasBasicHandling: state.hasBasicHandling,
            hasAdvancedHandling: state.hasAdvancedHandling,
            patterns: state.patterns,
            resilienceLibraries: Array.from(state.resilienceLibraries)
        };

        console.log(JSON.stringify(result));
    } catch (error) {
        console.error(JSON.stringify({
            error: `Error parsing TypeScript: ${error.message}`
        }));
        process.exit(1);
    }
}

if (process.argv.length < 3) {
    console.error(JSON.stringify({
        error: 'Please provide a file path as an argument.'
    }));
    process.exit(1);
}

const filePath = process.argv[2];
parseTypeScript(filePath);