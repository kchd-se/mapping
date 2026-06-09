import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../test-utils/render";
import { setupFetchMock, mockRoute, fixtures } from "../test-utils/mockApi";
import { ProjectSchemas } from "../components/project/project-schemas";

const PROJECT_ID = "proj-001";

/** Render ProjectSchemas with no pinned schemas so the pickers are visible. */
function renderTargetPicker() {
  mockRoute("GET", /\/projects\/proj-001\/schemas/, {
    project_id: PROJECT_ID,
    source: null,
    target: null,
  });
  return renderWithProviders(<ProjectSchemas projectId={PROJECT_ID} />);
}

describe("CatalogPicker", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── 1. Standard bundle cards are rendered ────────────────────────────────
  it("renders standard bundle cards for FHIR R4 and OMOP CDM", async () => {
    const schemas = fixtures.catalogSchemas();
    mockRoute("GET", /\/catalog\/schemas/, schemas);
    renderTargetPicker();

    await waitFor(() => {
      // Bundle cards are shown with accessible labels
      expect(
        screen.getByRole("button", { name: /Select FHIR R4 standard/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Select OMOP CDM 5\.4 standard/i }),
      ).toBeInTheDocument();
    });
  });

  // ── 2. Bundle cards show included profiles/tables ───────────────────────
  it("shows included profiles inside the FHIR R4 bundle card", async () => {
    const schemas = fixtures.catalogSchemas();
    mockRoute("GET", /\/catalog\/schemas/, schemas);
    renderTargetPicker();

    // Wait for the FHIR R4 bundle card to appear
    const fhirCard = await screen.findByRole("button", {
      name: /Select FHIR R4 standard/i,
    });

    // The card text content should include all profile names (FHIR_ prefix stripped)
    expect(fhirCard).toHaveTextContent("Patient");
    expect(fhirCard).toHaveTextContent("Organization");
    expect(fhirCard).toHaveTextContent("Encounter");
  });

  // ── 3. Selecting a bundle pins it with one click (no version picker) ─────
  it("pins standard bundle directly without a version picker", async () => {
    const user = userEvent.setup();
    const schemas = fixtures.catalogSchemas();
    const pinnedRef = fixtures.schemas().target!;

    mockRoute("GET", /\/catalog\/schemas(\?|$)/, schemas);
    mockRoute("POST", /\/schemas\/target\/select/, pinnedRef, 201);
    renderTargetPicker();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, {
      project_id: PROJECT_ID,
      source: null,
      target: pinnedRef,
    });

    const fhirCard = await screen.findByRole("button", {
      name: /Select FHIR R4 standard/i,
    });

    await user.click(fhirCard);

    await waitFor(() => {
      expect(screen.getByText("Target schema pinned")).toBeInTheDocument();
    });
  });

  // ── 4. Catalog list renders individual schema names ───────────────────────
  it("renders individual catalog schema names from API response", async () => {
    const schemas = fixtures.catalogSchemas();
    mockRoute("GET", /\/catalog\/schemas/, schemas);
    renderTargetPicker();

    // Default mode is "catalog" — the CatalogPicker should be visible
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Search schemas…")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("OMOP CDM Person")).toBeInTheDocument();
      expect(screen.getByText("FHIR Patient R4")).toBeInTheDocument();
      expect(screen.getByText("Custom Lab Schema")).toBeInTheDocument();
    });
  });

  // ── 5. Bundle schemas are NOT in the individual list ─────────────────────
  it("does NOT show bundle schemas in the individual schema list", async () => {
    const schemas = fixtures.catalogSchemas();
    mockRoute("GET", /\/catalog\/schemas/, schemas);
    renderTargetPicker();

    await waitFor(() =>
      screen.getByText("OMOP CDM Person"),
    );

    // Bundle schema names must not appear as link/button text in the individual list
    // (they appear only in the standard-card aria-labels, not as bare text nodes)
    expect(screen.queryByText("FHIR_R4")).not.toBeInTheDocument();
    expect(screen.queryByText("OMOP_CDM_5_4")).not.toBeInTheDocument();
  });

  // ── 6. Typing in search field sends q param ──────────────────────────────
  it("filters catalog by q param when user types in search box", async () => {
    const user = userEvent.setup();
    const allSchemas = fixtures.catalogSchemas();
    const filteredSchemas = allSchemas.filter((s) => s.name.toLowerCase().includes("omop"));

    // Specific filtered route must be registered BEFORE the general one,
    // because the mock router returns the first matching route and
    // /catalog/schemas?q=omop also satisfies the general (?|$) pattern.
    mockRoute("GET", /\/catalog\/schemas\?.*q=omop/, filteredSchemas);
    mockRoute("GET", /\/catalog\/schemas(\?|$)/, allSchemas);

    renderTargetPicker();

    await waitFor(() =>
      expect(screen.getByPlaceholderText("Search schemas…")).toBeInTheDocument(),
    );

    const searchInput = screen.getByPlaceholderText("Search schemas…");
    await user.type(searchInput, "omop");

    await waitFor(() => {
      expect(screen.getByText("OMOP CDM Person")).toBeInTheDocument();
      expect(screen.queryByText("FHIR Patient R4")).not.toBeInTheDocument();
    });
  });

  // ── 7. Clicking an individual schema triggers versions fetch ───────────
  it("fetches versions when an individual schema is selected", async () => {
    const user = userEvent.setup();
    const schemas = fixtures.catalogSchemas();
    const versions = fixtures.catalogVersions("cat-001");

    mockRoute("GET", /\/catalog\/schemas(\?|$)/, schemas);
    mockRoute("GET", /\/catalog\/schemas\/cat-001\/versions/, versions);

    renderTargetPicker();

    await waitFor(() =>
      expect(screen.getByText("OMOP CDM Person")).toBeInTheDocument(),
    );

    await user.click(screen.getByText("OMOP CDM Person"));

    await waitFor(() => {
      // A version selector label should appear
      expect(screen.getByText("Version")).toBeInTheDocument();
    });
  });

  // ── 8. Selecting version + confirming triggers POST target/select ────────
  it("calls POST /target/select when version is chosen and confirmed", async () => {
    const user = userEvent.setup();
    const schemas = fixtures.catalogSchemas();
    const versions = fixtures.catalogVersions("cat-001");
    const pinnedRef = fixtures.schemas().target!;

    mockRoute("GET", /\/catalog\/schemas(\?|$)/, schemas);
    mockRoute("GET", /\/catalog\/schemas\/cat-001\/versions/, versions);
    mockRoute("POST", /\/schemas\/target\/select/, pinnedRef, 201);

    // renderTargetPicker() registers the initial GET /projects/proj-001/schemas
    // returning {target: null}. The post-pin re-fetch route must come AFTER so
    // the first request sees null (picker shown) and the second sees pinnedRef.
    renderTargetPicker();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, {
      project_id: PROJECT_ID,
      source: null,
      target: pinnedRef,
    });

    await waitFor(() =>
      expect(screen.getByText("OMOP CDM Person")).toBeInTheDocument(),
    );
    await user.click(screen.getByText("OMOP CDM Person"));

    await waitFor(() =>
      expect(screen.getByText("Version")).toBeInTheDocument(),
    );

    // Open the version Select — scope to its container to avoid matching
    // the format <select> in the source panel (both have role="combobox").
    const versionDiv = screen.getByText("Version").parentElement!;
    const trigger = within(versionDiv).getByRole("combobox");
    await user.click(trigger);
    const option = await screen.findByText("v5.4");
    await user.click(option);

    // Confirm button should now be enabled
    const confirmBtn = screen.getByRole("button", { name: /Use "OMOP CDM Person"/i });
    expect(confirmBtn).not.toBeDisabled();
    await user.click(confirmBtn);

    await waitFor(() => {
      // After successful pin the toast message should appear
      expect(screen.getByText("Target schema pinned")).toBeInTheDocument();
    });
  });

  // ── 9. 401 from catalog list shows "Not authenticated" ───────────────────
  it('shows "Not authenticated" when catalog list returns 401', async () => {
    mockRoute("GET", /\/catalog\/schemas/, { detail: "Not authenticated" }, 401);

    renderTargetPicker();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Not authenticated");
    });
  });
});
