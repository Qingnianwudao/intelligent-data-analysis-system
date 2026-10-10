import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "./auth/AuthContext";
import { LoginPage } from "./auth/LoginPage";

describe("LoginPage", () => {
  it("renders demo login form", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: /NL2SQL/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /进入系统/i })).toBeInTheDocument();
  });
});
