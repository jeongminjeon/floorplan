"""
GUI application for the floorplanning tool.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import random
from floorplan_core import Block, FloorPlan
from floorplan_algorithm import calculate_floorplan


class FloorPlanGUI:
    """Main GUI application for floorplanning."""
    
    def __init__(self, root):
        """Initialize the GUI."""
        self.root = root
        self.root.title("Floorplanning Tool")
        self.root.geometry("1200x700")
        
        # Data
        self.blocks = []
        self.floorplan = None
        
        # Colors for visualization
        self.colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B88B', '#ABEBC6'
        ]
        self.color_index = 0
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Input section
        left_panel = tk.Frame(main_container, width=400, relief=tk.RAISED, borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Right panel - Visualization
        right_panel = tk.Frame(main_container, relief=tk.RAISED, borderwidth=1)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # --- LEFT PANEL WIDGETS ---
        
        # Title
        title_label = tk.Label(left_panel, text="Block Input", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Input frame
        input_frame = tk.Frame(left_panel)
        input_frame.pack(padx=10, pady=5, fill=tk.X)
        
        # Block name
        tk.Label(input_frame, text="Block Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = tk.Entry(input_frame, width=20)
        self.name_entry.grid(row=0, column=1, pady=5, padx=5)
        
        # Width
        tk.Label(input_frame, text="Width:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.width_entry = tk.Entry(input_frame, width=20)
        self.width_entry.grid(row=1, column=1, pady=5, padx=5)
        
        # Height
        tk.Label(input_frame, text="Height:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.height_entry = tk.Entry(input_frame, width=20)
        self.height_entry.grid(row=2, column=1, pady=5, padx=5)
        
        # Preferred location
        tk.Label(input_frame, text="Preferred Location:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.location_var = tk.StringVar(value="don't care")
        location_combo = ttk.Combobox(input_frame, textvariable=self.location_var, width=18, state="readonly")
        location_combo['values'] = ("don't care", "top-left", "top-right", "bottom-left", "bottom-right")
        location_combo.grid(row=3, column=1, pady=5, padx=5)
        
        # Neighbor
        tk.Label(input_frame, text="Neighbor (optional):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.neighbor_var = tk.StringVar(value="None")
        self.neighbor_combo = ttk.Combobox(input_frame, textvariable=self.neighbor_var, width=18, state="readonly")
        self.neighbor_combo['values'] = ("None",)
        self.neighbor_combo.grid(row=4, column=1, pady=5, padx=5)
        
        # Add block button
        add_button = tk.Button(left_panel, text="Add Block", command=self._add_block, 
                               bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        add_button.pack(pady=10)
        
        # --- LAYOUT SETTINGS ---
        
        # Separator
        separator = ttk.Separator(left_panel, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=10)
        
        # Settings label
        settings_label = tk.Label(left_panel, text="Layout Settings", font=("Arial", 11, "bold"))
        settings_label.pack(pady=(5, 5))
        
        # Settings frame
        settings_frame = tk.Frame(left_panel)
        settings_frame.pack(padx=10, pady=5, fill=tk.X)
        
        # Max aspect ratio
        tk.Label(settings_frame, text="Max Aspect Ratio:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.aspect_ratio_var = tk.StringVar(value="1:2")
        aspect_ratio_combo = ttk.Combobox(settings_frame, textvariable=self.aspect_ratio_var, width=18, state="readonly")
        aspect_ratio_combo['values'] = ("1:1 (Square)", "1:1.5", "1:2", "1:3", "1:4", "No limit")
        aspect_ratio_combo.grid(row=0, column=1, pady=5, padx=5)
        
        # Info label for aspect ratio
        aspect_info = tk.Label(settings_frame, text="Controls shape of result", 
                              font=("Arial", 8), fg="gray")
        aspect_info.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Blocks list
        list_label = tk.Label(left_panel, text="Added Blocks:", font=("Arial", 11, "bold"))
        list_label.pack(pady=(10, 5))
        
        # Frame for listbox and scrollbar
        list_frame = tk.Frame(left_panel)
        list_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.blocks_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10)
        self.blocks_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.blocks_listbox.yview)
        
        # Buttons for list management
        list_buttons_frame = tk.Frame(left_panel)
        list_buttons_frame.pack(pady=5)
        
        delete_button = tk.Button(list_buttons_frame, text="Delete Selected", 
                                  command=self._delete_block, bg="#f44336", fg="white")
        delete_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = tk.Button(list_buttons_frame, text="Clear All", 
                                command=self._clear_all, bg="#ff9800", fg="white")
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # Calculate button
        calculate_button = tk.Button(left_panel, text="Calculate Layout", 
                                     command=self._calculate_layout,
                                     bg="#2196F3", fg="white", 
                                     font=("Arial", 12, "bold"), height=2)
        calculate_button.pack(pady=20, padx=10, fill=tk.X)
        
        # --- RIGHT PANEL WIDGETS ---
        
        # Title
        vis_title = tk.Label(right_panel, text="Floorplan Visualization", 
                            font=("Arial", 14, "bold"))
        vis_title.pack(pady=10)
        
        # Info label
        self.info_label = tk.Label(right_panel, text="Add blocks and click 'Calculate Layout'", 
                                   font=("Arial", 10))
        self.info_label.pack(pady=5)
        
        # Canvas for drawing
        canvas_frame = tk.Frame(right_panel, bg="white")
        canvas_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", relief=tk.SUNKEN, borderwidth=2)
        self.canvas.pack(fill=tk.BOTH, expand=True)
    
    def _add_block(self):
        """Add a new block from the input fields."""
        # Validate inputs
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a block name.")
            return
        
        # Check for duplicate names
        if any(b.name == name for b in self.blocks):
            messagebox.showerror("Error", f"Block '{name}' already exists.")
            return
        
        try:
            width = float(self.width_entry.get())
            height = float(self.height_entry.get())
            if width <= 0 or height <= 0:
                raise ValueError("Dimensions must be positive")
        except ValueError as e:
            messagebox.showerror("Error", "Please enter valid positive numbers for width and height.")
            return
        
        location = self.location_var.get()
        neighbor = self.neighbor_var.get()
        neighbor = None if neighbor == "None" else neighbor
        
        # Create and add block
        block = Block(name, width, height, location, neighbor)
        self.blocks.append(block)
        
        # Update listbox
        display_text = f"{name} ({width}x{height})"
        if location != "don't care":
            display_text += f" - {location}"
        if neighbor:
            display_text += f" - abuts {neighbor}"
        self.blocks_listbox.insert(tk.END, display_text)
        
        # Update neighbor dropdown
        self._update_neighbor_dropdown()
        
        # Clear inputs
        self.name_entry.delete(0, tk.END)
        self.width_entry.delete(0, tk.END)
        self.height_entry.delete(0, tk.END)
        self.location_var.set("don't care")
        self.neighbor_var.set("None")
        
        # Focus back to name entry
        self.name_entry.focus()
    
    def _delete_block(self):
        """Delete the selected block."""
        selection = self.blocks_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a block to delete.")
            return
        
        index = selection[0]
        block_name = self.blocks[index].name
        
        # Remove block
        self.blocks.pop(index)
        self.blocks_listbox.delete(index)
        
        # Update neighbor dropdown
        self._update_neighbor_dropdown()
        
        # Clear canvas if no blocks left
        if not self.blocks:
            self.canvas.delete("all")
            self.info_label.config(text="Add blocks and click 'Calculate Layout'")
    
    def _clear_all(self):
        """Clear all blocks."""
        if self.blocks and not messagebox.askyesno("Confirm", "Clear all blocks?"):
            return
        
        self.blocks.clear()
        self.blocks_listbox.delete(0, tk.END)
        self.canvas.delete("all")
        self.info_label.config(text="Add blocks and click 'Calculate Layout'")
        self._update_neighbor_dropdown()
    
    def _update_neighbor_dropdown(self):
        """Update the neighbor dropdown with current block names."""
        names = ["None"] + [b.name for b in self.blocks]
        self.neighbor_combo['values'] = names
        if self.neighbor_var.get() not in names:
            self.neighbor_var.set("None")
    
    def _calculate_layout(self):
        """Calculate and display the floorplan."""
        if not self.blocks:
            messagebox.showwarning("Warning", "Please add at least one block.")
            return
        
        try:
            # Parse aspect ratio
            max_aspect_ratio = self._parse_aspect_ratio()
            
            # Calculate floorplan with aspect ratio constraint
            self.floorplan = calculate_floorplan(self.blocks, max_aspect_ratio)
            
            # Calculate actual aspect ratio
            actual_ratio = max(
                self.floorplan.bounding_width / self.floorplan.bounding_height if self.floorplan.bounding_height > 0 else 1,
                self.floorplan.bounding_height / self.floorplan.bounding_width if self.floorplan.bounding_width > 0 else 1
            )
            
            # Update info label
            info_text = f"Bounding Box: {self.floorplan.bounding_width:.1f} x {self.floorplan.bounding_height:.1f}"
            info_text += f" | Area: {self.floorplan.get_area():.1f} | Aspect: 1:{actual_ratio:.2f}"
            self.info_label.config(text=info_text)
            
            # Draw the floorplan
            self._draw_floorplan()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate layout: {str(e)}")
            self.info_label.config(text="Error calculating layout")
    
    def _parse_aspect_ratio(self):
        """Parse the aspect ratio from the dropdown."""
        aspect_str = self.aspect_ratio_var.get()
        
        if "No limit" in aspect_str:
            return 100.0  # Effectively no limit
        
        # Extract numeric part
        if "1:1 " in aspect_str:  # "1:1 (Square)"
            return 1.0
        elif "1:1.5" in aspect_str:
            return 1.5
        elif "1:2" in aspect_str:
            return 2.0
        elif "1:3" in aspect_str:
            return 3.0
        elif "1:4" in aspect_str:
            return 4.0
        else:
            return 2.0  # Default
    
    def _draw_floorplan(self):
        """Draw the floorplan on the canvas."""
        self.canvas.delete("all")
        
        if not self.floorplan or not self.floorplan.blocks:
            return
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Handle case where canvas hasn't been drawn yet
        if canvas_width <= 1:
            canvas_width = 600
        if canvas_height <= 1:
            canvas_height = 500
        
        # Calculate scale factor with margins
        margin = 40
        scale_x = (canvas_width - 2 * margin) / self.floorplan.bounding_width
        scale_y = (canvas_height - 2 * margin) / self.floorplan.bounding_height
        scale = min(scale_x, scale_y)
        
        # Draw bounding box
        bbox_width = self.floorplan.bounding_width * scale
        bbox_height = self.floorplan.bounding_height * scale
        bbox_x = margin
        bbox_y = margin
        
        self.canvas.create_rectangle(
            bbox_x, bbox_y,
            bbox_x + bbox_width, bbox_y + bbox_height,
            outline="black", width=2, dash=(5, 5)
        )
        
        # Draw each block
        for i, block in enumerate(self.floorplan.blocks):
            x1 = bbox_x + block.x * scale
            y1 = bbox_y + block.y * scale
            x2 = x1 + block.width * scale
            y2 = y1 + block.height * scale
            
            # Get color for this block
            color = self.colors[i % len(self.colors)]
            
            # Draw rectangle
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color, outline="black", width=2
            )
            
            # Draw block name
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            self.canvas.create_text(
                center_x, center_y - 8,
                text=block.name,
                font=("Arial", 10, "bold"),
                fill="black"
            )
            
            # Draw dimensions
            dim_text = f"{block.width:.1f} x {block.height:.1f}"
            if block.rotated:
                dim_text += " (R)"
            self.canvas.create_text(
                center_x, center_y + 8,
                text=dim_text,
                font=("Arial", 8),
                fill="black"
            )
        
        # Draw dimension labels for bounding box
        self.canvas.create_text(
            bbox_x + bbox_width / 2, bbox_y - 10,
            text=f"W: {self.floorplan.bounding_width:.1f}",
            font=("Arial", 9, "bold")
        )
        self.canvas.create_text(
            bbox_x - 15, bbox_y + bbox_height / 2,
            text=f"H: {self.floorplan.bounding_height:.1f}",
            font=("Arial", 9, "bold"),
            angle=90
        )


def run_gui():
    """Run the GUI application."""
    root = tk.Tk()
    app = FloorPlanGUI(root)
    root.mainloop()

