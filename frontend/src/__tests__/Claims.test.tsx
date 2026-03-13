import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Claims from "../pages/Claims";

vi.mock("../api/client", () => ({
  listClaims: vi.fn().mockResolvedValue([
    {
      id: "c1",
      patient_id: "p1",
      coded_encounter_id: "ce1",
      provider_name: "Dr. Smith",
      date_of_service: "2026-03-12",
      status: "draft",
      primary_payer_name: "Delta Dental",
      primary_payer_id: "DD001",
      primary_subscriber_id: "SUB-001",
      primary_group_number: "GRP-100",
      secondary_payer_name: null,
      preauth_required: false,
      total_fee_submitted: 300.0,
      procedures: [],
      narratives: [],
      created_at: null,
    },
  ]),
  submitClaim: vi.fn(),
  assessRisk: vi.fn(),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Claims />
    </BrowserRouter>,
  );
}

describe("Claims page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders claims list", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Dr. Smith")).toBeInTheDocument();
      expect(screen.getByText("Delta Dental")).toBeInTheDocument();
    });
  });

  it("shows heading", () => {
    renderPage();
    expect(screen.getByText("Claims")).toBeInTheDocument();
  });
});
