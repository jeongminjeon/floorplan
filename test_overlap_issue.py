"""Test to understand the overlap issue"""
import json
from floorplan_core import Block
from floorplan_algorithm import calculate_floorplan

# Load the blocks from the user's screenshot
with open('block5_abut_b1b8.json', 'r') as f:
    data = json.load(f)

blocks = []
for block_data in data:
    block = Block(
        block_data['name'],
        block_data['width'],
        block_data['height'],
        block_data.get('preferred_location', "don't care"),
        block_data.get('neighbor')
    )
    blocks.append(block)

print("Testing floorplan calculation...")
print("=" * 70)

# Calculate floorplan with 1:2 aspect ratio (as shown in screenshot)
floorplan = calculate_floorplan(blocks, max_aspect_ratio=2.0)

print(f"\nFloorplan bounds: {floorplan.bounding_width:.1f} x {floorplan.bounding_height:.1f}")
print(f"Aspect ratio: {max(floorplan.bounding_width, floorplan.bounding_height) / min(floorplan.bounding_width, floorplan.bounding_height):.2f}")
print(f"Has overlaps: {floorplan.has_overlaps()}")
print()

# Check for overlaps manually
print("Block positions:")
print("-" * 70)
for block in sorted(floorplan.blocks, key=lambda b: b.name):
    print(f"{block.name:5} at ({block.x:6.1f}, {block.y:6.1f}) size {block.width:6.1f}x{block.height:6.1f}")

print()
print("Checking for overlaps between all pairs:")
print("-" * 70)
overlaps_found = []
for i, b1 in enumerate(floorplan.blocks):
    for b2 in floorplan.blocks[i+1:]:
        # Check if rectangles overlap
        if not (b1.x + b1.width <= b2.x or  # b1 is left of b2
                b2.x + b2.width <= b1.x or  # b2 is left of b1
                b1.y + b1.height <= b2.y or # b1 is above b2
                b2.y + b2.height <= b1.y):  # b2 is above b1
            overlap_width = min(b1.x + b1.width, b2.x + b2.width) - max(b1.x, b2.x)
            overlap_height = min(b1.y + b1.height, b2.y + b2.height) - max(b1.y, b2.y)
            overlap_area = overlap_width * overlap_height
            overlaps_found.append((b1.name, b2.name, overlap_area))
            print(f"[X] OVERLAP: {b1.name} and {b2.name} (overlap area: {overlap_area:.1f})")

if not overlaps_found:
    print("[OK] No overlaps found!")
else:
    print(f"\n[X] Total overlaps found: {len(overlaps_found)}")

print("\n" + "=" * 70)

