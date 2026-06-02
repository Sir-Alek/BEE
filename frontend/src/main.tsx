import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { EliaThemeProvider, applyThemeFromUrl } from "./eliaTheme";
import "./eliaTheme.css";

applyThemeFromUrl();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <EliaThemeProvider>
      <App />
    </EliaThemeProvider>
  </React.StrictMode>,
);
