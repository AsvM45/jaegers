import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App.jsx";
import { DataProvider } from "./lib/data.jsx";
import { UiProvider } from "./lib/ui.jsx";
import { Redraw, SettingsProvider } from "./lib/settings.jsx";

// The app decides where a page opens (the top), not the browser.
if ("scrollRestoration" in history) history.scrollRestoration = "manual";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <SettingsProvider>
    <UiProvider>
      <DataProvider>
        <Redraw><App /></Redraw>
      </DataProvider>
    </UiProvider>
    </SettingsProvider>
  </StrictMode>,
);
