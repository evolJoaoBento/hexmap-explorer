"""
Test script for Minecraft-style biome generation
"""
from generation.minecraft_biomes import MinecraftBiomeGenerator

def test_biome_generation():
    """Test the biome generation system"""
    print("Testing Minecraft-style biome generation...")
    
    # Create generator with test seed
    generator = MinecraftBiomeGenerator(seed=12345)
    
    # Test biome generation in a 15x15 hex area
    print("\nBiome map (15x15 area around origin):")
    print("   ", end="")
    for q in range(-7, 8):
        print(f"{q:2}", end="")
    print()
    
    for r in range(-7, 8):
        print(f"{r:2} ", end="")
        for q in range(-7, 8):
            s = -q - r
            biome = generator.select_biome(q, r, s)
            # Use first letter of biome for compact display
            print(f"{biome[0].upper()}", end=" ")
        print()
    
    # Show legend
    print("\nLegend:")
    biomes_found = set()
    for r in range(-7, 8):
        for q in range(-7, 8):
            s = -q - r
            biome = generator.select_biome(q, r, s)
            biomes_found.add(biome)
    
    for biome in sorted(biomes_found):
        print(f"  {biome[0].upper()} = {biome}")
    
    # Test parameter generation for a few specific hexes
    print(f"\nDetailed parameters for hex (0,0,0):")
    params = generator.get_biome_parameters(0, 0, 0)
    print(f"  Temperature: {params.temperature:.3f}")
    print(f"  Humidity: {params.humidity:.3f}")
    print(f"  Continentalness: {params.continentalness:.3f}")
    print(f"  Erosion: {params.erosion:.3f}")
    print(f"  Weirdness: {params.weirdness:.3f}")
    print(f"  Selected biome: {generator.select_biome(0, 0, 0)}")

if __name__ == "__main__":
    test_biome_generation()