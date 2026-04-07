import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeAll } from "vitest";

beforeAll(() => {
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.setItem("mapping-user-id", "test-user");
    window.localStorage.setItem("mapping-user-role", "admin");
  }

  if (typeof Element !== "undefined") {
    Element.prototype.hasPointerCapture = Element.prototype.hasPointerCapture || (() => false);
    Element.prototype.setPointerCapture = Element.prototype.setPointerCapture || (() => {});
    Element.prototype.releasePointerCapture = Element.prototype.releasePointerCapture || (() => {});
  }

  if (typeof window !== "undefined") {
    window.HTMLElement.prototype.scrollIntoView = window.HTMLElement.prototype.scrollIntoView || (() => {});
  }
});

afterEach(() => {
  cleanup();
});
