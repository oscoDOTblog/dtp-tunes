"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Music2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await api.post("/api/auth/login", { username, password });
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-base px-4">
      <div className="w-full max-w-sm rounded-2xl bg-bg-elevated p-8 shadow-2xl">
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent-soft text-accent">
            <Music2 size={28} />
          </div>
          <h1 className="text-2xl font-bold text-fg-primary">dtp-tunes</h1>
          <p className="text-sm text-fg-secondary">Sign in to your music server</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-fg-secondary">Username</label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-fg-secondary">Password</label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && <p className="text-sm text-danger">{error}</p>}

          <Button type="submit" size="lg" className="mt-2 w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
}
