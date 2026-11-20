import { EventChat, EventRun } from "../components/EventDesk.jsx";
import { Page } from "./Page.jsx";
import { tr } from "../lib/i18n.js";

// Add events: type, paste, attach or dictate a message for the tower, or run the whole feed.
export default function AddEvents() {
  return (
    <Page title={tr("Add events")} subtitle={<span>{tr("Each message becomes an event in the feed")}</span>}>
      <div className="ask-page">
        <EventChat />
        <EventRun />
      </div>
    </Page>
  );
}
