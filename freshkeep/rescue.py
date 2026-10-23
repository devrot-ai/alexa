"""Deterministic rescue-meal engine.

The critical demo path NEVER depends on a generative model. A curated,
deterministic template set maps at-risk ingredients to concrete meals.
Optional Bedrock mode (see bedrock.py) only rewrites the *description*
text; ingredients, steps, and shopping items always come from here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import estimate_value, freshness_status, days_until_expiry, today


@dataclass(frozen=True)
class RecipeTemplate:
    key: str
    name: str
    blurb: str
    uses_categories: tuple[str, ...]          # categories of at-risk items it rescues
    uses_keywords: tuple[str, ...]            # name keywords it rescues (finer match)
    staples: tuple[str, ...]                  # assumed already owned
    nice_to_have: tuple[str, ...]             # may be missing -> shopping list
    steps: tuple[str, ...]
    minutes: int = 25


TEMPLATES: list[RecipeTemplate] = [
    RecipeTemplate(
        key="leftover-fried-rice",
        name="Rescue-It Fried Rice",
        blurb="Yesterday's rice and wilting greens become a 15-minute fried rice.",
        uses_categories=("leftovers", "grains", "produce"),
        uses_keywords=("rice", "spinach", "greens", "peas", "carrot", "broccoli"),
        staples=("oil", "salt"),
        nice_to_have=("soy sauce", "spring onion", "eggs"),
        steps=(
            "Heat oil in a wide pan over high heat.",
            "Add chopped at-risk vegetables; stir 2-3 minutes.",
            "Add leftover rice, breaking up clumps; toss until hot.",
            "Season with soy sauce; push aside, scramble an egg in, mix and serve.",
        ),
        minutes=15,
    ),
    RecipeTemplate(
        key="green-smoothie",
        name="Almost-Gone Green Smoothie",
        blurb="Wilted greens and aging yogurt blend into a fresh breakfast smoothie.",
        uses_categories=("produce", "dairy", "fruit"),
        uses_keywords=("spinach", "yogurt", "banana", "berries", "milk", "kale"),
        staples=("ice",),
        nice_to_have=("honey", "banana"),
        steps=(
            "Blend yogurt and a handful of greens until smooth.",
            "Add fruit and ice; blend again.",
            "Taste; add honey only if needed.",
        ),
        minutes=5,
    ),
    RecipeTemplate(
        key="veggie-curry",
        name="Clean-The-Fridge Veggie Curry",
        blurb="Any vegetables nearing expiry simmer happily into a coconut curry.",
        uses_categories=("produce", "condiments", "frozen"),
        uses_keywords=("tomato", "spinach", "peas", "cauliflower", "beans", "curry"),
        staples=("oil", "salt", "onion"),
        nice_to_have=("coconut milk", "curry powder"),
        steps=(
            "Sauté chopped onion; add spices and at-risk vegetables.",
            "Pour in coconut milk; simmer 12-15 minutes until tender.",
            "Season, then serve with rice or bread you already have.",
        ),
        minutes=25,
    ),
    RecipeTemplate(
        key="quesadillas",
        name="Spinach & Cheese Quesadillas",
        blurb="Aging dairy and tired greens, folded into crisp quesadillas.",
        uses_categories=("dairy", "produce", "grains"),
        uses_keywords=("cheese", "spinach", "tortilla", "bread", "paneer"),
        staples=("oil",),
        nice_to_have=("tortillas", "salsa"),
        steps=(
            "Wilt chopped greens in a dry pan for 1 minute.",
            "Layer cheese and greens on a tortilla; fold.",
            "Toast in a pan 2-3 minutes per side until crisp.",
        ),
        minutes=12,
    ),
    RecipeTemplate(
        key="chicken-tacos",
        name="Use-It-Up Chicken Tacos",
        blurb="Chicken that must cook today, in spiced tacos.",
        uses_categories=("protein", "produce"),
        uses_keywords=("chicken", "tomato", "lettuce", "onion"),
        staples=("oil", "salt"),
        nice_to_have=("tortillas", "salsa", "lime"),
        steps=(
            "Season and pan-cook diced chicken until done.",
            "Warm tortillas; fill with chicken and chopped fresh toppings.",
            "Finish with salsa or a squeeze of lime.",
        ),
        minutes=20,
    ),
    RecipeTemplate(
        key="tomato-soup",
        name="Roasted Tomato & Milk Soup",
        blurb="Soft tomatoes and aging milk become a silky soup.",
        uses_categories=("produce", "dairy"),
        uses_keywords=("tomato", "milk", "cream", "carrot"),
        staples=("oil", "salt", "pepper"),
        nice_to_have=("garlic bread",),
        steps=(
            "Roast or simmer chopped tomatoes with a little water.",
            "Blend until smooth; return to pot.",
            "Stir in milk gently (do not boil hard); season and serve.",
        ),
        minutes=20,
    ),
    RecipeTemplate(
        key="freezer-pasta-bake",
        name="Freezer-Cleanout Pasta Bake",
        blurb="Frozen veg and the last of the cheese, baked into pasta.",
        uses_categories=("frozen", "grains", "dairy"),
        uses_keywords=("peas", "pasta", "cheese", "corn", "broccoli"),
        staples=("oil", "salt"),
        nice_to_have=("pasta", "parmesan"),
        steps=(
            "Cook pasta; mix with thawed frozen vegetables.",
            "Top with remaining cheese; bake 15 minutes at 200°C.",
        ),
        minutes=30,
    ),
    RecipeTemplate(
        key="fruit-pancakes",
        name="Overripe-Fruit Pancakes",
        blurb="Spotted fruit gets mashed straight into pancake batter.",
        uses_categories=("fruit", "dairy"),
        uses_keywords=("banana", "berries", "mango", "apple", "milk"),
        staples=("flour",),
        nice_to_have=("eggs", "maple syrup"),
        steps=(
            "Mash overripe fruit; whisk with milk, flour and a pinch of salt.",
            "Cook small pancakes 2 minutes per side.",
            "Serve warm.",
        ),
        minutes=15,
    ),
    RecipeTemplate(
        key="bread-bruschetta",
        name="Stale-Bread Bruschetta",
        blurb="Bread going firm is toasted, topped with tomatoes, and rescued.",
        uses_categories=("grains", "produce"),
        uses_keywords=("bread", "tomato", "basil"),
        staples=("oil", "salt"),
        nice_to_have=("garlic", "basil"),
        steps=(
            "Toast sliced bread until golden.",
            "Top with chopped tomato, oil and salt.",
        ),
        minutes=10,
    ),
    RecipeTemplate(
        key="yogurt-parfait",
        name="Yogurt Rescue Parfait",
        blurb="Yogurt nearing its date layered with any fruit you have.",
        uses_categories=("dairy", "fruit"),
        uses_keywords=("yogurt", "banana", "berries", "granola"),
        staples=(),
        nice_to_have=("granola", "honey"),
        steps=(
            "Layer yogurt and chopped fruit in a glass.",
            "Top with granola or a drizzle of honey if you have it.",
        ),
        minutes=5,
    ),
    RecipeTemplate(
        key="veggie-omelette",
        name="Everything-Left Veggie Omelette",
        blurb="Eggs plus whatever vegetables are wilting — the classic rescue.",
        uses_categories=("protein", "produce", "dairy"),
        uses_keywords=("eggs", "spinach", "tomato", "onion", "cheese", "mushroom"),
        staples=("oil", "salt"),
        nice_to_have=("bread",),
        steps=(
            "Sauté chopped at-risk vegetables until soft.",
            "Pour in beaten eggs; cook until set.",
            "Fold and serve.",
        ),
        minutes=10,
    ),
]


def at_risk_items(items: list[dict[str, Any]], within_days: int = 2) -> list[dict[str, Any]]:
    """Items expiring within the window (or already expired), most urgent first."""
    ref = today()
    out = []
    for it in items:
        dl = days_until_expiry(it, ref)
        if dl is None:
            continue
        if dl <= within_days:
            enriched = dict(it)
            enriched["days_left"] = dl
            enriched["status"] = freshness_status(dl)
            out.append(enriched)
    out.sort(key=lambda x: x["days_left"])
    return out


def _matches(template: RecipeTemplate, item: dict[str, Any]) -> bool:
    if item.get("category") in template.uses_categories:
        return True
    name = item.get("name", "")
    return any(k in name for k in template.uses_keywords)


def plan_rescue(
    items: list[dict[str, Any]],
    within_days: int = 2,
    max_missing: int = 2,
) -> dict[str, Any]:
    """Pick the template that rescues the most at-risk items.

    Deterministic by construction: same input -> same plan.
    """
    at_risk = at_risk_items(items, within_days)
    if not at_risk:
        return {
            "has_plan": False,
            "message": "Nothing is close to expiring. Your kitchen is in good shape!",
            "rescued_items": [],
            "missing": [],
        }

    best: tuple[RecipeTemplate | None, list[dict[str, Any]]] = (None, [])
    for t in TEMPLATES:
        covered = [it for it in at_risk if _matches(t, it)]
        if len(covered) > len(best[1]):
            best = (t, covered)
    template, covered = best
    if template is None:
        # Fallback: no template matches — still surface the queue honestly.
        template = TEMPLATES[2]  # veggie curry accepts almost anything
        covered = at_risk[:3]

    covered = covered[:4]
    pantry_names = [it.get("name", "") for it in items]

    def _owned(candidate: str) -> bool:
        c = candidate.lower()
        return any(c == p or c in p or p in c for p in pantry_names if p)

    missing = [n for n in template.nice_to_have if not _owned(n)][:max_missing]
    est_saved = round(sum(estimate_value(it) for it in covered), 2)

    return {
        "has_plan": True,
        "recipe_key": template.key,
        "recipe_name": template.name,
        "blurb": template.blurb,
        "minutes": template.minutes,
        "rescued_items": [
            {"name": it["display_name"], "days_left": it["days_left"], "status": it["status"]}
            for it in covered
        ],
        "staples_assumed": list(template.staples),
        "missing": missing,
        "steps": list(template.steps),
        "estimated_savings_usd": est_saved,
        "note": "Savings are rough estimates for demo purposes, not store prices.",
    }
