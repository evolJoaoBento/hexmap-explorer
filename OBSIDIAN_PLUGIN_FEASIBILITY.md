# Revised Feasibility Assessment: Hexcrawl Obsidian Client Plugin

## **Difficulty Rating: MODERATE (5-6/10)**

This significantly simplifies the architecture! You want to keep the existing Flask server and create an Obsidian plugin as an **alternative client interface**.

### **Revised Architecture**

**Current**: Web Browser ↔ Flask Server (app.py)  
**Proposed**: Obsidian Plugin ↔ Flask Server (app.py) + Obsidian Vault Integration

### **Technical Approach**

**1. Plugin as HTTP Client (LOW-MODERATE COMPLEXITY)**
- Plugin makes HTTP requests to existing Flask API endpoints
- Reuse existing authentication system  
- Keep all generation logic server-side
- **Advantage**: Minimal server changes needed

**2. Obsidian-Specific Enhancements (MODERATE COMPLEXITY)**
- **Hex-to-Note Linking**: Each hex can reference `[[Hex 0101 - Forest]]` notes
- **Auto-note Creation**: Plugin creates/updates note files for explored hexes
- **Embedded Maps**: Display hex maps within notes using existing text-mapper plugin
- **Bidirectional Sync**: Changes in notes update hex descriptions on server

**3. Canvas Integration (MODERATE COMPLEXITY)**
- Use Obsidian Canvas API to display interactive hex map
- Click hex → open linked note
- Canvas nodes represent hexes with terrain icons
- Player position highlighted on canvas

### **Implementation Plan**

**Phase 1: Basic HTTP Client (1-2 weeks)**
- TypeScript plugin calling existing Flask endpoints:
  - `/api/new_game` 
  - `/api/get_map`
  - `/api/move`
  - `/api/generate_description`
- Simple UI panel showing hex data

**Phase 2: Obsidian Integration (2-3 weeks)**  
- Auto-create notes for explored hexes
- Format: `Hex 0101 - Forest.md` with hex description
- Plugin updates note content when hex descriptions change
- Wikilinks between hex notes

**Phase 3: Visual Interface (2-3 weeks)**
- Canvas-based hex map display
- Click-to-explore functionality
- Player position indicator
- Integration with existing text-mapper plugin for map rendering

**Phase 4: Advanced Features (2-4 weeks)**
- Real-time updates via polling or WebSocket connection
- Multi-player position display
- Master session controls (if authenticated as GM)
- Hex editing from Obsidian notes back to server

### **Key Advantages of This Approach**

1. **Minimal Server Changes**: Flask app continues working as-is
2. **Leverage Existing**: All generation, AI, and game logic stays server-side  
3. **Obsidian Native**: Full integration with vault, links, and note-taking
4. **Progressive Enhancement**: Can build incrementally
5. **Multi-Client**: Web browser and Obsidian can work simultaneously

### **Server Modifications Needed**

**Minor API Enhancements**:
- Add CORS headers for Obsidian plugin requests
- Optional: Add endpoints for bulk hex data export
- Optional: Webhook for real-time hex updates

**Example new endpoint**:
```python
@app.route('/api/obsidian/hex_notes', methods=['GET'])
def get_hex_notes():
    """Get hex data formatted for Obsidian note creation"""
```

### **Text-Mapper Integration**

**Simplified Approach**:
- Keep your current hex format on server
- Plugin converts to text-mapper format for display
- Use existing `hex_to_textmapper.py` logic in TypeScript
- Render maps using existing Obsidian text-mapper plugin

### **Timeline Estimate**

- **Basic HTTP client**: 1-2 weeks
- **Note integration**: 2-3 weeks  
- **Canvas/visual interface**: 2-3 weeks
- **Polish & advanced features**: 2-4 weeks

**Total: 7-12 weeks** (much more reasonable!)

### **Technical Requirements**

- TypeScript/JavaScript for plugin
- HTTP client (fetch API)
- Obsidian Plugin API knowledge
- Integration with existing text-mapper plugin
- Canvas API for interactive maps

This approach gives you the best of both worlds: robust server-side logic with Obsidian's powerful note-taking and linking capabilities.