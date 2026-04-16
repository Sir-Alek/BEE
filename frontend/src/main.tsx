import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { BeeThemeProvider, applyThemeFromUrl } from "./beeTheme";

applyThemeFromUrl();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BeeThemeProvider>
      <App />
    </BeeThemeProvider>
  </React.StrictMode>,
);
