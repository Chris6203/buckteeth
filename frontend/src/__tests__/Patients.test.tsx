import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Patients from "../pages/Patients";

vi.mock("../api/client", () => ({
  listPatients: vi.fn().mockResolvedValue([
    {
      id: "p1",
      first_name: "Jane",
      last_name: "Smith",
      date_of_birth: "1985-03-15",
      gender: "F",
      created_at: null,
    },
    {
      id: "p2",
      first_name: "John",
      last_name: "Doe",
      date_of_birth: "1972-07-22",
      gender: "M",
      created_at: null,
    },
  ]),
  createPatient: vi.fn().mockResolvedValue({
    id: "p3",
    first_name: "New",
    last_name: "Patient",
    date_of_birth: "2000-01-01",
    gender: "F",
    created_at: null,
  }),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Patients />
    </BrowserRouter>,
  );
}

describe("Patients page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders patient list", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Jane Smith")).toBeInTheDocument();
      expect(screen.getByText("John Doe")).toBeInTheDocument();
    });
  });

  it("shows heading", () => {
    renderPage();
    expect(screen.getByText("Patients")).toBeInTheDocument();
  });
});
