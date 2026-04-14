import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PlatformIdentityDialog } from "@/features/accounts/components/platform-identity-dialog";
import { createAccountSummary } from "@/test/mocks/factories";

describe("PlatformIdentityDialog", () => {
  it("submits a provider-aware platform identity payload with automatic fallback scope", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onOpenChange = vi.fn();

    render(
      <PlatformIdentityDialog
        open
        busy={false}
        error={null}
        mode="create"
        prerequisiteSatisfied
        onOpenChange={onOpenChange}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText("Label"), "Production Platform");
    await user.type(screen.getByLabelText("API key"), "sk-platform-test");
    await user.type(screen.getByLabelText("Organization"), "org_test");
    await user.type(screen.getByLabelText("Project"), "proj_test");

    expect(screen.getByText(/Register a fallback-only upstream identity for/i)).toBeInTheDocument();
    expect(screen.getByText("All supported fallback paths are enabled automatically for this key.")).toBeInTheDocument();
    expect(
      screen.getByText(
        /It can back \/v1\/models, stateless HTTP \/v1\/responses, stateless HTTP \/v1\/responses\/compact/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Websocket and continuity-bound requests stay on ChatGPT."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Add API key" }));

    expect(onSubmit).toHaveBeenCalledWith({
      label: "Production Platform",
      apiKey: "sk-platform-test",
      organization: "org_test",
      project: "proj_test",
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("blocks submission when no active ChatGPT account is available", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <PlatformIdentityDialog
        open
        busy={false}
        error={null}
        mode="create"
        prerequisiteSatisfied={false}
        onOpenChange={() => {}}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText("Label"), "Platform Key");
    await user.type(screen.getByLabelText("API key"), "sk-platform-test");

    expect(
      screen.getByText("Add or reactivate a ChatGPT account first. Platform keys cannot be used on their own."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add API key" })).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits only changed fields in edit mode and allows clearing org/project without replacing the key", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onOpenChange = vi.fn();

    render(
      <PlatformIdentityDialog
        open
        busy={false}
        error={null}
        mode="edit"
        account={createAccountSummary({
          accountId: "platform_1",
          email: "Platform Original",
          displayName: "Platform Original",
          label: "Platform Original",
          planType: "openai_platform",
          providerKind: "openai_platform",
          routingSubjectId: "platform_1",
          organization: "org_original",
          project: "proj_original",
          eligibleRouteFamilies: ["public_models_http", "public_responses_http", "backend_codex_http"],
          usage: null,
          auth: null,
        })}
        onOpenChange={onOpenChange}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled();
    expect(
      screen.getByText(
        "Leave blank to keep the current Platform API key. Enter a new key only when rotating credentials.",
      ),
    ).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Label"));
    await user.type(screen.getByLabelText("Label"), "Platform Renamed");
    await user.clear(screen.getByLabelText("Organization"));
    await user.clear(screen.getByLabelText("Project"));
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(onSubmit).toHaveBeenCalledWith({
      label: "Platform Renamed",
      organization: null,
      project: null,
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("allows editing even when no active ChatGPT account is currently available", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <PlatformIdentityDialog
        open
        busy={false}
        error={null}
        mode="edit"
        prerequisiteSatisfied={false}
        account={createAccountSummary({
          accountId: "platform_2",
          email: "Platform Original",
          displayName: "Platform Original",
          label: "Platform Original",
          planType: "openai_platform",
          providerKind: "openai_platform",
          routingSubjectId: "platform_2",
          eligibleRouteFamilies: ["public_models_http", "public_responses_http", "backend_codex_http"],
          usage: null,
          auth: null,
        })}
        onOpenChange={() => {}}
        onSubmit={onSubmit}
      />,
    );

    expect(
      screen.getByText(
        "Path selection is no longer configurable. This key always covers the full supported fallback scope.",
      ),
    ).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Label"));
    await user.type(screen.getByLabelText("Label"), "Platform Still Editable");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(onSubmit).toHaveBeenCalledWith({ label: "Platform Still Editable" });
  });
});
