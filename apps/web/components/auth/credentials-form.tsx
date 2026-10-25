"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import type { ApiErrorPayload } from "@/lib/auth-types";

type CredentialsFormProps = {
  mode: "login" | "register";
};

type FieldErrors = {
  email?: string;
  password?: string;
};

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateCredentials(mode: CredentialsFormProps["mode"], email: string, password: string) {
  const errors: FieldErrors = {};
  if (!email) {
    errors.email = "Enter your email address.";
  } else if (!EMAIL_PATTERN.test(email)) {
    errors.email = "Enter a valid email address.";
  }

  if (!password) {
    errors.password = "Enter your password.";
  } else if (mode === "register") {
    const missingRequirements = [
      password.length < 12 ? "12 characters" : null,
      !/[a-z]/.test(password) ? "a lowercase letter" : null,
      !/[A-Z]/.test(password) ? "an uppercase letter" : null,
      !/[0-9]/.test(password) ? "a number" : null,
      !/[^A-Za-z0-9\s]/.test(password) ? "a symbol" : null,
    ].filter(Boolean);

    if (missingRequirements.length > 0) {
      errors.password = `Your password still needs ${missingRequirements.join(", ")}.`;
    }
  }

  return errors;
}

async function readErrorMessage(response: Response) {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (payload.error?.message) {
      return payload.error.message;
    }
  } catch {
    // A safe fallback is returned below when the response is not JSON.
  }
  return "We could not complete that request. Please try again.";
}

type FieldProps = {
  id: string;
  label: string;
  value: string;
  error?: string;
  autoComplete: string;
  onChange: (value: string) => void;
};

function EmailField({ id, label, value, error, autoComplete, onChange }: FieldProps) {
  const errorId = `${id}-error`;
  return (
    <div>
      <label className="block text-sm font-semibold text-emerald-950" htmlFor={id}>
        {label}
      </label>
      <input
        aria-describedby={error ? errorId : undefined}
        aria-invalid={Boolean(error)}
        autoCapitalize="none"
        autoComplete={autoComplete}
        className="mt-2 min-h-12 w-full rounded-xl border border-emerald-950/15 bg-white px-4 text-base text-emerald-950 shadow-sm outline-none transition placeholder:text-emerald-950/35 focus:border-emerald-700 focus:ring-4 focus:ring-emerald-700/10 aria-invalid:border-red-700"
        id={id}
        inputMode="email"
        name="email"
        onChange={(event) => onChange(event.target.value)}
        placeholder="you@example.com"
        type="email"
        value={value}
      />
      {error ? (
        <p className="mt-2 text-sm text-red-800" id={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

function PasswordField({ id, label, value, error, autoComplete, onChange }: FieldProps) {
  const [isVisible, setIsVisible] = useState(false);
  const errorId = `${id}-error`;
  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <label className="block text-sm font-semibold text-emerald-950" htmlFor={id}>
          {label}
        </label>
        <button
          aria-controls={id}
          aria-label={isVisible ? "Hide password" : "Show password"}
          className="text-xs font-semibold text-emerald-700 hover:text-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
          onClick={() => setIsVisible((current) => !current)}
          type="button"
        >
          {isVisible ? "Hide" : "Show"}
        </button>
      </div>
      <input
        aria-describedby={error ? errorId : undefined}
        aria-invalid={Boolean(error)}
        autoComplete={autoComplete}
        className="mt-2 min-h-12 w-full rounded-xl border border-emerald-950/15 bg-white px-4 text-base text-emerald-950 shadow-sm outline-none transition focus:border-emerald-700 focus:ring-4 focus:ring-emerald-700/10 aria-invalid:border-red-700"
        id={id}
        maxLength={128}
        name="password"
        onChange={(event) => onChange(event.target.value)}
        type={isVisible ? "text" : "password"}
        value={value}
      />
      {error ? (
        <p className="mt-2 text-sm leading-6 text-red-800" id={errorId}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function CredentialsForm({ mode }: CredentialsFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const isRegistration = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    const errors = validateCredentials(mode, normalizedEmail, password);
    setFieldErrors(errors);
    setFormError(null);

    if (Object.keys(errors).length > 0) {
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ email: normalizedEmail, password }),
      });

      if (!response.ok) {
        setFormError(await readErrorMessage(response));
        setPassword("");
        return;
      }

      setPassword("");
      if (isRegistration) {
        setRegisteredEmail(normalizedEmail);
        return;
      }

      router.replace("/dashboard");
      router.refresh();
    } catch {
      setFormError("Authentication is temporarily unavailable. Please try again.");
      setPassword("");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (registeredEmail) {
    return (
      <div
        aria-live="polite"
        className="rounded-2xl border border-emerald-700/20 bg-emerald-50 p-6"
        role="status"
      >
        <span
          aria-hidden="true"
          className="grid h-10 w-10 place-items-center rounded-full bg-emerald-800 text-lg text-white"
        >
          ✓
        </span>
        <h2 className="mt-5 text-xl font-semibold text-emerald-950">Your account is ready.</h2>
        <p className="mt-2 text-sm leading-6 text-emerald-950/65">
          We created the account for <span className="font-semibold">{registeredEmail}</span>. You
          can now sign in securely.
        </p>
        <Link
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-full bg-emerald-950 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
          href="/login"
        >
          Continue to login
        </Link>
      </div>
    );
  }

  return (
    <form aria-busy={isSubmitting} className="space-y-5" noValidate onSubmit={handleSubmit}>
      {formError ? (
        <div
          aria-live="assertive"
          className="rounded-xl border border-red-700/20 bg-red-50 px-4 py-3 text-sm leading-6 text-red-900"
          role="alert"
        >
          {formError}
        </div>
      ) : null}

      <EmailField
        autoComplete="email"
        error={fieldErrors.email}
        id={`${mode}-email`}
        label="Email address"
        onChange={(value) => {
          setEmail(value);
          setFieldErrors((current) => ({ ...current, email: undefined }));
        }}
        value={email}
      />
      <PasswordField
        autoComplete={isRegistration ? "new-password" : "current-password"}
        error={fieldErrors.password}
        id={`${mode}-password`}
        label="Password"
        onChange={(value) => {
          setPassword(value);
          setFieldErrors((current) => ({ ...current, password: undefined }));
        }}
        value={password}
      />

      {isRegistration ? (
        <p className="text-xs leading-5 text-emerald-950/50">
          Use 12 to 128 characters with uppercase, lowercase, number, and symbol characters.
        </p>
      ) : null}

      <button
        className="inline-flex min-h-12 w-full items-center justify-center rounded-full bg-emerald-950 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/15 transition hover:bg-emerald-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800 disabled:cursor-wait disabled:bg-emerald-950/65"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? (
          <>
            <span
              aria-hidden="true"
              className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white"
            />
            {isRegistration ? "Creating account..." : "Signing in..."}
          </>
        ) : isRegistration ? (
          "Create account"
        ) : (
          "Sign in"
        )}
      </button>

      <p aria-live="polite" className="sr-only">
        {isSubmitting ? "Your authentication request is being processed." : ""}
      </p>
    </form>
  );
}
