"""
Core data structures for the floorplanning tool.
"""

class Block:
    """Represents a single block/module in the floorplan."""
    
    def __init__(self, name, width, height, preferred_location="don't care", neighbor=None):
        """
        Initialize a block.
        
        Args:
            name: Block identifier
            width: Block width
            height: Block height
            preferred_location: One of:
                - 'top-left-quad': Top-left quadrant
                - 'top-left-corner': Exact top-left corner
                - 'top-right-quad': Top-right quadrant
                - 'top-right-corner': Exact top-right corner
                - 'bottom-left-quad': Bottom-left quadrant
                - 'bottom-left-corner': Exact bottom-left corner
                - 'bottom-right-quad': Bottom-right quadrant
                - 'bottom-right-corner': Exact bottom-right corner
                - 'center': Center of layout
                - "don't care": No preference (default)
            neighbor: Optional name of neighboring block to abut
        """
        self.name = name
        self.original_width = width
        self.original_height = height
        self.width = width
        self.height = height
        self.preferred_location = preferred_location
        self.neighbor = neighbor
        self.x = 0  # Current x position
        self.y = 0  # Current y position
        self.rotated = False  # Whether block is rotated 90 degrees
    
    def rotate(self):
        """Rotate the block 90 degrees."""
        self.width, self.height = self.height, self.width
        self.rotated = not self.rotated
    
    def reset_rotation(self):
        """Reset block to original orientation."""
        if self.rotated:
            self.rotate()
    
    def get_area(self):
        """Return the area of the block."""
        return self.width * self.height
    
    def overlaps(self, other):
        """Check if this block overlaps with another block."""
        return not (self.x + self.width <= other.x or
                   other.x + other.width <= self.x or
                   self.y + self.height <= other.y or
                   other.y + other.height <= self.y)
    
    def abuts(self, other):
        """Check if this block abuts (is adjacent to) another block."""
        # Check horizontal abutment
        horizontal_abut = (
            (self.x + self.width == other.x or other.x + other.width == self.x) and
            not (self.y + self.height <= other.y or other.y + other.height <= self.y)
        )
        # Check vertical abutment
        vertical_abut = (
            (self.y + self.height == other.y or other.y + other.height == self.y) and
            not (self.x + self.width <= other.x or other.x + other.width <= self.x)
        )
        return horizontal_abut or vertical_abut
    
    def __repr__(self):
        rotation_str = " (rotated)" if self.rotated else ""
        return f"Block({self.name}, {self.width}x{self.height}, pos=({self.x},{self.y}){rotation_str})"


class FloorPlan:
    """Manages a collection of blocks and their layout."""
    
    def __init__(self):
        """Initialize an empty floorplan."""
        self.blocks = []
        self.bounding_width = 0
        self.bounding_height = 0
    
    def add_block(self, block):
        """Add a block to the floorplan."""
        self.blocks.append(block)
    
    def remove_block(self, block_name):
        """Remove a block by name."""
        self.blocks = [b for b in self.blocks if b.name != block_name]
    
    def get_block(self, block_name):
        """Get a block by name."""
        for block in self.blocks:
            if block.name == block_name:
                return block
        return None
    
    def clear_blocks(self):
        """Remove all blocks."""
        self.blocks = []
    
    def update_bounding_box(self):
        """Calculate the bounding box dimensions."""
        if not self.blocks:
            self.bounding_width = 0
            self.bounding_height = 0
            return
        
        max_x = max(block.x + block.width for block in self.blocks)
        max_y = max(block.y + block.height for block in self.blocks)
        self.bounding_width = max_x
        self.bounding_height = max_y
    
    def get_area(self):
        """Return the total area of the bounding rectangle."""
        return self.bounding_width * self.bounding_height
    
    def has_overlaps(self):
        """Check if any blocks overlap."""
        for i, block1 in enumerate(self.blocks):
            for block2 in self.blocks[i+1:]:
                if block1.overlaps(block2):
                    return True
        return False
    
    def __repr__(self):
        return f"FloorPlan({len(self.blocks)} blocks, {self.bounding_width}x{self.bounding_height})"

