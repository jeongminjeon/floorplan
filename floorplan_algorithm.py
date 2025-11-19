"""
Floorplanning algorithm implementation using Simulated Annealing.
"""

import copy
import random
import math
from floorplan_core import Block, FloorPlan


def calculate_floorplan(blocks, max_aspect_ratio=2.0):
    """
    Calculate optimal floorplan layout for given blocks using Simulated Annealing.
    
    Args:
        blocks: List of Block objects
        max_aspect_ratio: Maximum allowed width/height or height/width ratio (default: 2.0)
    
    Returns:
        FloorPlan object with blocks positioned to minimize bounding rectangle
    
    Raises:
        ValueError: If blocks have invalid dimensions
    """
    if not blocks:
        return FloorPlan()
    
    # Validate blocks
    for block in blocks:
        if block.width <= 0 or block.height <= 0:
            raise ValueError(f"Block '{block.name}' has invalid dimensions: {block.width}x{block.height}")
    
    # Validate aspect ratio
    if max_aspect_ratio < 1.0:
        raise ValueError(f"Max aspect ratio must be >= 1.0, got {max_aspect_ratio}")
    
    # Create a copy of blocks to avoid modifying originals
    blocks_copy = [copy.deepcopy(block) for block in blocks]
    
    # Get initial solution using greedy approach
    initial_floorplan = _get_initial_solution(blocks_copy)
    
    # Apply Simulated Annealing optimization
    optimized_floorplan = _simulated_annealing(initial_floorplan, max_aspect_ratio)
    
    return optimized_floorplan


def _get_initial_solution(blocks):
    """Generate initial solution using greedy approach."""
    # Group blocks by neighbor relationships
    neighbor_groups = _group_neighbors(blocks)
    
    # Sort by area (largest first) for better packing
    neighbor_groups.sort(key=lambda g: sum(b.get_area() for b in g), reverse=True)
    
    # Try multiple placement strategies and pick the best
    best_floorplan = None
    best_area = float('inf')
    
    for strategy in ['corners_first', 'row_based', 'column_based']:
        floorplan = _place_blocks(neighbor_groups, strategy)
        if floorplan.get_area() < best_area:
            best_area = floorplan.get_area()
            best_floorplan = floorplan
    
    # Try to optimize by shifting blocks
    _optimize_placement(best_floorplan)
    
    return best_floorplan


def _group_neighbors(blocks):
    """Group blocks that should be placed adjacent to each other."""
    groups = []
    used = set()
    
    for block in blocks:
        if block.name in used:
            continue
        
        group = [block]
        used.add(block.name)
        
        # Find neighbor if specified
        if block.neighbor:
            for other in blocks:
                if other.name == block.neighbor and other.name not in used:
                    group.append(other)
                    used.add(other.name)
                    break
        
        groups.append(group)
    
    return groups


def _place_blocks(neighbor_groups, strategy):
    """
    Place blocks using specified strategy.
    
    Args:
        neighbor_groups: List of block groups (each group is a list of blocks to place together)
        strategy: Placement strategy ('corners_first', 'row_based', or 'column_based')
    
    Returns:
        FloorPlan with blocks placed
    """
    floorplan = FloorPlan()
    
    if strategy == 'corners_first':
        _place_corners_first(floorplan, neighbor_groups)
    elif strategy == 'row_based':
        _place_row_based(floorplan, neighbor_groups)
    else:  # column_based
        _place_column_based(floorplan, neighbor_groups)
    
    floorplan.update_bounding_box()
    return floorplan


def _place_corners_first(floorplan, neighbor_groups):
    """Place blocks with corner preferences first, then fill remaining space."""
    corner_prefs = {
        'top-left': [],
        'top-right': [],
        'bottom-left': [],
        'bottom-right': [],
        "don't care": []
    }
    
    # Categorize groups by preferred location
    for group in neighbor_groups:
        pref = group[0].preferred_location
        corner_prefs[pref].append(group)
    
    # Place top-left corner blocks
    current_x, current_y = 0, 0
    for group in corner_prefs['top-left']:
        _place_group_at(group, current_x, current_y, floorplan)
        current_y += max(b.height for b in group)
    
    # Place top-right corner blocks (we'll adjust x later)
    tr_groups = []
    current_y = 0
    for group in corner_prefs['top-right']:
        temp_x = 0  # Placeholder
        _place_group_at(group, temp_x, current_y, floorplan)
        tr_groups.append((group, current_y))
        current_y += max(b.height for b in group)
    
    # Place bottom-left corner blocks (we'll adjust y later)
    bl_groups = []
    current_x = 0
    for group in corner_prefs['bottom-left']:
        temp_y = 0  # Placeholder
        _place_group_at(group, current_x, temp_y, floorplan)
        bl_groups.append((group, current_x))
        current_x += max(b.width for b in group)
    
    # Place bottom-right corner blocks (we'll adjust both later)
    br_groups = []
    for group in corner_prefs['bottom-right']:
        _place_group_at(group, 0, 0, floorplan)
        br_groups.append(group)
    
    # Place "don't care" blocks in remaining space
    for group in corner_prefs["don't care"]:
        pos = _find_best_position(group, floorplan)
        _place_group_at(group, pos[0], pos[1], floorplan)
    
    # Adjust positions to minimize bounding box
    floorplan.update_bounding_box()
    
    # Move top-right blocks to right edge
    for group, y_pos in tr_groups:
        max_width = max(b.width for b in group)
        for block in group:
            block.x = floorplan.bounding_width - max_width + (block.x - 0)
    
    # Move bottom-left blocks to bottom edge
    for group, x_pos in bl_groups:
        max_height = max(b.height for b in group)
        for block in group:
            block.y = floorplan.bounding_height - max_height + (block.y - 0)
    
    # Move bottom-right blocks to bottom-right corner
    for group in br_groups:
        max_width = max(b.width for b in group)
        max_height = max(b.height for b in group)
        for block in group:
            block.x = floorplan.bounding_width - max_width + (block.x - 0)
            block.y = floorplan.bounding_height - max_height + (block.y - 0)


def _place_row_based(floorplan, neighbor_groups):
    """Place blocks in rows, filling left to right."""
    current_x = 0
    current_y = 0
    row_height = 0
    max_width = 0
    
    for group in neighbor_groups:
        # Try both orientations and pick the better one
        best_orientation = _choose_best_orientation(group)
        if best_orientation == 'rotated':
            for block in group:
                block.rotate()
        
        group_width = sum(b.width for b in group)
        group_height = max(b.height for b in group)
        
        # Check if we need to start a new row
        if current_x > 0 and current_x + group_width > max_width + group_width * 2:
            current_x = 0
            current_y += row_height
            row_height = 0
        
        _place_group_at(group, current_x, current_y, floorplan)
        current_x += group_width
        row_height = max(row_height, group_height)
        max_width = max(max_width, current_x)


def _place_column_based(floorplan, neighbor_groups):
    """Place blocks in columns, filling top to bottom."""
    current_x = 0
    current_y = 0
    col_width = 0
    max_height = 0
    
    for group in neighbor_groups:
        # Try both orientations and pick the better one
        best_orientation = _choose_best_orientation(group)
        if best_orientation == 'rotated':
            for block in group:
                block.rotate()
        
        group_width = max(b.width for b in group)
        group_height = sum(b.height for b in group)
        
        # Check if we need to start a new column
        if current_y > 0 and current_y + group_height > max_height + group_height * 2:
            current_y = 0
            current_x += col_width
            col_width = 0
        
        _place_group_at(group, current_x, current_y, floorplan)
        current_y += group_height
        col_width = max(col_width, group_width)
        max_height = max(max_height, current_y)


def _choose_best_orientation(group):
    """Choose whether to rotate blocks in a group."""
    # Simple heuristic: prefer orientation that's more square-like
    original_aspect = sum(b.width for b in group) / max(b.height for b in group)
    rotated_aspect = sum(b.height for b in group) / max(b.width for b in group)
    
    # Closer to 1.0 is more square
    if abs(rotated_aspect - 1.0) < abs(original_aspect - 1.0):
        return 'rotated'
    return 'original'


def _place_group_at(group, x, y, floorplan):
    """Place a group of blocks at specified position."""
    if len(group) == 1:
        block = group[0]
        block.x = x
        block.y = y
        floorplan.add_block(block)
    else:
        # Place neighbor blocks adjacent to each other
        block1, block2 = group[0], group[1]
        
        # Try horizontal placement
        block1.x = x
        block1.y = y
        block2.x = x + block1.width
        block2.y = y
        
        floorplan.add_block(block1)
        floorplan.add_block(block2)


def _find_best_position(group, floorplan):
    """Find the best position for a group that minimizes bounding box growth."""
    if not floorplan.blocks:
        return (0, 0)
    
    floorplan.update_bounding_box()
    
    # Try several candidate positions
    candidates = [
        (0, 0),  # Top-left
        (floorplan.bounding_width, 0),  # Extend right
        (0, floorplan.bounding_height),  # Extend down
    ]
    
    # Try positions next to existing blocks
    for block in floorplan.blocks:
        candidates.append((block.x + block.width, block.y))
        candidates.append((block.x, block.y + block.height))
    
    best_pos = candidates[0]
    best_area = float('inf')
    
    group_width = sum(b.width for b in group) if len(group) > 1 else group[0].width
    group_height = max(b.height for b in group) if len(group) > 1 else group[0].height
    
    for pos in candidates:
        x, y = pos
        # Check if position causes overlap
        overlaps = False
        for block in floorplan.blocks:
            if not (x + group_width <= block.x or block.x + block.width <= x or
                   y + group_height <= block.y or block.y + block.height <= y):
                overlaps = True
                break
        
        if overlaps:
            continue
        
        # Calculate resulting bounding box
        new_width = max(floorplan.bounding_width, x + group_width)
        new_height = max(floorplan.bounding_height, y + group_height)
        area = new_width * new_height
        
        if area < best_area:
            best_area = area
            best_pos = pos
    
    return best_pos


def _optimize_placement(floorplan):
    """Try to optimize the placement by compacting blocks."""
    if not floorplan.blocks:
        return
    
    # Try to shift blocks towards origin
    max_iterations = 10
    for _ in range(max_iterations):
        improved = False
        
        for block in floorplan.blocks:
            # Try moving left
            original_x = block.x
            while block.x > 0:
                block.x -= 1
                if floorplan.has_overlaps():
                    block.x = original_x
                    break
                original_x = block.x
                improved = True
            
            # Try moving up
            original_y = block.y
            while block.y > 0:
                block.y -= 1
                if floorplan.has_overlaps():
                    block.y = original_y
                    break
                original_y = block.y
                improved = True
        
        if not improved:
            break
    
    floorplan.update_bounding_box()


def _simulated_annealing(initial_floorplan, max_aspect_ratio):
    """
    Optimize floorplan using Simulated Annealing.
    
    Args:
        initial_floorplan: Initial FloorPlan solution
        max_aspect_ratio: Maximum allowed aspect ratio
    
    Returns:
        Optimized FloorPlan
    """
    # SA parameters
    initial_temp = 5000.0
    final_temp = 0.1
    cooling_rate = 0.97
    iterations_per_temp = 100
    
    # Current solution
    current = copy.deepcopy(initial_floorplan)
    current_cost = _calculate_cost(current, max_aspect_ratio)
    
    # Best solution found
    best = copy.deepcopy(current)
    best_cost = current_cost
    
    # Temperature
    temperature = initial_temp
    
    # Run SA
    while temperature > final_temp:
        for _ in range(iterations_per_temp):
            # Generate neighbor solution
            neighbor = _generate_neighbor(current)
            neighbor_cost = _calculate_cost(neighbor, max_aspect_ratio)
            
            # Calculate cost difference
            delta = neighbor_cost - current_cost
            
            # Acceptance criterion
            if delta < 0 or random.random() < math.exp(-delta / temperature):
                current = neighbor
                current_cost = neighbor_cost
                
                # Update best if improved
                if current_cost < best_cost:
                    best = copy.deepcopy(current)
                    best_cost = current_cost
        
        # Cool down
        temperature *= cooling_rate
    
    return best


def _calculate_cost(floorplan, max_aspect_ratio):
    """
    Calculate cost of a floorplan.
    
    Cost = area + aspect_ratio_penalty
    """
    floorplan.update_bounding_box()
    
    # Base cost: area
    area = floorplan.get_area()
    
    # Aspect ratio penalty
    if floorplan.bounding_width == 0 or floorplan.bounding_height == 0:
        return float('inf')
    
    aspect_ratio = max(
        floorplan.bounding_width / floorplan.bounding_height,
        floorplan.bounding_height / floorplan.bounding_width
    )
    
    # Heavy penalty if aspect ratio exceeds limit
    if aspect_ratio > max_aspect_ratio:
        penalty = area * (aspect_ratio - max_aspect_ratio) * 100
    else:
        # Small penalty to encourage layouts closer to target
        penalty = area * (aspect_ratio - 1.0) * 0.5
    
    # Penalty for overlaps (should not happen, but just in case)
    if floorplan.has_overlaps():
        penalty += area * 100
    
    return area + penalty


def _generate_neighbor(floorplan):
    """
    Generate a neighbor solution by applying a random perturbation.
    
    Perturbations:
    1. Swap two blocks
    2. Rotate a random block
    3. Move a block to a new position
    4. Repack blocks in different order
    """
    neighbor = copy.deepcopy(floorplan)
    
    if not neighbor.blocks:
        return neighbor
    
    # Choose random perturbation with higher probability for more impactful moves
    perturbation = random.choices(
        ['swap', 'rotate', 'move', 'repack'],
        weights=[20, 30, 30, 20]
    )[0]
    
    if perturbation == 'swap' and len(neighbor.blocks) >= 2:
        # Swap positions of two random blocks
        idx1, idx2 = random.sample(range(len(neighbor.blocks)), 2)
        block1, block2 = neighbor.blocks[idx1], neighbor.blocks[idx2]
        
        # Swap positions
        block1.x, block2.x = block2.x, block1.x
        block1.y, block2.y = block2.y, block1.y
    
    elif perturbation == 'rotate':
        # Rotate a random block (or multiple blocks)
        num_rotations = random.randint(1, min(3, len(neighbor.blocks)))
        blocks_to_rotate = random.sample(neighbor.blocks, num_rotations)
        for block in blocks_to_rotate:
            block.rotate()
    
    elif perturbation == 'move':
        # Move a random block to a new position
        block = random.choice(neighbor.blocks)
        
        # Generate new position (within reasonable bounds)
        neighbor.update_bounding_box()
        
        # Try a random position with larger range
        max_dim = max(neighbor.bounding_width, neighbor.bounding_height)
        new_x = max(0, block.x + random.randint(-int(max_dim*0.5), int(max_dim*0.5)))
        new_y = max(0, block.y + random.randint(-int(max_dim*0.5), int(max_dim*0.5)))
        
        block.x = new_x
        block.y = new_y
    
    elif perturbation == 'repack':
        # Repack all blocks in a different arrangement
        # Shuffle block order
        random.shuffle(neighbor.blocks)
        
        # Repack in simple grid
        current_x = 0
        current_y = 0
        row_height = 0
        neighbor.update_bounding_box()
        
        # Try to match aspect ratio by adjusting row width
        total_area = sum(b.width * b.height for b in neighbor.blocks)
        target_width = (total_area * neighbor.bounding_width / max(neighbor.bounding_height, 1)) ** 0.5
        
        for block in neighbor.blocks:
            if current_x > target_width and current_x > 0:
                current_x = 0
                current_y += row_height
                row_height = 0
            
            block.x = current_x
            block.y = current_y
            current_x += block.width
            row_height = max(row_height, block.height)
    
    # Compact the solution
    _optimize_placement(neighbor)
    
    return neighbor

