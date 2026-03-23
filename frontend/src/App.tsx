import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import { ToastProvider } from "./components/Toast";
import Dashboard from "./pages/Dashboard";
import Encounters from "./pages/Encounters";
import Patients from "./pages/Patients";
import Claims from "./pages/Claims";
import Denials from "./pages/Denials";
import Setup from "./pages/Setup";

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/encounters" element={<Encounters />} />
            <Route path="/patients" element={<Patients />} />
            <Route path="/claims" element={<Claims />} />
            <Route path="/denials" element={<Denials />} />
            <Route path="/setup" element={<Setup />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </ToastProvider>
    </ErrorBoundary>
  );
}
