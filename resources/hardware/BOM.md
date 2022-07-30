**Warning: Still work-in-progress, might be incomplete**

# Required hardware
- Raspberry Pi Zero2
- Respeaker 2-Mic HAT
- IDC/40pin extender cable 25-30cm
- 1.8" fisheye dome ([ebay.com](https://www.ebay.com/itm/301729022732)) # very hard to find/buy elsewhere
- 90° angled GPIO headers for Raspberry Pi
- Visaton K20.40
- Wire mesh (90x50mm)
### Make or buy
- 3D printed: resources/openscad/hal9000-part*.scad (or on [printables.com](https://www.printables.com/model/218766-hal-9000))
- CNC cutout: Black acryl faceplate 185x90x3mm with 50mm cutout (resources/openscad/acryl-faceplate.scad)

# Required hardware, dependant on build variant (choose one only)
### Variant RoundyPI (recommended, but a little bit more expensive)
- RoundyPI ([tindie.com](https://www.tindie.com/products/sbc/roundypi-128-round-lcd-based-on-rp2040-mcu/))
### Variant Waveshare 19192
- Waveshare 240x240 1.28" round display
- Adafruit FT232h with USB-C
- 90° angled pin headers for FT232h

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
### Feature: mini 4-button row
- Adafruit PCF8591 ADC+DAC
- KC11B04 4 analog buttons # easily

# Other bits and pieces
- Various M2.5 standoffs and screws
- A couple of dupont female cables, 15+cm (partially one end has to be cut and soldered, like onto the rotary encoders)
- 2x M3 flat nut plate ([ebay.com](https://www.ebay.com/itm/174105488144?var=472963777627)) # easy to find/buy elsewhere
- right angled Micro-USB to left angled USB-C cable (15-25cm)
- left angled Micro-USB power cable
### Optional (recommended for visual appearance or other reasons)
- Black 50mm diameter heat-shrink tube (for enclosing the ReSpeaker as a visual improvement to better hide the Respeaker behind the wire mesh)
- 4x 15x3mm neodym round magnets with screw sinks (for magnetically "mounting" to a fridge)
