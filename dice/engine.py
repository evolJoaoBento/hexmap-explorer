"""
Dice Roll Engine
Handles parsing and evaluation of dice roll expressions
"""

import re
import random
import operator
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

@dataclass
class RollResult:
    """Container for dice roll results"""
    expression: str
    raw_rolls: Dict[str, List[int]]
    modifiers: List[Tuple[str, int]]
    total: int
    is_critical: bool = False
    is_fumble: bool = False
    breakdown: str = ""

    def to_dict(self):
        return {
            'expression': self.expression,
            'raw_rolls': self.raw_rolls,
            'modifiers': self.modifiers,
            'total': self.total,
            'is_critical': self.is_critical,
            'is_fumble': self.is_fumble,
            'breakdown': self.breakdown
        }

class DiceRollEngine:
    """
    Parses and evaluates dice roll expressions
    Supports:
    - Standard dice notation (3d6, d20)
    - Modifiers (+5, -2)
    - Complex expressions (3d6+2d8+5)
    - Advantage/Disadvantage
    - Keep highest/lowest (4d6kh3, 2d20kl1)
    - Exploding dice (3d6!)
    - Rerolls (4d6r1)
    """

    # Pattern for dice expressions
    DICE_PATTERN = re.compile(
        r'(\d*)d(\d+)(?:(kh|kl|k|dh|dl|d)(\d+))?(?:(r)(\d+))?(?:(!))?',
        re.IGNORECASE
    )

    # Pattern for modifiers
    MOD_PATTERN = re.compile(r'([+-])(\d+)')

    def __init__(self, seed: Optional[int] = None):
        """Initialize the dice engine with optional seed for testing"""
        if seed is not None:
            random.seed(seed)

    def roll(self, expression: str, advantage: bool = False, disadvantage: bool = False) -> RollResult:
        """
        Roll dice based on expression

        Args:
            expression: Dice roll expression (e.g., "3d6+2")
            advantage: Roll with advantage (for d20 rolls)
            disadvantage: Roll with disadvantage (for d20 rolls)

        Returns:
            RollResult object with all roll details
        """
        expression = expression.strip().lower()
        original_expression = expression

        raw_rolls = {}
        modifiers = []
        total = 0
        breakdown_parts = []
        has_d20 = 'd20' in expression
        is_critical = False
        is_fumble = False

        # Handle advantage/disadvantage for d20 rolls
        if has_d20 and (advantage or disadvantage):
            expression = self._handle_advantage_disadvantage(expression, advantage)

        # Find all dice expressions
        dice_matches = list(self.DICE_PATTERN.finditer(expression))

        # Process each dice expression
        for match in dice_matches:
            count = int(match.group(1) or 1)
            sides = int(match.group(2))
            keep_drop_type = match.group(3)
            keep_drop_count = int(match.group(4)) if match.group(4) else None
            reroll_below = int(match.group(6)) if match.group(6) else None
            exploding = bool(match.group(7))

            dice_key = f"{count}d{sides}"
            rolls = self._roll_dice(count, sides, reroll_below, exploding)

            # Apply keep/drop rules
            if keep_drop_type:
                rolls, kept_indices = self._apply_keep_drop(rolls, keep_drop_type, keep_drop_count)
                dice_key += f"{keep_drop_type}{keep_drop_count}"

            raw_rolls[dice_key] = rolls
            dice_total = sum(rolls)
            total += dice_total

            # Check for critical/fumble on d20
            if sides == 20 and count == 1:
                if rolls[0] == 20:
                    is_critical = True
                elif rolls[0] == 1:
                    is_fumble = True

            breakdown_parts.append(f"{dice_key}=[{','.join(map(str, rolls))}]={dice_total}")

        # Find and apply modifiers
        mod_matches = list(self.MOD_PATTERN.finditer(expression))
        for match in mod_matches:
            sign = match.group(1)
            value = int(match.group(2))

            if sign == '-':
                value = -value

            modifiers.append((sign, abs(value)))
            total += value
            breakdown_parts.append(f"{sign}{abs(value)}")

        # Build breakdown string
        breakdown = " ".join(breakdown_parts) + f" = {total}"

        return RollResult(
            expression=original_expression,
            raw_rolls=raw_rolls,
            modifiers=modifiers,
            total=total,
            is_critical=is_critical,
            is_fumble=is_fumble,
            breakdown=breakdown
        )

    def _roll_dice(self, count: int, sides: int, reroll_below: Optional[int] = None,
                   exploding: bool = False) -> List[int]:
        """Roll dice with optional reroll and exploding"""
        rolls = []

        for _ in range(count):
            roll = random.randint(1, sides)

            # Handle reroll
            if reroll_below and roll <= reroll_below:
                roll = random.randint(1, sides)

            rolls.append(roll)

            # Handle exploding dice
            if exploding and roll == sides:
                extra_rolls = self._roll_dice(1, sides, reroll_below, exploding)
                rolls.extend(extra_rolls)

        return rolls

    def _apply_keep_drop(self, rolls: List[int], keep_drop_type: str,
                        count: int) -> Tuple[List[int], List[int]]:
        """Apply keep/drop rules to rolls"""
        sorted_indices = sorted(range(len(rolls)), key=lambda i: rolls[i], reverse=True)

        if keep_drop_type in ['kh', 'k']:  # Keep highest
            kept_indices = sorted_indices[:count]
        elif keep_drop_type == 'kl':  # Keep lowest
            kept_indices = sorted_indices[-count:]
        elif keep_drop_type in ['dh', 'd']:  # Drop highest
            kept_indices = sorted_indices[count:]
        elif keep_drop_type == 'dl':  # Drop lowest
            kept_indices = sorted_indices[:-count]
        else:
            kept_indices = list(range(len(rolls)))

        kept_rolls = [rolls[i] for i in sorted(kept_indices)]
        return kept_rolls, kept_indices

    def _handle_advantage_disadvantage(self, expression: str, advantage: bool) -> str:
        """Convert d20 rolls to handle advantage/disadvantage"""
        # Replace single d20 with 2d20kh1 (advantage) or 2d20kl1 (disadvantage)
        if advantage:
            expression = re.sub(r'\bd20\b', '2d20kh1', expression)
        else:  # disadvantage
            expression = re.sub(r'\bd20\b', '2d20kl1', expression)
        return expression

    def parse_expression(self, expression: str) -> Dict[str, Any]:
        """Parse expression and return its components without rolling"""
        expression = expression.strip().lower()

        dice_matches = list(self.DICE_PATTERN.finditer(expression))
        mod_matches = list(self.MOD_PATTERN.finditer(expression))

        dice_components = []
        for match in dice_matches:
            count = int(match.group(1) or 1)
            sides = int(match.group(2))
            dice_components.append({
                'count': count,
                'sides': sides,
                'notation': f"{count}d{sides}"
            })

        modifiers = []
        for match in mod_matches:
            sign = match.group(1)
            value = int(match.group(2))
            modifiers.append({
                'sign': sign,
                'value': value
            })

        return {
            'expression': expression,
            'dice': dice_components,
            'modifiers': modifiers,
            'is_valid': len(dice_components) > 0 or len(modifiers) > 0
        }

    def bulk_roll(self, expression: str, count: int = 1) -> List[RollResult]:
        """Roll the same expression multiple times"""
        return [self.roll(expression) for _ in range(count)]

    def roll_with_context(self, expression: str, context: Dict[str, Any]) -> RollResult:
        """Roll with additional context (for future enhancements)"""
        # Extract context parameters
        advantage = context.get('advantage', False)
        disadvantage = context.get('disadvantage', False)

        # Perform the roll
        result = self.roll(expression, advantage, disadvantage)

        # Add context to result (for tracking purposes)
        result.context = context

        return result