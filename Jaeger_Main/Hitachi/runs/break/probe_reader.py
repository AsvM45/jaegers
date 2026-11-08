"""Probe the rule reader with novel messages. Prints kind(s) and evidence."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tower.graph import WorldGraph
from tower.agents.understand import understand

graph = WorldGraph()

cases = [
    # controls: recently taught phrasing should pass
    ("CTRL outage closed", "Lexington is closed for maintenance from March 16 to March 18."),
    ("CTRL outage will not run", "The San Antonio plant will not run from March 16 through March 18."),
    ("CTRL outage stops", "Assembly at Huntsville stops March 16 through March 18."),
    ("CTRL delay moved", "The airbag module delivery from SUP-17 to San Antonio has been moved from March 15 to March 18."),
    ("CTRL delay was now", "San Antonio receiving: airbag modules from SUP-17, was March 15, now March 18."),
    ("CTRL quality scrap", "Scrap LOT-0001."),
    ("CTRL quality stop using", "Stop using lot LOT-0001."),
    ("CTRL noise cafeteria", "The cafeteria at Lexington is closed from March 16 to March 18."),
    ("CTRL noise tour", "The plant tour will not run at San Antonio from March 16 through March 18."),
    ("CTRL noise picnic scrap", "Please scrap the old brochure. The San Antonio picnic is March 16 and March 17."),

    # outage paraphrases the closed/stops/will-not-run fixes do not cover
    ("OUT will be closed", "Lexington will be closed for maintenance from March 16 to March 18."),
    ("OUT will be closed 2", "San Antonio will be closed from March 16 through March 18."),
    ("OUT closes", "The Huntsville plant closes from March 16 to March 18."),
    ("OUT closes 2", "Jackson closes for maintenance March 16 through March 18."),
    ("OUT set to close", "Lexington is set to close from March 16 to March 18."),
    ("OUT set to close 2", "The Princeton plant is set to close for maintenance from March 16 through March 18."),
    ("OUT not running", "San Antonio is not running from March 16 through March 18."),
    ("OUT isn't running", "The Jackson plant isn't running from March 16 to March 18."),
    ("OUT won't be running", "Greensboro won't be running March 16 through March 18."),
    ("OUT will not be running", "Huntsville will not be running from March 16 to March 18."),
    ("OUT cannot operate", "Princeton cannot operate from March 16 through March 18."),
    ("OUT will not operate", "The Lexington plant will not operate from March 16 to March 18."),
    ("OUT won't operate", "San Antonio won't operate March 16 through March 18."),
    ("OUT halts", "Assembly at Huntsville halts March 16 through March 18."),
    ("OUT halts 2", "Assembly at Greensboro halts from March 16 to March 18."),
    ("OUT downtime", "Planned downtime at Lexington from March 16 through March 18."),
    ("OUT downtime 2", "Huntsville has downtime from March 16 to March 18."),
    ("OUT out of service", "Jackson is out of service from March 16 to March 18."),
    ("OUT out of service 2", "The Greensboro plant is out of service March 16 through March 18."),
    ("OUT out of commission", "Princeton is out of commission from March 16 through March 18."),
    ("OUT cancelled", "Production at Princeton is cancelled from March 16 to March 18."),
    ("OUT cancelled 2", "Builds at Lexington are cancelled March 16 through March 18."),
    ("OUT ceased", "San Antonio ceased operations from March 16 to March 18."),
    ("OUT ceases", "Operations at Jackson cease March 16 through March 18."),
    ("OUT idled", "The Jackson plant is idled from March 16 through March 18."),
    ("OUT idled 2", "Lexington is idled March 16 through March 18."),
    ("OUT shuttered", "The Huntsville plant is shuttered from March 16 to March 18."),
    ("OUT shuttered 2", "Greensboro is shuttered March 16 through March 18."),
    ("OUT power out", "Power is out at Greensboro from March 16 to March 18."),
    ("OUT no power", "Lexington has no power from March 16 through March 18."),
    ("OUT blacked out", "Huntsville is blacked out from March 16 to March 18."),
    ("OUT goes offline", "Princeton goes offline March 16 through March 18."),
    ("OUT goes dark", "Jackson goes dark March 16 through March 18."),
    ("OUT won't be building", "Lexington won't be building from March 16 to March 18."),
    ("OUT not producing", "San Antonio is not producing from March 16 through March 18."),
    ("OUT in maintenance", "Lexington is in maintenance from March 16 to March 18."),
    ("OUT into maintenance", "San Antonio goes into maintenance from March 16 through March 18."),
    ("OUT remain dark", "Huntsville will remain dark from March 16 to March 18."),
    ("OUT sit idle no", "We will idle Princeton from March 16 through March 18."),
    ("OUT knocked out", "The Greensboro plant is knocked out from March 16 to March 18."),
    ("OUT offline for maint no from?", "The line at Huntsville goes offline from March 16 to March 18."),
    ("OUT no assembly", "No assembly at Greensboro from March 16 to March 18."),
    ("OUT suspended ops verb first", "Lexington suspended operations from March 16 to March 18."),
    ("OUT will stay closed", "Lexington will stay closed from March 16 to March 18."),
    ("OUT remains shut", "The Princeton plant remains shut from March 16 through March 18."),
    ("OUT dark days", "Jackson will be dark March 16 through March 18."),
    ("OUT taken offline", "The Huntsville plant has been taken offline from March 16 to March 18."),
    ("OUT curtailed", "Production at San Antonio is curtailed from March 16 to March 18."),
    ("OUT zero output", "Output at Princeton is zero from March 16 through March 18."),
    ("OUT not producing vehicles", "Greensboro isn't producing from March 16 to March 18."),

    # delay paraphrases
    ("DLY due expected", "Airbag modules for San Antonio are due March 15 and expected March 18."),
    ("DLY due expected 2", "Airbag modules headed to San Antonio, due March 15, expected March 18."),
    ("DLY shifted", "The airbag module delivery to San Antonio shifted from March 15 to March 18."),
    ("DLY shifted 2", "Airbag modules for San Antonio shifted from March 15 to March 18."),
    ("DLY bumped", "The airbag module delivery to San Antonio was bumped from March 15 to March 18."),
    ("DLY bumped 2", "Airbag modules for San Antonio got bumped from March 15 to March 18."),
    ("DLY pushed from", "SUP-17 pushed airbag modules for San Antonio from March 15 to March 18."),
    ("DLY pushed from 2", "Sentinel pushed the airbag modules to San Antonio from March 15 to March 18."),
    ("DLY revised", "The airbag module delivery to San Antonio was revised from March 15 to March 18."),
    ("DLY revised 2", "Airbag modules for San Antonio were revised from March 15 to March 18."),
    ("DLY instead of", "Airbag modules for San Antonio arrive March 18 instead of March 15."),
    ("DLY instead of 2", "The airbag module delivery to San Antonio comes March 18 instead of March 15."),
    ("DLY deferred", "The airbag module delivery to San Antonio is deferred from March 15 to March 18."),
    ("DLY deferred 2", "Airbag modules for San Antonio are deferred from March 15 until March 18."),
    ("DLY didn't ship", "Airbag modules for San Antonio didn't ship on March 15; they ship on March 18."),
    ("DLY didn't ship 2", "The airbag modules for San Antonio didn't ship March 15 and ship March 18."),
    ("DLY put off", "Airbag modules for San Antonio are put off from March 15 until March 18."),
    ("DLY put off 2", "The airbag module delivery to San Antonio is put off from March 15 to March 18."),
    ("DLY quoting", "SUP-17 is quoting March 18 for airbag modules to San Antonio, not March 15."),
    ("DLY quoting 2", "Sentinel is quoting March 18 rather than March 15 on airbag modules for San Antonio."),
    ("DLY moved back", "Airbag modules for San Antonio moved back from March 15 to March 18."),
    ("DLY carrier moved", "The carrier moved airbag modules for San Antonio from March 15 to March 18."),
    ("DLY re-dated", "Airbag modules for San Antonio were re-dated from March 15 to March 18."),
    ("DLY backordered", "Airbag modules for San Antonio are backordered from March 15 to March 18."),
    ("DLY not on time", "Airbag modules from SUP-17 to San Antonio will not be on time, March 15 versus March 18."),
    ("DLY was now long", "The airbag module shipment for San Antonio was supposed to be here March 15 based on the last carrier update, now March 18."),
    ("DLY battery shifted", "Battery packs for Lexington shifted from March 15 to March 18."),
    ("DLY harness deferred", "The heavy-duty wiring harness delivery to Princeton is deferred from March 15 to March 18."),
    ("DLY brake bumped", "Brake kits for Jackson were bumped from March 15 to March 18."),
    ("DLY display put off", "The 12-inch display delivery to Huntsville is put off from March 15 to March 18."),

    # quality paraphrases
    ("QL don't use", "Don't use LOT-0001."),
    ("QL don't use 2", "Don't use lot LOT-0001 on the line."),
    ("QL scrap the", "Scrap the LOT-0001."),
    ("QL scrap the 2", "Please scrap the lot LOT-0001."),
    ("QL is scrap", "LOT-0001 is scrap."),
    ("QL should be scrapped", "LOT-0001 should be scrapped."),
    ("QL reject", "Reject LOT-0001."),
    ("QL rejected", "LOT-0001 is rejected."),
    ("QL do not install", "Do not install LOT-0001."),
    ("QL don't install", "Don't install LOT-0001."),
    ("QL containment", "Containment for LOT-0001."),
    ("QL containment 2", "Containment notice on LOT-0001."),
    ("QL out of tolerance", "Airbag modules at San Antonio are out of tolerance for builds from February 22 to February 24."),
    ("QL out of tolerance 2", "Airbag modules at San Antonio are out of tolerance, builds February 22 through February 24."),
    ("QL hold for inspection", "Hold airbag modules at San Antonio for inspection, builds February 22 to February 24."),
    ("QL held for inspection", "Airbag modules at San Antonio are held for inspection covering builds February 22 through February 24."),
    ("QL failed check", "LOT-0001 failed the incoming check."),
    ("QL failed check 2", "LOT-0001 failed incoming inspection."),
    ("QL do not build", "Do not build with LOT-0001."),
    ("QL cease use", "Cease use of LOT-0001."),
    ("QL purge", "Purge LOT-0001 from the line."),
    ("QL impound", "Impound LOT-0001."),
    ("QL segregate", "Segregate LOT-0001."),
    ("QL seals leak order", "The seals on LOT-0001 leak."),
    ("QL scrap it", "LOT-0001: scrap it."),
    ("QL remove", "Remove LOT-0001 from production."),
    ("QL don't build", "Don't build with LOT-0001."),
    ("QL quarantine control", "Quarantine LOT-0001."),
    ("QL out of spec control", "Airbag modules at San Antonio are out of spec for builds February 22 to February 24."),

    # negation / cancellation false positives
    ("NEG not down", "Lexington is not down from March 16 to March 18."),
    ("NEG not down 2", "San Antonio is not down from March 16 through March 18."),
    ("NEG not shut down", "Lexington is not shut down from March 16 to March 18."),
    ("NEG not shut down 2", "The plant at Jackson is not shut down March 16 through March 18."),
    ("NEG plant not closed", "The San Antonio plant is not closed from March 16 to March 18."),
    ("NEG plant not closed 2", "The Lexington plant is not closed from March 16 through March 18."),
    ("NEG not delayed", "Airbag modules for San Antonio are not delayed from March 15 to March 18."),
    ("NEG not delayed 2", "The airbag module delivery to San Antonio is not delayed, March 15 to March 18."),
    ("NEG no delay", "No delay on airbag modules to San Antonio from March 15 to March 18."),
    ("NEG no defects", "Airbag modules at San Antonio show no defects for builds February 22 through February 24."),
    ("NEG no defects 2", "No defects in airbag modules at San Antonio, builds February 22 to February 24."),
    ("NEG qc no faults", "QC showed no faults on airbag modules at San Antonio, builds February 22 to February 24."),
    ("NEG inspection no cracks", "Inspection showed no cracks in airbag modules at San Antonio from February 22 to February 24."),
    ("NEG hold lifted", "The quality hold on LOT-0001 is lifted."),
    ("NEG hold released", "Quality hold on LOT-0001 has been released."),
    ("NEG outage cancelled", "The Lexington outage from March 16 to March 18 is cancelled."),
    ("NEG outage cancelled 2", "Cancel the Lexington outage planned for March 16 through March 18."),
    ("NEG delay resolved", "The airbag module delay to San Antonio from March 15 to March 18 has been resolved."),
    ("NEG back on schedule", "Airbag modules for San Antonio are back on schedule after the March 15 to March 18 delay."),
    ("NEG no outage", "There is no outage at Princeton from March 16 to March 18."),
    ("NEG not offline", "Huntsville is not offline from March 16 to March 18."),
    ("NEG production not stopped", "Production at Greensboro is not stopped from March 16 to March 18."),

    # picnic / cafeteria / tour false positives
    ("NOISE cafe line", "The cafeteria line is closed at Lexington from March 16 to March 18."),
    ("NOISE serving line", "The serving line is closed at the Lexington cafeteria from March 16 through March 18."),
    ("NOISE lunch line", "The lunch line at San Antonio is closed from March 16 to March 18."),
    ("NOISE plant tour stopped", "The plant tour is stopped at San Antonio from March 16 through March 18."),
    ("NOISE plant tour stopped 2", "The plant tour stopped at San Antonio from March 16 to March 18."),
    ("NOISE tour suspended", "The plant tour at Huntsville is suspended from March 16 to March 18."),
    ("NOISE picnic assembly", "Assembly of the picnic signs stops at Huntsville from March 16 to March 18."),
    ("NOISE picnic assembly 2", "Assembly for the picnic stops at Greensboro March 16 through March 18."),
    ("NOISE picnic delivery", "The picnic delivery to San Antonio has been moved from March 16 to March 18."),
    ("NOISE cafeteria shipment", "The cafeteria shipment for the Lexington picnic has been moved from March 16 to March 18."),
    ("NOISE tour rescheduled", "The plant tour at Jackson is rescheduled from March 16 to March 18."),
    ("NOISE picnic delayed", "The San Antonio picnic is delayed from March 16 to March 18."),
    ("NOISE cafeteria down", "The cafeteria at Lexington is down March 16 through March 18."),
    ("NOISE tour offline", "The tour at Princeton is offline from March 16 to March 18."),
    ("NOISE brochure defect", "There is a defect in the picnic slides at Lexington."),
    ("NOISE line for cafeteria", "The line for the cafeteria at Lexington is closed from March 16 to March 18."),

    # incomplete operational wording that should escalate, not drop as noise
    ("INC will be closed", "Lexington will be closed next week."),
    ("INC will be closed 2", "San Antonio will be closed for maintenance next week."),
    ("INC cannot operate", "Princeton cannot operate next week."),
    ("INC halts", "Assembly at Huntsville halts next week."),
    ("INC bumped no date", "The airbag module delivery to San Antonio was bumped."),
    ("INC shifted no date", "Airbag modules for San Antonio shifted."),
    ("INC downtime no date", "Planned downtime at Lexington next week."),
    ("INC don't install no", "Do not install the airbag modules at San Antonio."),
    ("INC closes no date", "The Huntsville plant closes next week."),
    ("INC deferred no date", "The battery pack delivery to Lexington is deferred."),

    # compound split gaps
    ("CMP firstly", "Firstly, Lexington is down March 16 through March 18. Secondly, the airbag module order to San Antonio is rescheduled from March 15 to March 19."),
    ("CMP semicolon", "Lexington is down March 16 through March 18; the airbag module delivery to San Antonio has been moved from March 15 to March 18."),
    ("CMP and", "Lexington is down March 16 through March 18 and San Antonio is down March 23 through March 25."),
    ("CMP also no comma", "Lexington is down March 16 through March 18. Also the airbag module order to San Antonio is rescheduled from March 15 to March 19."),
    ("CMP plus", "Lexington is down March 16 through March 18. Plus, airbag modules to San Antonio are rescheduled from March 15 to March 19."),
]


def main() -> None:
    for label, text in cases:
        found = understand(graph, text)
        kinds = [item.kind for item in found]
        bits = []
        for item in found:
            ev = item.evidence[0] if item.evidence else ""
            bits.append(f"{item.kind}|{ev[:110]}")
        print(f"{label}\t{kinds}\t{' || '.join(bits)}")


if __name__ == "__main__":
    main()
