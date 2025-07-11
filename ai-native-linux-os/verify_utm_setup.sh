#!/bin/bash

echo "🔍 AI-Native Linux OS - UTM Setup Verification"
echo "=============================================="
echo

# Check UTM installation
echo "1. Checking UTM installation..."
if command -v utmctl &> /dev/null; then
    echo "   ✅ UTM is installed and available"
    utmctl version 2>/dev/null || echo "   📱 UTM GUI version available"
else
    echo "   ❌ UTM not found in PATH"
    if [ -d "/Applications/UTM.app" ]; then
        echo "   ℹ️  UTM app found in Applications folder"
    else
        echo "   ❌ UTM app not found. Please install UTM first."
        exit 1
    fi
fi
echo

# Check Ubuntu ISO download
echo "2. Checking Ubuntu Desktop ISO..."
ISO_PATH="$HOME/Downloads/ubuntu-24.04-desktop-arm64.iso"
if [ -f "$ISO_PATH" ]; then
    ISO_SIZE=$(ls -lh "$ISO_PATH" | awk '{print $5}')
    echo "   📁 ISO file found: $ISO_SIZE"
    
    # Check if it's a reasonable size (should be ~5GB)
    ACTUAL_SIZE=$(stat -f%z "$ISO_PATH" 2>/dev/null || stat -c%s "$ISO_PATH" 2>/dev/null)
    if [ "$ACTUAL_SIZE" -gt 1000000000 ]; then
        echo "   ✅ ISO appears to be complete (>1GB)"
    else
        echo "   ⚠️  ISO seems small, might still be downloading..."
        echo "   📊 Current size: $ISO_SIZE"
    fi
else
    echo "   ⬇️  ISO not found, still downloading or needs to be downloaded"
    echo "   📥 Expected location: $ISO_PATH"
fi
echo

# Check system resources
echo "3. Checking system resources..."
TOTAL_RAM=$(sysctl hw.memsize | awk '{print int($2/1024/1024/1024)}')
echo "   💾 Total RAM: ${TOTAL_RAM}GB"

if [ "$TOTAL_RAM" -ge 16 ]; then
    echo "   ✅ Excellent! You can allocate 8GB to the VM"
elif [ "$TOTAL_RAM" -ge 12 ]; then
    echo "   ✅ Good! You can allocate 6GB to the VM"
elif [ "$TOTAL_RAM" -ge 8 ]; then
    echo "   ⚠️  Adequate. Allocate 4GB to the VM, close other apps"
else
    echo "   ❌ Low RAM. VM may be slow with <8GB total"
fi

# Check available disk space
echo "   💿 Checking disk space..."
AVAILABLE_SPACE=$(df -h ~ | tail -1 | awk '{print $4}')
echo "   📊 Available space: $AVAILABLE_SPACE"
echo

# Check project files
echo "4. Checking AI-Native Linux OS files..."
if [ -f "requirements.txt" ]; then
    echo "   ✅ Project files found in current directory"
    echo "   📋 Requirements file: $(wc -l < requirements.txt) packages"
    
    if [ -f "quick_test.sh" ]; then
        echo "   ✅ Quick test script available"
    fi
    
    if [ -d "src" ]; then
        echo "   ✅ Source code directory found"
        echo "   📁 Components: $(ls src/ | wc -l | tr -d ' ') modules"
    fi
else
    echo "   ❌ Project files not found in current directory"
    echo "   💡 Make sure you're in the ai-native-linux-os directory"
fi
echo

# Provide next steps
echo "🚀 Next Steps:"
echo "=============="

if [ -f "$ISO_PATH" ] && [ "$ACTUAL_SIZE" -gt 1000000000 ]; then
    echo "✅ You're ready to proceed! Follow these steps:"
    echo
    echo "1. Open UTM from Applications"
    echo "2. Click 'Create a New Virtual Machine'"
    echo "3. Select 'Virtualize' → 'Linux'"
    echo "4. Use this ISO: $ISO_PATH"
    echo "5. Configure:"
    echo "   - RAM: 6-8GB (recommended for your ${TOTAL_RAM}GB system)"
    echo "   - CPU: 4-6 cores"
    echo "   - Storage: 60GB"
    echo "   - Network: Shared with port forwarding (8080→8080, 2222→22)"
    echo
    echo "📖 Full instructions: see UTM_SETUP_GUIDE.md"
else
    echo "⏳ Wait for Ubuntu ISO download to complete, then run this script again"
    echo "📥 Download progress: check ~/Downloads/ folder"
    echo
    echo "💡 While waiting, you can:"
    echo "   - Review the setup guide: UTM_SETUP_GUIDE.md"
    echo "   - Test components locally: ./quick_test.sh"
fi
echo

echo "📚 Documentation:"
echo "   - Full setup guide: UTM_SETUP_GUIDE.md"
echo "   - Testing guide: test_on_mac.md"
echo "   - Quick demo: ./quick_test.sh"
echo
echo "🎯 Goal: Get your AI-native Linux OS running in UTM with full desktop environment!" 