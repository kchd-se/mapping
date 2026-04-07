import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../test-utils/render";
import { setupFetchMock, mockRoute, fixtures } from "../test-utils/mockApi";
import { ProjectValidation } from "../components/project/project-validation";

async function openSelectAndChoose(user: ReturnType<typeof userEvent.setup>) {
  const trigger = screen.getByRole("combobox");
  await user.click(trigger);

  await waitFor(() => {
    const option = document.querySelector("[role='option']");
    expect(option).toBeTruthy();
  });

  const option = document.querySelector("[role='option']") as HTMLElement;
  await user.click(option);
}

describe("Validation Panel", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders validation issues after running validation", async () => {
    const versions = fixtures.mappingVersions();
    const validation = fixtures.validation();
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/validate/, validation);

    renderWithProviders(<ProjectValidation projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Run Validation Suite")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);

    await user.click(screen.getByText("Run Validation Suite"));

    await waitFor(() => {
      expect(
        screen.getByText("Required target field is not mapped to any source"),
      ).toBeInTheDocument();
    });

    expect(
      screen.getByText("Source and target field types differ"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Field name does not follow target naming convention"),
    ).toBeInTheDocument();
  });

  it("displays rule IDs for each issue", async () => {
    const versions = fixtures.mappingVersions();
    const validation = fixtures.validation();
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/validate/, validation);

    renderWithProviders(<ProjectValidation projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Run Validation Suite")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);
    await user.click(screen.getByText("Run Validation Suite"));

    await waitFor(() => {
      expect(
        screen.getByText("Required target field is not mapped to any source"),
      ).toBeInTheDocument();
    });

    const ruleSpans = document.querySelectorAll("span.font-mono");
    const ruleTexts = Array.from(ruleSpans).map((s) => s.textContent?.trim());

    expect(ruleTexts.some((t) => t?.includes("REQUIRED_FIELD_UNMAPPED"))).toBe(true);
    expect(ruleTexts.some((t) => t?.includes("TYPE_MISMATCH"))).toBe(true);
    expect(ruleTexts.some((t) => t?.includes("NAMING_CONVENTION"))).toBe(true);
  });

  it("displays error and warning counts", async () => {
    const versions = fixtures.mappingVersions();
    const validation = fixtures.validation();
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/validate/, validation);

    renderWithProviders(<ProjectValidation projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Run Validation Suite")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);
    await user.click(screen.getByText("Run Validation Suite"));

    await waitFor(() => {
      expect(screen.getByText("Checks Failed")).toBeInTheDocument();
    });

    const errorsSection = screen.getByText("Errors").closest("div")!;
    expect(errorsSection.parentElement?.textContent).toContain("1");

    const warningsSection = screen.getByText("Warnings").closest("div")!;
    expect(warningsSection.parentElement?.textContent).toContain("1");
  });

  it("does not invent validation logic — issues come from mocked API", async () => {
    const versions = fixtures.mappingVersions();
    const emptyValidation = {
      project_id: "proj-001",
      mapping_version_id: "mv-001",
      has_errors: false,
      error_count: 0,
      warning_count: 0,
      issues: [],
    };
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/validate/, emptyValidation);

    renderWithProviders(<ProjectValidation projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Run Validation Suite")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);
    await user.click(screen.getByText("Run Validation Suite"));

    await waitFor(() => {
      expect(screen.getByText("Validation Passed")).toBeInTheDocument();
    });

    expect(
      screen.queryByText("Required target field is not mapped to any source"),
    ).not.toBeInTheDocument();
  });
});
