# Claude Development Guidelines for Hexcrawl Project

## Project Architecture Overview

This is a **sophisticated multi-client hexcrawl system** for tabletop RPG exploration with:

**🏗️ Core Architecture:**
- **Client-Server Model** with Flask backend (app.py - 49KB)
- **Multiple frontends**: Obsidian plugin, web interface, desktop apps
- **Real-time multiplayer** via SocketIO
- **Dual authentication**: JWT (API clients) + Sessions (web interface)

**🎯 Key Components:**
- **Backend**: Flask server with extensive middleware (CORS, rate limiting, security)
- **Frontend**: TypeScript Obsidian plugin with custom hex map renderer
- **Core Engine**: Hex map system with cube coordinates (q,r,s)
- **Generation**: Multiple terrain/biome generators + AI descriptions via Ollama
- **Data Layer**: SQLite database + JSON map persistence
- **Security**: Comprehensive protection (JWT, CSRF, rate limiting, input validation)

**🎮 Features:**
- **10+ specialized generators** for different use cases
- **Minecraft-style biome generation** with 6D noise
- **Export capabilities** (text-mapper, JSON, images)
- **Campaign integration** via Obsidian notes

## Critical Build Process - MUST FOLLOW

**⚠️ IMPORTANT: When modifying TypeScript files in the Obsidian plugin, you MUST compile and deploy the changes!**

### Plugin Development Workflow

1. **Edit TypeScript Files**: Make changes to files in `obsidian-hexcrawl-plugin/src/`
2. **Build the Plugin**: Always run the build command after making changes:
   ```bash
   cd obsidian-hexcrawl-plugin
   npm run build
   ```
3. **Reload Plugin**: Tell the user to disable and re-enable the plugin in Obsidian settings

### Build Commands Reference

- `npm run dev` - Development build with watching
- `npm run build` - Production build (TypeScript → JavaScript)
- `npm run deploy` - Same as build (no longer copies files since we're working directly in the plugin directory)

### Server Restart Requirements

**⚠️ IMPORTANT: When modifying Python files in the backend, you MUST restart the Flask server!**

1. **After Backend Changes**: Any changes to `app.py`, `auth.py`, or other Python files require server restart
2. **Kill Current Server**: Stop the running Flask server process
3. **Restart Server**: Run `python app.py` to start the server with new changes
4. **Note**: The Flask server does NOT automatically reload changes in production mode

### Common Mistakes to Avoid

❌ **NEVER** assume TypeScript changes are automatically active
❌ **NEVER** tell user to "reload plugin" without building first
❌ **NEVER** expect debugging output from uncompiled TypeScript

✅ **ALWAYS** run `npm run build` after TypeScript changes
✅ **ALWAYS** verify build succeeded before asking user to test  

### Project Structure

```
hexcrawl/
├── obsidian-hexcrawl-plugin/          # Obsidian plugin source
│   ├── src/                           # TypeScript source files
│   │   ├── main.ts                    # Main plugin file
│   │   ├── authView.ts                # Authentication UI
│   │   ├── hexcrawlView.ts            # Main game view
│   │   └── types.ts                   # Type definitions
│   ├── main.js                        # Compiled JavaScript (generated)
│   └── package.json                   # Build scripts
├── app.py                             # Flask server
├── auth.py                            # Authentication logic
└── requirements.txt                   # Python dependencies
```

### Development Notes

- **Plugin Files**: Edit `.ts` files in `src/`, compiled to `main.js`
- **Server Files**: Edit `.py` files directly, restart server to apply changes
- **Database**: SQLite database created automatically
- **CORS**: Configured for local development

### Authentication Architecture

- **JWT Tokens**: Bearer tokens in Authorization header
- **Token Storage**: Base64 encoded in plugin settings
- **Token Persistence**: Restored on plugin reload via `initializeApiClient()`
- **Failsafe**: Automatic token restoration if lost during reinitialization

## Testing Checklist

When making plugin changes:

1. ✅ Build TypeScript: `npm run build`
2. ✅ Reload plugin in Obsidian settings
3. ✅ Test functionality
4. ✅ Check browser console for logs
5. ✅ Verify server logs for API calls

## Server Commands

- **Start Server**: `python app.py`
- **Background Server Check**: Look for multiple instances in task manager
- **Kill Background Tasks**: Use Task Manager or `taskkill` commands

## Debugging

- **Plugin Logs**: Browser Developer Tools → Console
- **Server Logs**: Terminal running `python app.py`
- **Network Requests**: Browser Developer Tools → Network tab
- **Authentication**: Check `/api/auth/session-debug` endpoint

## Architecture Notes for Development

**🔄 Data Flow:**
```
Obsidian Plugin → JWT Auth → Flask API → Core Engine → Database/Files
     ↓              ↓           ↓           ↓            ↓
TypeScript    → Axios Client → Routes → HexMap/Gen → SQLite/JSON
```

**📁 Key Files by Function:**
- **API Endpoints**: `app.py` (main server)
- **Authentication**: `auth.py` (JWT + sessions)
- **Map Logic**: `core/map.py` (HexMap class)
- **Generation**: `generation/manager.py` (orchestrates all generators)
- **Plugin Main**: `obsidian-hexcrawl-plugin/src/main.ts`
- **Plugin Views**: `src/authView.ts`, `src/hexcrawlView.ts`

**🔧 Development Patterns:**
- **Hex Coordinates**: Always use cube coordinates (q,r,s) internally
- **Authentication**: JWT tokens in `Bearer ${token}` format for API
- **Error Handling**: Server returns JSON error responses with status codes
- **Real-time Updates**: SocketIO for multiplayer synchronization
- **Map Persistence**: JSON files for map data, SQLite for user/session data

**⚠️ Common Pitfalls:**
- **Token Loss**: API client reinitialization can wipe JWT tokens (use failsafe restoration)
- **Coordinate Systems**: Mix of offset (x,y) and cube (q,r,s) - be consistent
- **Build Process**: TypeScript changes invisible until `npm run build && npm run deploy`
- **Multiple Generators**: 10+ generators with similar code - choose the right one

---

**Remember: TypeScript changes are NEVER active until built!**