import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { renderWithProviders } from "../test-utils/render";
import { setupFetchMock, mockRoute, fixtures } from "../test-utils/mockApi";
import { ProjectsList } from "../pages/projects-list";

describe("Project Management", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders project list from API response", async () => {
    const projects = fixtures.projects();
    mockRoute("GET", /\/projects(\?|$)/, projects);

    renderWithProviders(<ProjectsList />);

    await waitFor(() => {
      expect(screen.getByText("EHR Integration Pipeline")).toBeInTheDocument();
    });

    expect(screen.getByText("Claims Data Migration")).toBeInTheDocument();
    expect(screen.getByText("Lab Results Mapping")).toBeInTheDocument();
    expect(screen.getByText("Pharmacy Records")).toBeInTheDocument();
    expect(screen.getByText("Retired Demographics Project")).toBeInTheDocument();
  });

  it("displays project status for each project", async () => {
    const projects = fixtures.projects();
    mockRoute("GET", /\/projects(\?|$)/, projects);

    renderWithProviders(<ProjectsList />);

    await waitFor(() => {
      expect(screen.getByText("EHR Integration Pipeline")).toBeInTheDocument();
    });

    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(screen.getByText("review")).toBeInTheDocument();
    expect(screen.getByText("approved")).toBeInTheDocument();
    expect(screen.getByText("published")).toBeInTheDocument();
    expect(screen.getByText("archived")).toBeInTheDocument();
  });

  it("does not contain hardcoded projects", async () => {
    mockRoute("GET", /\/projects(\?|$)/, []);

    renderWithProviders(<ProjectsList />);

    await waitFor(() => {
      expect(screen.getByText("No active projects")).toBeInTheDocument();
    });

    expect(screen.queryByText("EHR Integration Pipeline")).not.toBeInTheDocument();
    expect(screen.queryByText("Claims Data Migration")).not.toBeInTheDocument();
  });

  it("renders all projects returned by API, not a subset", async () => {
    const projects = fixtures.projects();
    mockRoute("GET", /\/projects(\?|$)/, projects);

    renderWithProviders(<ProjectsList />);

    await waitFor(() => {
      expect(screen.getByText("EHR Integration Pipeline")).toBeInTheDocument();
    });

    const renderedCards = projects.map((p) =>
      screen.getByText(p.name),
    );
    expect(renderedCards).toHaveLength(projects.length);
  });

  it("fails explicitly when fetch is unmocked", async () => {
    vi.restoreAllMocks();
    setupFetchMock();

    renderWithProviders(<ProjectsList />);

    await waitFor(() => {
      const errorEl = screen.queryByTestId("text-api-error");
      expect(errorEl).toBeInTheDocument();
    });
  });

  it("opens create project dialog and creates a project successfully", async () => {
    const projects = fixtures.projects();
    const newProject = {
      id: "proj-new-001",
      name: "New Test Project",
      description: "A new project",
      status: "draft",
      owner: "dev-user",
      sensitivity: "healthcare_highly_sensitive",
      created_at: "2026-04-07T12:00:00Z",
    };
    mockRoute("GET", /\/projects(\?|$)/, projects);
    mockRoute("POST", /\/projects$/, newProject, 201);
    mockRoute("GET", /\/projects\/proj-new-001$/, newProject);

    renderWithProviders(<ProjectsList />);

    await waitFor(() => {
      expect(screen.getByTestId("button-new-project")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("button-new-project"));

    await waitFor(() => {
      expect(screen.getByTestId("input-project-name")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("input-project-name"), {
      target: { value: "New Test Project" },
    });

    const createBtn = screen.getByTestId("button-create-project");
    expect(createBtn).not.toBeDisabled();
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(screen.queryByTestId("input-project-name")).not.toBeInTheDocument();
    });
  });

  it("shows error toast when project creation fails", async () => {
    mockRoute("GET", /\/projects(\?|$)/, []);
    mockRoute("POST", /\/projects$/, { detail: "API unavailable" }, 503);

    renderWithProviders(<ProjectsList />);

    await waitFor(() => {
      expect(screen.getByTestId("button-new-project")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("button-new-project"));

    await waitFor(() => {
      expect(screen.getByTestId("input-project-name")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("input-project-name"), {
      target: { value: "Failing Project" },
    });

    fireEvent.click(screen.getByTestId("button-create-project"));

    await waitFor(() => {
      expect(screen.getByText("Failed to create project")).toBeInTheDocument();
    });
  });
});
