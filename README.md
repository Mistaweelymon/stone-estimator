# 🪨 Stone Slab Estimator Pro

A web-based estimation tool designed specifically for Stone Fabricators. This application calculates the optimal nesting of countertop pieces onto slabs, accounting for grain direction, saw blade thickness (kerf), and slab edge defects.

**Live App:** [Click here to launch](https://share.streamlit.io/YOUR-USERNAME/stone-estimator) *(Replace with your actual link)*

## 🚀 Key Features

* **2D Nesting Engine:** Uses a custom "Guillotine Packer" algorithm to arrange rectangular pieces onto slabs with zero overlap.
* **Fabrication Physics:**
    * **Slab Edge Trim:** Defines a "Safe Zone" by trimming unusable rough edges from the slab.
    * **Saw Kerf:** Automatically adds blade width to all 4 sides of every piece to ensure accurate spacing.
* **Grain Direction Control:** Locks pieces to the horizontal axis to maintain vein flow (critical for Granite/Marble), or allows rotation for solid materials (Quartz).
* **Smart Seaming:** Automatically detects if a piece is too long for a slab and cuts it, enforcing a "25-inch Rule" to prevent tiny, unusable slivers.
* **Job Ticket Generation:** Exports a professional HTML/PDF Report with cut lists, cost breakdowns, and visual layout maps for the sawyer.

## 📐 How the Math Works

### 1. The Packing Algorithm (Guillotine Split)
Unlike generic nesting software, this engine uses a **Guillotine Split** strategy to match how a bridge saw actually cuts stone.
1.  **Placement:** It places a piece in the best available spot (using "Best Short Side Fit").
2.  **The Cut:** Once placed, the remaining empty space is split into two disjoint rectangles (Right and Top).
3.  **Result:** This ensures that no pieces ever overlap and that the layout is physically cuttable.

### 2. Tolerance vs. Kerf
The app distinguishes between *Material Issues* and *Process Tolerance*:
* **Slab Edge Trim (Quality Control):**
    * *Formula:* `Usable_Slab_Length = Full_Slab_Length - (2 * Trim)`
    * *Example:* A 130" slab with 1" trim becomes a 128" usable bin. This effectively shrinks the "bucket" we put pieces in.
* **Saw Kerf (Process):**
    * *Formula:* `Packing_Piece_Length = Input_Piece_Length + (2 * Kerf)`
    * *Example:* A 50" counter with 1/8" kerf occupies 50.25" of space. This effectively grows the pieces to ensure the blade doesn't eat into the stone.

### 3. Smart Seaming Logic
If a piece is longer than the usable slab length:
1.  The app calculates how many slabs are needed to span that length.
2.  **The 25-Inch Rule:** If the final remnant piece would be smaller than 25 inches (e.g., a 4-inch sliver), the app "steals" length from the previous piece to make the small piece exactly 25 inches.
    * *Why?* It is impossible to polish and glue a 4-inch seam safely. A 25-inch piece is stable and workable.

## 🛠️ Installation (Local)

To run this app on your own computer:

1.  **Install Python** (3.8 or higher).
2.  **Install Dependencies:**
    ```bash
    pip install streamlit matplotlib
    ```
3.  **Run the App:**
    ```bash
    streamlit run stone_web.py
    ```

## 📄 License
Private Tool. Built for internal estimation and fabrication planning.
