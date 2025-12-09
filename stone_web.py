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
        self.rects = []  # Stores (x, y, w, h, id)
        # Free rects track the USABLE space
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
            
            # Guillotine Split
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
    # We now pass the USABLE size to the packer, not the full slab size
    def __init__(self, usable_l, usable_w):
        self.slab_l = usable_l
        self.slab_w = usable_w
        self.bins = []

    def pack(self, pieces):
        # pieces = (l, w, id, can_rotate)
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
                    return False, f"Piece '{pid}' ({pl:.2f}x{pw:.2f} with kerf) fits nowhere."
                self.bins.append(new_bin)
        return True, "Success"

# ==========================================
#   HTML TICKET GENERATOR
# ==========================================
def generate_html_ticket(packer, slab_l, slab_w, slab_trim, kerf, slabs_used, total_cost, waste_pct):
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
            rect.safe-zone {{ fill: none; stroke: #ff4444; stroke-width: 1; stroke-dasharray: 5,5; }}
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
            <strong>Slabs Needed:</strong> {slabs_used} <br>
            <strong>Total Cost:</strong> ${total_cost:,.2f} <br>
            <strong>Waste:</strong> {waste_pct:.1f}% <br>
            <strong>Full Slab Size:</strong> {slab_l} x {slab_w} in <br>
            <small><em>(Includes {slab_trim}" edge trim and {kerf}" saw kerf)</em></small>
        </div>

        <h3>Cut List</h3>
        <table>
            <tr><th>Piece ID</th><th>Dimensions (Final Cut Size)</th></tr>
    """
    
    # Calculate offset to center the usable area in the full slab
    offset_x = slab_trim
    offset_y = slab_trim

    for b in packer.bins:
        for (rx, ry, rw, rh, rid) in b.rects:
            # Remove the double kerf to show actual stone size
            final_l = rw - (2 * kerf)
            final_w = rh - (2 * kerf)
            html += f"<tr><td>{rid}</td><td>{final_l:.3f} x {final_w:.3f}</td></tr>"

    html += "</table><h3>Slab Layouts</h3>"

    for i, b in enumerate(packer.bins):
        html += f"""
        <div class="slab-box">
            <h4>Slab #{i+1}</h4>
            <svg viewBox="0 0 {slab_l} {slab_w}" width="100%">
                <rect x="0" y="0" width="{slab_l}" height="{slab_w}" fill="none" stroke="black" stroke-width="0.2"/>
                
                <rect x="{offset_x}" y="{offset_y}" width="{slab_l - (2*slab_trim)}" height="{slab_w - (2*slab_trim)}" class="safe-zone" />
        """
        
        for (rx, ry, rw, rh, rid) in b.rects:
            # Logic: 
            # Packer coords (rx) start at 0 inside the safe zone.
            # We must shift them by 'slab_trim' to place them correctly on the full slab.
            # We must also ADD 'kerf' to the start position to draw the inner stone, 
            # and SUBTRACT (2*kerf) from size to draw the actual piece, not the cut box.
            
            draw_x = rx + offset_x + kerf
            draw_y = ry + offset_y + kerf
            draw_w = rw - (2 * kerf)
            draw_h = rh - (2 * kerf)

            font_size = min(draw_w, draw_h) * 0.2
            if font_size > 3: font_size = 3
            
            html += f"""
                <rect class="piece" x="{draw_x}" y="{draw_y}" width="{draw_w}" height="{draw_h}" />
                <text x="{draw_x + draw_w/2}" y="{draw_y + draw_h/2}" font-size="{font_size}">
                    {rid} ({draw_w:.1f}x{draw_h:.1f})
                </text>
            """
        
        html += "</svg></div>"

    html += "</body></html>"
    return html

# ==========================================
#   WEB INTERFACE (Streamlit)
# ==========================================

st.set_page_config(page_title="Stone Estimator Web", layout="wide")

st.title("🪨 Stone Slab Estimator Pro")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Slab Settings")
    slab_l = st.number_input("Full Slab Length (in)", value=130.0)
    slab_w = st.number_input("Full Slab Width (in)", value=65.0)
    cost = st.number_input("Cost per Slab ($)", value=0.0)
    
    st.divider()
    st.write("### Tolerances")
    
    # 1. Slab Edge Trim (Reduces usable bin size)
    slab_trim = st.number_input("Slab Edge Trim (in)", value=1.0, step=0.5, 
                               help="Amount to subtract from ALL slab edges to account for rough/unusable edges.")
    
    # 2. Saw Kerf (Increases piece size)
    kerf = st.number_input("Saw Blade / Kerf (in)", value=0.125, step=0.001, format="%.3f",
                           help="Space added to ALL 4 sides of every piece for the blade width.")

    st.header("Actions")
    if st.button("Clear All Pieces"):
        st.session_state['pieces'] = []
        st.rerun()

# --- INITIALIZE STATE ---
if 'pieces' not in st.session_state:
    st.session_state['pieces'] = []

# --- ADD PIECES FORM ---
st.subheader("2. Add Pieces")
col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 2, 1.5, 1.5, 1, 1.5, 1.5])

with col1: room = st.text_input("Room", "Kitchen")
with col2: name = st.text_input("Piece Name", "Counter")
with col3: l = st.number_input("Length", min_value=0.0, value=0.0)
with col4: w = st.number_input("Width", min_value=0.0, value=0.0)
with col5: qty = st.number_input("Qty", min_value=1, value=1)
with col6: rot = st.checkbox("Allow Rotation?")
with col7: 
    st.write("") 
    add_btn = st.button("➕ Add")

if add_btn:
    if l > 0 and w > 0:
        st.session_state['pieces'].append({
            "room": room, "name": name, "l": l, "w": w, "qty": qty, "rot": rot
        })
    else:
        st.error("Please enter valid dimensions.")

# --- SHOW LIST ---
if st.session_state['pieces']:
    st.write("### Current Cut List")
    display_data = []
    for i, p in enumerate(st.session_state['pieces']):
        display_data.append({
            "Room": p['room'], 
            "Name": p['name'], 
            "Dims": f"{p['l']} x {p['w']}", 
            "Rotate": "Yes" if p['rot'] else "No",
            "Qty": p['qty']
        })
    st.table(display_data)

# --- CALCULATE ---
if st.button("🚀 CALCULATE LAYOUT", type="primary"):
    if not st.session_state['pieces']:
        st.warning("Add pieces first!")
    else:
        # Calculate USABLE slab area
        usable_l = slab_l - (2 * slab_trim)
        usable_w = slab_w - (2 * slab_trim)
        
        if usable_l <= 0 or usable_w <= 0:
            st.error("Error: Edge Trim is too large! It consumes the entire slab.")
        else:
            packing_list = []
            total_project_area = 0
            error_msg = None

            for p in st.session_state['pieces']:
                
                # Bounds Check uses USABLE size
                # Piece size includes KERF padding on all sides (2 * kerf)
                piece_total_w = p['w'] + (2 * kerf)
                piece_total_l = p['l'] + (2 * kerf)
                
                if not p['rot'] and (piece_total_w > usable_w):
                    error_msg = f"Piece '{p['name']}' ({piece_total_w}\" w/ kerf) is too wide for usable slab ({usable_w}\"). Rotation OFF."
                    break

                for _ in range(p['qty']):
                    rem_len = p['l']
                    parts = []
                    # Smart Seam
                    while rem_len > 0:
                        # Max cut is based on usable length minus kerf padding
                        max_cut_len = usable_l - (2 * kerf)
                        cut = min(rem_len, max_cut_len)
                        
                        fut = rem_len - cut
                        if fut > 0 and fut < 25.0: 
                            adjustment = 25.0 - fut
                            cut -= adjustment
                        
                        parts.append(cut)
                        rem_len -= cut
                    
                    count = len(parts)
                    for idx, plen in enumerate(parts):
                        pid = f"{p['room']}: {p['name']}" + (f" ({idx+1}/{count})" if count > 1 else "")
                        
                        # IMPORTANT: Add KERF to dimensions here for packing
                        pack_l = plen + (2 * kerf)
                        pack_w = p['w'] + (2 * kerf)
                        
                        packing_list.append((pack_l, pack_w, pid, p['rot']))
                        total_project_area += (plen * p['w']) # Area uses actual stone size

            if error_msg:
                st.error(error_msg)
            else:
                packer = StonePacker(usable_l, usable_w)
                success, msg = packer.pack(packing_list)

                if not success:
                    st.error(msg)
                else:
                    slabs_used = len(packer.bins)
                    total_mat_cost = slabs_used * cost
                    total_slab_area = slabs_used * (slab_l * slab_w)
                    waste_pct = ((total_slab_area - total_project_area) / total_slab_area * 100) if total_slab_area else 0
                    waste_cost = (waste_pct / 100) * total_mat_cost
                    
                    html_ticket = generate_html_ticket(packer, slab_l, slab_w, slab_trim, kerf, slabs_used, total_mat_cost, waste_pct)

                    st.success("Calculation Complete!")
                    
                    col_res1, col_res2 = st.columns([1, 1])
                    with col_res1:
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Slabs Needed", slabs_used)
                        m2.metric("Total Cost", f"${total_mat_cost:,.2f}")
                        m3.metric("Waste", f"{waste_pct:.1f}%")
                    
                    with col_res2:
                        st.download_button(
                            label="📄 Download Printable Job Ticket (HTML)",
                            data=html_ticket,
                            file_name="stone_job_ticket.html",
                            mime="text/html",
                            help="Download this file, open it, and press Ctrl+P to save as PDF."
                        )

                    st.divider()

                    # --- VISUALIZER ---
                    offset_x = slab_trim
                    offset_y = slab_trim

                    for i, b in enumerate(packer.bins):
                        st.subheader(f"Slab #{i+1}")
                        
                        fig, ax = plt.subplots(figsize=(10, 5))
                        
                        # 1. Draw Full Slab (Black Border)
                        ax.add_patch(patches.Rectangle((0, 0), slab_l, slab_w, linewidth=2, edgecolor='black', facecolor='#eeeeee'))
                        
                        # 2. Draw Safe Zone (Red Dashed)
                        ax.add_patch(patches.Rectangle((offset_x, offset_y), usable_l, usable_w, 
                                                       linewidth=1, edgecolor='red', linestyle='--', facecolor='none', label="Safe Zone"))

                        # 3. Draw Pieces
                        for (rx, ry, rw, rh, rid) in b.rects:
                            # Shift to global coords
                            draw_x = rx + offset_x + kerf
                            draw_y = ry + offset_y + kerf
                            
                            # Shrink back to actual stone size (remove kerf)
                            draw_w = rw - (2 * kerf)
                            draw_h = rh - (2 * kerf)
                            
                            ax.add_patch(patches.Rectangle((draw_x, draw_y), draw_w, draw_h, linewidth=1, edgecolor='green', facecolor='#d1e7dd'))
                            
                            cx = draw_x + draw_w/2
                            cy = draw_y + draw_h/2
                            
                            font_size = 8
                            if draw_w < 20 or draw_h < 10: font_size = 6
                            
                            ax.text(cx, cy, f"{rid}\n{draw_w:.1f}x{draw_h:.1f}", 
                                    ha='center', va='center', fontsize=font_size, color='black')

                        ax.set_xlim(0, slab_l)
                        ax.set_ylim(0, slab_w)
                        ax.set_aspect('equal')
                        plt.axis('off')
                        
                        st.pyplot(fig)
