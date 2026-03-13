import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Denials from "../pages/Denials";

vi.mock("../api/client", () => ({
  listDenials: vi.fn().mockResolvedValue([
    {
      id: "d1",
      claim_id: "c1",
      denial_reason_code: "D0001",
      denial_reason_description: "Not medically necessary",
      denied_amount: 500.0,
      payer_name: "Delta Dental",
      status: "denied",
      created_at: null,
    },
  ]),
  generateAppeal: vi.fn().mockResolvedValue({
    id: "a1",
    denial_id: "d1",
    appeal_text: "Appeal letter text...",
    case_law_citations: [],
    generated_by: "ai",
    status: "draft",
    created_at: null,
  }),
}));

function renderPage() {
  return render(
    <BrowserRouter>
      <Denials />
    </BrowserRouter>,
  );
}

describe("Denials page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders denials list", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Delta Dental")).toBeInTheDocument();
      expect(
        screen.getByText("Not medically necessary"),
      ).toBeInTheDocument();
    });
  });

  it("shows heading", () => {
    renderPage();
    expect(screen.getByText("Denials")).toBeInTheDocument();
  });
});
