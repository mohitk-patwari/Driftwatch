"""Deterministic prose generation. No LLM — word banks + a seeded shuffle.

Same (seq, style, weather) always produces the same dispatch; the voice only
moves because drift.py moves the style vector between runs.
"""
import hashlib
import random

# Each lexicon has two flavors (ornate/plain, chosen by austerity) of
# free-standing clauses that read naturally joined with commas and "and",
# plus one image line per weather label used to seed the weather sentence.
LEXICON_WORDS = {
    "tidal": {
        "ornate": [
            "the tide draws back over stones it has smoothed for years",
            "brine climbs the pilings and hangs there, deciding",
            "the estuary keeps its mouth half open through the grey hour",
            "a line of foam marks where the last swell surrendered",
            "the shoreline exhales salt into air already thick with it",
            "gulls hold their distance from water offering nothing today",
            "the jetty stands drowned to the knee, patient about it",
            "somewhere past the breakers the sea keeps a ledger no one reads",
            "the mudflats hoard the low light until the tide reclaims it",
            "a channel marker leans, rehearsing its own collapse",
        ],
        "plain": [
            "the tide is out again",
            "water sits low along the flats",
            "the pilings are wet to the same mark as yesterday",
            "gulls stand on the sandbar",
            "the channel is calm this morning",
            "the jetty is still standing",
            "the estuary looks the same as it did last week",
            "nothing moved on the water today",
            "the sea is flat past the breakers",
            "the shoreline held its shape overnight",
        ],
        "weather": {
            "clear": "the horizon is drawn in one clean line",
            "cloud": "a grey ceiling sits low over the water",
            "fog": "the shoreline dissolves a few boat-lengths out",
            "drizzle": "a fine rain pocks the flats without committing",
            "rain": "rain stitches the surface from bank to bank",
            "shower": "a squall crosses fast and leaves the pilings dark",
            "storm": "the swell is up and the jetty takes the worst of it",
            "unobserved": "no reading came back from the coast today",
        },
    },
    "mineral": {
        "ornate": [
            "the quarry keeps its silence the way it always has",
            "strata stack up the cliff face like an argument nobody finished",
            "a fault line runs the length of the ridge, patient as ever",
            "loose scree ticks downhill on its own schedule",
            "the old cuts in the rock have started to soften at the edges",
            "granite holds the last of the day's heat long after dark",
            "a boulder field spreads below the ridge, going nowhere",
            "the cliff has shed another inch since anyone last measured",
            "mineral veins catch what light there is and give little back",
            "the outcrop wears the same weather it wore a thousand years ago",
        ],
        "plain": [
            "the rock face is unchanged since yesterday",
            "the quarry is quiet",
            "no new cracks have opened in the cliff",
            "the ground here is mostly stone",
            "the ridge looks the same from every angle today",
            "loose gravel covers the lower slope",
            "the cliff face is dry",
            "nothing has shifted on the scree slope",
            "the outcrop is bare rock, nothing growing on it",
            "the quarry walls held through the night",
        ],
        "weather": {
            "clear": "light sits flat and hard on the exposed stone",
            "cloud": "the cliffs have gone the color of old cement",
            "fog": "the ridge line disappears past the first talus slope",
            "drizzle": "a thin wet film darkens the granite without pooling",
            "rain": "runoff finds the old cracks and follows them down",
            "shower": "a short hard rain scours the ledges and quits",
            "storm": "loose scree shifts somewhere above and nobody goes to look",
            "unobserved": "the survey returned nothing from the rock today",
        },
    },
    "avian": {
        "ornate": [
            "a wing beat crosses the strait and nothing else moves",
            "the colony keeps its usual argument on the far rocks",
            "something high and silent rides the thermal without effort",
            "a single call goes unanswered across open water",
            "the roost has thinned since the season turned",
            "feathers mark the tideline where a gull gave up its meal",
            "a flight line forms and breaks and forms again",
            "the birds keep a memory of a coast that never existed",
            "wingtips cut the fog before the rest of the bird arrives",
            "the nesting ledge holds three birds and one argument",
        ],
        "plain": [
            "a few birds are on the water",
            "the gulls are quiet today",
            "nothing much is flying",
            "the birds are staying close to shore",
            "one bird crossed the bay this morning",
            "the roost looks empty from here",
            "no unusual birds were seen today",
            "the flock is smaller than last week",
            "the birds ignored the weather entirely",
            "a gull sat on the same post as yesterday",
        ],
        "weather": {
            "clear": "birds hold a high, unbothered line across open sky",
            "cloud": "wings cut a flat grey with nothing to rise toward",
            "fog": "calls carry from birds that cannot be seen",
            "drizzle": "a few birds keep low, unwilling to commit to flight",
            "rain": "the flock has gone to ground somewhere out of sight",
            "shower": "birds scatter ahead of the squall and do not return yet",
            "storm": "nothing flies; even the gulls have taken shelter",
            "unobserved": "no wingbeat crossed the sensor's range today",
        },
    },
    "mechanical": {
        "ornate": [
            "the sensor array keeps its patient, indifferent watch",
            "somewhere in the housing a relay clicks for no one",
            "the mast holds its post against a coast that isn't there",
            "cable runs disappear into ground that was never surveyed",
            "the instruments log a coastline with more patience than it deserves",
            "a gauge needle drifts a fraction and no one corrects it",
            "the uplink hums through another cycle, unremarked",
            "rust has started at the seams, on schedule",
            "the station runs itself through another indifferent hour",
            "a warning light blinks at a threshold nobody set",
        ],
        "plain": [
            "the sensors are working",
            "nothing needs fixing today",
            "the equipment ran normally overnight",
            "power levels are steady",
            "the readings came in on schedule",
            "no faults were logged",
            "the mast is upright and secure",
            "the uplink connected without issue",
            "maintenance is not due yet",
            "the station reported normally",
        ],
        "weather": {
            "clear": "the instruments run clean with nothing to correct for",
            "cloud": "the sensors log a flat grey reading, nothing remarkable",
            "fog": "the cameras return a blur past thirty meters",
            "drizzle": "moisture beads on the housing but the readings hold steady",
            "rain": "the drainage channels are working exactly as designed",
            "shower": "a burst of static crossed the line during the worst of it",
            "storm": "the mast is logging vibration above its usual tolerance",
            "unobserved": "the uplink returned nothing usable today",
        },
    },
    "botanical": {
        "ornate": [
            "salt-grass leans the way it always leans, away from the water",
            "the dune scrub has claimed another foot of open sand",
            "something green persists where nothing should grow at all",
            "the marsh keeps its slow, patient argument with the tide",
            "roots hold the dune together against a coast that keeps testing it",
            "a single stand of reed marks where fresh water used to run",
            "the scrub has gone the color of the season without asking",
            "green things keep growing toward a sea that isn't really there",
            "the marsh grass records the tide better than any gauge does",
            "something in the dune line is flowering out of season",
        ],
        "plain": [
            "the grass along the dune is still green",
            "nothing has died back this week",
            "the marsh plants look the same as always",
            "growth is slow this time of year",
            "the scrub hasn't changed much",
            "the reeds are standing upright",
            "no new growth was noted today",
            "the dune vegetation is holding steady",
            "the marsh looks unchanged from the last visit",
            "the plants seem unaffected by the weather",
        ],
        "weather": {
            "clear": "the scrub along the dune holds still in dry light",
            "cloud": "the salt-grass has gone dull under the flat sky",
            "fog": "the marsh reeds stand half-erased in the haze",
            "drizzle": "leaves along the dune line hold a fine bead of wet",
            "rain": "the marsh is drinking everything the sky sends down",
            "shower": "the grasses bend hard and spring back once it passes",
            "storm": "something in the dune scrub has been flattened overnight",
            "unobserved": "no growth reading came back from the marsh today",
        },
    },
}


def _wordcount(s):
    return len(s.split())


def _temp_clause(temp_c):
    if temp_c is None:
        return "the instruments recorded no temperature"
    if temp_c < 18:
        desc = "sharp"
    elif temp_c < 24:
        desc = "mild"
    elif temp_c < 29:
        desc = "warm"
    else:
        desc = "heavy"
    return f"the air reads {desc} at {temp_c:.0f}°C"


def _wind_clause(wind_kph):
    if wind_kph is None:
        return "the wind gauge stayed silent"
    if wind_kph < 10:
        desc = "barely moving"
    elif wind_kph < 25:
        desc = "steady"
    elif wind_kph < 40:
        desc = "pushing hard"
    else:
        desc = "working the whole coast"
    return f"wind is {desc} at {wind_kph:.0f} kph"


def _build_sentence(rng, pool, used, target, seed_fragment=None):
    fragments = []
    words = 0
    if seed_fragment:
        fragments.append(seed_fragment)
        words += _wordcount(seed_fragment)
        used.add(seed_fragment)

    candidates = [f for f in pool if f not in used]
    rng.shuffle(candidates)
    for frag in candidates:
        if words >= target - 2:
            break
        fragments.append(frag)
        used.add(frag)
        words += _wordcount(frag)

    if not fragments:
        fragments = [rng.choice(pool)]

    if len(fragments) == 1:
        text = fragments[0]
    else:
        text = ", ".join(fragments[:-1]) + ", and " + fragments[-1]
    text = text[0].upper() + text[1:]
    if not text.endswith((".", "!", "?")):
        text += "."
    return text


def compose(seq, style, weather):
    """Returns (title, body) for one dispatch."""
    seed = "|".join([
        str(seq),
        f"{float(style['sentence_target']):.2f}",
        f"{float(style['austerity']):.4f}",
        style["lexicon"],
        str(weather.get("label")),
        str(weather.get("temp_c")),
        str(weather.get("wind_kph")),
    ])
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())

    bank = LEXICON_WORDS[style["lexicon"]]
    flavor = "plain" if float(style["austerity"]) >= 0.5 else "ornate"
    pool = bank[flavor]
    target = float(style["sentence_target"])

    num_sentences = rng.choice([2, 3, 3, 4])
    weather_idx = rng.randrange(num_sentences)
    weather_seed = bank["weather"].get(weather.get("label"), bank["weather"]["unobserved"])

    used = set()
    sentences = []
    for i in range(num_sentences):
        if i == weather_idx:
            extra = rng.choice([_temp_clause(weather.get("temp_c")),
                                 _wind_clause(weather.get("wind_kph"))])
            seed_fragment = f"{weather_seed}, {extra}"
            sentences.append(_build_sentence(rng, pool, used, target, seed_fragment))
        else:
            sentences.append(_build_sentence(rng, pool, used, target))

    return f"Dispatch {seq}", " ".join(sentences)


def demo():
    weather_cases = [
        {"temp_c": 24.1, "code": 61, "label": "rain", "wind_kph": 12.3},
        {"temp_c": None, "code": None, "label": "unobserved", "wind_kph": None},
    ]
    style = {"sentence_target": 14, "austerity": 0.3, "lexicon": "avian", "repetition_pressure": 0.1}
    for w in weather_cases:
        title, body = compose(1, style, w)
        assert title == "Dispatch 1"
        assert 2 <= body.count(".") + body.count("!") + body.count("?") <= 4
        assert len(body.split()) > 0

    same_a = compose(5, style, weather_cases[0])
    same_b = compose(5, style, weather_cases[0])
    assert same_a == same_b, "compose must be deterministic for identical inputs"

    other = compose(6, style, weather_cases[0])
    assert other != same_a, "different seq must change the body"
    print("compose.py OK:", same_a[1][:80], "...")


if __name__ == "__main__":
    demo()
