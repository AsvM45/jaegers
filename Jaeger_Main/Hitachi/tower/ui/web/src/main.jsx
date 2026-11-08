import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App.jsx";
import { DataProvider } from "./lib/data.jsx";
import { UiProvider } from "./lib/ui.jsx";

// The app decides where a page opens (the top), not the browser.
if ("scrollRestoration" in history) history.scrollRestoration = "manual";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <UiProvider>
      <DataProvider>
        <App />
      </DataProvider>
    </UiProvider>
  </StrictMode>,
);
