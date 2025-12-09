import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# ==========================================
#   CUSTOM PACKING ENGINE (Guillotine Logic)
# ==========================================
class SimpleBin:
    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.rects = []
        self.free_rects = [(0, 0, width, height)]

    def add_rect(self, width, height, rid, can_rotate):
        best_rect_idx = -1
        best_short_side_fit = float('inf')
        best_orientation = (width, height)
        
        orientations = [(width, height)]
        if can_rotate:
            orientations.append((height, width))

        for i, free in enumerate(self.free_rects):
            fx, fy, fw, fh = free
            for (test_w, test_h) in orientations:
                if test_w <= fw and test_h <= fh:
                    leftover_w = fw - test_w
                    leftover_h = fh - test_h
                    short_side = min(leftover_w, leftover_h)
                    
                    if short_side < best_short_side_fit:
                        best_short_side_fit = short_side
                        best_rect_idx = i
                        best_orientation = (test_w, test_h)

        if best_rect_idx != -1:
            fx, fy, fw, fh = self.free_rects.pop(best_rect_idx)
            final_w, final_h = best_orientation
            self.rects.append((fx, fy, final_w, final_h, rid))
            
            # Guillotine Split (Disjoint Rectangles)
            rem_w = fw - final_w
            rem_h = fh - final_h
            
            if rem_w < rem_h:
                if rem_w > 0: self.free_rects.append((fx + final_w, fy, rem_w, final_h))
                if rem_h > 0: self.free_rects.append((fx, fy + final_h, fw, rem_h))
            else:
                if rem_w > 0: self.free_rects.append((fx + final_w, fy, rem_w, fh))
                if rem_h > 0: self.free_rects.append((fx, fy + final_h, final_w, rem_h))
            return True
        return False

class StonePacker:
    def __init__(self, slab_l, slab_w):
        self.slab_l = slab_l
        self.slab_w = slab_w
        self.bins = []

    def pack(self, pieces):
        # Sort by Area (Largest first)
        pieces.sort(key=lambda x: x[0] * x[1], reverse=True)
        
        for p in pieces:
            pl, pw, pid, rot = p
            placed = False
            for b in self.bins:
                if b.add_rect(pl, pw, pid, rot):
                    placed = True
                    break
            if not placed:
                new_bin = SimpleBin(self.slab_l, self.slab_w)
                if not new_bin.add_rect(pl, pw, pid, rot):
                    return False, f"Piece '{pid}' ({pl}x{pw}) is too big for slab."
                self.bins.append(new_bin)
        return True, "Success"

# ==========================================
#   HTML TICKET GENERATOR
# ==========================================
def generate_html_ticket(packer, slab_l, slab_w, margin, slabs_used, total_cost, waste_pct):
    html = f"""
    <html>
    <head>
        <title>Fabrication Job Ticket</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
            .summary {{ background: #f0f0f0; padding: 15px; margin-bottom: 20px; border-radius: 5px; }}
            .slab-box {{ border: 1px solid #ccc; padding: 10px; margin-bottom: 30px; page-break-inside: avoid; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            svg {{ background: #fafafa; border: 1px solid #000; }}
            rect.piece {{ fill: #d1e7dd; stroke: #28a745; stroke-width: 1; }}
            text {{ font-family: Arial; font-size: 0.4px; text-anchor: middle; dominant-baseline: middle; }}
            
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Fabrication Job Ticket</h1>
            <button class="no-print" onclick="window.print()" style="font-size:16px; padding:10px 20px; cursor:pointer;">🖨️ PRINT / SAVE AS PDF</button>
        </div>
        
        <div class="summary">
