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
      expect(screen.getByText("person.person_id")).toBeInTheDocument();
    });

    expect(screen.getByText("person.birth_datetime")).toBeInTheDocument();

    const targetFieldPaths = suggestions.field_suggestions.map(
      (fs) => fs.target_field_path,
    );
    for (const path of targetFieldPaths) {
      expect(screen.getByText(path)).toBeInTheDocument();
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
      expect(screen.getByText("person.person_id")).toBeInTheDocument();
    });

    const personIdField = suggestions.field_suggestions[0];
    for (const cand of personIdField.candidates) {
      const label = cand.source_field_ids.join(" + ");
      expect(screen.getByText(label)).toBeInTheDocument();
    }

    expect(
      screen.getAllByText((text) => text.includes("src-")).length,
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
      expect(screen.getByText("person.person_id")).toBeInTheDocument();
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
      expect(screen.getByText("person.person_id")).toBeInTheDocument();
    });

    const allCandidateButtons = screen.getAllByRole("button").filter((btn) => {
      const text = btn.textContent || "";
      return text.includes("src-");
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

  it("allows user to select an alternative source field and reflects override in UI", async () => {
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
      expect(screen.getByText("person.person_id")).toBeInTheDocument();
    });

    const alternativeButton = screen.getByRole("button", { name: "src-mrn" });
    await user.click(alternativeButton);

    const inputFields = screen.getAllByPlaceholderText("e.g. patient.id");
    const personIdInput = inputFields[0] as HTMLInputElement;

    await waitFor(() => {
      expect(personIdInput.value).toBe("src-mrn");
    });
  });

  it("allows manual text entry in the source field input", async () => {
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
      expect(screen.getByText("person.person_id")).toBeInTheDocument();
    });

    const inputFields = screen.getAllByPlaceholderText("e.g. patient.id");
    const personIdInput = inputFields[0] as HTMLInputElement;

    await user.clear(personIdInput);
    await user.type(personIdInput, "custom-field-abc");

    expect(personIdInput.value).toBe("custom-field-abc");
  });
});
