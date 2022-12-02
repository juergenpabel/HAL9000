# Required hardware
- Raspberry Pi Zero2
- Respeaker 2-Mic HAT
- IDC/40pin extender cable 25-30cm
- 1.8" fisheye dome ([ebay.com](https://www.ebay.com/itm/301729022732)) # very hard to find/buy elsewhere
- 90° angled GPIO headers for Raspberry Pi
- Visaton K28.40 (previous versions used a K20.40 but that one is limited in terms of loudness)
- Wire mesh (90x50mm)
### Make or buy
- 3D printed: resources/openscad/hal9000-part*.scad (or STLs on [printables.com](https://www.printables.com/model/218766-hal-9000)) # Note: the display top frame and display cover exist in m5core2 and roundypi variants, print accordingly (everything else is "generic")
- CNC cutout: Black acryl faceplate 185x90x3mm with 50mm cutout (resources/openscad/acryl-faceplate.scad)

# Required hardware, dependant on build variant (choose one only, both work just as well)
### Variant m5stack Core2 (recommended, due to better availabily)
- M5Stack Core2 ([m5stack.com](https://docs.m5stack.com/en/core/core2))
- USB OTG cable Micro-USB->USB-C, 15-25cm with both connectors in 90° angle (for the Pi0: right-angled when looking from the Pi0)
- Cable: Grove->Qwiic/Stemma, 15-20cm (I couldn't find one with >10cm online, so I made on myself)
### Variant RoundyPI
- RoundyPI ([tindie.com](https://www.tindie.com/products/sbc/roundypi-128-round-lcd-based-on-rp2040-mcu/))
- USB OTG cable Micro-USB->Micro-USB, 15-25cm with one connector in 90° angle (for the Pi0: right-angled when looking from the Pi0)
- 6-pin 90° angled GPIO header
- Cable: Dupont(female)->Qwiic/Stemma, 15-20cm

# Optional hardware (only required if feature is desired)
### Feature: RFID Reader
- Adafruit MCP23017 GPIO expander (only one, can used also for rotary-encoder and motion sensor)
- RC522 I2C V1.1 ([ebay.com](https://www.ebay.de/itm/311768931452)) # easy to find/buy elsewhere, just make sure it is this specific version
### Feature: Rotary-Encoder
- Adafruit MCP23017 GPIO expander (only one, can used also for RFID reader and motion sensor)
- 2x 12mm Rotary Encoder (6mm shaft diameter) with button
### Feature: Motion sensor
- Adafruit MCP23017 GPIO expander (only one, can used also for RFID reader and rotary-encoder)
- 5.8GHz XYC-WB-DC motion sensor ([ebay.com](https://www.ebay.com/itm/255283290250)) # easy to find/buy elsewhere

# Other bits and pieces
- Various M2.5 standoffs and M2.5 + M3 screws
- A couple of dupont female cables, 10-20cm (partially one end has to be cut and soldered, like for onto the rotary encoders)
- 2x M3 flat nut plate ([ebay.com](https://www.ebay.com/itm/174105488144?var=472963777627)) # easy to find/buy elsewhere
- Flat Micro-USB power cable (for the Pi0: left-angled when looking from the Pi0)
### Optional (recommended for visual appearance or other reasons)
- Black 50mm diameter heat-shrink tube (for enclosing the ReSpeaker as a visual improvement to better hide the Respeaker behind the wire mesh)
- 4x 15x3mm neodym round magnets with screw sinks (for like magnetically "attaching" to a fridge or such)

