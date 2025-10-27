"""
Test biome generation to isolate crashes
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_import():
    """Test if we can import the biome generator"""
    try:
        from generation.minecraft_biomes import MinecraftBiomeGenerator
        print("[OK] Import successful")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        return False

def test_generator_creation():
    """Test creating a generator instance"""
    try:
        from generation.minecraft_biomes import MinecraftBiomeGenerator
        generator = MinecraftBiomeGenerator(12345)
        print("[OK] Generator creation successful")
        return generator
    except Exception as e:
        print(f"[FAIL] Generator creation failed: {e}")
        return None

def test_single_biome():
    """Test generating a single biome"""
    try:
        from generation.minecraft_biomes import MinecraftBiomeGenerator
        generator = MinecraftBiomeGenerator(12345)
        biome = generator.select_biome(0, 0, 0)
        print(f"[OK] Single biome generation successful: {biome}")
        return True
    except Exception as e:
        print(f"[FAIL] Single biome generation failed: {e}")
        return False

def test_multiple_biomes():
    """Test generating multiple biomes"""
    try:
        from generation.minecraft_biomes import MinecraftBiomeGenerator
        generator = MinecraftBiomeGenerator(12345)
        
        for i in range(10):
            biome = generator.select_biome(i, 0, -i)
            print(f"  Hex {i}: {biome}")
        
        print("[OK] Multiple biome generation successful")
        return True
    except Exception as e:
        print(f"[FAIL] Multiple biome generation failed: {e}")
        return False

def main():
    print("=== BIOME GENERATION TEST ===")
    
    if not test_basic_import():
        return
    
    if not test_generator_creation():
        return
    
    if not test_single_biome():
        return
    
    if not test_multiple_biomes():
        return
    
    print("\n[OK] All tests passed! Biome generation is working.")

if __name__ == "__main__":
    main()