import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./app/App";
import { AssessmentProvider } from "./features/assessment/AssessmentContext";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AssessmentProvider>
        <App />
      </AssessmentProvider>
    </BrowserRouter>
  </StrictMode>
);
