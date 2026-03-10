import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";

describe("App shell", () => {
  it("renders loading state", () => {
    const { getByText } = render(
      <MemoryRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(getByText(/loading/i)).toBeTruthy();
  });
});
