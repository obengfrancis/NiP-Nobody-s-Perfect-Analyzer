#!/usr/bin/env ruby
# Ruby Parser for Exception Handling and Resilience Patterns
# Outputs JSON format consistent with other enhanced parsers

require 'json'

begin
  gem 'parser', '>= 3.0.0'
  require 'parser/current'
rescue Gem::LoadError => e
  error_output = {
    hasBasicHandling: false,
    hasAdvancedHandling: false,
    patterns: {},
    resilienceLibraries: [],
    error: "Parser gem not found: #{e.message}"
  }
  puts JSON.generate(error_output)
  exit 1
end

# ============================================================================
#  Ruby Resilience Libraries
# ============================================================================

RESILIENCE_LIBRARIES = {
  'retryable' => { patterns: ['retry'], type: 'retry' },
  'retriable' => { patterns: ['retry'], type: 'retry' },
  'circuitbox' => { patterns: ['circuit_breaker'], type: 'circuit_breaker' },
  'semian' => { patterns: ['circuit_breaker'], type: 'circuit_breaker' },
  'stoplight' => { patterns: ['circuit_breaker'], type: 'circuit_breaker' },
  'faraday-retry' => { patterns: ['retry'], type: 'retry' },
  'faraday' => { patterns: ['timeout', 'retry'], type: 'http_client' },
  'httparty' => { patterns: ['timeout'], type: 'http_client' },
  'typhoeus' => { patterns: ['timeout', 'retry'], type: 'http_client' },
  'rest-client' => { patterns: ['timeout'], type: 'http_client' },
  'net/http' => { patterns: [], type: 'http_client' },
  'timeout' => { patterns: ['timeout'], type: 'timeout' }
}.freeze

# ============================================================================
# Ruby Code Analyzer
# ============================================================================

class RubyCodeAnalyzer
  def initialize(code)
    @code = code
    @has_basic_handling = false
    @has_advanced_handling = false
    @patterns = {
      rescue: false,
      ensure: false,
      timeout: false,
      retry: false,
      circuit_breaker: false,
      exponential_backoff: false,
      status_check: false,
      rate_limiting: false
    }
    @resilience_libraries = []
  end

  def analyze
    begin
      # Parse code into AST
      @ast = Parser::CurrentRuby.parse(@code)
      
      # Detect require statements
      detect_requires
      
      # Traverse AST for patterns
      process_node(@ast)
      
    rescue Parser::SyntaxError => e
      # If parsing fails, return default (no patterns detected)
      return generate_output
    end

    generate_output
  end

  private

  # Detect require/require_relative statements
  def detect_requires
    # Pattern: require 'library_name'
    @code.scan(/require\s+['"]([^'"]+)['"]/).each do |match|
      library = match[0]
      
      # Check if it's a resilience library
      if RESILIENCE_LIBRARIES.key?(library)
        @resilience_libraries << library unless @resilience_libraries.include?(library)
        @has_advanced_handling = true
        
        # Set pattern flags based on library
        lib_info = RESILIENCE_LIBRARIES[library]
        lib_info[:patterns].each do |pattern|
          @patterns[pattern.to_sym] = true
        end
      end
    end
  end

  # Main AST traversal
  def process_node(node)
    return unless node.is_a?(Parser::AST::Node)

    case node.type
    when :rescue
      # Rescue blocks (begin/rescue/end)
      @has_basic_handling = true
      @patterns[:rescue] = true

    when :ensure
      # Ensure blocks
      @has_basic_handling = true
      @patterns[:ensure] = true

    when :send
      analyze_method_call(node)

    when :const
      analyze_constant_access(node)

    when :block
      analyze_block(node)
    end

    # Recursively process children
    node.children.each { |child| process_node(child) }
  end

  # Analyze method calls
  def analyze_method_call(node)
    receiver = node.children[0]
    method_name = node.children[1]
    
    return unless method_name

    method_str = method_name.to_s.downcase

    # Timeout patterns
    if method_str.include?('timeout')
      @has_advanced_handling = true
      @patterns[:timeout] = true
    end

    # Retry patterns
    if method_str.include?('retry') || method_str == 'retryable' || method_str == 'retriable'
      @has_advanced_handling = true
      @patterns[:retry] = true
    end

    # Circuit breaker patterns
    if method_str.include?('circuit') || method_str.include?('breaker')
      @has_advanced_handling = true
      @patterns[:circuit_breaker] = true
    end

    # Exponential backoff patterns
    if method_str.include?('backoff') || method_str.include?('exponential')
      @has_advanced_handling = true
      @patterns[:exponential_backoff] = true
    end

    # Rate limiting patterns
    if method_str.include?('throttle') || method_str.include?('rate_limit')
      @has_advanced_handling = true
      @patterns[:rate_limiting] = true
    end

    # Status code checks - various patterns
    if ['code', 'status', 'status_code', 'response_code'].include?(method_str)
      @has_basic_handling = true
      @patterns[:status_check] = true
    end

    # HTTParty specific patterns
    if receiver && receiver.type == :const && receiver.children[1] == :HTTParty
      @has_advanced_handling = true
    end
  end

  # Analyze constant access (e.g., Timeout::Error, Net::HTTP)
  def analyze_constant_access(node)
    const_name = node.children[1]
    return unless const_name

    const_str = const_name.to_s

    # Timeout constant
    if const_str == 'Timeout'
      @has_advanced_handling = true
      @patterns[:timeout] = true
    end

    # Circuit breaker constants
    if const_str.include?('Circuit') || const_str == 'Circuitbox' || const_str == 'Semian'
      @has_advanced_handling = true
      @patterns[:circuit_breaker] = true
    end

    # Retryable/Retriable constants
    if const_str == 'Retryable' || const_str == 'Retriable'
      @has_advanced_handling = true
      @patterns[:retry] = true
    end
  end

  # Analyze blocks (for retryable, Timeout.timeout, etc.)
  def analyze_block(node)
    # Check if this is a block call
    send_node = node.children[0]
    return unless send_node && send_node.type == :send

    method_name = send_node.children[1]
    return unless method_name

    method_str = method_name.to_s.downcase

    # Retryable block pattern
    if method_str == 'retryable' || method_str == 'retriable'
      @has_advanced_handling = true
      @patterns[:retry] = true
      
      # Check for exponential backoff in options
      args = send_node.children[2..-1]
      args.each do |arg|
        if arg.is_a?(Parser::AST::Node) && arg.type == :hash
          check_hash_for_backoff(arg)
        end
      end
    end

    # Timeout.timeout block pattern
    if method_str == 'timeout'
      receiver = send_node.children[0]
      if receiver && receiver.type == :const && receiver.children[1] == :Timeout
        @has_advanced_handling = true
        @patterns[:timeout] = true
      end
    end

    # Circuit breaker block patterns
    if method_str == 'circuit' && send_node.children[0]
      receiver = send_node.children[0]
      if receiver.type == :const
        const_name = receiver.children[1].to_s
        if const_name.include?('Circuit') || const_name == 'Circuitbox'
          @has_advanced_handling = true
          @patterns[:circuit_breaker] = true
        end
      end
    end
  end

  # Check hash arguments for exponential backoff configuration
  def check_hash_for_backoff(hash_node)
    hash_node.children.each do |pair|
      next unless pair.type == :pair
      
      key = pair.children[0]
      next unless key.type == :sym
      
      key_name = key.children[0].to_s.downcase
      
      if key_name.include?('backoff') || key_name.include?('exponential')
        @has_advanced_handling = true
        @patterns[:exponential_backoff] = true
      end
    end
  end

  # Generate JSON output
  def generate_output
    {
      hasBasicHandling: @has_basic_handling,
      hasAdvancedHandling: @has_advanced_handling,
      patterns: @patterns,
      resilienceLibraries: @resilience_libraries.uniq
    }
  end
end

# ============================================================================
#  Main Execution
# ============================================================================

if ARGV.empty?
  error_output = {
    hasBasicHandling: false,
    hasAdvancedHandling: false,
    patterns: {},
    resilienceLibraries: [],
    error: 'No Ruby code file provided'
  }
  puts JSON.generate(error_output)
  exit 1
end

file_path = ARGV[0]

begin
  ruby_code = File.read(file_path)
  analyzer = RubyCodeAnalyzer.new(ruby_code)
  result = analyzer.analyze
  puts JSON.generate(result)
rescue Errno::ENOENT => e
  error_output = {
    hasBasicHandling: false,
    hasAdvancedHandling: false,
    patterns: {},
    resilienceLibraries: [],
    error: "File not found: #{e.message}"
  }
  puts JSON.generate(error_output)
  exit 1
rescue => e
  error_output = {
    hasBasicHandling: false,
    hasAdvancedHandling: false,
    patterns: {},
    resilienceLibraries: [],
    error: "Error processing file: #{e.message}"
  }
  puts JSON.generate(error_output)
  exit 1
end