"""Guion del vídeo 001 de Hidden Engineering. Ejecutar para generar el .json que lee el motor."""
import json
from pathlib import Path

# ── rutas aproximadas (lon, lat) ──
MAREA = [[-75.98, 36.85], [-60, 38.5], [-40, 41.5], [-20, 44.5], [-8, 44.3], [-2.98, 43.38]]
CABLE_1858 = [[-10.35, 51.93], [-25, 52.6], [-40, 51.2], [-53.37, 47.88]]
TONGA = [[184.8, -21.14], [182.0, -20.2], [178.44, -18.14]]  # cruza el antimeridiano
EGYPT = [[5.37, 43.3], [8, 40], [15, 36.5], [25, 33.8], [29.9, 31.2], [32.55, 29.97], [35, 26],
         [38.5, 20], [43.3, 12.6], [50, 12.5], [60, 15], [72.87, 19.07]]
WORLD_BBOX = [-100, -52, 260, 72]
WORLD_ROUTES = [
    {"points": [[-74, 40.5], [-40, 45], [-4.5, 50.8]]},
    {"points": MAREA},
    {"points": [[-80.2, 25.8], [-60, 5], [-40, -5], [-38.5, -3.7]]},
    {"points": [[-38.5, -3.7], [-20, 10], [-12, 30], [-9.1, 38.7]]},
    {"points": EGYPT},
    {"points": [[72.87, 19.07], [80, 5], [95, 5], [103.8, 1.3]]},
    {"points": [[103.8, 1.3], [110, 10], [114.2, 22.3], [125, 28], [139.8, 35]]},
    {"points": [[241.6, 33.9], [220, 28], [202, 21.3], [170, 28], [139.8, 35]]},
    {"points": [[236, 45], [200, 48], [165, 42], [140.5, 36]]},
    {"points": [[151.2, -33.9], [170, -20], [185, -5], [202, 21.3]]},
    {"points": [[18.4, -33.9], [5, -20], [0, 0], [-15, 15], [-9.1, 38.7]]},
    {"points": [[103.8, 1.3], [108, -15], [115.9, -31.9]]},
    {"points": [[-4.5, 50.8], [-2, 49], [5, 52.5]]},
]

DEEP = [
    {"label": "Optical fibers (the data)", "color": "accent", "r": 0.16},
    {"label": "Protective tube + gel", "color": "#9FB3CF", "r": 0.30},
    {"label": "Steel wires (strength)", "color": "#C9D2DE", "r": 0.52},
    {"label": "Copper layer (power)", "color": "#E08A3C", "r": 0.64},
    {"label": "Polyethylene insulation", "color": "#26334A", "r": 1.0},
]
SHORE = DEEP + [
    {"label": "Extra steel armor", "color": "#6B7A90", "r": 1.18},
    {"label": "Tar-soaked outer layer", "color": "#3A3A3A", "r": 1.28},
]
SHORE = [dict(x, r=x["r"] / 1.28) for x in SHORE]

REPEATERS = {
    "nodes": [
        {"id": "a", "label": "Shore station", "x": 0.1, "y": 0.55},
        {"id": "b", "label": "Repeater", "x": 0.3, "y": 0.55, "color": "panel"},
        {"id": "c", "label": "Repeater", "x": 0.5, "y": 0.55},
        {"id": "d", "label": "Repeater", "x": 0.7, "y": 0.55},
        {"id": "e", "label": "Shore station", "x": 0.9, "y": 0.55},
    ],
    "edges": [["a", "b", "~70 km"], ["b", "c", "~70 km"], ["c", "d", "~70 km"], ["d", "e", "~70 km"]],
    "pulse": True,
}

script = {
    "videoId": "001-cables-submarinos",
    "channel": "ingenieria",
    "title": "99% of the Internet Runs Through These Hidden Cables",
    "hook_chapter": "The cable under your feet",
    "sources": [
        {"id": "s1", "url": "https://www2.telegeography.com/submarine-cable-faqs-frequently-asked-questions",
         "note": "TeleGeography – submarine cable FAQ (number of cables, total length, share of traffic)"},
        {"id": "s2", "url": "https://news.microsoft.com/",
         "note": "Microsoft – MAREA cable completed in 2017 (6,600 km, 160 Tbps design capacity)"},
        {"id": "s3", "url": "https://www.iscpc.org/",
         "note": "International Cable Protection Committee – causes and frequency of cable faults"},
        {"id": "s4", "url": "https://atlantic-cable.com/",
         "note": "History of the Atlantic Cable – 1858 cable, Queen Victoria's message, 1866 Great Eastern"},
        {"id": "s5", "url": "https://www.reuters.com/",
         "note": "Reuters, Jan–Feb 2022 – Tonga cable cut by the Hunga Tonga eruption and repaired ~5 weeks later"},
    ],
    "metadata": {
        "alt_titles": [
            "The Internet Isn't in the Sky. It's at the Bottom of the Ocean",
            "How a Cable Thinner Than a Garden Hose Carries the Internet",
        ],
        "thumbnails": [
            {"text": "99% of the internet", "art": "cross_section"},
            {"text": "It's under the ocean", "bg": "map", "art": "cross_section", "art_scale": 0.8},
            {"text": "Thinner than a hose", "art": "cross_section"},
        ],
        "description": (
            "The internet isn't in the sky. About 99% of the data traveling between continents runs through "
            "cables lying on the bottom of the ocean — some of them as thin as a garden hose and almost 8 km deep.\n\n"
            "In this video: what's actually inside an undersea cable, how ships lay 6,600 km of cable across the "
            "Atlantic, the spectacular failure of the first transatlantic cable in 1858, how light crosses an ocean "
            "thanks to repeaters powered from the shore, why satellites can't replace them, and what happened when a "
            "volcano cut Tonga off from the world."
        ),
        "tags": ["undersea cables", "submarine cables", "how the internet works", "internet cables",
                 "fiber optic cable", "engineering explained", "hidden engineering", "infrastructure",
                 "how does the internet work", "marea cable", "transatlantic cable", "1858 atlantic cable",
                 "tonga internet", "satellite vs cable", "internet infrastructure", "ocean cables",
                 "engineering documentary", "how it works", "technology explained", "science explained"],
        "hashtags": ["#engineering", "#internet", "#howitworks"],
        "pinned_comment": "Before watching this, did you think the internet between continents went through satellites or cables? Be honest 👇",
    },
    "chapters": [
        {"n": 0, "title": "The hook", "scenes": [
            {"type": "map_route", "thumb": True, "narration": "Right now, the video you're watching probably crossed an ocean to reach you. But it didn't fly through the air.",
             "data": {"bbox": WORLD_BBOX, "routes": WORLD_ROUTES}},
            {"type": "big_number", "narration": "About ninety-nine percent of all the data traveling between continents goes through cables lying on the bottom of the sea.",
             "data": {"value": "99%", "caption": "of data between continents travels through undersea cables", "highlight": ["undersea", "cables"]}},
            {"type": "big_number", "narration": "In the deep ocean, many of them are about as thick as a garden hose. And some rest almost eight kilometers below the surface.",
             "data": {"kicker": "Deepest cables", "value": "8,000 m", "caption": "below the surface, as thin as a garden hose", "highlight": ["garden", "hose"]}},
            {"type": "text", "narration": "So how does a cable that thin carry the internet across an entire ocean? And what happens when one breaks?",
             "data": {"text": "How does a cable this thin carry the internet across an ocean?", "highlight": ["thin", "ocean"]}},
        ]},
        {"n": 1, "title": "What's inside", "title_youtube": "What's inside an undersea cable", "scenes": [
            {"type": "text", "narration": "By the end of this video, you'll see how a volcano cut an entire country off from the internet, and why satellites still can't replace these cables. But first, let's cut one open.",
             "data": {"kicker": "Coming up", "text": "A volcano, a missing country and why satellites can't win", "highlight": ["volcano", "satellites"]}},
            {"type": "cross_section", "thumb": True, "narration": "This is what a typical deep sea cable looks like inside. At the very center are the optical fibers, the strands of glass that carry the data as pulses of light.",
             "data": {"layers": DEEP, "highlight": 0, "title": "Deep-sea cable"}},
            {"type": "scale", "narration": "The light travels through a glass core about nine micrometers wide. That's roughly ten times thinner than a human hair.",
             "data": {"title": "Thinner than a hair", "items": [{"label": "Human hair", "size": 80, "sub": "~80 micrometers"}, {"label": "Fiber core", "size": 9, "sub": "~9 micrometers"}], "highlight": 1}},
            {"type": "cross_section", "narration": "Around the fibers there's a protective tube, and then a layer of steel wires that gives the cable its strength. It has to survive being lowered kilometers into the sea.",
             "data": {"layers": DEEP, "highlight": 2, "title": "Deep-sea cable"}},
            {"type": "cross_section", "narration": "Then comes a thin layer of copper. That's not for the data. It carries electricity along the entire cable, and in a few minutes you'll see why it needs it.",
             "data": {"layers": DEEP, "highlight": 3, "title": "Deep-sea cable"}},
            {"type": "cross_section", "narration": "Finally, everything is wrapped in polyethylene insulation. And in the deep ocean, that's often the entire cable.",
             "data": {"layers": DEEP, "highlight": 4, "title": "Deep-sea cable"}},
            {"type": "cross_section", "narration": "Near the coast, things change. The cable gets extra layers of steel armor, because the real danger isn't the deep sea. It's the shallow water close to land.",
             "data": {"layers": SHORE, "highlight": 5, "title": "Near the shore"}},
            {"type": "big_number", "narration": "Today there are more than five hundred of these cables in service around the world, adding up to roughly one point four million kilometers.",
             "data": {"value": "1.4 million km", "caption": "of undersea cable in service", "highlight": ["undersea"]}},
            {"type": "big_number", "narration": "That's enough cable to wrap around the Earth about thirty-five times.",
             "data": {"value": "35x", "caption": "around the Earth", "color": "accent2"}},
            {"type": "map_route", "narration": "And when you draw them on a map, you see the real shape of the internet. Not a cloud. A web of cables tying every continent together.",
             "data": {"bbox": WORLD_BBOX, "routes": WORLD_ROUTES, "title": "Major cable routes (simplified)"}},
        ]},
        {"n": 2, "title": "Laying it across an ocean", "title_youtube": "How you lay a cable across an ocean", "scenes": [
            {"type": "map_route", "narration": "Take MAREA, one of the most powerful cables ever laid across the Atlantic. It runs about six thousand six hundred kilometers, from Virginia Beach in the United States to the coast near Bilbao, in Spain.",
             "data": {"bbox": [-85, 22, 8, 58], "routes": [{"points": MAREA, "label": "MAREA · 6,600 km"}],
                      "points": [{"lon": -75.98, "lat": 36.85, "label": "Virginia Beach", "anchor": "rm"}, {"lon": -2.98, "lat": 43.38, "label": "Bilbao", "anchor": "mb"}]}},
            {"type": "big_number", "narration": "When it was completed in 2017, it was designed to carry up to one hundred and sixty terabits per second.",
             "data": {"kicker": "MAREA design capacity", "value": "160 Tbps", "caption": "terabits per second"}},
            {"type": "text", "narration": "That's enough to stream tens of millions of HD videos at the same time, through a single cable.",
             "data": {"text": "Tens of millions of HD streams. One cable.", "highlight": ["millions", "One"]}},
            {"type": "diagram", "narration": "But you can't just throw a cable into the sea. First, survey ships map the seabed along the route, to avoid volcanoes, steep slopes, shipwrecks and rough terrain.",
             "data": {"title": "Before the first meter", "nodes": [
                 {"id": "1", "label": "Survey the seabed", "x": 0.15, "y": 0.55}, {"id": "2", "label": "Plan the route", "x": 0.38, "y": 0.55},
                 {"id": "3", "label": "Load the ship", "x": 0.62, "y": 0.55}, {"id": "4", "label": "Lay & bury", "x": 0.85, "y": 0.55}],
                 "edges": [["1", "2"], ["2", "3"], ["3", "4"]]}},
            {"type": "text", "narration": "Then the cable is loaded onto a specialized ship, coiled inside giant tanks. A single ship can carry thousands of kilometers of cable in one trip.",
             "data": {"kicker": "Cable ship", "text": "Thousands of kilometers of cable in a single trip", "highlight": ["Thousands"]}},
            {"type": "text", "narration": "Near the coast, the ship tows an underwater plough that cuts a trench and buries the cable, often a meter or more below the seabed.",
             "data": {"kicker": "Shallow water", "text": "An underwater plough buries the cable in the seabed", "highlight": ["plough", "buries"]}},
            {"type": "line_chart", "narration": "But in the deep ocean, the cable is simply lowered and left lying on the bottom, following every hill and valley of the seabed. Down there, almost nothing can hurt it.",
             "data": {"title": "Seabed profile (illustrative)", "color": "accent", "ymax": 10,
                      "points": [[0, 9.5], [1, 9], [2, 6], [3, 3], [4, 2.2], [5, 3], [6, 1.5], [7, 2.5], [8, 2], [9, 3.5], [10, 6.5], [11, 9], [12, 9.5]],
                      "xlabels": [[0, "USA"], [6, "Mid-Atlantic"], [12, "Spain"]]}},
            {"type": "text", "narration": "Today, this is almost routine. But the first time anyone tried it, more than a century and a half ago, it ended in one of the most spectacular failures in engineering history.",
             "data": {"text": "The first attempt was a disaster", "highlight": ["disaster"]}},
        ]},
        {"n": 3, "title": "The first cable", "title_youtube": "The 1858 disaster", "scenes": [
            {"type": "timeline", "narration": "In 1858, engineers laid the first cable across the Atlantic, from Ireland to Newfoundland.",
             "data": {"title": "Crossing the Atlantic", "focus": 0, "events": [
                 {"year": 1858, "label": "First transatlantic cable"}, {"year": 1866, "label": "First lasting cable"},
                 {"year": 1956, "label": "First telephone cable"}, {"year": 1988, "label": "First fiber optic cable"},
                 {"year": 2017, "label": "MAREA"}]}},
            {"type": "map_route", "narration": "It was a telegraph cable. No light, no fiber. Just copper wire carrying electrical pulses that operators read as dots and dashes.",
             "data": {"bbox": [-70, 38, 5, 62], "routes": [{"points": CABLE_1858, "label": "1858"}],
                      "points": [{"lon": -10.35, "lat": 51.93, "label": "Ireland", "anchor": "mb"}, {"lon": -53.37, "lat": 47.88, "label": "Newfoundland", "anchor": "mt"}]}},
            {"type": "big_number", "narration": "Both sides of the ocean celebrated. But the cable was painfully slow. A message from Queen Victoria to the American president, just ninety-eight words, took around sixteen hours to get through.",
             "data": {"kicker": "Queen Victoria's 98-word message", "value": "16 hours", "caption": "to send across the Atlantic", "color": "accent2"}},
            {"type": "stamp", "narration": "Then it got worse. To speed it up, an engineer pushed much higher voltages through the line. The insulation failed, and after about three weeks, the cable went dead.",
             "data": {"doc_title": "Atlantic Telegraph 1858", "text": "Dead"}},
            {"type": "timeline", "narration": "But engineers didn't give up. In 1866, a giant ship called the Great Eastern laid a new cable that finally worked. Messages that took ten days by ship now crossed the ocean in minutes.",
             "data": {"title": "Crossing the Atlantic", "focus": 1, "events": [
                 {"year": 1858, "label": "First transatlantic cable"}, {"year": 1866, "label": "The Great Eastern succeeds"},
                 {"year": 1956, "label": "First telephone cable"}, {"year": 1988, "label": "First fiber optic cable"},
                 {"year": 2017, "label": "MAREA"}]}},
            {"type": "timeline", "narration": "More than a century later, in 1988, the first fiber optic cable crossed the Atlantic. Instead of electricity, it used light. And light has one big problem.",
             "data": {"title": "Crossing the Atlantic", "focus": 3, "events": [
                 {"year": 1858, "label": "First transatlantic cable"}, {"year": 1866, "label": "The Great Eastern succeeds"},
                 {"year": 1956, "label": "First telephone cable"}, {"year": 1988, "label": "Light replaces electricity"},
                 {"year": 2017, "label": "MAREA"}]}},
            {"type": "text", "narration": "If you're enjoying this, subscribe. Every week we explain another piece of hidden engineering that keeps the world running.",
             "data": {"kicker": "Hidden Engineering", "text": "Subscribe for a new hidden system every week", "highlight": ["Subscribe"]}},
        ]},
        {"n": 4, "title": "How light crosses an ocean", "title_youtube": "How light crosses an ocean", "scenes": [
            {"type": "diagram", "narration": "Even in the purest glass, light slowly fades as it travels. After around a hundred kilometers, the signal becomes too weak to read.",
             "data": {"title": "The signal fades", "nodes": [{"id": "a", "label": "Shore station", "x": 0.12, "y": 0.55}, {"id": "b", "label": "Too weak to read", "x": 0.88, "y": 0.55, "color": "red"}],
                      "edges": [["a", "b", "~100 km"]], "pulse": True, "pulse_period": 3}},
            {"type": "diagram", "narration": "So every fifty to a hundred kilometers, engineers place a repeater. It's a sealed metal cylinder on the cable that boosts the light and sends it on to the next one.",
             "data": dict(REPEATERS, title="Repeaters boost the light")},
            {"type": "text", "narration": "And this is where that copper layer comes in. Repeaters need electricity. But there are no power outlets at the bottom of the ocean.",
             "data": {"text": "No power outlets at the bottom of the ocean", "highlight": ["power", "ocean"]}},
            {"type": "big_number", "narration": "So stations on the coast push direct current through the copper, at up to around fifteen thousand volts, to feed every repeater along the line.",
             "data": {"kicker": "Power fed from the shore", "value": "15,000 V", "caption": "through the copper layer", "color": "accent2"}},
            {"type": "big_number", "narration": "And they're designed to run for around twenty-five years without maintenance, in total darkness, under crushing pressure.",
             "data": {"kicker": "Design life", "value": "25 years", "caption": "no maintenance, total darkness"}},
            {"type": "versus", "narration": "So why not just use satellites? Two reasons. Speed, and capacity.",
             "data": {"left": {"name": "Cable", "lines": ["Hundreds of Tbps", "~70 ms round trip"], "title_color": "accent"},
                      "right": {"name": "Satellite", "lines": ["Far less capacity", "~600 ms round trip"]}}},
            {"type": "bars", "narration": "A traditional satellite sits about thirty-six thousand kilometers above the Earth. A round trip through it takes around half a second. Through a cable, New York to London and back takes well under a tenth of a second.",
             "data": {"title": "Round trip, New York – London", "highlight": 0, "bars": [
                 {"label": "Undersea cable", "value": 70, "display": "~70 ms"}, {"label": "Geostationary satellite", "value": 600, "display": "~600 ms", "color": "red"}]}},
            {"type": "text", "narration": "Newer satellites in low orbit are much faster. But all of them together still carry only a small fraction of what the cables carry.",
             "data": {"text": "Satellites carry only a small fraction of the traffic", "highlight": ["fraction"]}},
        ]},
        {"n": 5, "title": "When cables break", "title_youtube": "When cables break", "scenes": [
            {"type": "big_number", "narration": "And yes, cables break. Somewhere in the world, it happens around one hundred and fifty to two hundred times a year.",
             "data": {"value": "150-200", "caption": "cable faults every year", "color": "red"}},
            {"type": "list", "narration": "Remember the shallow water? That's where most damage happens. Fishing gear and ship anchors dragged across the seabed cause most faults. Sharks have been filmed biting cables, but they cause almost none.",
             "data": {"title": "What breaks cables", "items": ["Fishing gear", "Ship anchors", "Earthquakes & landslides", "Sharks (almost never)"], "marks": ["x", "x", "x", "check"]}},
            {"type": "diagram", "narration": "When a cable breaks, a repair ship sails to the spot, drags a hook along the seabed to catch it, lifts both ends onto the deck, splices in a new section, tests it, and lowers it back down.",
             "data": {"title": "How a cable is repaired", "nodes": [
                 {"id": "1", "label": "Locate the fault", "x": 0.12, "y": 0.45}, {"id": "2", "label": "Hook the cable", "x": 0.37, "y": 0.62},
                 {"id": "3", "label": "Splice & test", "x": 0.63, "y": 0.45}, {"id": "4", "label": "Lower it back", "x": 0.88, "y": 0.62}],
                 "edges": [["1", "2"], ["2", "3"], ["3", "4"]]}},
            {"type": "text", "narration": "Most of the time, you never notice. Traffic is instantly rerouted through other cables.",
             "data": {"text": "Traffic is rerouted. You never notice.", "highlight": ["never"]}},
            {"type": "map_route", "narration": "But some places have no backup. In January 2022, a massive underwater volcano erupted near Tonga, in the South Pacific.",
             "data": {"bbox": [170, -28, 192, -12], "routes": [{"points": TONGA, "label": "Tonga's only international cable", "color": "red"}],
                      "points": [{"lon": 184.8, "lat": -21.14, "label": "Tonga", "anchor": "lm", "color": "red"}, {"lon": 178.44, "lat": -18.14, "label": "Fiji", "anchor": "rm"}]}},
            {"type": "stamp", "narration": "The eruption cut the single international cable connecting the country to the rest of the world. Almost overnight, Tonga was nearly offline.",
             "data": {"doc_title": "Tonga · January 2022", "text": "Offline"}},
            {"type": "big_number", "narration": "It took about five weeks before a repair ship could restore the connection.",
             "data": {"value": "5 weeks", "caption": "until the cable was repaired", "color": "red"}},
            {"type": "map_route", "narration": "Some routes are also chokepoints. A large share of the traffic between Europe and Asia squeezes through Egypt and the Red Sea, a few narrow paths that much of the world depends on.",
             "data": {"bbox": [-5, 2, 80, 50], "routes": [{"points": EGYPT, "label": "Europe – Asia", "color": "accent"}],
                      "points": [{"lon": 31.2, "lat": 30.0, "label": "Egypt", "anchor": "mt", "color": "red"}]}},
            {"type": "list", "narration": "So who owns all this? For decades, telecom companies built most cables. Today, tech giants like Google, Meta, Microsoft and Amazon fund many of the new ones, and use a huge share of the capacity.",
             "data": {"title": "Who builds the new cables", "items": ["Google", "Meta", "Microsoft", "Amazon", "Telecom operators"]}},
        ]},
        {"n": 6, "title": "The answer", "card": False, "title_youtube": "The answer", "scenes": [
            {"type": "cross_section", "narration": "So how does a cable as thin as a garden hose carry the internet across an ocean? Light, trapped in glass thinner than a hair, boosted every few dozen kilometers by machines powered from the shore, lying on the seabed for decades.",
             "data": {"layers": DEEP, "highlight": 0, "title": "The whole answer"}},
            {"type": "map_route", "narration": "Every message, every video call, every video that crosses an ocean travels this way. The internet isn't in the sky. It's at the bottom of the sea.",
             "data": {"bbox": WORLD_BBOX, "routes": WORLD_ROUTES, "title": "The internet is at the bottom of the sea"}},
            {"type": "end_screen", "minDuration": 20, "narration": "And if you think that's hidden, wait until you see why planes almost never fly in a straight line. That's the next video.",
             "data": {"text": "Next hidden system", "next_title": "Why planes don't fly in straight lines", "next_label": "Watch next", "sub_label": "Subscribe"}},
        ]},
    ],
    "short": {
        "title": "99% of the internet is under the ocean 🌊 #shorts",
        "description": "The internet isn't in the sky. Full video on the channel. #engineering #internet #howitworks",
        "scenes": [
            {"type": "big_number", "narration": "Ninety-nine percent of the internet between continents doesn't fly through the air.",
             "data": {"value": "99%", "caption": "of intercontinental data"}},
            {"type": "map_route", "narration": "It runs through cables on the bottom of the ocean, some almost eight kilometers deep.",
             "data": {"bbox": [-85, 22, 8, 58], "routes": [{"points": MAREA}]}},
            {"type": "cross_section", "narration": "Inside, glass fibers ten times thinner than a hair carry the data as light, with copper feeding power to boosters every seventy kilometers.",
             "data": {"layers": DEEP, "highlight": 0}},
            {"type": "text", "narration": "And when a volcano cut Tonga's only cable, the whole country went nearly offline for weeks. Full story on the channel.",
             "data": {"text": "A volcano took a whole country offline", "highlight": ["volcano", "offline"]}},
        ],
    },
}

out = Path(__file__).with_suffix(".json")
out.write_text(json.dumps(script, ensure_ascii=False, indent=1), "utf-8")
words = sum(len(s.get("narration", "").split()) for c in script["chapters"] for s in c["scenes"])
print(f"{out.name}: {sum(len(c['scenes']) for c in script['chapters'])} escenas, {words} palabras")
