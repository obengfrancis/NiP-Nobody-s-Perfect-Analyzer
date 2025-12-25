// Comprehensive JavaScript Resilience Patterns Test File

// ENHANCEMENT 1: Import detection
const axios = require('axios');
const axiosRetry = require('axios-retry');
const CircuitBreaker = require('opossum');
const pRetry = require('p-retry');
const Bottleneck = require('bottleneck');

// Configure axios retry (ENHANCEMENT 2: Configuration object detection)
axiosRetry(axios, {
    retries: 3,                              // ← retry config
    retryDelay: axiosRetry.exponentialDelay, // ← exponential backoff
    timeout: 5000                            // ← timeout config
});

// ENHANCEMENT 3: Circuit breaker instantiation
const breaker = new CircuitBreaker(async (url) => {
    return axios.get(url);
}, {
    timeout: 3000,        // ← timeout
    errorThresholdPercentage: 50,
    resetTimeout: 30000
});

// ENHANCEMENT 4: Rate limiter instantiation
const limiter = new Bottleneck({
    maxConcurrent: 5,
    minTime: 200
});

// ENHANCEMENT 5: Async/await with try-catch (BASIC)
async function fetchDataWithRetry(url) {
    try {
        // ENHANCEMENT 6: p-retry library usage
        const response = await pRetry(async () => {
            return axios.get(url, { timeout: 5000 });
        }, {
            retries: 3,
            onFailedAttempt: error => {
                console.log(`Attempt ${error.attemptNumber} failed`);
            }
        });
        
        // ENHANCEMENT 7: Status code check (BASIC)
        if (response.status === 200) {
            return response.data;
        }
        
    } catch (error) {
        console.error('All retry attempts failed:', error);
        throw error;
    }
}

// ENHANCEMENT 8: Circuit breaker method call
async function fetchWithCircuitBreaker(url) {
    try {
        const result = await breaker.fire(url);  // ← breaker.fire() detection
        return result;
    } catch (error) {
        console.error('Circuit breaker error:', error);
        throw error;
    }
}

// ENHANCEMENT 9: Promise.race for timeout pattern
async function fetchWithTimeout(url, timeoutMs) {
    const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Timeout')), timeoutMs);
    });
    
    const fetchPromise = axios.get(url);
    
    return Promise.race([fetchPromise, timeoutPromise]);  // ← Promise.race detection
}

// ENHANCEMENT 10: Promise .catch() error handling (BASIC)
function fetchWithPromiseCatch(url) {
    return axios.get(url)
        .then(response => response.data)
        .catch(error => {  // ← .catch() detection
            console.error('Request failed:', error);
            throw error;
        });
}

// ENHANCEMENT 11: Rate limiter usage
async function fetchWithRateLimit(url) {
    return limiter.schedule(async () => {  // ← limiter.schedule() detection
        const response = await axios.get(url);
        return response.data;
    });
}

// ENHANCEMENT 12: Manual retry with exponential backoff
async function manualRetryWithBackoff(url) {
    let retries = 3;
    let backoff = 1000;
    
    while (retries > 0) {
        try {
            const response = await axios.get(url);
            return response.data;
        } catch (error) {
            retries--;
            if (retries > 0) {
                await new Promise(resolve => setTimeout(resolve, backoff));
                backoff *= 2;  // ← Exponential backoff
            } else {
                throw error;
            }
        }
    }
}

// ENHANCEMENT 13: Custom circuit breaker class
class CustomCircuitBreaker {
    constructor(options) {
        this.failureThreshold = options.threshold || 5;
        this.resetTimeout = options.resetTimeout || 60000;
        this.failures = 0;
        this.state = 'CLOSED';
    }
    
    async execute(fn) {
        if (this.state === 'OPEN') {
            throw new Error('Circuit breaker is open');
        }
        
        try {
            const result = await fn();
            this.failures = 0;
            return result;
        } catch (error) {
            this.failures++;
            if (this.failures >= this.failureThreshold) {
                this.state = 'OPEN';
                setTimeout(() => {
                    this.state = 'CLOSED';
                    this.failures = 0;
                }, this.resetTimeout);
            }
            throw error;
        }
    }
}

// ENHANCEMENT 14: AbortController for timeout (modern pattern)
async function fetchWithAbortController(url, timeoutMs) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    
    try {
        const response = await fetch(url, { 
            signal: controller.signal,
            timeout: timeoutMs  // ← timeout config
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request timeout');
        }
        throw error;
    }
}

// Export functions
module.exports = {
    fetchDataWithRetry,
    fetchWithCircuitBreaker,
    fetchWithTimeout,
    fetchWithPromiseCatch,
    fetchWithRateLimit,
    manualRetryWithBackoff,
    fetchWithAbortController,
    CustomCircuitBreaker
};