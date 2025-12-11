import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import json
import collections

# ==========================================
#   CUSTOM PACKING ENGINE (Guillotine + Row Priority)
# ==========================================
class SimpleBin:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.rects = []
        self.free_rects = [(0, 0, width, height)]

    def add_rect(self, width, height, rid, can_rotate):
        best_rect_idx = -1
        best_score = float('inf')
        best_orientation = (width, height)
        orientations = [(width, height)]
        if can_rotate: orientations.append((height, width))

        for i, free in enumerate(self.free_rects):
            fx, fy, fw, fh = free
            for (test_w, test_h) in orientations:
                if test_w <= fw + 0.001 and test_h <= fh + 0.001:
                    leftover_w, leftover_h = fw - test_w, fh - test_h
                    short_side = min(leftover_w, leftover_h)
                    if short_side < best_score:
                        best_score, best_rect_idx, best_orientation = short_side, i, (test_w, test_h)

        if best_rect_idx != -1:
            fx, fy, fw, fh = self.free_rects.pop(best_rect_idx)
            final_w, final_h = best_orientation
            self.rects.append((fx, fy, final_w, final_h, rid))
            
            rem_w, rem_h = fw - final_w, fh - final_h
            
            # Row Priority Split Logic
            force_horizontal = (final_h < 10) 
            split_horizontal = True if force_horizontal else ((fw * rem_h) >= (rem_w * fh))

            if split_horizontal:
                if rem_w > 0: self.free_rects.append((fx + final_w, fy, rem_w, final_h))
                if rem_h > 0: self.free_rects.append((fx, fy + final_h, fw, rem_h))
            else:
                if rem_w > 0: self.free_rects.append((fx + final_w, fy, rem_w, fh))
                if rem_h > 0: self.free_rects.append((fx, fy + final_h, final_w, rem_h))
            return True
        return False

class StonePacker:
    def __init__(self, usable_l, usable_w):
        self.slab_l, self.slab_w = usable_l, usable_w
        self.bins = []

    def pack(self, pieces):
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
                    return False, f"Piece '{pid}' fits nowhere."
                self.bins.append(new_bin)
        return True, "Success"

# ==========================================
#   HTML TICKET GENERATOR (With SF Calcs)
# ==========================================
def generate_html_ticket(packer, job_name, material, slab_l, slab_w, slab_trim, kerf, slabs_used, total_cost, waste_pct):
    safe_w = slab_l - (2 * slab_trim)
    safe_h = slab_w - (2 * slab_trim)
    
    room_sf = collections.defaultdict(float)
    total_stone_sf = 0.0
    
    cut_list_rows = ""
    for b in packer.bins:
        for (rx, ry, rw, rh, rid) in b.rects:
            final_l = rw - (2*kerf)
            final_w = rh - (2*kerf)
            piece_sf = (final_l * final_w) / 144.0
            total_stone_sf += piece_sf
            
            room_name = rid.split(":")[0] if ":" in rid else "Unassigned"
            room_sf[room_name] += piece_sf
            
            cut_list_rows += f"<tr><td>{rid}</td><td>{final_l:.1f} x {final_w:.1f}</td><td>{piece_sf:.2f} sq ft</td></tr>"

    room_rows = ""
    for r, area in room_sf.items():
        room_rows += f"<tr><td>{r}</td><td>{area:.2f} sq ft</td></tr>"

    html = f"""
    <html>
    <head>
        <title>Job Ticket: {job_name}</title>
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
            rect.safe {{ fill: none; stroke: red; stroke-width: 0.5; stroke-dasharray: 5,5; }}
            text {{ font-family: Arial; font-size: 0.4px; text-anchor: middle; dominant-baseline: middle; }}
            .stats-container {{ display: flex; gap: 20px; }}
            .stats-box {{ flex: 1; border: 1px solid #ddd; padding: 10px; }}
            @media print {{ .no-print {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Job Ticket: {job_name}</h1>
            <button class="no-print" onclick="window.print()" style="font-size:16px; padding:10px 20px; cursor:pointer;">🖨️ PRINT / SAVE AS PDF</button>
        </div>
        
        <div class="summary">
            <strong>Material:</strong> {material} <br>
            <strong>Total Finished Stone:</strong> {total_stone_sf:.2f} sq ft <br>
            <strong>Slabs Needed:</strong> {slabs_used} (${total_cost:,.2f}) <br>
            <strong>Waste Factor:</strong> {waste_pct:.1f}%
        </div>

        <div class="stats-container">
            <div class="stats-box">
                <h3>Room Breakdown</h3>
                <table>
                    <tr><th>Room</th><th>Total Sq Ft</th></tr>
                    {room_rows}
                </table>
            </div>
            <div class="stats-box">
                <h3>Cut List</h3>
                <table>
                    <tr><th>Piece ID</th><th>Dimensions</th><th>Sq Ft</th></tr>
                    {cut_list_rows}
                </table>
            </div>
        </div>

        <h3>Slab Layouts</h3>
    """

    for i, b in enumerate(packer.bins):
        html += f"""
        <div class="slab-box">
            <h4>Slab #{i+1}</h4>
            <svg viewBox="0 0 {slab_l} {slab_w}" width="100%">
                <rect x="0" y="0" width="{slab_l}" height="{slab_w}" fill="none" stroke="black" stroke-width="0.2"/>
                <rect x="{slab_trim}" y="{slab_trim}" width="{safe_w}" height="{safe_h}" class="safe"/>
        """
        for (rx, ry, rw, rh, rid) in b.rects:
            draw_x = rx + slab_trim + kerf
            draw_y = ry + slab_trim + kerf
            draw_w = rw - (2*kerf)
            draw_h = rh - (2*kerf)
            font_size = min(draw_w, draw_h) * 0.25
            if font_size > 3: font_size = 3
            
            html += f"""
                <rect class="piece" x="{draw_x}" y="{draw_y}" width="{draw_w}" height="{draw_h}" />
                <text x="{draw_x + draw_w/2}" y="{draw_y + draw_h/2}" font-size="{font_size}">{rid} ({draw_w:.0f}x{draw_h:.0f})</text>
            """
        html += "</svg></div>"
    html += "</body></html>"
    return html

# ==========================================
#   WEB INTERFACE
# ==========================================
st.set_page_config(page_title="Stone Estimator Pro", layout="wide")
st.title("🪨 Stone Slab Estimator Pro")

if 'pieces' not in st.session_state: st.session_state['pieces'] = []
if 'editing_idx' not in st.session_state: st.session_state['editing_idx'] = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Job Management")
    uploaded_file = st.file_uploader("Load Saved Job (.json)", type="json")
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.session_state['pieces'] = data.get('pieces', [])
            st.session_state['job_name_load'] = data.get('job_name', "")
            st.session_state['material_load'] = data.get('material', "")
            st.session_state['slab_l_load'] = data.get('slab_l', 130.0)
            st.session_state['slab_w_load'] = data.get('slab_w', 65.0)
            st.success(f"Loaded: {data.get('job_name')}")
        except: st.error("Invalid file.")

    st.divider()
    st.header("1. Job Settings")
    default_job = st.session_state.get('job_name_load', "Smith Kitchen")
    default_mat = st.session_state.get('material_load', "White Quartz")
    default_l = st.session_state.get('slab_l_load', 130.0)
    default_w = st.session_state.get('slab_w_load', 65.0)

    job_name = st.text_input("Job Name", value=default_job)
    material = st.text_input("Stone / Material", value=default_mat)
    col_s1, col_s2 = st.columns(2)
    with col_s1: slab_l = st.number_input("Slab Length", value=default_l)
    with col_s2: slab_w = st.number_input("Slab Width", value=default_w)
    cost = st.number_input("Cost per Slab ($)", value=0.0)
    slab_trim = st.number_input("Edge Trim (in)", value=1.0)
    kerf = st.number_input("Saw Kerf (in)", value=0.125, format="%.3f")

    job_data = {"job_name": job_name, "material": material, "slab_l": slab_l, "slab_w": slab_w, "pieces": st.session_state['pieces']}
    st.download_button("💾 Save Job to File", json.dumps(job_data, indent=2), f"{job_name.replace(' ', '_')}.json", "application/json")
    if st.button("Clear All"):
        st.session_state['pieces'] = []
        st.session_state['editing_idx'] = None
        st.rerun()

# --- EDIT (Updated with Rotation Checkbox) ---
if st.session_state['editing_idx'] is not None:
    idx = st.session_state['editing_idx']
    p = st.session_state['pieces'][idx]
    st.info(f"✏️ Editing: {p['name']}")
    with st.form("edit"):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1, 1, 1, 1])
        nr = c1.text_input("Room", p['room'])
        nn = c2.text_input("Name", p['name'])
        nl = c3.number_input("L", value=p['l'])
        nw = c4.number_input("W", value=p['w'])
        nq = c5.number_input("Qty", value=p['qty'])
        nrot = c6.checkbox("Rotate?", value=p['rot']) # ADDED THIS CHECKBOX
        
        if st.form_submit_button("Update"):
            st.session_state['pieces'][idx] = {"room": nr, "name": nn, "l": nl, "w": nw, "qty": nq, "rot": nrot}
            st.session_state['editing_idx'] = None
            st.rerun()

# --- ADD ---
st.subheader(f"2. Add Pieces for: {material}")
c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 2, 1.5, 1.5, 1, 1, 1])
room = c1.text_input("Room", "Kitchen", key="ar")
name = c2.text_input("Name", "Counter", key="an")
l = c3.number_input("Length", 0.0, key="al")
w = c4.number_input("Width", 0.0, key="aw")
qty = c5.number_input("Qty", 1, key="aq")
rot = c6.checkbox("Rotate?", key="arot")
if c7.button("➕ Add"):
    if l > 0 and w > 0:
        st.session_state['pieces'].append({"room": room, "name": name, "l": l, "w": w, "qty": qty, "rot": rot})
        st.rerun()

# --- LIST ---
if st.session_state['pieces']:
    st.write("### Cut List")
    for i, p in enumerate(st.session_state['pieces']):
        c1, c2, c3 = st.columns([6, 1, 1])
        rot_status = " (Rotatable)" if p['rot'] else ""
        c1.write(f"**{p['qty']}x** {p['room']} - {p['name']} ({p['l']} x {p['w']}){rot_status}")
        if c2.button("Edit", key=f"e{i}"): st.session_state['editing_idx'] = i; st.rerun()
        if c3.button("❌", key=f"d{i}"): st.session_state['pieces'].pop(i); st.rerun()

# --- CALCULATE ---
if st.button("🚀 CALCULATE LAYOUT", type="primary"):
    usable_l = slab_l - (2 * slab_trim)
    usable_w = slab_w - (2 * slab_trim)
    
    if usable_l <= 0 or usable_w <= 0:
        st.error("Edge Trim too big!")
    elif not st.session_state['pieces']:
        st.warning("No pieces.")
    else:
        packing_list = []
        total_area = 0
        error = None

        for p in st.session_state['pieces']:
            p_tot_w = p['w'] + (2 * kerf)
            if not p['rot'] and p_tot_w > usable_w:
                error = f"Piece '{p['name']}' too wide."
                break
            for _ in range(p['qty']):
                rem = p['l']
                parts = []
                while rem > 0:
                    max_cut = usable_l - (2*kerf)
                    cut = min(rem, max_cut)
                    fut = rem - cut
                    if 0 < fut < 25.0: cut -= (25.0 - fut)
                    parts.append(cut)
                    rem -= cut
                for idx, plen in enumerate(parts):
                    pid = f"{p['room']}: {p['name']}" + (f" ({idx+1}/{len(parts)})" if len(parts)>1 else "")
                    packing_list.append((plen + (2*kerf), p['w'] + (2*kerf), pid, p['rot']))
                    total_area += (plen * p['w'])

        if error: st.error(error)
        else:
            packer = StonePacker(usable_l, usable_w)
            success, msg = packer.pack(packing_list)
            if not success: st.error(msg)
            else:
                slabs = len(packer.bins)
                waste = ((slabs * slab_l * slab_w - total_area) / (slabs * slab_l * slab_w) * 100)
                tot_cost = slabs * cost
                
                # --- LIVE STATS ---
                room_sf = collections.defaultdict(float)
                final_stone_sf = 0.0
                for b in packer.bins:
                    for (rx, ry, rw, rh, rid) in b.rects:
                        f_l = rw - (2*kerf)
                        f_w = rh - (2*kerf)
                        sf = (f_l * f_w) / 144.0
                        final_stone_sf += sf
                        r_name = rid.split(":")[0] if ":" in rid else "Other"
                        room_sf[r_name] += sf

                st.success(f"Success! {slabs} Slabs Needed.")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Material Cost", f"${tot_cost:,.2f}")
                c2.metric("Finished Stone", f"{final_stone_sf:.2f} sq ft")
                c3.metric("Waste", f"{waste:.1f}%")
                
                st.write("### 🏠 Room Breakdown")
                room_data = [{"Room": r, "Sq Ft": f"{s:.2f}"} for r, s in room_sf.items()]
                st.table(room_data)

                html = generate_html_ticket(packer, job_name, material, slab_l, slab_w, slab_trim, kerf, slabs, tot_cost, waste)
                st.download_button("📄 Download Job Ticket", html, "ticket.html", "text/html")
                
                st.divider()
                for i, b in enumerate(packer.bins):
                    st.subheader(f"Slab #{i+1}")
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.add_patch(patches.Rectangle((0, 0), slab_l, slab_w, facecolor='#eee', edgecolor='black'))
                    ax.add_patch(patches.Rectangle((slab_trim, slab_trim), usable_l, usable_w, linewidth=1.5, linestyle='--', edgecolor='red', facecolor='none'))
                    
                    for (rx, ry, rw, rh, rid) in b.rects:
                        dx, dy = rx + slab_trim + kerf, ry + slab_trim + kerf
                        dw, dh = rw - (2*kerf), rh - (2*kerf)
                        ax.add_patch(patches.Rectangle((dx, dy), dw, dh, facecolor='#d1e7dd', edgecolor='green'))
                        
                        cx, cy = dx + dw/2, dy + dh/2
                        lbl = f"{rid}\n{dw:.1f}x{dh:.1f}"
                        rot_deg = 90 if dh > dw else 0
                        font_size = 8
                        if min(dw, dh) < 10: font_size = 6
                        ax.text(cx, cy, lbl, ha='center', va='center', fontsize=font_size, rotation=rot_deg, color='black')
                        
                    ax.set_xlim(0, slab_l); ax.set_ylim(0, slab_w); ax.set_aspect('equal'); plt.axis('off')
                    st.pyplot(fig)
