import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../test-utils/render";
import { setupFetchMock, mockRoute, fixtures } from "../test-utils/mockApi";
import { ProjectExport } from "../components/project/project-export";

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

describe("Export", () => {
  beforeEach(() => {
    setupFetchMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("triggers export and displays mapping artifact", async () => {
    const versions = fixtures.mappingVersions();
    const exportResult = fixtures.exportResult();
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/export/, exportResult);

    renderWithProviders(<ProjectExport projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Compile Export")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);
    await user.click(screen.getByText("Compile Export"));

    await waitFor(() => {
      expect(screen.getByText("Compiled Mapping")).toBeInTheDocument();
    });

    expect(screen.getByText("Download JSON")).toBeInTheDocument();
  });

  it("displays the generated transformation script as text", async () => {
    const versions = fixtures.mappingVersions();
    const exportResult = fixtures.exportResult();
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/export/, exportResult);

    renderWithProviders(<ProjectExport projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Compile Export")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);
    await user.click(screen.getByText("Compile Export"));

    await waitFor(() => {
      expect(screen.getByText("Transformation Script")).toBeInTheDocument();
    });

    const scriptContent = screen.getByText((content) =>
      content.includes("execution not supported in v1"),
    );
    expect(scriptContent).toBeInTheDocument();
  });

  it("displays a label indicating execution is not supported in v1", async () => {
    const versions = fixtures.mappingVersions();
    const exportResult = fixtures.exportResult();
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/export/, exportResult);

    renderWithProviders(<ProjectExport projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Compile Export")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);
    await user.click(screen.getByText("Compile Export"));

    await waitFor(() => {
      const scriptContent = screen.getByText((content) =>
        content.includes("execution not supported in v1"),
      );
      expect(scriptContent).toBeInTheDocument();
    });
  });

  it("displays the artifact JSON content", async () => {
    const versions = fixtures.mappingVersions();
    const exportResult = fixtures.exportResult();
    mockRoute("GET", /\/projects\/proj-001\/mappings(\?|$)/, versions);
    mockRoute("POST", /\/projects\/proj-001\/export/, exportResult);

    renderWithProviders(<ProjectExport projectId="proj-001" />);
    const user = userEvent.setup();

    await waitFor(() => {
      expect(screen.getByText("Compile Export")).toBeInTheDocument();
    });

    await openSelectAndChoose(user);
    await user.click(screen.getByText("Compile Export"));

    await waitFor(() => {
      const preElements = document.querySelectorAll("pre");
      const hasArtifactJson = Array.from(preElements).some((pre) =>
        pre.textContent?.includes("person.person_id"),
      );
      expect(hasArtifactJson).toBe(true);
    });
  });
});
