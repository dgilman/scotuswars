import subprocess
import colorsys
import json

from jinja2 import Environment, FileSystemLoader, select_autoescape

import scotuswars

state_names_obj = {v: k for k, v in scotuswars.STATE_ABBRV.items()}
state_names = json.dumps(state_names_obj)

env = Environment(loader=FileSystemLoader("."), autoescape=select_autoescape(["html"]),)

template = env.get_template("index.template.html")
table_template = env.get_template("table.template.html")

with open("United_States_Political_Control_map.svg") as fd:
    svg = fd.read()

scotuswars_dict = scotuswars.main()
state_stats_json = json.dumps(scotuswars_dict)

# colormap:
# go from HSV 0 1 1 (red) -> 0 0 1 (white) -> 1/3 0 1 (white) -> 1/3 1 1 (green)
# we need 256 steps, and 128 is white

saturation_step = 1.0 / 128
green = 1.0 / 3.0
red = 0.0

def color_map(channel):
    return round(channel*0xFF)

hsv_colors = []
for off in range(128):
    hsv_colors.append((red, 1 - (off*saturation_step), 1))
for off in range(1, 129):
    hsv_colors.append((green, (off*saturation_step), 1))
rgb_colors = [colorsys.hsv_to_rgb(*color) for color in hsv_colors]
web_colors = [(color_map(r), color_map(g), color_map(b)) for r, g, b in rgb_colors]
web_colors_js = json.dumps([f'rgb({red},{green},{blue})' for red, green, blue in web_colors])

with open("index.html", "w") as out_fd:
    out_fd.write(
        template.render(state_stats_json=state_stats_json, svg=svg, web_colors_js=web_colors_js, state_names=state_names)
    )

with open("table.html", "w") as out_fd:
    out_fd.write(
        table_template.render(scotuswars=scotuswars_dict, state_names=state_names_obj)
    )

subprocess.run(["gzip", "-kf", "-9", "index.html"])
