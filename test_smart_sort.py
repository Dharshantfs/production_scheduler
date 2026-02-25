import os
import sys

# Mocking frappe objects
class DictObj(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        return super().__getattribute__(name)

UNIT_QUALITY_ORDER = {
	"Unit 2": ["GOLD","SILVER","BRONZE","CLASSIC","SUPER CLASSIC","LIFE STYLE",
	           "ECO SPECIAL","ECO GREEN","SUPER ECO","ULTRA","DELUXE"],
}

COLOR_ORDER_LIST = [
	"LEMON YELLOW", "YELLOW", "GOLDEN YELLOW", "ORANGE", "CHERRY RED", "RED",
	"LAVENDER", "PINK", "PEACH", "GREEN", "LEAF GREEN", "PARROT GREEN", "MEHNDI GREEN", "OLIVE GREEN",
	"SKY BLUE", "TURKEY BLUE", "CYAN", "NXT BLUE", "AQUA BLUE", "INK BLUE", "NAVY BLUE",
	"MEDICAL BLUE", "GREY", "BROWN", "MAROON", "LIGHT BEIGE", "BEIGE", "BLACK"
]
COLOR_PRIORITY = {c: i for i, c in enumerate(COLOR_ORDER_LIST)}
def color_sort_key(c): return COLOR_PRIORITY.get(c, 999)

def test_sequence():
    color_items = [
        {"name": "1", "colorKey": "GOLDEN YELLOW", "quality": "GOLD", "gsm": 80, "unit": "Unit 2"},
        {"name": "2", "colorKey": "GOLDEN YELLOW", "quality": "ULTRA", "gsm": 80, "unit": "Unit 2"},
        {"name": "3", "colorKey": "RED", "quality": "BRONZE", "gsm": 80, "unit": "Unit 2"},
        {"name": "4", "colorKey": "RED", "quality": "BRONZE", "gsm": 50, "unit": "Unit 2"},
        {"name": "5", "colorKey": "MEDICAL BLUE", "quality": "ULTRA", "gsm": 65, "unit": "Unit 2"},
        {"name": "6", "colorKey": "BLACK", "quality": "ULTRA", "gsm": 80, "unit": "Unit 2"},
    ]
    
    sequence = []
    seq_no = [0]
    unit = "Unit 2"
    effective_seed = "ULTRA"
    current_seed_color = "MEDICAL BLUE"

    remaining = list(color_items)
    quality_order = UNIT_QUALITY_ORDER.get(unit, [])

    if not effective_seed and remaining:
        for q in quality_order:
            if any(i["quality"] == q for i in remaining):
                effective_seed = q
                break
        if not effective_seed:
            effective_seed = remaining[0]["quality"]

    max_loops = len(remaining) * 2 + 5
    loops = 0

    while remaining and loops < max_loops:
        loops += 1

        qual_pool = [i for i in remaining if i["quality"] == effective_seed]
        print(f"Loop {loops}: current_qual={effective_seed}, count={len(qual_pool)}, current_seed_color={current_seed_color}")

        if not qual_pool:
            advanced = False
            if quality_order:
                try:
                    qi = quality_order.index(effective_seed)
                except ValueError:
                    qi = -1
                search_order = quality_order[qi+1:] + quality_order[:qi+1] if qi != -1 else quality_order
                for nq in search_order:
                    if any(i["quality"] == nq for i in remaining):
                        effective_seed = nq
                        advanced = True
                        current_seed_color = None
                        break
            if not advanced:
                effective_seed = remaining[0]["quality"]
                current_seed_color = None
            continue

        pool_colors = sorted(list({i["colorKey"] for i in qual_pool}), key=color_sort_key)
        
        if current_seed_color and current_seed_color in COLOR_PRIORITY:
            seed_idx = COLOR_PRIORITY[current_seed_color]
            valid_options = [c for c in pool_colors if COLOR_PRIORITY.get(c, -1) >= seed_idx]
            chosen_color = valid_options[0] if valid_options else pool_colors[0]
        else:
            chosen_color = pool_colors[0]

        color_batch = sorted(
            [i for i in qual_pool if i["colorKey"] == chosen_color],
            key=lambda i: (i.get("gsm") or 0)
        )

        for i in color_batch:
            remaining.remove(i)

        for idx, item in enumerate(color_batch):
            seq_no[0] += 1
            sequence.append({
                **item,
                "sequence_no": seq_no[0],
                "phase": "color",
                "is_seed_bridge": (idx == len(color_batch) - 1) and len(remaining) > 0,
            })
            print(f"  --> Added: Qual={item['quality']}, Color={item['colorKey']}, GSM={item['gsm']}")

        current_seed_color = chosen_color

test_sequence()
