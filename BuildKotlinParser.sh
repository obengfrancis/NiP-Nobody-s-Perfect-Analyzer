#!/bin/bash
# Enhanced build script for Kotlin parser with ALL dependencies bundled

echo "Building Kotlin Parser with all dependencies..."

# Step 1: Download Gson if not present
if [ ! -f "gson-2.10.1.jar" ]; then
    echo "Downloading Gson library..."
    curl -L -o gson-2.10.1.jar \
        https://repo1.maven.org/maven2/com/google/code/gson/gson/2.10.1/gson-2.10.1.jar
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to download Gson!"
        exit 1
    fi
fi

# Step 2: Find Kotlin home directory
echo "Locating Kotlin installation..."
KOTLIN_HOME=$(dirname $(dirname $(which kotlinc)))
echo "Kotlin home: $KOTLIN_HOME"

# Step 3: Find Kotlin stdlib JAR (the main one, not jdk8)
KOTLIN_LIB=""

# Try different locations
if [ -f "$KOTLIN_HOME/lib/kotlin-stdlib.jar" ]; then
    KOTLIN_LIB="$KOTLIN_HOME/lib/kotlin-stdlib.jar"
elif [ -f "$KOTLIN_HOME/libexec/lib/kotlin-stdlib.jar" ]; then
    KOTLIN_LIB="$KOTLIN_HOME/libexec/lib/kotlin-stdlib.jar"
else
    # Search for it (excluding jdk7/jdk8 versions)
    KOTLIN_LIB=$(find $KOTLIN_HOME -name "kotlin-stdlib.jar" 2>/dev/null | grep -v jdk | head -1)
fi

if [ ! -f "$KOTLIN_LIB" ]; then
    echo "❌ Could not find kotlin-stdlib.jar"
    echo "Searched in: $KOTLIN_HOME"
    echo ""
    echo "Available Kotlin JARs:"
    find $KOTLIN_HOME -name "kotlin-*.jar" 2>/dev/null | head -10
    exit 1
fi

echo "Found Kotlin stdlib: $KOTLIN_LIB"

# Step 4: Clean up old files
rm -rf build_temp
mkdir -p build_temp

# Step 5: Compile Kotlin to class files
echo "Compiling Kotlin code..."
kotlinc -cp gson-2.10.1.jar \
    ParseKotlin.kt \
    -d build_temp/

if [ $? -ne 0 ]; then
    echo "❌ Kotlin compilation failed!"
    rm -rf build_temp
    exit 1
fi

# Step 6: Extract all dependency JARs
echo "Extracting dependencies..."
cd build_temp

# Extract Gson
echo "  - Extracting Gson..."
jar xf ../gson-2.10.1.jar
rm -rf META-INF/maven

# Extract Kotlin stdlib (the main one)
echo "  - Extracting Kotlin stdlib..."
jar xf "$KOTLIN_LIB"

# Clean up signature files that might cause conflicts
rm -rf META-INF/*.SF META-INF/*.RSA META-INF/*.DSA

# Step 7: Create manifest
echo "Creating manifest..."
cat > MANIFEST.MF << EOF
Manifest-Version: 1.0
Main-Class: ParseKotlinKt

EOF

# Step 8: Create fat JAR with everything
echo "Creating fat JAR with all dependencies..."
jar cfm ../parse_kotlin.jar MANIFEST.MF .

cd ..

# Step 9: Verify critical classes are in the JAR
echo "Verifying JAR contents..."
if jar tf parse_kotlin.jar | grep -q "kotlin/Pair.class"; then
    echo "  ✅ kotlin.Pair found in JAR"
else
    echo "  ❌ WARNING: kotlin.Pair NOT found in JAR!"
fi

if jar tf parse_kotlin.jar | grep -q "com/google/gson/Gson.class"; then
    echo "  ✅ Gson found in JAR"
else
    echo "  ❌ WARNING: Gson NOT found in JAR!"
fi

if jar tf parse_kotlin.jar | grep -q "ParseKotlinKt.class"; then
    echo "  ✅ Parser classes found in JAR"
else
    echo "  ❌ WARNING: Parser classes NOT found in JAR!"
fi

# Clean up
rm -rf build_temp

if [ -f "parse_kotlin.jar" ]; then
    echo ""
    echo "✅ Build successful!"
    echo "JAR created: parse_kotlin.jar"
    echo "JAR size: $(ls -lh parse_kotlin.jar | awk '{print $5}')"
    echo ""
    echo "Test it with:"
    echo "  java -jar parse_kotlin.jar test_kotlin_basic.kt"
else
    echo "❌ Build failed!"
    exit 1
fi