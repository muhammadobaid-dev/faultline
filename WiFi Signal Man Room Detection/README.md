# WiFi Device Room Detection (Camera Screen)

Windows pe LAN/WiFi devices scan karke **CCTV camera-style** dashboard pe dikhata hai. Har device ko MAC se **room** aur **person** assign karo — phir woh Quad View aur Floor Plan pe live dikhega.

## Setup

```bash
cd "WiFi Signal Man Room Detection"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Browser: [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Use

1. App open hote hi background scan start hota hai (ARP + ping sweep).
2. Side panel mein devices dikhenge (IP, MAC, hostname).
3. **Assign Room / Person** form se mapping save karo.
4. **▦** = Quad camera rooms · **⌂** = Floor plan · **⟳** = Scan abhi.

Mappings `data/devices.json` mein save hoti hain. Rooms `data/rooms.json` se edit ho sakte hain.

## Limits

- Exact GPS / automatic triangulation nahi — room **manual map** hai.
- Phone sleep / ARP timeout se device thodi der gayab ho sakta hai.
- Same WiFi/LAN pe hone wale devices dikhte hain.
