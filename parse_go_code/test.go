package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/cenkalti/backoff/v4"
	"github.com/sony/gobreaker"
)

// This comprehensive test file demonstrates ALL the resilience patterns
// that the enhanced Go parser should detect.

// Global circuit breaker
var cb *gobreaker.CircuitBreaker

func init() {
	// PATTERN: Circuit Breaker Configuration
	settings := gobreaker.Settings{
		Name:        "HTTP_Breaker",
		MaxRequests: 3,
		Interval:    time.Second * 10,
		Timeout:     time.Second * 60,
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			failureRatio := float64(counts.TotalFailures) / float64(counts.Requests)
			return counts.Requests >= 3 && failureRatio >= 0.6
		},
	}
	cb = gobreaker.NewCircuitBreaker(settings)
}

// Example 1: Context-based timeout (THE standard Go pattern)
func callAPIWithTimeout() error {
	// PATTERN: context.WithTimeout - Advanced timeout handling
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// PATTERN: Error checking - Basic error handling
	if err := makeHTTPRequest(ctx); err != nil {
		return fmt.Errorf("API call failed: %w", err)
	}

	return nil
}

// Example 2: Context with deadline
func callAPIWithDeadline() error {
	// PATTERN: context.WithDeadline - Advanced timeout handling
	deadline := time.Now().Add(10 * time.Second)
	ctx, cancel := context.WithDeadline(context.Background(), deadline)
	defer cancel()

	// PATTERN: Error checking with inline assignment
	if err := makeHTTPRequest(ctx); err != nil {
		return err
	}

	return nil
}

// Example 3: Exponential backoff with retry
func callAPIWithBackoff() error {
	// PATTERN: Backoff configuration - Exponential backoff
	expBackoff := backoff.NewExponentialBackOff()
	expBackoff.InitialInterval = 500 * time.Millisecond
	expBackoff.MaxInterval = 60 * time.Second
	expBackoff.MaxElapsedTime = 5 * time.Minute

	// PATTERN: Retry operation
	operation := func() error {
		ctx := context.Background()
		return makeHTTPRequest(ctx)
	}

	// PATTERN: backoff.Retry - Advanced retry with exponential backoff
	err := backoff.Retry(operation, expBackoff)
	if err != nil {
		return fmt.Errorf("all retry attempts failed: %w", err)
	}

	return nil
}

// Example 4: Circuit breaker pattern
func callAPIWithCircuitBreaker() error {
	// PATTERN: Circuit breaker execution
	result, err := cb.Execute(func() (interface{}, error) {
		ctx := context.Background()
		return nil, makeHTTPRequest(ctx)
	})

	if err != nil {
		return fmt.Errorf("circuit breaker: %w", err)
	}

	_ = result
	return nil
}

// Example 5: Combined patterns - Context timeout + Retry + Circuit breaker
func resilientAPICall() error {
	// PATTERN: Multiple resilience patterns combined
	operation := func() error {
		// Context timeout
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()

		// Circuit breaker
		_, err := cb.Execute(func() (interface{}, error) {
			return nil, makeHTTPRequest(ctx)
		})

		return err
	}

	// Exponential backoff retry
	expBackoff := backoff.NewExponentialBackOff()
	err := backoff.Retry(operation, expBackoff)

	if err != nil {
		log.Printf("Resilient call failed after retries: %v", err)
		return err
	}

	return nil
}

// Example 6: Defer and recover (Go's panic handling)
func callAPIWithPanicRecovery() (err error) {
	// PATTERN: defer/recover - Basic error handling (Go style)
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("recovered from panic: %v", r)
			log.Printf("Panic recovered: %v", r)
		}
	}()

	ctx := context.Background()
	return makeHTTPRequest(ctx)
}

// Example 7: Timeout using time.After (alternative pattern)
func callAPIWithTimeAfter() error {
	ctx := context.Background()
	resultChan := make(chan error, 1)

	go func() {
		resultChan <- makeHTTPRequest(ctx)
	}()

	// PATTERN: time.After for timeout
	select {
	case err := <-resultChan:
		if err != nil {
			return err
		}
		return nil
	case <-time.After(5 * time.Second):
		return errors.New("request timed out")
	}
}

// Example 8: HTTP status code checking
func callAPIWithStatusCheck() error {
	ctx := context.Background()

	resp, err := performHTTPCall(ctx)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// PATTERN: Status code check - Basic error handling
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	return nil
}

// Example 9: Retry with custom backoff policy
func callAPIWithCustomBackoff() error {
	// PATTERN: Custom backoff configuration
	constantBackoff := backoff.NewConstantBackOff(time.Second * 2)

	operation := func() error {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		return makeHTTPRequest(ctx)
	}

	// Retry with custom backoff
	return backoff.Retry(operation, backoff.WithMaxRetries(constantBackoff, 3))
}

// Example 10: Context cancellation
func callAPIWithCancellation() error {
	// PATTERN: context.WithCancel
	ctx, cancel := context.WithCancel(context.Background())
	
	// Cancel after some condition
	go func() {
		time.Sleep(2 * time.Second)
		cancel()
	}()

	return makeHTTPRequest(ctx)
}

// Example 11: Multiple error checks in sequence
func chainedAPICalls() error {
	ctx := context.Background()

	// PATTERN: Sequential error checks
	if err := makeHTTPRequest(ctx); err != nil {
		return fmt.Errorf("first call failed: %w", err)
	}

	if err := makeHTTPRequest(ctx); err != nil {
		return fmt.Errorf("second call failed: %w", err)
	}

	if err := makeHTTPRequest(ctx); err != nil {
		return fmt.Errorf("third call failed: %w", err)
	}

	return nil
}

// Example 12: Goroutine with timeout and error handling
func asyncCallWithTimeout() error {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	errChan := make(chan error, 1)

	go func() {
		defer func() {
			if r := recover(); r != nil {
				errChan <- fmt.Errorf("goroutine panic: %v", r)
			}
		}()

		if err := makeHTTPRequest(ctx); err != nil {
			errChan <- err
			return
		}
		errChan <- nil
	}()

	select {
	case err := <-errChan:
		return err
	case <-ctx.Done():
		return ctx.Err()
	}
}

// Helper functions (simulated)

func makeHTTPRequest(ctx context.Context) error {
	// Simulated HTTP request
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-time.After(100 * time.Millisecond):
		return nil
	}
}

func performHTTPCall(ctx context.Context) (*http.Response, error) {
	// Simulated HTTP call
	req, err := http.NewRequestWithContext(ctx, "GET", "https://api.example.com", nil)
	if err != nil {
		return nil, err
	}

	client := &http.Client{Timeout: 5 * time.Second}
	return client.Do(req)
}

func main() {
	fmt.Println("Testing resilience patterns...")

	// Test all patterns
	patterns := []struct {
		name string
		fn   func() error
	}{
		{"Context Timeout", callAPIWithTimeout},
		{"Context Deadline", callAPIWithDeadline},
		{"Exponential Backoff", callAPIWithBackoff},
		{"Circuit Breaker", callAPIWithCircuitBreaker},
		{"Combined Resilience", resilientAPICall},
		{"Panic Recovery", callAPIWithPanicRecovery},
		{"Time.After Timeout", callAPIWithTimeAfter},
		{"Status Check", callAPIWithStatusCheck},
		{"Custom Backoff", callAPIWithCustomBackoff},
		{"Cancellation", callAPIWithCancellation},
		{"Chained Calls", chainedAPICalls},
		{"Async with Timeout", asyncCallWithTimeout},
	}

	for _, p := range patterns {
		fmt.Printf("Testing %s... ", p.name)
		if err := p.fn(); err != nil {
			fmt.Printf("Error: %v\n", err)
		} else {
			fmt.Println("OK")
		}
	}
}