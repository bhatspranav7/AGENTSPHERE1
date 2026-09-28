import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppProvider } from "./app-context";
import { Layout } from "./components/Layout";
import Architecture from "./pages/Architecture";
import Crew from "./pages/Crew";
import Insights from "./pages/Insights";
import Launch from "./pages/Launch";
import RunDetail from "./pages/RunDetail";
import Runs from "./pages/Runs";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AppProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<Launch />} />
            <Route path="/runs" element={<Runs />} />
            <Route path="/runs/:id" element={<RunDetail />} />
            <Route path="/insights" element={<Insights />} />
            <Route path="/crew" element={<Crew />} />
            <Route path="/architecture" element={<Architecture />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </AppProvider>
    </BrowserRouter>
  </StrictMode>,
);
