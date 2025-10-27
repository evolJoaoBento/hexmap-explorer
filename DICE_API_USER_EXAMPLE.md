# Dice Roll API - User Example Scenarios

## Scenario 1: D&D Player During Combat

### Context
Sarah is playing a Fighter in a D&D 5e game. She's in combat and needs to make various rolls.

### 1. Attack Roll with Longsword

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "d20+7",
    "description": "Longsword attack",
    "campaign_id": "curse-of-strahd",
    "session_id": "session-12"
  }'
```

**Response:**
```json
{
  "id": 42,
  "expression": "d20+7",
  "raw_rolls": {"1d20": [15]},
  "modifiers": [["+", 7]],
  "total": 22,
  "is_critical": false,
  "is_fumble": false,
  "breakdown": "1d20=[15]=15 +7 = 22"
}
```
*Sarah hits with a 22!*

### 2. Rolling Damage

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "1d8+5",
    "description": "Longsword damage",
    "campaign_id": "curse-of-strahd"
  }'
```

**Response:**
```json
{
  "id": 43,
  "total": 11,
  "breakdown": "1d8=[6]=6 +5 = 11"
}
```
*11 slashing damage!*

### 3. Critical Hit!

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "d20+7",
    "description": "Longsword attack - Action Surge"
  }'
```

**Response:**
```json
{
  "id": 44,
  "expression": "d20+7",
  "raw_rolls": {"1d20": [20]},
  "total": 27,
  "is_critical": true,
  "is_fumble": false,
  "breakdown": "1d20=[20]=20 +7 = 27"
}
```
*CRITICAL HIT! Now rolling double damage dice:*

**Critical Damage Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "2d8+5",
    "description": "Critical hit damage!"
  }'
```

**Response:**
```json
{
  "id": 45,
  "total": 18,
  "breakdown": "2d8=[7,6]=13 +5 = 18"
}
```

## Scenario 2: Rolling for Stats (Character Creation)

### Rolling 4d6 drop lowest for each ability score

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "4d6kh3",
    "count": 6,
    "description": "Rolling ability scores"
  }'
```

**Response:**
```json
{
  "count": 6,
  "expression": "4d6kh3",
  "results": [
    {"id": 46, "total": 15, "breakdown": "4d6kh3=[6,5,4,2]=15 = 15"},
    {"id": 47, "total": 13, "breakdown": "4d6kh3=[5,4,4,1]=13 = 13"},
    {"id": 48, "total": 16, "breakdown": "4d6kh3=[6,6,4,3]=16 = 16"},
    {"id": 49, "total": 11, "breakdown": "4d6kh3=[4,4,3,2]=11 = 11"},
    {"id": 50, "total": 14, "breakdown": "4d6kh3=[5,5,4,3]=14 = 14"},
    {"id": 51, "total": 12, "breakdown": "4d6kh3=[5,4,3,1]=12 = 12"}
  ],
  "summary": {
    "total": 81,
    "average": 13.5,
    "min": 11,
    "max": 16
  }
}
```
*Stats: STR 16, DEX 15, CON 14, INT 13, WIS 12, CHA 11*

## Scenario 3: Using Templates (Authenticated User)

### First, authenticate to get a token
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "sarah", "password": "password123"}'
```

Response includes JWT token: `eyJhbGciOiJIUzI1NiIs...`

### Create a Template for Sneak Attack

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/templates \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sneak Attack (Level 5)",
    "expression": "3d6",
    "description": "Rogue sneak attack damage at level 5",
    "category": "attack",
    "is_public": false
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "Sneak Attack (Level 5)",
  "expression": "3d6",
  "category": "attack",
  "created_at": "2024-01-25T15:30:00"
}
```

### Use the Template

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/templates/1/roll \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"campaign_id": "curse-of-strahd"}'
```

**Response:**
```json
{
  "id": 52,
  "template_name": "Sneak Attack (Level 5)",
  "expression": "3d6",
  "total": 11,
  "breakdown": "3d6=[4,3,4]=11 = 11"
}
```

## Scenario 4: Advantage/Disadvantage

### Rolling with Advantage (Rogue hiding)

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "d20+9",
    "advantage": true,
    "description": "Stealth check with advantage"
  }'
```

**Response:**
```json
{
  "id": 53,
  "expression": "d20+9",
  "raw_rolls": {"2d20kh1": [17, 8]},
  "total": 26,
  "breakdown": "2d20kh1=[17,8]=17 +9 = 26",
  "advantage": true
}
```
*Rolled 8 and 17, keeping the 17 for a total of 26!*

### Rolling with Disadvantage (Poisoned)

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "d20+5",
    "disadvantage": true,
    "description": "Attack while poisoned"
  }'
```

**Response:**
```json
{
  "id": 54,
  "expression": "d20+5",
  "raw_rolls": {"2d20kl1": [14, 7]},
  "total": 12,
  "breakdown": "2d20kl1=[14,7]=7 +5 = 12",
  "disadvantage": true
}
```
*Rolled 14 and 7, forced to take the 7 for a total of 12*

## Scenario 5: Complex Spell - Fireball

### Rolling 8d6 fire damage

**Request:**
```bash
curl -X POST http://localhost:5000/api/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "8d6",
    "description": "Fireball damage (3rd level)"
  }'
```

**Response:**
```json
{
  "id": 55,
  "expression": "8d6",
  "raw_rolls": {"8d6": [4, 6, 3, 5, 2, 6, 4, 3]},
  "total": 33,
  "breakdown": "8d6=[4,6,3,5,2,6,4,3]=33 = 33"
}
```
*33 fire damage to all creatures in the area!*

## Scenario 6: Checking Statistics

### View your roll statistics

**Request:**
```bash
curl -X GET http://localhost:5000/api/dice/statistics \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response:**
```json
{
  "stats": {
    "user_id": 1,
    "total_rolls": 247,
    "total_d20_rolls": 89,
    "critical_count": 4,
    "fumble_count": 3,
    "average_roll": 12.7,
    "highest_roll": 38,
    "lowest_roll": 2,
    "dice_distribution": {
      "d20": 89,
      "d6": 124,
      "d8": 22,
      "d10": 8,
      "d12": 4
    },
    "last_updated": "2024-01-25T16:45:00"
  }
}
```

## Scenario 7: Interactive Python Script

```python
import requests
import json

class DiceRoller:
    def __init__(self, base_url="http://localhost:5000", token=None):
        self.base_url = base_url
        self.token = token
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def roll(self, expression, description=""):
        response = requests.post(
            f"{self.base_url}/api/dice/roll",
            headers=self.headers,
            json={
                "expression": expression,
                "description": description
            }
        )
        return response.json()

    def attack_roll(self, bonus, advantage=False):
        """Make an attack roll with optional advantage"""
        result = requests.post(
            f"{self.base_url}/api/dice/roll",
            headers=self.headers,
            json={
                "expression": f"d20+{bonus}",
                "advantage": advantage,
                "description": "Attack roll"
            }
        ).json()

        if result.get('is_critical'):
            print("⚔️ CRITICAL HIT!")
        elif result.get('is_fumble'):
            print("💥 CRITICAL MISS!")

        return result

# Usage
roller = DiceRoller()

# Make an attack
attack = roller.attack_roll(bonus=7, advantage=False)
print(f"Attack roll: {attack['total']} ({attack['breakdown']})")

if attack['total'] >= 15:  # Hit AC 15
    damage = roller.roll("1d8+5", "Longsword damage")
    print(f"Damage: {damage['total']} ({damage['breakdown']})")
else:
    print("Miss!")

# Roll initiative
initiative = roller.roll("d20+3", "Initiative")
print(f"Initiative: {initiative['total']}")
```

## Scenario 8: Web Application Integration

```javascript
// JavaScript/TypeScript in a web app

class DiceAPI {
    constructor(baseUrl = 'http://localhost:5000') {
        this.baseUrl = baseUrl;
        this.token = localStorage.getItem('jwt_token');
    }

    async roll(expression, options = {}) {
        const response = await fetch(`${this.baseUrl}/api/dice/roll`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(this.token && { 'Authorization': `Bearer ${this.token}` })
            },
            body: JSON.stringify({
                expression,
                ...options
            })
        });
        return response.json();
    }

    async rollWithAdvantage(modifier) {
        return this.roll(`d20+${modifier}`, {
            advantage: true,
            description: 'Roll with advantage'
        });
    }
}

// Usage in game
const dice = new DiceAPI();

// Player clicks "Roll Attack" button
async function onAttackClick() {
    const result = await dice.roll('d20+7', {
        description: 'Longsword attack',
        campaign_id: currentCampaign.id
    });

    // Update UI
    displayRoll(result);

    if (result.is_critical) {
        showCriticalAnimation();
        // Auto-roll critical damage
        const critDamage = await dice.roll('2d8+5', {
            description: 'Critical damage!'
        });
        displayDamage(critDamage);
    } else if (result.total >= targetAC) {
        // Normal hit - roll damage
        const damage = await dice.roll('1d8+5', {
            description: 'Longsword damage'
        });
        displayDamage(damage);
    } else {
        showMissAnimation();
    }
}

// Display function
function displayRoll(result) {
    const rollDisplay = document.getElementById('roll-result');
    rollDisplay.innerHTML = `
        <div class="roll-result ${result.is_critical ? 'critical' : ''}">
            <h3>${result.total}</h3>
            <p>${result.breakdown}</p>
            ${result.is_critical ? '<span class="badge">CRIT!</span>' : ''}
            ${result.is_fumble ? '<span class="badge">FUMBLE!</span>' : ''}
        </div>
    `;
}
```

## Scenario 9: Obsidian Plugin Integration

```typescript
// In Obsidian plugin
class DiceRollCommand {
    constructor(apiClient) {
        this.api = apiClient;
    }

    async executeRoll(expression: string) {
        try {
            const result = await this.api.post('/api/dice/roll', {
                expression: expression,
                source: 'obsidian-plugin',
                campaign_id: this.getCurrentCampaignId()
            });

            // Create markdown note with result
            this.createRollNote(result);

            // Show notification
            new Notice(`Rolled ${result.total}!`);

            return result;
        } catch (error) {
            new Notice(`Roll failed: ${error.message}`);
        }
    }

    createRollNote(result: any) {
        const content = `
## Dice Roll Result

**Expression:** \`${result.expression}\`
**Result:** **${result.total}**
**Breakdown:** ${result.breakdown}
**Time:** ${new Date().toLocaleString()}

${result.is_critical ? '🎯 **CRITICAL HIT!**' : ''}
${result.is_fumble ? '💥 **CRITICAL MISS!**' : ''}

---
Tags: #dice-roll #session-${this.getCurrentSession()}
`;

        // Add to current note or create new one
        this.app.vault.create(
            `Rolls/${new Date().toISOString()}.md`,
            content
        );
    }
}
```

## Common Patterns

### 1. Save Favorite Rolls as Templates
Users create templates for frequently used rolls (attacks, saves, skills)

### 2. Session Tracking
All rolls include campaign_id and session_id for later review

### 3. Advantage/Disadvantage Shortcuts
Quick buttons/commands for common D&D 5e mechanics

### 4. Damage Cascades
Attack roll → if hit → damage roll → if crit → extra damage

### 5. Bulk Rolling
Initiative for multiple enemies, mass saving throws

### 6. Statistical Analysis
Track lucky/unlucky streaks, most common rolls, crit rates

This is how real users interact with the dice API - from simple command-line rolls to fully integrated game applications!