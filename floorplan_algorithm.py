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
    """Group blocks that should be placed adjacent to each other (handles chains)."""
    groups = []
    used = set()
    
    # Build a map of who depends on whom
    block_map = {b.name: b for b in blocks}
    depends_on = {}  # block_name -> neighbor_name
    depended_by = {}  # block_name -> [list of blocks that depend on it]
    
    for block in blocks:
        if block.neighbor:
            depends_on[block.name] = block.neighbor
            if block.neighbor not in depended_by:
                depended_by[block.neighbor] = []
            depended_by[block.neighbor].append(block.name)
    
    # Find root blocks (blocks that are not dependent on anyone or start chains)
    for block in blocks:
        if block.name in used:
            continue
        
        # Find the root of this chain (the block that no one depends on in this chain)
        current = block
        chain_members = set([block.name])
        
        # Follow dependencies backwards to find the root
        while current.name in depends_on:
            neighbor_name = depends_on[current.name]
            if neighbor_name in chain_members:  # Circular dependency, break
                break
            if neighbor_name in block_map:
                current = block_map[neighbor_name]
                chain_members.add(current.name)
            else:
                break
        
        # Now current is the root, build the group by following forward dependencies
        group = []
        to_process = [current.name]
        
        while to_process:
            current_name = to_process.pop(0)
            if current_name in used or current_name not in block_map:
                continue
            
            group.append(block_map[current_name])
            used.add(current_name)
            
            # Add blocks that depend on this one
            if current_name in depended_by:
                to_process.extend(depended_by[current_name])
        
        if group:
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
    """Place blocks with location preferences (corners, quadrants, center)."""
    location_prefs = {
        'top-left-corner': [],
        'top-left-quad': [],
        'top-right-corner': [],
        'top-right-quad': [],
        'bottom-left-corner': [],
        'bottom-left-quad': [],
        'bottom-right-corner': [],
        'bottom-right-quad': [],
        'center': [],
        "don't care": []
    }
    
    # Categorize groups by preferred location
    for group in neighbor_groups:
        pref = group[0].preferred_location
        # Handle legacy location names for backward compatibility
        if pref == 'top-left':
            pref = 'top-left-corner'
        elif pref == 'top-right':
            pref = 'top-right-corner'
        elif pref == 'bottom-left':
            pref = 'bottom-left-corner'
        elif pref == 'bottom-right':
            pref = 'bottom-right-corner'
        
        if pref in location_prefs:
            location_prefs[pref].append(group)
        else:
            location_prefs["don't care"].append(group)
    
    # Place exact corner blocks first
    tlc_groups = []
    current_y = 0
    for group in location_prefs['top-left-corner']:
        _place_group_at(group, 0, current_y, floorplan)
        tlc_groups.append(group)
        current_y += max(b.height for b in group)
    
    trc_groups = []
    current_y = 0
    for group in location_prefs['top-right-corner']:
        _place_group_at(group, 0, current_y, floorplan)  # Temporary, will adjust
        trc_groups.append((group, current_y))
        current_y += max(b.height for b in group)
    
    blc_groups = []
    current_x = 0
    for group in location_prefs['bottom-left-corner']:
        _place_group_at(group, current_x, 0, floorplan)  # Temporary, will adjust
        blc_groups.append((group, current_x))
        current_x += max(b.width for b in group)
    
    brc_groups = []
    for group in location_prefs['bottom-right-corner']:
        _place_group_at(group, 0, 0, floorplan)  # Temporary, will adjust
        brc_groups.append(group)
    
    # Place quadrant blocks - they have more flexibility
    for pref_type in ['top-left-quad', 'top-right-quad', 'bottom-left-quad', 'bottom-right-quad']:
        for group in location_prefs[pref_type]:
            pos = _find_quadrant_position(group, floorplan, pref_type)
            _place_group_at(group, pos[0], pos[1], floorplan)
    
    # Place center blocks
    for group in location_prefs['center']:
        pos = _find_center_position(group, floorplan)
        _place_group_at(group, pos[0], pos[1], floorplan)
    
    # Place "don't care" blocks in best remaining space
    for group in location_prefs["don't care"]:
        pos = _find_best_position(group, floorplan)
        _place_group_at(group, pos[0], pos[1], floorplan)
    
    # Adjust corner positions to actual corners
    floorplan.update_bounding_box()
    
    # Adjust top-right corner blocks
    for group, y_pos in trc_groups:
        max_width = max(b.width for b in group)
        for block in group:
            block.x = floorplan.bounding_width - max_width + (block.x - 0)
    
    # Adjust bottom-left corner blocks
    for group, x_pos in blc_groups:
        max_height = max(b.height for b in group)
        for block in group:
            block.y = floorplan.bounding_height - max_height + (block.y - 0)
    
    # Adjust bottom-right corner blocks
    for group in brc_groups:
        max_width = max(b.width for b in group)
        max_height = max(b.height for b in group)
        for block in group:
            block.x = floorplan.bounding_width - max_width + (block.x - 0)
            block.y = floorplan.bounding_height - max_height + (block.y - 0)


def _find_quadrant_position(group, floorplan, quadrant):
    """Find a suitable position within a specific quadrant."""
    if not floorplan.blocks:
        return (0, 0)
    
    floorplan.update_bounding_box()
    
    group_width = sum(b.width for b in group) if len(group) > 1 else group[0].width
    group_height = max(b.height for b in group) if len(group) > 1 else group[0].height
    
    # Define quadrant boundaries
    mid_x = floorplan.bounding_width / 2
    mid_y = floorplan.bounding_height / 2
    
    if quadrant == 'top-left-quad':
        candidates = [(x, y) for x in range(0, int(mid_x), 10) 
                     for y in range(0, int(mid_y), 10)]
    elif quadrant == 'top-right-quad':
        candidates = [(x, y) for x in range(int(mid_x), int(floorplan.bounding_width), 10) 
                     for y in range(0, int(mid_y), 10)]
    elif quadrant == 'bottom-left-quad':
        candidates = [(x, y) for x in range(0, int(mid_x), 10) 
                     for y in range(int(mid_y), int(floorplan.bounding_height), 10)]
    else:  # bottom-right-quad
        candidates = [(x, y) for x in range(int(mid_x), int(floorplan.bounding_width), 10) 
                     for y in range(int(mid_y), int(floorplan.bounding_height), 10)]
    
    # Add fallback positions
    candidates.append((0, 0))
    
    return _find_best_from_candidates(group, floorplan, candidates, group_width, group_height)


def _find_center_position(group, floorplan):
    """Find a position near the center of the floorplan."""
    if not floorplan.blocks:
        return (0, 0)
    
    floorplan.update_bounding_box()
    
    group_width = sum(b.width for b in group) if len(group) > 1 else group[0].width
    group_height = max(b.height for b in group) if len(group) > 1 else group[0].height
    
    # Try positions near center
    mid_x = floorplan.bounding_width / 2
    mid_y = floorplan.bounding_height / 2
    
    candidates = [
        (mid_x - group_width / 2, mid_y - group_height / 2),  # Exact center
        (mid_x, mid_y),
        (mid_x - group_width, mid_y),
        (mid_x, mid_y - group_height),
        (0, 0)  # Fallback
    ]
    
    return _find_best_from_candidates(group, floorplan, candidates, group_width, group_height)


def _find_best_from_candidates(group, floorplan, candidates, group_width, group_height):
    """Find the best position from a list of candidates."""
    best_pos = candidates[0] if candidates else (0, 0)
    best_area = float('inf')
    
    for pos in candidates:
        x, y = max(0, pos[0]), max(0, pos[1])
        
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
            best_pos = (x, y)
    
    return best_pos


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
    """Place a group of blocks at specified position (handles chains)."""
    if len(group) == 0:
        return
    
    if len(group) == 1:
        block = group[0]
        block.x = x
        block.y = y
        floorplan.add_block(block)
    else:
        # Place multiple blocks in a chain - need to respect neighbor relationships
        # Build dependency map for this group
        block_map = {b.name: b for b in group}
        depends_on = {b.name: b.neighbor for b in group if b.neighbor and b.neighbor in block_map}
        
        # Find root (block with no dependency in this group)
        roots = [b for b in group if b.name not in depends_on or depends_on[b.name] not in block_map]
        if not roots:
            # Circular or all depend on external - just use first
            roots = [group[0]]
        
        # Place root block
        current_block = roots[0]
        current_block.x = x
        current_block.y = y
        floorplan.add_block(current_block)
        placed = {current_block.name}
        
        # Place remaining blocks adjacent to their neighbors
        remaining = [b for b in group if b.name not in placed]
        max_iterations = len(group) * 2
        iteration = 0
        
        while remaining and iteration < max_iterations:
            iteration += 1
            placed_any = False
            
            for block in list(remaining):
                if block.neighbor and block.neighbor in placed and block.neighbor in block_map:
                    # Place this block adjacent to its neighbor
                    neighbor_block = block_map[block.neighbor]
                    
                    # Try horizontal placement first (right side of neighbor)
                    block.x = neighbor_block.x + neighbor_block.width
                    block.y = neighbor_block.y
                    
                    # Check if this causes overlap with already placed blocks
                    overlaps = any(
                        not (block.x + block.width <= placed_block.x or 
                             placed_block.x + placed_block.width <= block.x or
                             block.y + block.height <= placed_block.y or 
                             placed_block.y + placed_block.height <= block.y)
                        for placed_name in placed 
                        for placed_block in [block_map.get(placed_name)]
                        if placed_block
                    )
                    
                    if overlaps:
                        # Try vertical placement (below neighbor)
                        block.x = neighbor_block.x
                        block.y = neighbor_block.y + neighbor_block.height
                    
                    floorplan.add_block(block)
                    placed.add(block.name)
                    remaining.remove(block)
                    placed_any = True
            
            if not placed_any:
                # Can't place any more based on dependencies, place remaining arbitrarily
                for block in remaining:
                    block.x = x
                    block.y = y
                    floorplan.add_block(block)
                    placed.add(block.name)
                remaining.clear()


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
    """Try to optimize the placement by compacting blocks without violating location constraints."""
    if not floorplan.blocks:
        return
    
    # Try to shift blocks towards origin, but respect location constraints
    max_iterations = 10
    for _ in range(max_iterations):
        improved = False
        
        for block in floorplan.blocks:
            # Skip blocks with strict location constraints
            if block.preferred_location in ['top-left-corner', 'top-right-corner', 
                                            'bottom-left-corner', 'bottom-right-corner',
                                            'center']:
                continue
            
            # Try moving left (for blocks without location constraints or quadrant blocks)
            original_x = block.x
            while block.x > 0:
                block.x -= 1
                if floorplan.has_overlaps() or _violates_location_constraint(block, floorplan):
                    block.x = original_x
                    break
                original_x = block.x
                improved = True
            
            # Try moving up
            original_y = block.y
            while block.y > 0:
                block.y -= 1
                if floorplan.has_overlaps() or _violates_location_constraint(block, floorplan):
                    block.y = original_y
                    break
                original_y = block.y
                improved = True
        
        if not improved:
            break
    
    floorplan.update_bounding_box()


def _enforce_corner_constraints(floorplan):
    """
    Post-processing step: Force blocks with corner constraints to exact corner positions.
    This ensures corner constraints are always satisfied after optimization.
    """
    if not floorplan.blocks:
        return
    
    # First pass: Identify corner blocks
    corner_blocks = {}
    for block in floorplan.blocks:
        pref = block.preferred_location
        # Handle legacy names
        if pref == 'top-left':
            pref = 'top-left-corner'
        elif pref == 'top-right':
            pref = 'top-right-corner'
        elif pref == 'bottom-left':
            pref = 'bottom-left-corner'
        elif pref == 'bottom-right':
            pref = 'bottom-right-corner'
        
        if 'corner' in pref:
            corner_blocks[pref] = block
    
    if not corner_blocks:
        return  # No corner constraints to enforce
    
    # Update bounding box
    floorplan.update_bounding_box()
    
    # Snap each corner block to its exact position
    # Do this iteratively and repack to avoid overlaps
    max_iterations = 20
    for iteration in range(max_iterations):
        moved_any = False
        floorplan.update_bounding_box()
        
        # Top-left corner: (0, 0)
        if 'top-left-corner' in corner_blocks:
            block = corner_blocks['top-left-corner']
            if block.x != 0 or block.y != 0:
                block.x = 0
                block.y = 0
                moved_any = True
        
        # Top-right corner
        if 'top-right-corner' in corner_blocks:
            block = corner_blocks['top-right-corner']
            expected_x = floorplan.bounding_width - block.width
            if abs(block.x - expected_x) > 1:
                block.x = expected_x
                moved_any = True
            if block.y != 0:
                block.y = 0
                moved_any = True
        
        # Bottom-left corner
        if 'bottom-left-corner' in corner_blocks:
            block = corner_blocks['bottom-left-corner']
            expected_y = floorplan.bounding_height - block.height
            if block.x != 0:
                block.x = 0
                moved_any = True
            if abs(block.y - expected_y) > 1:
                block.y = expected_y
                moved_any = True
        
        # Bottom-right corner
        if 'bottom-right-corner' in corner_blocks:
            block = corner_blocks['bottom-right-corner']
            expected_x = floorplan.bounding_width - block.width
            expected_y = floorplan.bounding_height - block.height
            if abs(block.x - expected_x) > 1 or abs(block.y - expected_y) > 1:
                block.x = expected_x
                block.y = expected_y
                moved_any = True
        
        # If we have overlaps after snapping, resolve them by moving non-corner blocks
        if floorplan.has_overlaps():
            # Find all overlapping blocks
            overlapping_blocks = set()
            for i, b1 in enumerate(floorplan.blocks):
                for b2 in floorplan.blocks[i+1:]:
                    if b1.overlaps(b2):
                        # Only move the non-corner block
                        if b1.preferred_location not in corner_blocks.values():
                            overlapping_blocks.add(b1)
                        if b2.preferred_location not in corner_blocks.values():
                            overlapping_blocks.add(b2)
            
            # Move overlapping non-corner blocks to non-overlapping positions
            for block in overlapping_blocks:
                if block.preferred_location in corner_blocks.values():
                    continue  # Never move corner blocks
                
                original_x, original_y = block.x, block.y
                best_pos = None
                best_overlap_count = float('inf')
                
                # Try positions in a grid pattern
                for test_x in range(0, int(floorplan.bounding_width) + 100, 50):
                    for test_y in range(0, int(floorplan.bounding_height) + 100, 50):
                        block.x = test_x
                        block.y = test_y
                        
                        # Count overlaps at this position
                        overlap_count = sum(1 for other in floorplan.blocks 
                                          if other != block and block.overlaps(other))
                        
                        if overlap_count == 0:
                            best_pos = (test_x, test_y)
                            moved_any = True
                            break
                        elif overlap_count < best_overlap_count:
                            best_overlap_count = overlap_count
                            best_pos = (test_x, test_y)
                    
                    if best_pos and best_overlap_count == 0:
                        break
                
                if best_pos:
                    block.x, block.y = best_pos
                else:
                    block.x, block.y = original_x, original_y
        
        floorplan.update_bounding_box()
        if not moved_any and not floorplan.has_overlaps():
            break
    
    # Final cleanup: Aggressively compact to remove gaps while keeping corners locked
    floorplan.update_bounding_box()
    _compact_with_locked_corners(floorplan, corner_blocks)


def _compact_with_locked_corners(floorplan, corner_blocks):
    """
    Aggressively compact the floorplan while keeping corner blocks locked.
    This fills gaps created by corner enforcement.
    """
    if not floorplan.blocks:
        return
    
    # Get set of corner block objects
    locked_blocks = set(corner_blocks.values())
    
    # Multiple passes to fill gaps
    max_passes = 20
    for pass_num in range(max_passes):
        floorplan.update_bounding_box()
        improved = False
        
        # Sort blocks by their distance from origin (process closer blocks first)
        movable_blocks = [b for b in floorplan.blocks if b not in locked_blocks]
        movable_blocks.sort(key=lambda b: b.x + b.y)
        
        for block in movable_blocks:
            # Try to move block left and up to fill gaps
            original_x, original_y = block.x, block.y
            
            # Try moving left in larger steps first, then fine-tune
            for step in [50, 10, 5, 1]:
                while block.x >= step:
                    block.x -= step
                    if floorplan.has_overlaps() or _violates_location_constraint(block, floorplan):
                        block.x += step
                        break
                    improved = True
            
            # Try moving up
            for step in [50, 10, 5, 1]:
                while block.y >= step:
                    block.y -= step
                    if floorplan.has_overlaps() or _violates_location_constraint(block, floorplan):
                        block.y += step
                        break
                    improved = True
            
            # Also try moving to completely fill any gaps
            # Try positions closer to other blocks
            if block.x != original_x or block.y != original_y:
                improved = True
        
        # Try to shrink bounding box by moving blocks from edges
        if pass_num % 3 == 0:  # Every 3rd pass
            floorplan.update_bounding_box()
            
            # Find blocks at the right edge (excluding right-corner blocks)
            for block in movable_blocks:
                if block.x + block.width >= floorplan.bounding_width - 10:
                    # Try moving this block left
                    original_x = block.x
                    for new_x in range(0, int(original_x), 10):
                        block.x = new_x
                        if not floorplan.has_overlaps() and not _violates_location_constraint(block, floorplan):
                            improved = True
                            break
                        block.x = original_x
            
            # Find blocks at the bottom edge (excluding bottom-corner blocks)
            for block in movable_blocks:
                if block.y + block.height >= floorplan.bounding_height - 10:
                    # Try moving this block up
                    original_y = block.y
                    for new_y in range(0, int(original_y), 10):
                        block.y = new_y
                        if not floorplan.has_overlaps() and not _violates_location_constraint(block, floorplan):
                            improved = True
                            break
                        block.y = original_y
        
        if not improved:
            break
    
    # Final "tetris-style" packing: Try to fit blocks into any gaps
    # Sort blocks by size (larger blocks first)
    movable_blocks.sort(key=lambda b: b.width * b.height, reverse=True)
    
    for block in movable_blocks:
        original_x, original_y = block.x, block.y
        best_x, best_y = original_x, original_y
        best_density = _calculate_local_density(block, floorplan)
        
        # Try a grid of positions
        step = 20
        for test_x in range(0, int(floorplan.bounding_width) - int(block.width) + 1, step):
            for test_y in range(0, int(floorplan.bounding_height) - int(block.height) + 1, step):
                block.x, block.y = test_x, test_y
                
                if (not floorplan.has_overlaps() and 
                    not _violates_location_constraint(block, floorplan)):
                    # Prefer positions with higher local density (more blocks nearby)
                    density = _calculate_local_density(block, floorplan)
                    if density > best_density or (density == best_density and test_x + test_y < best_x + best_y):
                        best_density = density
                        best_x, best_y = test_x, test_y
        
        block.x, block.y = best_x, best_y
        
        # Fine-tune position
        while block.x > 0:
            block.x -= 1
            if floorplan.has_overlaps() or _violates_location_constraint(block, floorplan):
                block.x += 1
                break
        
        while block.y > 0:
            block.y -= 1
            if floorplan.has_overlaps() or _violates_location_constraint(block, floorplan):
                block.y += 1
                break
    
    floorplan.update_bounding_box()


def _calculate_local_density(block, floorplan):
    """
    Calculate how many other blocks are near this block (encourages tight packing).
    Higher values mean more blocks nearby.
    """
    density = 0
    for other in floorplan.blocks:
        if other == block:
            continue
        
        # Calculate distance between block centers
        dx = abs((block.x + block.width/2) - (other.x + other.width/2))
        dy = abs((block.y + block.height/2) - (other.y + other.height/2))
        distance = (dx*dx + dy*dy) ** 0.5
        
        # Blocks within 200 units contribute to density
        if distance < 200:
            density += 1
        
        # Adjacent blocks contribute more
        if block.abuts(other):
            density += 5
    
    return density


def _violates_location_constraint(block, floorplan):
    """Check if a block's current position violates its location constraint."""
    pref = block.preferred_location
    
    if pref == "don't care":
        return False
    
    floorplan.update_bounding_box()
    mid_x = floorplan.bounding_width / 2
    mid_y = floorplan.bounding_height / 2
    block_center_x = block.x + block.width / 2
    block_center_y = block.y + block.height / 2
    
    # Check quadrant constraints
    if pref == 'top-left-quad':
        return block_center_x > mid_x or block_center_y > mid_y
    elif pref == 'top-right-quad':
        return block_center_x < mid_x or block_center_y > mid_y
    elif pref == 'bottom-left-quad':
        return block_center_x > mid_x or block_center_y < mid_y
    elif pref == 'bottom-right-quad':
        return block_center_x < mid_x or block_center_y < mid_y
    
    return False


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
            
            # CRITICAL: Immediately reject solutions with overlaps
            # Overlaps are NEVER acceptable - this is a hard constraint
            if neighbor.has_overlaps():
                continue  # Skip this neighbor, try again
            
            # Calculate cost (aspect ratio and constraints are handled via penalties)
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
    
    # Post-processing: Force corner blocks to exact corner positions
    _enforce_corner_constraints(best)
    
    return best


def _calculate_cost(floorplan, max_aspect_ratio):
    """
    Calculate cost of a floorplan.
    
    Cost = area + aspect_ratio_penalty + location_constraint_penalty
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
    
    penalty = 0
    
    # Heavy penalty if aspect ratio exceeds limit
    if aspect_ratio > max_aspect_ratio:
        penalty = area * (aspect_ratio - max_aspect_ratio) * 100
    else:
        # Small penalty to encourage layouts closer to target
        penalty = area * (aspect_ratio - 1.0) * 0.5
    
    # CRITICAL: Overlaps are NEVER acceptable - use massive penalty
    if floorplan.has_overlaps():
        penalty += area * 100000  # Make this 20x larger than constraint penalties
    
    # Heavy penalties for violating constraints (both equally important)
    location_penalty = _calculate_location_penalty(floorplan)
    neighbor_penalty = _calculate_neighbor_penalty(floorplan)
    
    # Use extremely heavy penalties to strictly enforce both types of constraints
    # Must be less than overlap penalty (100000) but still very large
    penalty += (location_penalty + neighbor_penalty) * area * 10000
    
    return area + penalty


def _calculate_location_penalty(floorplan):
    """
    Calculate penalty for violating location constraints.
    Returns a value between 0 (perfect) and number of violations.
    """
    if not floorplan.blocks:
        return 0
    
    floorplan.update_bounding_box()
    penalty = 0
    
    # Define boundaries
    mid_x = floorplan.bounding_width / 2
    mid_y = floorplan.bounding_height / 2
    
    for block in floorplan.blocks:
        pref = block.preferred_location
        
        # Skip blocks without preferences
        if pref == "don't care":
            continue
        
        # Handle legacy names
        if pref == 'top-left':
            pref = 'top-left-corner'
        elif pref == 'top-right':
            pref = 'top-right-corner'
        elif pref == 'bottom-left':
            pref = 'bottom-left-corner'
        elif pref == 'bottom-right':
            pref = 'bottom-right-corner'
        
        block_center_x = block.x + block.width / 2
        block_center_y = block.y + block.height / 2
        
        # Check corner constraints (VERY strict - must be exactly at corner)
        tolerance = 2.0  # Allow only 2 pixels of tolerance
        
        if pref == 'top-left-corner':
            # Block MUST be at (0, 0)
            if block.x > tolerance or block.y > tolerance:
                penalty += 1
        
        elif pref == 'top-right-corner':
            # Block MUST be at right edge, top
            expected_x = floorplan.bounding_width - block.width
            if abs(block.x - expected_x) > tolerance or block.y > tolerance:
                penalty += 1
        
        elif pref == 'bottom-left-corner':
            # Block MUST be at left edge, bottom
            expected_y = floorplan.bounding_height - block.height
            if block.x > tolerance or abs(block.y - expected_y) > tolerance:
                penalty += 1
        
        elif pref == 'bottom-right-corner':
            # Block MUST be at right edge, bottom
            expected_x = floorplan.bounding_width - block.width
            expected_y = floorplan.bounding_height - block.height
            if abs(block.x - expected_x) > tolerance or abs(block.y - expected_y) > tolerance:
                penalty += 1
        
        # Check quadrant constraints (more flexible)
        elif pref == 'top-left-quad':
            if block_center_x > mid_x or block_center_y > mid_y:
                penalty += 0.5
        
        elif pref == 'top-right-quad':
            if block_center_x < mid_x or block_center_y > mid_y:
                penalty += 0.5
        
        elif pref == 'bottom-left-quad':
            if block_center_x > mid_x or block_center_y < mid_y:
                penalty += 0.5
        
        elif pref == 'bottom-right-quad':
            if block_center_x < mid_x or block_center_y < mid_y:
                penalty += 0.5
        
        # Check center constraint
        elif pref == 'center':
            # Block center should be reasonably close to layout center
            dist_from_center = abs(block_center_x - mid_x) + abs(block_center_y - mid_y)
            max_dist = (floorplan.bounding_width + floorplan.bounding_height) / 4
            if dist_from_center > max_dist * 0.6:  # Allow some flexibility
                penalty += 0.5
    
    return penalty


def _calculate_neighbor_penalty(floorplan):
    """
    Calculate penalty for violating neighbor/abutting constraints.
    Returns number of neighbor relationships that are not satisfied.
    """
    if not floorplan.blocks:
        return 0
    
    penalty = 0
    
    # Build a map of block names to blocks for quick lookup
    block_map = {block.name: block for block in floorplan.blocks}
    
    for block in floorplan.blocks:
        if block.neighbor:
            # Check if the neighbor exists
            if block.neighbor not in block_map:
                # Neighbor doesn't exist - penalize
                penalty += 1
                continue
            
            neighbor_block = block_map[block.neighbor]
            
            # Check if blocks are actually abutting (adjacent)
            if not block.abuts(neighbor_block):
                # Not abutting - penalize heavily
                penalty += 1
    
    return penalty


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
    
    # Build neighbor relationship map
    has_neighbor = {block.name for block in neighbor.blocks if block.neighbor}
    
    # Choose random perturbation with higher probability for more impactful moves
    perturbation = random.choices(
        ['swap', 'rotate', 'move', 'repack'],
        weights=[20, 30, 30, 20]
    )[0]
    
    if perturbation == 'swap' and len(neighbor.blocks) >= 2:
        # Swap positions of two random blocks (avoid swapping blocks with neighbor constraints)
        # Get blocks without neighbor constraints if possible
        blocks_without_neighbors = [b for b in neighbor.blocks if b.name not in has_neighbor and not b.neighbor]
        
        if len(blocks_without_neighbors) >= 2:
            # Swap only blocks without neighbor constraints
            block1, block2 = random.sample(blocks_without_neighbors, 2)
        else:
            # Fall back to any two blocks
            idx1, idx2 = random.sample(range(len(neighbor.blocks)), 2)
            block1, block2 = neighbor.blocks[idx1], neighbor.blocks[idx2]
        
        # Swap positions
        block1.x, block2.x = block2.x, block1.x
        block1.y, block2.y = block2.y, block1.y
    
    elif perturbation == 'rotate':
        # Rotate a random block (avoid blocks with neighbor constraints)
        blocks_without_neighbors = [b for b in neighbor.blocks if not b.neighbor]
        
        if blocks_without_neighbors:
            num_rotations = random.randint(1, min(3, len(blocks_without_neighbors)))
            blocks_to_rotate = random.sample(blocks_without_neighbors, num_rotations)
        else:
            # Fall back to rotating any block
            num_rotations = random.randint(1, min(3, len(neighbor.blocks)))
            blocks_to_rotate = random.sample(neighbor.blocks, num_rotations)
        
        for block in blocks_to_rotate:
            block.rotate()
    
    elif perturbation == 'move':
        # Move a random block to a new position (prefer blocks without neighbor constraints)
        blocks_without_neighbors = [b for b in neighbor.blocks if not b.neighbor and b.name not in has_neighbor]
        
        if blocks_without_neighbors:
            block = random.choice(blocks_without_neighbors)
        else:
            # If all blocks have constraints, pick randomly
            block = random.choice(neighbor.blocks)
        
        # Generate new position (within reasonable bounds)
        neighbor.update_bounding_box()
        
        # Try a random position with larger range
        max_dim = max(neighbor.bounding_width, neighbor.bounding_height)
        new_x = max(0, block.x + random.randint(-int(max_dim*0.5), int(max_dim*0.5)))
        new_y = max(0, block.y + random.randint(-int(max_dim*0.5), int(max_dim*0.5)))
        
        block.x = new_x
        block.y = new_y
        
        # If this block has a neighbor, try to move the neighbor with it to maintain abutment
        if block.neighbor:
            neighbor_block = next((b for b in neighbor.blocks if b.name == block.neighbor), None)
            if neighbor_block:
                # Calculate offset and move neighbor
                offset_x = neighbor_block.x - (block.x - new_x)
                offset_y = neighbor_block.y - (block.y - new_y)
                neighbor_block.x = offset_x
                neighbor_block.y = offset_y
    
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

