import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import after mocking fetch
import { listPatients, createPatient, health } from "../api/client";

beforeEach(() => {
  mockFetch.mockReset();
  localStorage.clear();
});

describe("API client", () => {
  it("health check calls /health", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: "healthy", version: "0.1.0" }),
    });

    const result = await health();
    expect(result.status).toBe("healthy");
    expect(mockFetch).toHaveBeenCalledWith(
      "/health",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Tenant-ID": expect.any(String),
        }),
      }),
    );
  });

  it("listPatients calls /v1/patients", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: "abc", first_name: "Jane" }],
    });

    const patients = await listPatients();
    expect(patients).toHaveLength(1);
    expect(patients[0].first_name).toBe("Jane");
  });

  it("createPatient sends POST with body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: "new-id", first_name: "John" }),
    });

    await createPatient({
      first_name: "John",
      last_name: "Doe",
      date_of_birth: "1990-01-01",
      gender: "M",
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "/v1/patients",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("John"),
      }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Not found" }),
    });

    await expect(listPatients()).rejects.toThrow("Not found");
  });

  it("uses tenant ID from localStorage", async () => {
    localStorage.setItem("tenantId", "custom-tenant-id");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    await listPatients();

    expect(mockFetch).toHaveBeenCalledWith(
      "/v1/patients",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Tenant-ID": "custom-tenant-id",
        }),
      }),
    );
  });
});
