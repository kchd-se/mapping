import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../test-utils/render";
import { setupFetchMock, mockRoute, fixtures } from "../test-utils/mockApi";
import { ProjectMapping } from "../components/project/project-mapping";

describe("Mapping Editor", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows schema-not-configured message when no schemas are pinned", async () => {
    mockRoute("GET", /\/projects\/proj-001\/schemas/, {
      project_id: "proj-001",
      source: null,
      target: null,
    });

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    await waitFor(() => {
      expect(screen.getByText("Schemas Not Configured")).toBeInTheDocument();
    });
  });

  it("renders one row per target field after generating suggestions", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText("person.birth_datetime").length).toBeGreaterThan(0);

    const targetFieldPaths = suggestions.field_suggestions.map(
      (fs) => fs.target_field_path,
    );
    for (const path of targetFieldPaths) {
      expect(screen.getAllByText(path).length).toBeGreaterThan(0);
    }
  });

  it("renders multiple TOP-K suggestions for each target field", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    const personIdField = suggestions.field_suggestions[0];
    for (const cand of personIdField.candidates) {
      const label = (cand.source_field_paths ?? cand.source_field_ids).join(" + ");
      expect(screen.getByText(label)).toBeInTheDocument();
    }

    expect(
      screen.getAllByText((text) => text.includes("patient.")).length,
    ).toBeGreaterThanOrEqual(personIdField.candidates.length);
  });

  it("displays confidence scores for each suggestion", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
    expect(screen.getByText("45%")).toBeInTheDocument();
    expect(screen.getByText("88%")).toBeInTheDocument();
    expect(screen.getByText("55%")).toBeInTheDocument();
  });

  it("displays explainability text (reasons) for suggestions", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getByText("Exact name match after normalization")).toBeInTheDocument();
    });

    expect(screen.getByText("Both are identifier fields")).toBeInTheDocument();
    expect(screen.getByText("Date-of-birth semantic match")).toBeInTheDocument();
  });

  it("does NOT collapse suggestions to a single option", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    // In the source-centric layout, target field paths appear as candidate buttons.
    // person.person_id appears once per source row that maps to it (3 rows).
    // person.birth_datetime appears once per source row that maps to it (2 rows).
    const allCandidateButtons = screen.getAllByRole("button").filter((btn) => {
      const text = btn.textContent || "";
      return text.includes("person.");
    });

    const totalCandidates = suggestions.field_suggestions.reduce(
      (sum, fs) => sum + fs.candidates.length,
      0,
    );

    expect(allCandidateButtons.length).toBeGreaterThanOrEqual(totalCandidates);
  });
});

describe("Manual Override", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("allows user to select an unselected target candidate and marks it as active", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    // After auto-map, person.person_id is mapped to patient.patientId (src-patient-id).
    // The person.person_id button in other source rows (e.g. patient.personnummer) is unselected.
    // Find the unselected person.person_id button and click it.
    const allPersonIdButtons = screen.getAllByRole("button", { name: "person.person_id" });
    const unselectedButton = allPersonIdButtons.find(
      (btn) => btn.getAttribute("aria-pressed") === "false"
    );
    expect(unselectedButton).toBeDefined();
    await user.click(unselectedButton!);

    await waitFor(() => {
      expect(unselectedButton).toHaveAttribute("aria-pressed", "true");
    });
  });

  it("allows adding notes to a selected target mapping", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    // After auto-map, rows with selected targets show a notes input.
    const notesInputs = screen.getAllByPlaceholderText("e.g. Casting / limits...");
    expect(notesInputs.length).toBeGreaterThanOrEqual(1);

    const firstNotesInput = notesInputs[0] as HTMLInputElement;
    await user.clear(firstNotesInput);
    await user.type(firstNotesInput, "requires type cast");

    expect(firstNotesInput.value).toBe("requires type cast");
  });

  it("deselects a target candidate by clicking its active button again", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText("Auto-Map Engine")).toBeInTheDocument();
    });
    await user.click(screen.getByText("Auto-Map Engine"));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    // Find the currently-selected (aria-pressed=true) person.person_id button.
    const allPersonIdButtons = screen.getAllByRole("button", { name: "person.person_id" });
    const selectedButton = allPersonIdButtons.find(
      (btn) => btn.getAttribute("aria-pressed") === "true"
    );
    expect(selectedButton).toBeDefined();

    // Click it to deselect.
    await user.click(selectedButton!);

    await waitFor(() => {
      expect(selectedButton).toHaveAttribute("aria-pressed", "false");
    });
  });
});

describe("Saved Drafts", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the saved drafts panel when prior versions exist", async () => {
    const schemas = fixtures.schemas();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("GET", /\/projects\/proj-001\/mappings/, fixtures.mappingVersions());

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    await waitFor(() => {
      expect(screen.getByText("Saved Drafts")).toBeInTheDocument();
    });

    expect(screen.getByText("Draft v1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Load/i })).toBeInTheDocument();
  });

  it("shows a banner and pre-fills version label after loading a draft", async () => {
    const schemas = fixtures.schemas();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("GET", /\/projects\/proj-001\/mappings/, fixtures.mappingVersions());

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Load/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Load/i }));

    await waitFor(() => {
      expect(screen.getByText(/Draft "Draft v1" loaded/)).toBeInTheDocument();
    });

    const versionInput = screen.getByPlaceholderText("e.g. Draft v1") as HTMLInputElement;
    expect(versionInput.value).toBe("Draft v1");
  });

  it("shows Update Draft and Save as New buttons after loading a draft", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("GET", /\/projects\/proj-001\/mappings/, fixtures.mappingVersions());
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Load/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Load/i }));
    await user.click(screen.getByRole("button", { name: /Auto-Map Engine/i }));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    expect(screen.getByRole("button", { name: /Update Draft/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Save as New/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Save Draft$/i })).toBeNull();
  });

  it("calls PUT endpoint when Update Draft is clicked", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    const updatedVersion = { ...fixtures.mappingVersions()[0], rule_count: 2 };
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("GET", /\/projects\/proj-001\/mappings/, fixtures.mappingVersions());
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);
    mockRoute("PUT", /\/projects\/proj-001\/mappings\/mv-001/, updatedVersion);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Load/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Load/i }));
    await user.click(screen.getByRole("button", { name: /Auto-Map Engine/i }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Update Draft/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Update Draft/i }));

    await waitFor(() => {
      expect(screen.getByText(/"Draft v1" updated/)).toBeInTheDocument();
    });
  });

  it("applies loaded draft rules as pre-selected when Auto-Map is run next", async () => {
    const schemas = fixtures.schemas();
    const suggestions = fixtures.suggestions();
    mockRoute("GET", /\/projects\/proj-001\/schemas/, schemas);
    mockRoute("GET", /\/projects\/proj-001\/mappings/, fixtures.mappingVersions());
    mockRoute("POST", /\/projects\/proj-001\/suggestions/, suggestions);

    renderWithProviders(<ProjectMapping projectId="proj-001" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Load/i })).toBeInTheDocument();
    });

    // Load the draft first
    await user.click(screen.getByRole("button", { name: /Load/i }));

    // Then run Auto-Map — loaded rules should be preserved
    await user.click(screen.getByRole("button", { name: /Auto-Map Engine/i }));

    await waitFor(() => {
      expect(screen.getAllByText("person.person_id").length).toBeGreaterThan(0);
    });

    // The draft maps src-patient-id → person.person_id (confidence 0.95), so that
    // button should be selected (aria-pressed=true).
    const allPersonIdButtons = screen.getAllByRole("button", { name: "person.person_id" });
    const selectedButton = allPersonIdButtons.find(
      (btn) => btn.getAttribute("aria-pressed") === "true"
    );
    expect(selectedButton).toBeDefined();
  });
});
