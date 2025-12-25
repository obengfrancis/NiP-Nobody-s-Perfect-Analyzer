#!/usr/bin/env node

const fs = require("fs");
const parser = require("@babel/parser");
const traverse = require("@babel/traverse").default;

const filePath = process.argv[2];

if (!filePath) {
  console.error("Usage: node parse_javascript.js <file.js>");
  // Still exit 0 so Python can just treat this as 'no patterns'
  console.log(
    JSON.stringify({
      hasBasicHandling: false,
      hasAdvancedHandling: false,
      patterns: {},
      resilienceLibraries: [],
    })
  );
  process.exit(0);
}

const code = fs.readFileSync(filePath, "utf8");

// ---------- Parse safely ----------
let ast;
try {
  ast = parser.parse(code, {
    sourceType: "unambiguous",
    plugins: [
      "jsx",
      "typescript",
      "classProperties",
      "objectRestSpread",
      "dynamicImport",
      // optional extras that show up in modern code:
      "optionalChaining",
      "nullishCoalescingOperator",
      "topLevelAwait",
    ],
  });
} catch (e) {
  console.error("JS parse error:", e.message);
  console.log(
    JSON.stringify({
      hasBasicHandling: false,
      hasAdvancedHandling: false,
      patterns: {},
      resilienceLibraries: [],
    })
  );
  process.exit(0);
}

// ---------- Analysis state ----------
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
  },
  resilienceLibraries: new Set(),
};

// Resilience libraries exactly as you defined
const RESILIENCE_LIBRARIES = {
  // Retry libraries
  "axios-retry": { patterns: ["retry"], type: "retry" },
  "p-retry": { patterns: ["retry"], type: "retry" },
  "async-retry": { patterns: ["retry"], type: "retry" },
  retry: { patterns: ["retry"], type: "retry" },
  "node-retry": { patterns: ["retry"], type: "retry" },

  // Circuit breaker libraries
  opossum: { patterns: ["circuit_breaker"], type: "circuit_breaker" },
  cockatiel: {
    patterns: ["retry", "circuit_breaker", "timeout"],
    type: "multi",
  },
  brakes: { patterns: ["circuit_breaker"], type: "circuit_breaker" },

  // Rate limiting libraries
  bottleneck: { patterns: ["rate_limiting"], type: "rate_limiting" },
  "p-limit": { patterns: ["rate_limiting"], type: "rate_limiting" },
  "p-throttle": { patterns: ["rate_limiting"], type: "rate_limiting" },
  limiter: { patterns: ["rate_limiting"], type: "rate_limiting" },

  // Timeout libraries
  "promise-timeout": { patterns: ["timeout"], type: "timeout" },
  "p-timeout": { patterns: ["timeout"], type: "timeout" },
  "timeout-abort-controller": { patterns: ["timeout"], type: "timeout" },

  // Multi-purpose libraries
  bluebird: { patterns: ["timeout", "retry"], type: "multi" },
  async: { patterns: ["retry"], type: "multi" },
  got: { patterns: ["retry", "timeout"], type: "http_client" },
  axios: { patterns: ["timeout"], type: "http_client" },
};

// ---------- Helper analyzers ----------
function analyzeImports(path) {
  let source = null;

  // import X from 'library'
  if (path.node.source && path.node.source.value) {
    source = path.node.source.value;
  }

  // require('library')
  if (
    path.node.callee &&
    path.node.callee.type === "Identifier" &&
    path.node.callee.name === "require" &&
    path.node.arguments &&
    path.node.arguments.length > 0 &&
    path.node.arguments[0].type === "StringLiteral"
  ) {
    source = path.node.arguments[0].value;
  }

  if (source && RESILIENCE_LIBRARIES[source]) {
    state.resilienceLibraries.add(source);
    state.hasAdvancedHandling = true;

    const library = RESILIENCE_LIBRARIES[source];
    library.patterns.forEach((pattern) => {
      state.patterns[pattern] = true;
    });
  }
}

function analyzeCallExpression(path) {
  const callee = path.node.callee;

  // functionName(...)
  if (callee.type === "Identifier") {
    const name = callee.name.toLowerCase();

    if (name.includes("timeout") || name === "settimeout") {
      state.hasAdvancedHandling = true;
      state.patterns.timeout = true;
    }

    if (name.includes("retry")) {
      state.hasAdvancedHandling = true;
      state.patterns.retry = true;
    }

    if (name.includes("breaker") || name.includes("circuitbreaker")) {
      state.hasAdvancedHandling = true;
      state.patterns.circuit_breaker = true;
    }

    if (name.includes("backoff")) {
      state.hasAdvancedHandling = true;
      state.patterns.exponential_backoff = true;
    }

    if (name.includes("limit") || name.includes("throttle")) {
      state.hasAdvancedHandling = true;
      state.patterns.rate_limiting = true;
    }
  }

  // object.method(...)
  if (callee.type === "MemberExpression") {
    const obj = callee.object;
    const prop = callee.property;

    const objectName =
      obj && obj.type === "Identifier" ? obj.name.toLowerCase() : "";
    const propertyName =
      prop && prop.type === "Identifier" ? prop.name.toLowerCase() : "";

    // Status checks: res.status, res.statusCode
    if (propertyName === "status" || propertyName === "statuscode") {
      state.hasBasicHandling = true;
      state.patterns.status_check = true;
    }

    // Promise.race(...)
    if (objectName === "promise" && propertyName === "race") {
      state.hasAdvancedHandling = true;
      state.patterns.timeout = true;
    }

    // Promise.catch(...)
    if (propertyName === "catch") {
      state.hasBasicHandling = true;
      state.patterns.promise_catch = true;
    }

    // breaker.fire(), breaker.execute(), etc.
    if (objectName.includes("breaker") || objectName.includes("circuit")) {
      if (
        ["fire", "execute", "call", "run"].includes(propertyName)
      ) {
        state.hasAdvancedHandling = true;
        state.patterns.circuit_breaker = true;
      }
    }

    // retrySomething.method()
    if (objectName.includes("retry")) {
      state.hasAdvancedHandling = true;
      state.patterns.retry = true;
    }

    // limiter.schedule(), limiter.submit(), limiter.wrap()
    if (
      objectName.includes("limit") ||
      objectName.includes("throttle") ||
      objectName === "bottleneck"
    ) {
      if (
        ["schedule", "submit", "wrap"].includes(propertyName)
      ) {
        state.hasAdvancedHandling = true;
        state.patterns.rate_limiting = true;
      }
    }

    // axios.retry(...)
    if (objectName.includes("axios") && propertyName.includes("retry")) {
      state.hasAdvancedHandling = true;
      state.patterns.retry = true;
    }
  }
}

function analyzeObjectProperty(path) {
  const key = path.node.key;
  const keyName =
    (key && key.name) || (key && key.value) || null;

  if (!keyName) return;

  const name = String(keyName).toLowerCase();

  if (name === "timeout") {
    state.hasAdvancedHandling = true;
    state.patterns.timeout = true;
  }

  if (name === "retries" || name === "retry" || name === "maxretries") {
    state.hasAdvancedHandling = true;
    state.patterns.retry = true;
  }

  if (name.includes("backoff") || name === "retrydelay") {
    state.hasAdvancedHandling = true;
    state.patterns.exponential_backoff = true;
  }

  if (name.includes("breaker") || name === "threshold") {
    state.hasAdvancedHandling = true;
    state.patterns.circuit_breaker = true;
  }
}

function analyzeClassDeclaration(path) {
  const id = path.node.id;
  if (!id || !id.name) return;

  const className = id.name.toLowerCase();

  if (
    className.includes("circuitbreaker") ||
    className.includes("breaker")
  ) {
    state.hasAdvancedHandling = true;
    state.patterns.circuit_breaker = true;
  }

  if (className.includes("retry")) {
    state.hasAdvancedHandling = true;
    state.patterns.retry = true;
  }

  if (className.includes("limiter") || className.includes("throttle")) {
    state.hasAdvancedHandling = true;
    state.patterns.rate_limiting = true;
  }
}

function analyzeNewExpression(path) {
  const callee = path.node.callee;
  if (!callee || callee.type !== "Identifier") return;

  const className = callee.name.toLowerCase();

  if (
    className.includes("circuitbreaker") ||
    className.includes("breaker")
  ) {
    state.hasAdvancedHandling = true;
    state.patterns.circuit_breaker = true;
  }

  if (className === "bottleneck") {
    state.hasAdvancedHandling = true;
    state.patterns.rate_limiting = true;
  }

  if (className === "abortcontroller") {
    state.hasAdvancedHandling = true;
    state.patterns.timeout = true;
  }
}

// ---------- Traverse AST ----------
traverse(ast, {
  // Basic: try/catch/finally
  TryStatement(path) {
    state.hasBasicHandling = true;
    state.patterns.try_catch = true;
  },

  // Imports
  ImportDeclaration(path) {
    analyzeImports(path);
  },

  // require(...) + call patterns
  CallExpression(path) {
    analyzeImports(path); // detect require('lib')
    analyzeCallExpression(path);
  },

  // Config objects
  ObjectProperty(path) {
    analyzeObjectProperty(path);
  },

  // Class declarations
  ClassDeclaration(path) {
    analyzeClassDeclaration(path);
  },

  // new Something(...)
  NewExpression(path) {
    analyzeNewExpression(path);
  },

  // Member expressions (status, .catch)
  MemberExpression(path) {
    const prop = path.node.property;
    if (!prop || prop.type !== "Identifier") return;

    const name = prop.name;

    if (name === "catch") {
      state.hasBasicHandling = true;
      state.patterns.promise_catch = true;
    }

    if (name === "status" || name === "statusCode") {
      state.hasBasicHandling = true;
      state.patterns.status_check = true;
    }
  },
});

// ---------- Output ----------
const result = {
  hasBasicHandling: state.hasBasicHandling,
  hasAdvancedHandling: state.hasAdvancedHandling,
  patterns: state.patterns,
  resilienceLibraries: Array.from(state.resilienceLibraries),
};

console.log(JSON.stringify(result));
