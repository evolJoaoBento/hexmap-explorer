# Hex Map Explorer Refactoring Plan
## Modular & System-Agnostic Architecture

### Overview
Transform the monolithic 2000+ line hex_map_explorer.py into a modular, system-agnostic architecture that supports multiple TTRPG systems while maintaining all current features.

---

## Phase 1: Core Refactoring (Week 1-2)
**Goal**: Break down the monolithic file into logical modules without changing functionality

### Tasks:
- [ ] **1.1 Create Core Directory Structure**
  ```
  hexcrawl/
  ├── engine/
  │   ├── world/
  │   ├── entities/
  │   ├── mechanics/
  │   └── events/
  ├── systems/
  │   ├── core/
  │   └── rulesets/
  └── modules/
  ```

- [ ] **1.2 Extract Domain Models**
  - [ ] Move `Hex` class to `engine/world/hex.py`
  - [ ] Create `engine/world/terrain.py` for terrain definitions
  - [ ] Move coordinate helpers to `engine/world/coordinates.py`
  - [ ] Extract map logic to `engine/world/map.py`

- [ ] **1.3 Separate Business Logic**
  - [ ] Move `TravelSystem` to `modules/travel/travel_service.py`
  - [ ] Extract movement calculations to `engine/mechanics/movement.py`
  - [ ] Create `engine/mechanics/exploration.py` for visibility logic
  - [ ] Move time tracking to `engine/mechanics/time.py`

- [ ] **1.4 Isolate Rendering**
  - [ ] Move `HexMapRenderer` to `rendering/pipeline/renderer.py`
  - [ ] Extract `PixelArtSprites` to `rendering/sprites/generator.py`
  - [ ] Create layer system in `rendering/pipeline/layers/`

- [ ] **1.5 Separate External Services**
  - [ ] Move `OllamaClient` to `api/implementations/ollama.py`
  - [ ] Extract `GenerationManager` to `modules/generation/manager.py`
  - [ ] Create abstract AI interface in `api/interfaces/ai_provider.py`

---

## Phase 2: System Abstraction (Week 3-4)
**Goal**: Make the game engine system-agnostic

### Tasks:
- [ ] **2.1 Create System Interfaces**
  ```python
  # systems/core/interfaces.py
  class IRuleset:
      def get_movement_cost(terrain, transport)
      def calculate_movement_points(party, pace)
      def apply_condition(character, condition)
      def get_rest_recovery(rest_type)
  ```

- [ ] **2.2 Extract D&D 5e Rules**
  - [ ] Create `systems/rulesets/dnd5e/ruleset.json`
  - [ ] Move D&D-specific constants to configuration
  - [ ] Implement `systems/rulesets/dnd5e/rules.py`
  - [ ] Extract ranger/navigator/outlander to D&D module

- [ ] **2.3 Create Generic Ruleset**
  - [ ] Implement `systems/rulesets/generic/ruleset.json`
  - [ ] Define basic movement and rest mechanics
  - [ ] Remove system-specific terminology

- [ ] **2.4 Build Ruleset Loader**
  - [ ] Create `systems/loader.py` for dynamic loading
  - [ ] Implement `systems/core/registry.py` for ruleset management
  - [ ] Add ruleset switching capability

---

## Phase 3: Modularization (Week 5-6)
**Goal**: Create pluggable feature modules

### Tasks:
- [ ] **3.1 Implement Event System**
  ```python
  # engine/events/event_bus.py
  class EventBus:
      def emit(event)
      def subscribe(event_type, handler)
  ```

- [ ] **3.2 Create Module System**
  - [ ] Define module interface in `modules/base.py`
  - [ ] Implement module loader in `modules/loader.py`
  - [ ] Create module registry in `modules/registry.py`

- [ ] **3.3 Convert Features to Modules**
  - [ ] Travel module with own UI panel
  - [ ] Generation module (AI descriptions)
  - [ ] Party management module
  - [ ] Save/Load module

- [ ] **3.4 Implement UI Component System**
  - [ ] Create `ui/framework/panel.py` base class
  - [ ] Build `ui/framework/window.py` manager
  - [ ] Implement `ui/panels/` for each module
  - [ ] Add `ui/adapters/system_ui.py` for system-specific UI

---

## Phase 4: Enhanced Features (Week 7-8)
**Goal**: Add advanced capabilities

### Tasks:
- [ ] **4.1 Plugin System**
  - [ ] Create `plugins/manager.py` for discovery
  - [ ] Define plugin hooks in `plugins/hooks.py`
  - [ ] Add plugin configuration system

- [ ] **4.2 System Builder Tool**
  - [ ] Create `apps/system_builder.py`
  - [ ] Build ruleset editor UI
  - [ ] Add validation for custom rulesets

- [ ] **4.3 Theme Support**
  - [ ] Create `rendering/themes/` structure
  - [ ] Implement theme loader
  - [ ] Add theme switching capability

- [ ] **4.4 Settings Migration**
  - [ ] Create new settings structure
  - [ ] Build migration tool for old saves
  - [ ] Update configuration system

---

## File Migration Map

### From `hex_map_explorer.py` (2006 lines) to:

| Original Section | Lines | New Location | Status |
|-----------------|-------|--------------|---------|
| Constants (TERRAIN_TYPES, etc) | 1-84 | `systems/rulesets/dnd5e/data/` | ⏳ |
| Hex class | 85-106 | `engine/world/hex.py` | ⏳ |
| TravelSystem class | 107-257 | `modules/travel/travel_service.py` | ⏳ |
| PixelArtSprites class | 258-495 | `rendering/sprites/generator.py` | ⏳ |
| OllamaClient class | 496-599 | `api/implementations/ollama.py` | ⏳ |
| GenerationManager class | 600-659 | `modules/generation/manager.py` | ⏳ |
| HexMap class | 660-855 | `engine/world/map.py` | ⏳ |
| HexMapRenderer class | 856-1544 | `rendering/pipeline/renderer.py` | ⏳ |
| HexMapExplorer class | 1545-2006 | `apps/explorer.py` | ⏳ |

---

## Testing Strategy

### Unit Tests
- [ ] Test each module independently
- [ ] Mock system interfaces for testing
- [ ] Test event system communication

### Integration Tests
- [ ] Test module interactions
- [ ] Test ruleset switching
- [ ] Test save/load with different systems

### Regression Tests
- [ ] Ensure D&D 5e functionality unchanged
- [ ] Verify all current features work
- [ ] Test backward compatibility

---

## Migration Steps

### Step 1: Parallel Development
1. Keep `hex_map_explorer.py` working
2. Build new structure alongside
3. Gradually move functionality

### Step 2: Feature Parity
1. Test each migrated feature
2. Ensure identical behavior
3. Document any changes

### Step 3: Cutover
1. Switch main.py to use new structure
2. Keep old file as backup
3. Run extensive testing

### Step 4: Cleanup
1. Remove old monolithic file
2. Update documentation
3. Create migration guide

---

## Success Criteria

- [ ] All current features work identically
- [ ] Can switch between D&D 5e and generic rulesets
- [ ] Each module under 300 lines
- [ ] No circular dependencies
- [ ] 80%+ test coverage
- [ ] Load time under 2 seconds
- [ ] Memory usage not increased by >20%

---

## Configuration Examples

### D&D 5e Ruleset (`systems/rulesets/dnd5e/ruleset.json`)
```json
{
  "id": "dnd5e",
  "name": "Dungeons & Dragons 5th Edition",
  "version": "1.0.0",
  "movement": {
    "base_speed": 30,
    "pace_multipliers": {
      "slow": 0.67,
      "normal": 1.0,
      "fast": 1.33
    },
    "terrain_difficulty": {
      "easy": 1.0,
      "moderate": 1.5,
      "difficult": 2.0,
      "impassable": 999
    }
  },
  "conditions": [
    {
      "id": "exhaustion",
      "levels": 6,
      "effects": ["speed_reduction", "disadvantage", "death"]
    }
  ],
  "party_roles": [
    {
      "id": "ranger",
      "benefits": ["favored_terrain", "natural_explorer"]
    },
    {
      "id": "navigator",
      "benefits": ["cant_get_lost", "bonus_movement"]
    }
  ]
}
```

### Generic Ruleset (`systems/rulesets/generic/ruleset.json`)
```json
{
  "id": "generic",
  "name": "Generic TTRPG System",
  "version": "1.0.0",
  "movement": {
    "base_units_per_period": 8,
    "travel_speeds": {
      "cautious": 6,
      "standard": 8,
      "rushed": 10
    },
    "terrain_modifiers": {
      "clear": 1.0,
      "rough": 1.5,
      "very_rough": 2.0,
      "blocked": 999
    }
  },
  "conditions": [
    {
      "id": "fatigued",
      "effect": "reduced_movement"
    },
    {
      "id": "rested",
      "effect": "restored_movement"
    }
  ]
}
```

---

## Module Structure Example

### Travel Module (`modules/travel/`)
```python
# __init__.py
from .travel_service import TravelService
from .travel_ui import TravelPanel

class TravelModule:
    def __init__(self):
        self.service = TravelService()
        self.panel = TravelPanel()
    
    def on_load(self, engine):
        engine.register_service('travel', self.service)
        engine.ui.register_panel(self.panel)
    
    def on_ruleset_change(self, ruleset):
        self.service.set_ruleset(ruleset)
        self.panel.update_display(ruleset)
```

---

## Next Steps

1. **Review this plan** and adjust based on priorities
2. **Set up development branch** for refactoring
3. **Start with Phase 1.1** - Create directory structure
4. **Begin extracting** smallest, most independent components first
5. **Test continuously** to ensure no regression

---

## Notes

- Keep backwards compatibility until Phase 4
- Document all breaking changes
- Create examples for each new system
- Consider community feedback during development
- Plan for internationalization (i18n) support

---

*Last Updated: [Current Date]*
*Status: Ready to Begin*