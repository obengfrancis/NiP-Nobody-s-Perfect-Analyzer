#!/bin/bash

echo "============================================"
echo "Testing Enhanced JavaParserAnalyzer"
echo "============================================"
echo ""

# Set the JAR path
JAR_PATH="target/your-artifact-id-1.0-SNAPSHOT.jar"

# Check if JAR exists
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: JAR not found at $JAR_PATH"
    echo "Please run: mvn clean package"
    exit 1
fi

echo "JAR found at: $JAR_PATH"
echo ""

# Test 1: Mixed (Both Basic and Advanced)
echo "TEST 1: Mixed Pattern (Both Basic + Advanced)"
echo "Expected: hasBasicHandling=true, hasAdvancedHandling=true"
echo "File: test_file.java"
echo "---"
java -jar "$JAR_PATH" test_file.java
echo ""
echo ""

# Test 2: Basic Only
echo "TEST 2: Basic Pattern Only"
echo "Expected: hasBasicHandling=true, hasAdvancedHandling=false"
echo "File: test_basic.java"
echo "---"
java -jar "$JAR_PATH" test_basic.java
echo ""
echo ""

# Test 3: None
echo "TEST 3: No Exception Handling"
echo "Expected: hasBasicHandling=false, hasAdvancedHandling=false"
echo "File: test_none.java"
echo "---"
java -jar "$JAR_PATH" test_none.java
echo ""
echo ""

echo "============================================"
echo "Testing Complete!"
echo "============================================"
echo ""
echo "VERIFICATION CHECKLIST:"
echo "  [ ] Test 1 shows hasAdvancedHandling: true (detects @Retry annotation)"
echo "  [ ] Test 1 shows hasBasicHandling: true (detects try-catch)"
echo "  [ ] Test 1 includes 'resilience_libraries': ['Resilience4j']"
echo "  [ ] Test 1 shows patterns with retry: true, try_catch: true"
echo "  [ ] Test 2 shows hasBasicHandling: true, hasAdvancedHandling: false"
echo "  [ ] Test 3 shows both false"
echo ""
echo "If all checks pass, the enhanced analyzer is working correctly!"