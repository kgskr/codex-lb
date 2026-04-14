import { useMemo, useState } from "react";
import type { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type {
  AccountSummary,
  PlatformIdentityCreateRequest,
  PlatformIdentityUpdateRequest,
} from "@/features/accounts/schemas";

function normalizeOptionalText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

type PlatformIdentityFormState = {
  label: string;
  apiKey: string;
  organization: string;
  project: string;
};

function createPlatformIdentityFormState({
  isEdit,
  label,
  organization,
  project,
}: {
  isEdit: boolean;
  label: string;
  organization: string | null;
  project: string | null;
}): PlatformIdentityFormState {
  if (!isEdit) {
    return {
      label: "",
      apiKey: "",
      organization: "",
      project: "",
    };
  }
  return {
    label,
    apiKey: "",
    organization: organization ?? "",
    project: project ?? "",
  };
}

export type PlatformIdentityDialogProps = {
  open: boolean;
  busy: boolean;
  error: string | null;
  mode?: "create" | "edit";
  account?: AccountSummary | null;
  prerequisiteSatisfied?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (
    payload: PlatformIdentityCreateRequest | PlatformIdentityUpdateRequest,
  ) => Promise<void>;
};

export function PlatformIdentityDialog({
  open,
  busy,
  error,
  mode = "create",
  account = null,
  prerequisiteSatisfied = true,
  onOpenChange,
  onSubmit,
}: PlatformIdentityDialogProps) {
  const isEdit = mode === "edit";
  const initialLabel = account ? account.label ?? account.displayName ?? account.email : "";
  const initialOrganization = account?.organization ?? null;
  const initialProject = account?.project ?? null;

  const handleOpenChange = (nextOpen: boolean) => {
    onOpenChange(nextOpen);
  };

  const formKey = [
    mode,
    account?.accountId ?? "create",
    initialLabel,
    initialOrganization ?? "",
    initialProject ?? "",
  ].join(":");

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit OpenAI Platform API key" : "Add OpenAI Platform API key"}</DialogTitle>
          <DialogDescription>
            {isEdit ? (
              <>
                Update the fallback-only upstream identity for the full supported HTTP fallback scope. ChatGPT accounts
                stay primary, and this key is used only when the compatible ChatGPT pool is unhealthy under the
                primary or secondary drain thresholds.
              </>
            ) : (
              <>
                Register a fallback-only upstream identity for the full supported HTTP fallback scope. ChatGPT
                accounts stay primary, and this key is used only when the compatible ChatGPT pool is unhealthy under
                the primary or secondary drain thresholds.
              </>
            )}
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <PlatformIdentityDialogForm
            key={formKey}
            busy={busy}
            error={error}
            mode={mode}
            account={account}
            prerequisiteSatisfied={prerequisiteSatisfied}
            initialLabel={initialLabel}
            initialOrganization={initialOrganization}
            initialProject={initialProject}
            onOpenChange={onOpenChange}
            onSubmit={onSubmit}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

type PlatformIdentityDialogFormProps = {
  busy: boolean;
  error: string | null;
  mode: "create" | "edit";
  account: AccountSummary | null;
  prerequisiteSatisfied: boolean;
  initialLabel: string;
  initialOrganization: string | null;
  initialProject: string | null;
  onOpenChange: (open: boolean) => void;
  onSubmit: (
    payload: PlatformIdentityCreateRequest | PlatformIdentityUpdateRequest,
  ) => Promise<void>;
};

function PlatformIdentityDialogForm({
  busy,
  error,
  mode,
  account,
  prerequisiteSatisfied,
  initialLabel,
  initialOrganization,
  initialProject,
  onOpenChange,
  onSubmit,
}: PlatformIdentityDialogFormProps) {
  const isEdit = mode === "edit";
  const [formState, setFormState] = useState(() =>
    createPlatformIdentityFormState({
      isEdit,
      label: initialLabel,
      organization: initialOrganization,
      project: initialProject,
    }),
  );
  const { label, apiKey, organization, project } = formState;

  const resetForm = () => {
    setFormState(
      createPlatformIdentityFormState({
        isEdit,
        label: initialLabel,
        organization: initialOrganization,
        project: initialProject,
      }),
    );
  };

  const hasChanges = useMemo(() => {
    if (!isEdit || !account) {
      return true;
    }
    const nextLabel = label.trim();
    const nextOrganization = normalizeOptionalText(organization);
    const nextProject = normalizeOptionalText(project);
    return (
      nextLabel !== initialLabel ||
      apiKey.trim().length > 0 ||
      nextOrganization !== initialOrganization ||
      nextProject !== initialProject
    );
  }, [
    account,
    apiKey,
    initialLabel,
    initialOrganization,
    initialProject,
    isEdit,
    label,
    organization,
    project,
  ]);

  const canSubmit = useMemo(
    () =>
      label.trim().length > 0 &&
      (isEdit ? !!account && hasChanges : prerequisiteSatisfied && apiKey.trim().length > 0),
    [account, apiKey, hasChanges, isEdit, label, prerequisiteSatisfied],
  );

  const updateFormState = <Key extends keyof PlatformIdentityFormState>(
    key: Key,
    value: PlatformIdentityFormState[Key],
  ) => {
    setFormState((current) => ({ ...current, [key]: value }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) {
      return;
    }
    if (isEdit) {
      const payload: PlatformIdentityUpdateRequest = {};
      const nextLabel = label.trim();
      const nextOrganization = normalizeOptionalText(organization);
      const nextProject = normalizeOptionalText(project);

      if (nextLabel !== initialLabel) {
        payload.label = nextLabel;
      }
      if (apiKey.trim().length > 0) {
        payload.apiKey = apiKey.trim();
      }
      if (nextOrganization !== initialOrganization) {
        payload.organization = nextOrganization;
      }
      if (nextProject !== initialProject) {
        payload.project = nextProject;
      }
      await onSubmit(payload);
    } else {
      await onSubmit({
        label,
        apiKey,
        organization,
        project,
      });
    }
    resetForm();
    onOpenChange(false);
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="platform-label">Label</Label>
        <Input
          id="platform-label"
          placeholder="Production platform key"
          value={label}
          onChange={(event) => updateFormState("label", event.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="platform-api-key">API key</Label>
        <Input
          id="platform-api-key"
          type="password"
          placeholder={isEdit ? "Leave blank to keep the existing key" : "sk-..."}
          value={apiKey}
          onChange={(event) => updateFormState("apiKey", event.target.value)}
        />
        {isEdit ? (
          <p className="text-xs text-muted-foreground">
            Leave blank to keep the current Platform API key. Enter a new key only when rotating credentials.
          </p>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="platform-organization">Organization</Label>
          <Input
            id="platform-organization"
            placeholder="org_..."
            value={organization}
            onChange={(event) => updateFormState("organization", event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="platform-project">Project</Label>
          <Input
            id="platform-project"
            placeholder="proj_..."
            value={project}
            onChange={(event) => updateFormState("project", event.target.value)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Fallback scope</Label>
        <div className="rounded-lg border bg-muted/20 p-3 text-xs text-muted-foreground">
          <p>All supported fallback paths are enabled automatically for this key.</p>
          <p className="mt-2">
            It can back <code>/v1/models</code>, stateless HTTP <code>/v1/responses</code>, stateless HTTP{" "}
            <code>/v1/responses/compact</code>, <code>/backend-api/codex/models</code>, stateless HTTP{" "}
            <code>/backend-api/codex/responses</code>, and stateless HTTP{" "}
            <code>/backend-api/codex/responses/compact</code>.
          </p>
          <p className="mt-2">Websocket and continuity-bound requests stay on ChatGPT.</p>
        </div>
        <p className="text-xs text-muted-foreground">
          {isEdit
            ? "Path selection is no longer configurable. This key always covers the full supported fallback scope."
            : "Requires an existing ChatGPT account that is not paused or deactivated. Only one Platform API key can be registered, and it is used only as fallback behind the ChatGPT pool."}
        </p>
        {!isEdit && !prerequisiteSatisfied ? (
          <p className="text-xs text-destructive">
            Add or reactivate a ChatGPT account first. Platform keys cannot be used on their own.
          </p>
        ) : null}
      </div>

      {error ? (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 px-2 py-1 text-xs text-destructive">
          {error}
        </p>
      ) : null}

      <DialogFooter>
        <Button type="submit" disabled={busy || !canSubmit}>
          {isEdit ? "Save changes" : "Add API key"}
        </Button>
      </DialogFooter>
    </form>
  );
}
