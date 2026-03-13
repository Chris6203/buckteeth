import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Dashboard from "../pages/Dashboard";

vi.mock("../api/client", () => ({
  listPatients: vi.fn().mockResolvedValue([{ id: "p1" }, { id: "p2" }]),
  listClaims: vi.fn().mockResolvedValue([{ id: "c1" }]),
  listDenials: vi.fn().mockResolvedValue([{ id: "d1" }, { id: "d2" }, { id: "d3" }]),
  health: vi.fn().mockResolvedValue({ status: "healthy", version: "0.1.0" }),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Dashboard />
    </BrowserRouter>,
  );
}

describe("Dashboard page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders summary cards with counts", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument(); // patients
      expect(screen.getByText("1")).toBeInTheDocument(); // claims
      expect(screen.getByText("3")).toBeInTheDocument(); // denials
    });
  });

  it("shows API connected status", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Connected/)).toBeInTheDocument();
    });
  });
});
