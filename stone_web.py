import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from io import BytesIO

# ==========================================
#   CUSTOM PACKING ENGINE (The Brains)
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
            
            if fw > final_w:
                self.free_rects.append((fx + final_w, fy, fw - final_w, fh))
            if fh > final_h:
                self.free_rects.append((fx, fy + final_h, fw, fh - final_h))
            return True
        return False

class StonePacker:
    def __init__(self, slab_l, slab_w):
        self.slab_l = slab_l
        self.slab_w = slab_w
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
                    return False, f"Piece '{pid}' ({pl}x{pw}) is too big for slab."
                self.bins.append(new_bin)
        return True, "Success"

# ==========================================
#   WEB INTERFACE (Streamlit)
# ==========================================

st.set_page_config(page_title="Stone Estimator Web", layout="wide")

st.title("🪨 Stone Slab Estimator Pro")

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.header("1. Slab Settings")
    slab_l = st.number_input("Slab Length (in)", value=130.0)
    slab_w = st.number_input("Slab Width (in)", value=65.0)
    cost = st.number_input("Cost per Slab ($)", value=0.0)
    margin = st.number_input("Safety Margin (in)", value=0.5)

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
# FIX: Changed min_value to 0.0 to match the default value, preventing the crash
with col3: l = st.number_input("Length", min_value=0.0, value=0.0)
with col4: w = st.number_input("Width", min_value=0.0, value=0.0)
with col5: qty = st.number_input("Qty", min_value=1, value=1)
with col6: rot = st.checkbox("Allow Rotation?")
with col7: 
    st.write("") # Spacer
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
        # Prepare Packing List
        packing_list = []
        total_project_area = 0
        error_msg = None

        for p in st.session_state['pieces']:
            # Bounds Check
            if not p['rot'] and (p['w'] + margin > slab_w):
                error_msg = f"Piece '{p['name']}' is too wide ({p['w']}\") for slab ({slab_w}\") and rotation is OFF."
                break

            for _ in range(p['qty']):
                # Seam Logic
                rem_len = p['l']
                parts = []
                while rem_len > 0:
                    cut = min(rem_len, slab_l - margin)
                    fut = rem_len - cut
                    if fut > 0 and fut < 25.0: cut -= (25.0 - fut)
                    parts.append(cut)
                    rem_len -= cut
                
                count = len(parts)
                for idx, plen in enumerate(parts):
                    pid = f"{p['room']}: {p['name']}" + (f" ({idx+1}/{count})" if count > 1 else "")
                    packing_list.append((plen + margin, p['w'] + margin, pid, p['rot']))
                    total_project_area += (plen * p['w'])

        if error_msg:
            st.error(error_msg)
        else:
            # RUN PACKER
            packer = StonePacker(slab_l, slab_w)
            success, msg = packer.pack(packing_list)

            if not success:
                st.error(msg)
            else:
                # --- SHOW RESULTS ---
                slabs_used = len(packer.bins)
                total_mat_cost = slabs_used * cost
                total_slab_area = slabs_used * (slab_l * slab_w)
                waste_pct = ((total_slab_area - total_project_area) / total_slab_area * 100) if total_slab_area else 0
                waste_cost = (waste_pct / 100) * total_mat_cost

                st.success("Calculation Complete!")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Slabs Needed", slabs_used)
                m2.metric("Total Cost", f"${total_mat_cost:,.2f}")
                m3.metric("Waste", f"{waste_pct:.1f}% (${waste_cost:,.2f})")

                st.divider()

                # --- DRAW VISUALS ---
                for i, b in enumerate(packer.bins):
                    st.subheader(f"Slab #{i+1}")
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.add_patch(patches.Rectangle((0, 0), slab_l, slab_w, linewidth=2, edgecolor='black', facecolor='#f0f0f0'))
                    
                    for (rx, ry, rw, rh, rid) in b.rects:
                        ax.add_patch(patches.Rectangle((rx, ry), rw, rh, linewidth=1, edgecolor='green', facecolor='#d1e7dd'))
                        
                        cx = rx + rw/2
                        cy = ry + rh/2
                        display_l = rw - margin
                        display_w = rh - margin
                        
                        # Dynamic Font Size
                        font_size = 8
                        if rw < 20 or rh < 10: font_size = 6
                        
                        ax.text(cx, cy, f"{rid}\n{display_l:.1f}x{display_w:.1f}", 
                                ha='center', va='center', fontsize=font_size, color='black')

                    ax.set_xlim(0, slab_l)
                    ax.set_ylim(0, slab_w)
                    ax.set_aspect('equal')
                    plt.axis('off')
                    
                    st.pyplot(fig)