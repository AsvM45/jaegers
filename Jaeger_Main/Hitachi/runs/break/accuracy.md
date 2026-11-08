# Rule-reader misses

Rules only (`understand` with no model). Today is 2027-03-08. About 170 novel messages, each miss below checked with a second paraphrase. Recent fixes still pass: "is closed", "will not run", "assembly … stops", "delivery … has been moved", "was … now" inside 48 characters, "scrap LOT-", "stop using lot", "1. 2." lists, and bullets. "The cafeteria at Lexington is closed" and "the plant tour will not run at San Antonio" stay noise.

144 confirmed rows are in `accuracy.json`.

## Bug classes

1. **Negation and cancellation still open an incident.** "not down", "not shut down", "plant is not closed", "not offline", "no outage", "not delayed", "no delay", "no defects", and "QC showed no faults" all match the positive keyword. A lifted quality hold, a cancelled outage, and a resolved delay do the same. Expected noise.

2. **Cafeteria, tour, and picnic chatter is not guarded.** The cafeteria guard only blocks "closed" directly on the plant name, and the tour guard only blocks "will not run" after "at <plant>". "The cafeteria line is closed", "the cafeteria is down/offline", "the plant tour is stopped/suspended", and "picnic assembly stops" become outages. A picnic delivery that "has been moved", and a defect in picnic materials, are escalated instead of ignored.

3. **Closed and run paraphrases next to the new fixes.** "will be closed", "closes", "set to close", "will stay closed", and "remains shut" are noise. So are "is not running", "won't be running", "cannot operate", "halts" (the list has "stops" and "halted"), and "isn't producing".

4. **Other outage wording with a plant and dates is noise.** Confirmed: downtime, out of service, idled, in maintenance, ceased operations, production cancelled, power is out, no power, blacked out, no assembly, "goes offline" without "from", "suspended operations", "idle the plant", shuttered.

5. **Delay wording with a part, a plant, and two dates is noise.** Confirmed: due/expected, shifted, bumped, "pushed from" (only "pushed back/out/to"), "delivery was revised", "arrive … instead of", deferred, "didn't ship", put off, "is quoting"/"quoted" (only "now quoting"), "moved" with no arrival/delivery/shipment noun in front, and "was … now" when more than 48 characters sit between the words.

6. **Quality wording on a real lot, or on a part plus plant plus two dates, is missed.** Confirmed: "don't use", "scrap the LOT-", "LOT- is scrap", reject, "do not install", containment (the sample notice only matched via "scrap LOT-"), out of tolerance (out of spec works), "hold for inspection", "failed incoming inspection" when a word sits between failed and inspection, "seals leak" in that order. "don't build with LOT-" is noise. "do not build with LOT-" is escalated, because "not build" is read as an outage phrase and then cannot be finished.

7. **The same gaps with no dates become noise instead of an escalation.** "Lexington will be closed next week", "the airbag module delivery was bumped", and "assembly halts next week" name our operations and are incomplete. They should be unconfirmed.

8. **A second full incident is dropped** unless the join is one of the taught splitters. "Firstly/Secondly", "Also" with no comma, a semicolon, and "and" leave one section. Outage is tried first, so the later delay or the second plant outage disappears.
