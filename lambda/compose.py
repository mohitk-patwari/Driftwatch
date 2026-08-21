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
            "the low tide leaves a rime of salt on everything it touched",
            "a heron stands motionless at the tideline, waiting on nothing",
            "the current runs sideways against the pilings today",
            "kelp strands mark the last high-water line in a ragged row",
            "the bar has shifted again since the last survey",
            "a single buoy rides the swell, counting nothing",
            "salt has worked white lines into every plank of the jetty",
            "the current drags a single gull backward before it corrects",
            "driftwood collects in the same corner it always collects in",
            "the tideline shifts a hand's width and nobody marks it",
            "cormorants dry their wings on a post that leans further each year",
            "the estuary mouth narrows with every season's silt",
            "a rope, long since cut loose, drifts against the pilings",
            "spray reaches the road only on the roughest days",
            "the flats hold the shape of yesterday's low tide",
            "a crab shell bleaches white on the upper strand",
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
            "the water is clear near the shore",
            "a boat passed through around midday",
            "the tide chart matched what actually happened",
            "salt crust has formed on the lower pilings",
            "the current is running the usual direction",
            "the sandbar is exposed at low tide",
            "the water level matches yesterday's mark",
            "no debris washed up overnight",
            "the boat ramp is clear",
            "the tide came in on schedule",
            "the buoy is still in its usual spot",
            "the wind has not shifted the sandbar",
            "the dock is dry at low tide",
            "nothing unusual washed ashore",
            "the water is the same color as yesterday",
            "the mooring lines are holding",
        ],
        "weather": {
            "clear": [
                "the horizon is drawn in one clean line",
                "light lies flat and bright across the whole channel",
                "the water gives back the sky without a ripple",
                "the flats hold a hard, clean glare past noon",
                "not a cloud stands between the tide and the sun",
                "the horizon holds steady, nothing to blur it",
            ],
            "cloud": [
                "a grey ceiling sits low over the water",
                "the sky presses down grey over the whole inlet",
                "cloud cover flattens the light across the water",
                "no shadow falls anywhere along the shoreline",
                "the ceiling hangs low and gives nothing away",
                "a dull grey sits over the estuary all morning",
            ],
            "fog": [
                "the shoreline dissolves a few boat-lengths out",
                "the channel markers vanish before the first bend",
                "fog sits thick over the flats and won't lift",
                "the far shore has gone entirely out of view",
                "visibility drops to a few boat-lengths and holds",
                "the mist hasn't burned off since first light",
            ],
            "drizzle": [
                "a fine rain pocks the flats without committing",
                "a thin drizzle beads on the rail and drips",
                "fine rain drifts sideways without ever committing",
                "the flats take a light wetting, nothing more",
                "drizzle hangs in the air more than it falls",
                "a soft rain blurs the line between water and sky",
            ],
            "rain": [
                "rain stitches the surface from bank to bank",
                "steady rain works the whole length of the channel",
                "the surface pocks under a rain that won't let up",
                "water rises to meet water coming down",
                "rain drums the pilings without pause",
                "the tide takes on rain faster than it can shed it",
            ],
            "shower": [
                "a squall crosses fast and leaves the pilings dark",
                "a hard shower crosses the flats and moves on",
                "rain comes in bursts, gone before it settles",
                "a squall darkens the water and passes quickly",
                "the shower blows through and leaves the light changed",
                "brief rain hammers the jetty then quits",
            ],
            "storm": [
                "the swell is up and the jetty takes the worst of it",
                "the channel churns under a sky gone the color of iron",
                "waves break well past where they usually break",
                "the storm has the whole estuary working hard",
                "wind drives the tide higher than the charts allow",
                "the jetty takes green water over the rail",
            ],
            "unobserved": [
                "no reading came back from the coast today",
                "the coast sent back nothing usable this run",
                "the sensor found no signal off the water today",
                "no weather came back from the station this time",
                "the reading failed somewhere between the coast and here",
                "today's forecast never made it back",
            ],
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
            "a seam of quartz catches the light and lets it go",
            "the old quarry road has gone soft with disuse",
            "frost has worked a new crack into the north face",
            "the talus pile grows an inch nobody will notice",
            "lichen has claimed another patch of the shaded rock",
            "the survey stakes lean at the same angle as last year",
            "the last blast face still smells faintly of powder",
            "a rusted cart track disappears under fresh scree",
            "the quarry pool holds the sky better than any mirror should",
            "wind has scoured a new hollow into the soft stone",
            "the survey flag has faded to the color of the rock itself",
            "a single spark of mica catches the eye and lets it go",
            "the access gate hangs open on a hinge nobody fixed",
            "heat shimmers off the exposed cut by midday",
            "the old drill holes are filling in with dust",
            "a hawk uses the updraft off the cliff face and nothing else",
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
            "the gravel path is dry",
            "no new rockfall was reported",
            "the survey markers are still in place",
            "the north face is in shadow most of the day",
            "the access road is passable",
            "dust covers the lower ledges",
            "the equipment shed is locked",
            "no blasting is scheduled this week",
            "the water table in the pit is unchanged",
            "the perimeter fence is intact",
            "the last inspection found nothing to flag",
            "the stockpile hasn't grown or shrunk",
            "the crusher is idle today",
            "no new dust complaints were filed",
            "the haul road is graded and dry",
            "the site is secure for the night",
        ],
        "weather": {
            "clear": [
                "light sits flat and hard on the exposed stone",
                "the stone holds a hard glare with nothing to soften it",
                "not a cloud crosses the ridge all day",
                "sunlight bakes the exposed rock white",
                "the quarry walls throw back a flat, dry light",
                "clear sky leaves the cliff face fully exposed",
            ],
            "cloud": [
                "the cliffs have gone the color of old cement",
                "a flat grey sits over the whole ridge line",
                "cloud cover drains the color out of the stone",
                "the cliffs sit under a low, even grey",
                "no shadow moves across the rock face today",
                "overcast light flattens every crack in the granite",
            ],
            "fog": [
                "the ridge line disappears past the first talus slope",
                "the outcrop is lost somewhere past the first bend",
                "fog fills the quarry and won't burn off",
                "the ridge has gone entirely out of sight",
                "visibility ends a few meters past the scree",
                "mist sits in the cuts and hides the far wall",
            ],
            "drizzle": [
                "a thin wet film darkens the granite without pooling",
                "a fine wet settles on the stone and stays",
                "light rain darkens the rock without running",
                "drizzle beads on the granite and clings there",
                "the cliff face takes a faint wetting, nothing more",
                "a thin rain drifts across the quarry, barely felt",
            ],
            "rain": [
                "runoff finds the old cracks and follows them down",
                "steady rain finds every seam in the rock",
                "water runs the cliff face top to bottom",
                "rain works the cracks it always works",
                "the quarry floor is running with runoff",
                "rain drums the ledges without pause",
            ],
            "shower": [
                "a short hard rain scours the ledges and quits",
                "a hard burst scours the scree and quits",
                "a short rain hammers the outcrop then clears",
                "rain comes fast, strips the dust, and moves off",
                "the shower leaves the granite dark and streaked",
                "a quick storm passes over the ridge and is gone",
            ],
            "storm": [
                "loose scree shifts somewhere above and nobody goes to look",
                "scree lets go somewhere above and no one checks",
                "the ridge takes wind hard enough to move loose rock",
                "storm light turns the whole quarry the color of slate",
                "something shifted on the talus slope overnight",
                "the cliff face is taking more than its usual weather",
            ],
            "unobserved": [
                "the survey returned nothing from the rock today",
                "the rock sent back no reading this time",
                "the sensor found nothing on the ridge today",
                "no survey data made it back from the quarry",
                "the station logged nothing off the stone",
                "today's rock reading never came through",
            ],
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
            "a heron holds its post at the water's edge, unmoved",
            "the far rocks carry more argument than birds",
            "something small crosses low and fast, gone before it's named",
            "the colony's noise has settled into its evening register",
            "a single feather turns slowly on the current",
            "the roost holds its shape against a sky doing nothing",
            "a cormorant surfaces with nothing and dives again anyway",
            "the tern colony argues about the same patch of sand it always argues about",
            "something crosses high enough to be only a shape",
            "a wing print is pressed into the wet sand and already fading",
            "the gulls have worked out a hierarchy nobody wrote down",
            "a single egg sits unattended on the upper ledge",
            "the flock takes the same bearing it took yesterday",
            "molted feathers collect along the tideline in small drifts",
            "a young bird tests the air and doesn't trust it yet",
            "the roost counts one fewer than last week, unexplained",
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
            "a heron stood at the water's edge this morning",
            "the count was about the same as last week",
            "no unusual calls were heard today",
            "a few birds crossed overhead at dusk",
            "the nesting site looks undisturbed",
            "the shorebirds kept their usual distance",
            "the nest count is unchanged",
            "a banded bird was seen again today",
            "the feeding area was busy this morning",
            "no dead birds were found on the beach",
            "the chicks are growing as expected",
            "the colony is quieter in the afternoons",
            "migration hasn't started yet this season",
            "the usual species were present today",
            "no predators were spotted near the roost",
            "the birds returned to the same perch",
        ],
        "weather": {
            "clear": [
                "birds hold a high, unbothered line across open sky",
                "wings hold steady against a sky with nothing in it",
                "the birds climb high where the light is clean",
                "not a cloud interrupts the flight line today",
                "gulls ride the thermals without a single course change",
                "clear air puts the whole flock up high",
            ],
            "cloud": [
                "wings cut a flat grey with nothing to rise toward",
                "birds hold low under a flat, grey ceiling",
                "wingbeats cut a sky with nothing to rise toward",
                "the flock stays close to the water under cloud",
                "grey light flattens every bird against the sky",
                "no bird climbs far under today's low ceiling",
            ],
            "fog": [
                "calls carry from birds that cannot be seen",
                "birds call from somewhere inside the fog and stay hidden",
                "wings pass overhead unseen, only the sound arriving",
                "the roost has vanished into the mist entirely",
                "fog swallows the flock a few wingbeats out",
                "nothing visible flies, though the calls keep coming",
            ],
            "drizzle": [
                "a few birds keep low, unwilling to commit to flight",
                "a few birds sit low, waiting out the wet",
                "wings stay folded while the drizzle holds",
                "the flock keeps close to shore in the fine rain",
                "birds move little, unwilling to fly wet",
                "a light rain keeps most wings on the ground",
            ],
            "rain": [
                "the flock has gone to ground somewhere out of sight",
                "the birds have gone to ground until this passes",
                "no wing lifts while the rain holds steady",
                "the roost sits empty, everything sheltering",
                "rain has cleared the sky of every bird",
                "the flock waits out the rain somewhere unseen",
            ],
            "shower": [
                "birds scatter ahead of the squall and do not return yet",
                "a burst of rain empties the sky fast",
                "wings break for cover as the shower crosses",
                "the flock scatters, then starts drifting back",
                "birds ride out the short rain low and close",
                "gulls scatter, then start drifting back once it clears",
            ],
            "storm": [
                "nothing flies; even the gulls have taken shelter",
                "nothing flies; even the gulls have gone to ground",
                "the storm has emptied the sky of every wing",
                "no bird risks the air while this holds",
                "the roost is silent, everything sheltering",
                "wind has grounded the whole flock",
            ],
            "unobserved": [
                "no wingbeat crossed the sensor's range today",
                "no wingbeat registered on the sensor today",
                "the range came back empty of any bird",
                "nothing crossed the station's field today",
                "the count returned nothing this run",
                "today's bird reading never came through",
            ],
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
            "the backup battery holds its charge without complaint",
            "a firmware counter ticks over unnoticed",
            "the housing seal has started to show its age",
            "diagnostics return green across every panel",
            "the antenna holds its bearing through another cycle",
            "a log entry closes itself out, satisfied with nothing",
            "a spare fuse sits untouched in its slot, waiting",
            "the enclosure hums at a pitch only the equipment notices",
            "condensation traces the same path down the same panel",
            "a cable tie has finally given up after years of sun",
            "the calibration log shows nothing worth flagging",
            "solar input tracks the day exactly as the model predicts",
            "an old firmware note still references hardware long since replaced",
            "the backup link stands ready, untested since installation",
            "a single LED blinks in a pattern only the technician remembers",
            "the mounting bolts have not backed out since the last check",
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
            "the battery is fully charged",
            "the last diagnostic passed without issue",
            "the antenna is aligned correctly",
            "logs are being written on schedule",
            "the enclosure is sealed and dry",
            "firmware is up to date",
            "the solar panel is clean",
            "signal strength is normal",
            "the last software update installed cleanly",
            "no alerts fired overnight",
            "the case temperature is within range",
            "the ground connection tested fine",
            "spare parts inventory is current",
            "the clock is synced correctly",
            "no packet loss was recorded",
            "the mount is stable in the wind",
        ],
        "weather": {
            "clear": [
                "the instruments run clean with nothing to correct for",
                "the array runs a clean baseline with nothing to flag",
                "sensors report a flat, uneventful sky",
                "no correction was needed on any channel today",
                "the station logs clear conditions without incident",
                "instruments hold steady readings straight through",
            ],
            "cloud": [
                "the sensors log a flat grey reading, nothing remarkable",
                "the array reports an even, uneventful overcast",
                "no anomaly shows in today's cloud reading",
                "the station's optics see nothing but grey",
                "overcast registers as a flat line on every channel",
                "sensors log the ceiling without a single spike",
            ],
            "fog": [
                "the cameras return a blur past thirty meters",
                "the cameras return nothing past thirty meters",
                "optical sensors report a wall of blur",
                "visibility readings bottom out across the array",
                "the lens sees fog and little else today",
                "the station's cameras are effectively blind past the dock",
            ],
            "drizzle": [
                "moisture beads on the housing but the readings hold steady",
                "moisture collects on the housing, readings hold steady",
                "a light wet coats the array without affecting output",
                "sensors shrug off the fine rain, no change logged",
                "the housing beads up but the signal stays clean",
                "drizzle registers on the gauge and nowhere else",
            ],
            "rain": [
                "the drainage channels are working exactly as designed",
                "the drainage system runs exactly as designed",
                "rain sensors log steady input, nothing unusual",
                "runoff channels are handling the load fine",
                "the array logs rain without any fault",
                "water moves through the system as engineered",
            ],
            "shower": [
                "a burst of static crossed the line during the worst of it",
                "a burst of static crossed the line mid-shower",
                "the signal blipped once and cleared",
                "a short interference spike showed during the worst of it",
                "the array logged a brief dropout, now stable",
                "readings jumped during the burst, then settled",
            ],
            "storm": [
                "the mast is logging vibration above its usual tolerance",
                "wind load is pushing the structure past its normal range",
                "the array is registering stress it doesn't usually see",
                "vibration readings are elevated across every channel",
                "the station is running hot under today's wind load",
                "the mast has flagged its own tolerance twice this hour",
            ],
            "unobserved": [
                "the uplink returned nothing usable today",
                "the uplink returned nothing usable this run",
                "no signal made it back from the array",
                "the station logged a blank reading today",
                "connection dropped before any data came through",
                "today's telemetry never arrived",
            ],
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
            "a stand of sea lavender holds its color past its season",
            "the dune's leeward side has gone thick with new growth",
            "something has been grazing the low scrub again",
            "seed heads bow the grass without breaking it",
            "the marsh edge has crept a little further inland",
            "moss has taken the shaded side of every post",
            "a stand of pickleweed holds its red long past when it should fade",
            "something has tunneled under the boardwalk overnight",
            "the marsh grass parts around a channel too small to name",
            "seed pods rattle in the wind like something counting",
            "a vine has reached the fence and is deciding what to do next",
            "the dune's shadow line has moved a little further east",
            "insects work the flowering scrub in numbers nobody counted",
            "the reed bed holds water long after the rest of the marsh has dried",
            "something green has taken root in the old boat hull",
            "the grass line remembers a flood no one else does",
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
            "the grass is due for its seasonal die-back",
            "new shoots are visible near the boardwalk",
            "the marsh edge looks the same as last visit",
            "no invasive species were noted today",
            "the dune fencing is holding the sand in place",
            "the reeds have grown taller this month",
            "the boardwalk is clear of overgrowth",
            "no erosion was noted along the path",
            "the wildflowers are still blooming",
            "the marsh smells the same as always",
            "insect activity is normal for the season",
            "the fence line is holding back the sand",
            "no dead patches were found in the scrub",
            "the water level in the marsh is steady",
            "the trail markers are all visible",
            "growth along the path is being managed",
        ],
        "weather": {
            "clear": [
                "the scrub along the dune holds still in dry light",
                "the dune grass stands still under a hard, dry light",
                "nothing stirs in the scrub with the sky this clear",
                "sunlight bleaches the salt-grass a shade paler",
                "the marsh holds its shape under open sky",
                "dry light settles over the whole dune line",
            ],
            "cloud": [
                "the salt-grass has gone dull under the flat sky",
                "the salt-grass has gone dull under flat grey sky",
                "no shadow crosses the marsh under today's overcast",
                "the dune scrub sits colorless under low cloud",
                "grey light flattens every blade along the ridge",
                "the reeds hold still under a sky with nothing in it",
            ],
            "fog": [
                "the marsh reeds stand half-erased in the haze",
                "fog softens the whole dune line to a blur",
                "the scrub has gone grey and indistinct in the mist",
                "visibility drops to a few stalks of grass",
                "the marsh disappears into its own haze",
                "the reeds are there only as shapes in the fog",
            ],
            "drizzle": [
                "leaves along the dune line hold a fine bead of wet",
                "leaves along the dune hold a fine bead of wet",
                "a light rain darkens the salt-grass without soaking it",
                "drizzle settles on the reeds and clings there",
                "the scrub takes a faint wetting, nothing more",
                "fine rain beads on every blade along the ridge",
            ],
            "rain": [
                "the marsh is drinking everything the sky sends down",
                "rain soaks into the dune line without runoff",
                "the reeds bend under steady, soaking rain",
                "water pools between the tussocks after the rain",
                "the scrub is heavy and dark with today's rain",
                "the marsh has taken on all the rain it can hold",
            ],
            "shower": [
                "the grasses bend hard and spring back once it passes",
                "a quick rain flattens the scrub, then it's gone",
                "the reeds take a hard soaking and straighten after",
                "rain hammers the dune line and clears fast",
                "the marsh grass bows under the burst and recovers",
                "a short rain passes and the scrub springs back",
            ],
            "storm": [
                "something in the dune scrub has been flattened overnight",
                "the marsh took real damage in last night's wind",
                "reeds are down in patches across the whole line",
                "the storm has left the scrub torn and leaning",
                "wind has stripped leaves off half the dune line",
                "the dune grass is flattened in long, wind-drawn rows",
            ],
            "unobserved": [
                "no growth reading came back from the marsh today",
                "the sensor found nothing green to report",
                "today's vegetation survey came back empty",
                "no reading made it back from the dune line",
                "the marsh gauge returned nothing usable",
                "today's growth check never came through",
            ],
        },
    },
}

# Measurement clauses (temp/wind), pooled per lexicon like the weather image
# lines. Some entries carry no {val} placeholder at all — picking one of those
# is how a dispatch ends up omitting the numeric reading.
MEASUREMENT_CLAUSES = {
    "tidal": {
        "temp": [
            "the air reads {desc} at {val:.0f}°C",
            "the salt air runs {desc}, {val:.0f}°C on the gauge",
            "it's {desc} over the water, {val:.0f}°C by the reading",
            "the tide brings {desc} air today",
            "heat off the flats sits {desc}",
            "{val:.0f}°C on the gauge, {desc} for the season",
        ],
        "wind": [
            "wind is {desc} at {val:.0f} kph",
            "the wind off the water runs {desc}, {val:.0f} kph",
            "{val:.0f} kph across the flats, {desc} by any measure",
            "the wind is {desc} today",
            "air moves {desc} over the channel",
            "gusts hold {desc} at {val:.0f} kph",
        ],
    },
    "mineral": {
        "temp": [
            "the air reads {desc} at {val:.0f}°C",
            "heat off the rock sits {desc}, {val:.0f}°C on the gauge",
            "the stone holds {desc} air, {val:.0f}°C by the reading",
            "it's {desc} across the quarry today",
            "the ridge sits {desc} in today's air",
            "{val:.0f}°C on the gauge, {desc} for the exposure",
        ],
        "wind": [
            "wind is {desc} at {val:.0f} kph",
            "wind off the ridge runs {desc}, {val:.0f} kph",
            "{val:.0f} kph over the scree, {desc} by any measure",
            "the wind is {desc} up on the ridge today",
            "air moves {desc} across the quarry",
            "gusts hold {desc} at {val:.0f} kph",
        ],
    },
    "avian": {
        "temp": [
            "the air reads {desc} at {val:.0f}°C",
            "the air the birds fly through sits {desc}, {val:.0f}°C",
            "it's {desc} aloft today, {val:.0f}°C by the reading",
            "the air is {desc} for flying today",
            "heat sits {desc} over the roost",
            "{val:.0f}°C on the gauge, {desc} for the season",
        ],
        "wind": [
            "wind is {desc} at {val:.0f} kph",
            "wind under the wings runs {desc}, {val:.0f} kph",
            "{val:.0f} kph today, {desc} by any measure",
            "the wind is {desc} for flying today",
            "air moves {desc} over the roost",
            "gusts hold {desc} at {val:.0f} kph",
        ],
    },
    "mechanical": {
        "temp": [
            "the air reads {desc} at {val:.0f}°C",
            "the sensor logs {desc} air, {val:.0f}°C",
            "the gauge shows {desc}, {val:.0f}°C on the reading",
            "the station logs {desc} conditions today",
            "the array reads {desc} for the hour",
            "{val:.0f}°C on the gauge, {desc} for the run",
        ],
        "wind": [
            "wind is {desc} at {val:.0f} kph",
            "the anemometer logs {desc}, {val:.0f} kph",
            "{val:.0f} kph on the gauge, {desc} by any measure",
            "the wind sensor logs {desc} conditions",
            "the array reads {desc} wind for the hour",
            "gusts hold {desc} at {val:.0f} kph",
        ],
    },
    "botanical": {
        "temp": [
            "the air reads {desc} at {val:.0f}°C",
            "the air over the marsh sits {desc}, {val:.0f}°C",
            "it's {desc} across the dune line, {val:.0f}°C by the reading",
            "the air is {desc} over the scrub today",
            "heat sits {desc} across the marsh",
            "{val:.0f}°C on the gauge, {desc} for the season",
        ],
        "wind": [
            "wind is {desc} at {val:.0f} kph",
            "wind off the dune runs {desc}, {val:.0f} kph",
            "{val:.0f} kph over the marsh, {desc} by any measure",
            "the wind is {desc} across the dune line today",
            "air moves {desc} through the reeds",
            "gusts hold {desc} at {val:.0f} kph",
        ],
    },
}


def _wordcount(s):
    return len(s.split())


def _temp_desc(temp_c):
    if temp_c < 18:
        return "sharp"
    if temp_c < 24:
        return "mild"
    if temp_c < 29:
        return "warm"
    return "heavy"


def _wind_desc(wind_kph):
    if wind_kph < 10:
        return "barely moving"
    if wind_kph < 25:
        return "steady"
    if wind_kph < 40:
        return "pushing hard"
    return "working the whole coast"


def _measurement_clause(kind, value, lexicon, seq):
    if value is None:
        return "the instruments recorded no temperature" if kind == "temp" else "the wind gauge stayed silent"
    desc = _temp_desc(value) if kind == "temp" else _wind_desc(value)
    pool = MEASUREMENT_CLAUSES[lexicon][kind]
    template = pool[_seq_index(len(pool), seq, "measurement", kind, lexicon)]
    return template.format(desc=desc, val=value)


def _build_sentence(rng, pool, used, target, seed_fragment=None, rank=None):
    fragments = []
    words = 0
    if seed_fragment:
        fragments.append(seed_fragment)
        words += _wordcount(seed_fragment)
        used.add(seed_fragment)

    candidates = [f for f in pool if f not in used]
    if rank:
        # Prefer fragments not seen in the last 20 entries (or seen longest
        # ago); rng.random() breaks ties among equally-fresh candidates so
        # selection still varies dispatch to dispatch.
        # ponytail: with ~26 lines/pool and ~2-3 consumed per dispatch, this
        # spaces reuse out but doesn't guarantee zero repeats across a full
        # 20-entry window at high sentence_target. Widen pools further if
        # audits still find repeats closer than ~6-8 dispatches apart.
        candidates.sort(key=lambda f: (-rank.get(f, len(rank)), rng.random()))
    else:
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


def _seq_index(n, *parts):
    """Deterministic index in [0, n) from seq (+ context), independent of the
    prose rng — so weather phrasing/position don't ride on fragment-selection
    draws that can coincidentally repeat."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:4], "big") % n


def compose(seq, style, weather, recent_bodies=None):
    """Returns (title, body) for one dispatch.

    recent_bodies (optional): bodies of the last ~20 entries, used only to
    avoid reusing a body line that already appears verbatim in them.
    """
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

    recent_bodies = recent_bodies or []
    recent_lower = [b.lower() for b in recent_bodies]
    rank = {
        f: next((i for i, b in enumerate(recent_lower) if f in b), len(recent_lower))
        for f in pool
    }

    num_sentences = rng.choice([2, 3, 3, 4])
    label = weather.get("label")
    weather_idx = _seq_index(num_sentences, seq, "position", style["lexicon"], label)
    weather_pool = bank["weather"].get(label, bank["weather"]["unobserved"])
    weather_seed = weather_pool[_seq_index(len(weather_pool), seq, "phrase", style["lexicon"], label)]

    used = set()
    sentences = []
    for i in range(num_sentences):
        if i == weather_idx:
            kind = rng.choice(["temp", "wind"])
            value = weather.get("temp_c") if kind == "temp" else weather.get("wind_kph")
            extra = _measurement_clause(kind, value, style["lexicon"], seq)
            seed_fragment = f"{weather_seed}, {extra}"
            sentences.append(_build_sentence(rng, pool, used, target, seed_fragment, rank))
        else:
            sentences.append(_build_sentence(rng, pool, used, target, rank=rank))

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

    # Weather phrasing must not repeat verbatim across consecutive dispatches,
    # and its sentence position must not be pinned to one slot.
    pool = LEXICON_WORDS[style["lexicon"]]["weather"][weather_cases[0]["label"]]
    phrases_used, positions = set(), set()
    for s in range(1, 9):
        body = compose(s, style, weather_cases[0])[1]
        sentences = body.split(". ")
        hit_i, hit_phrase = next(
            (i, p) for i, sent in enumerate(sentences) for p in pool if p[1:] in sent.lower()
        )
        phrases_used.add(hit_phrase)
        positions.add(hit_i)
    assert len(phrases_used) > 1, "weather phrasing repeats verbatim"
    assert len(positions) > 1, "weather sentence is pinned to one position"

    # Measurement clause (temp/wind) must vary across seqs and sometimes drop
    # the numeric reading entirely.
    temp_texts = {_measurement_clause("temp", 24.0, "tidal", s) for s in range(1, 9)}
    assert len(temp_texts) > 1, "measurement phrasing repeats verbatim"
    assert any("°C" not in t for t in temp_texts), "no dispatch omitted the numeric reading"

    # A body line seen in the last 20 entries must not reappear verbatim.
    mineral_style = {"sentence_target": 14, "austerity": 0.3, "lexicon": "mineral", "repetition_pressure": 0.1}
    mineral_weather = {"temp_c": 20.0, "code": 2, "label": "cloud", "wind_kph": 8.0}
    reused_line = "the old cuts in the rock have started to soften at the edges"
    recent = [f"{reused_line} filler filler filler."]
    for s in range(1, 6):
        body = compose(s, mineral_style, mineral_weather, recent_bodies=recent)[1]
        assert reused_line not in body.lower(), "excluded body line reappeared"

    print("compose.py OK:", same_a[1][:80], "...")


if __name__ == "__main__":
    demo()
