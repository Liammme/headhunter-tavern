"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { createClaim } from "../lib/api";
import type { JobCardPayload } from "../lib/types";

export default function ClaimDialog({ job }: { job: JobCardPayload }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [isPending, startTransition] = useTransition();

  function toggleDialog(nextOpen: boolean) {
    setOpen(nextOpen);
    setMessage("");

    if (!nextOpen) {
      setName("");
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");

    try {
      await createClaim(job.id, name);
      setMessage("认领成功");
      setName("");
      toggleDialog(false);
      startTransition(() => {
        router.refresh();
      });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "认领失败");
    } finally {
      setSaving(false);
    }
  }

  return open ? (
    <div className="claim-dialog">
      <h4>{job.claimed_names.length ? "我也认领" : "认领"}</h4>
      <form className="claim-form" onSubmit={handleSubmit}>
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="请输入你的名字"
          required
        />
        {message ? <span>{message}</span> : null}
        <div className="dialog-actions">
          <button className="text-button" type="button" onClick={() => toggleDialog(false)}>
            取消
          </button>
          <button className="claim-trigger" type="submit" disabled={saving || isPending}>
            {saving || isPending ? "提交中..." : job.claimed_names.length ? "我也认领" : "认领"}
          </button>
        </div>
      </form>
    </div>
  ) : (
    <button className="claim-trigger" type="button" onClick={() => toggleDialog(true)}>
      {job.claimed_names.length ? "我也认领" : "认领"}
    </button>
  );
}
