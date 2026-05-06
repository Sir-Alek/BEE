import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { EliaThemeProvider, applyThemeFromUrl } from "./eliaTheme";

applyThemeFromUrl();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <EliaThemeProvider>
      <App />
    </EliaThemeProvider>
  </React.StrictMode>,
);
