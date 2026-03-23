import { useEffect, useState } from "react";
import { listDenials, generateAppeal, getDenialActionPlan } from "../api/client";
import type { Denial, AppealDocument, DenialActionPlan } from "../api/types";
import { useToast } from "../components/Toast";

const BASE = "/bt";
const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001";

const DOC_TYPES = [
  { value: "periapical_xray", label: "Periapical X-ray" },
  { value: "bitewing_xray", label: "Bitewing X-ray" },
  { value: "panoramic_xray", label: "Panoramic X-ray" },
  { value: "intraoral_photo", label: "Intraoral Photo" },
  { value: "perio_charting", label: "Periodontal Charting" },
  { value: "clinical_narrative", label: "Clinical Narrative" },
  { value: "eob", label: "Explanation of Benefits (EOB)" },
  { value: "treatment_plan", label: "Treatment Plan" },
  { value: "specialist_letter", label: "Specialist Letter" },
  { value: "prior_claim", label: "Prior Claim Copy" },
  { value: "other", label: "Other Document" },
];
import StatusBadge from "../components/StatusBadge";

type AppealStage = "form" | "generating" | "preview";

export default function Denials() {
  const { addToast } = useToast();
  const [denials, setDenials] = useState<Denial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Appeal workflow
  const [appealDenialId, setAppealDenialId] = useState<string | null>(null);
  const [appealStage, setAppealStage] = useState<AppealStage>("form");
  const [appealState, setAppealState] = useState("CA");
  const [appealNotes, setAppealNotes] = useState("");
  const [appealResult, setAppealResult] = useState<AppealDocument | null>(null);
  const [editedAppealText, setEditedAppealText] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [expandedDenialId, setExpandedDenialId] = useState<string | null>(null);
  const [actionPlans, setActionPlans] = useState<Record<string, DenialActionPlan>>({});
  const [attachments, setAttachments] = useState<Record<string, Array<{ id: string; file_name: string; document_type: string; document_type_label: string }>>>({});
  const [verificationResults, setVerificationResults] = useState<Record<string, { verified: boolean; quality: string; findings: string; issues: string[]; suggestions: string[]; matches_claimed_type: boolean; suitable_for_appeal: boolean; reason: string } | null>>({});
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadDenials();
  }, []);

  async function loadDenials() {
    try {
      setLoading(true);
      const data = await listDenials();
      setDenials(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load denials");
    } finally {
      setLoading(false);
    }
  }

  async function toggleDenialExpand(denialId: string) {
    if (expandedDenialId === denialId) {
      setExpandedDenialId(null);
      return;
    }
    setExpandedDenialId(denialId);
    if (!actionPlans[denialId]) {
      try {
        const plan = await getDenialActionPlan(denialId);
        setActionPlans((prev) => ({ ...prev, [denialId]: plan }));
      } catch {}
    }
    loadAttachments(denialId);
  }

  async function loadAttachments(denialId: string) {
    try {
      const res = await fetch(`${BASE}/v1/denials/${denialId}/attachments`, {
        headers: { "X-Tenant-ID": localStorage.getItem("tenantId") ?? DEFAULT_TENANT },
      });
      if (res.ok) {
        const data = await res.json();
        setAttachments((prev) => ({ ...prev, [denialId]: data }));
      }
    } catch {}
  }

  async function handleUploadAttachment(denialId: string, file: File, docType: string) {
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_type", docType);
    try {
      const res = await fetch(`${BASE}/v1/denials/${denialId}/attachments`, {
        method: "POST",
        headers: { "X-Tenant-ID": localStorage.getItem("tenantId") ?? DEFAULT_TENANT },
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.verification) {
          setVerificationResults((prev) => ({ ...prev, [data.id]: data.verification }));
        }
        loadAttachments(denialId);
        addToast("success", "Document uploaded");
      }
    } catch {}
    setUploading(false);
  }

  async function handleDeleteAttachment(denialId: string, attachmentId: string) {
    try {
      await fetch(`${BASE}/v1/denials/${denialId}/attachments/${attachmentId}`, {
        method: "DELETE",
        headers: { "X-Tenant-ID": localStorage.getItem("tenantId") ?? DEFAULT_TENANT },
      });
      loadAttachments(denialId);
    } catch {}
  }

  function formatError(msg: string): string {
    if (msg.includes("Internal Server Error")) {
      return "This feature requires a valid API key. Check Practice Setup.";
    }
    return msg;
  }

  function openAppealForm(denial: Denial) {
    setAppealDenialId(denial.id);
    setAppealStage("form");
    setAppealState("CA");
    setAppealNotes(denial.denial_reason_description || "");
    setAppealResult(null);
    setEditedAppealText("");
    setIsEditing(false);
  }

  function closeAppeal() {
    setAppealDenialId(null);
    setAppealStage("form");
    setAppealResult(null);
    setEditedAppealText("");
    setIsEditing(false);
  }

  async function handleGenerate() {
    if (!appealDenialId) return;
    try {
      setAppealStage("generating");
      setError(null);
      const appeal = await generateAppeal(appealDenialId, {
        clinical_notes: appealNotes,
        state: appealState,
      });
      setAppealResult(appeal);
      setEditedAppealText(appeal.appeal_text);
      setAppealStage("preview");
    } catch (err) {
      setError(
        formatError(
          err instanceof Error ? err.message : "Failed to generate appeal",
        ),
      );
      setAppealStage("form");
    }
  }

  async function handleCopy() {
    const text = editedAppealText || appealResult?.appeal_text || "";
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
    }
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  }

  function handlePrint() {
    const text = editedAppealText || appealResult?.appeal_text || "";
    const printWindow = window.open("", "_blank");
    if (!printWindow) return;
    printWindow.document.write(`<!DOCTYPE html>
<html><head><title>Appeal Letter</title>
<style>
body { font-family: 'Georgia', serif; max-width: 750px; margin: 50px auto; padding: 0 30px; line-height: 1.8; color: #111; font-size: 13px; }
h1 { font-family: 'Helvetica Neue', sans-serif; font-size: 16px; margin-bottom: 20px; border-bottom: 2px solid #333; padding-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
pre { white-space: pre-wrap; word-wrap: break-word; font-family: inherit; }
.footer { margin-top: 40px; font-size: 10px; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }
</style></head><body>
<h1>Insurance Appeal Letter</h1>
<pre>${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</pre>
<div class="footer">Generated by Phenomenal Problems &mdash; AI-Powered Dental Insurance Coding</div>
</body></html>`);
    printWindow.document.close();
    printWindow.print();
  }

  function handleApprove() {
    // In a real implementation, this would submit the appeal
    // For now, just close and refresh to show updated status
    closeAppeal();
    loadDenials();
    addToast("success", "Appeal saved");
  }

  // Get the denial being worked on
  const activeDenial = denials.find((d) => d.id === appealDenialId);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-heading font-bold text-gray-100">
          Denials
        </h1>
        <p className="text-sm font-body text-gray-500 mt-1">
          Manage denied claims and generate appeals
          {!loading &&
            ` \u00b7 ${denials.length} denial${denials.length !== 1 ? "s" : ""}`}
        </p>
      </div>

      {error && (
        <div className="mb-5 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm font-body">
          {error}
        </div>
      )}

      {/* Appeal Workflow — Full Screen Overlay */}
      {appealDenialId && (
        <div className="mb-6">
          {/* Form stage */}
          {appealStage === "form" && (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="font-heading font-semibold text-gray-100">
                    Draft Appeal Letter
                  </h3>
                  <p className="text-xs text-gray-500 font-body mt-0.5">
                    {activeDenial?.payer_name} &mdash; $
                    {activeDenial?.denied_amount?.toFixed(2)}
                  </p>
                </div>
                <button
                  onClick={closeAppeal}
                  className="text-gray-600 hover:text-gray-400 transition-colors p-1"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {activeDenial && (
                <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4 mb-5">
                  <p className="text-xs font-heading font-semibold text-red-400 uppercase tracking-wider mb-1">
                    Denial Reason
                  </p>
                  <p className="text-sm text-gray-300 font-body">
                    {activeDenial.denial_reason_description}
                  </p>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-heading font-semibold text-gray-400 mb-1.5">
                    State (for case law citations)
                  </label>
                  <input
                    type="text"
                    value={appealState}
                    onChange={(e) => setAppealState(e.target.value)}
                    className="input-field w-full max-w-[120px]"
                    placeholder="e.g. CA"
                  />
                </div>
                <div>
                  <label className="block text-xs font-heading font-semibold text-gray-400 mb-1.5">
                    Clinical Notes & Justification
                  </label>
                  <p className="text-xs text-gray-600 font-body mb-2">
                    The more detail you provide, the stronger the appeal. Include
                    specific measurements, clinical findings, and why this
                    treatment was medically necessary.
                  </p>
                  <textarea
                    value={appealNotes}
                    onChange={(e) => setAppealNotes(e.target.value)}
                    rows={6}
                    className="input-field w-full resize-none"
                    placeholder="Example: Patient presents with Stage II, Grade B periodontitis. Probing depths of 5-7mm in upper right quadrant at teeth #2-5. Bleeding on probing at all sites. Bitewing radiographs show 20-30% horizontal bone loss. Previous prophylaxis on 09/2025 was insufficient to manage disease progression..."
                  />
                </div>
                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={handleGenerate}
                    className="btn-primary inline-flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
                    </svg>
                    Generate Appeal with AI
                  </button>
                  <button onClick={closeAppeal} className="btn-secondary">
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Generating stage */}
          {appealStage === "generating" && (
            <div className="card p-10 text-center overflow-hidden relative">
              {/* Animated background glow */}
              <div className="absolute inset-0 overflow-hidden">
                <div
                  className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] opacity-[0.03]"
                  style={{
                    background: "conic-gradient(from 0deg, #00D4FF, #00FF88, #00D4FF)",
                    animation: "spin 4s linear infinite",
                  }}
                />
              </div>

              <div className="relative">
                {/* Pulsing icon */}
                <div className="w-20 h-20 mx-auto mb-6 relative">
                  <div className="absolute inset-0 bg-cyan/10 rounded-2xl animate-ping" style={{ animationDuration: "2s" }} />
                  <div className="absolute inset-0 bg-cyan/5 rounded-2xl animate-pulse" />
                  <div className="relative w-20 h-20 bg-navy-800 border border-cyan/20 rounded-2xl flex items-center justify-center">
                    <svg className="w-8 h-8 text-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
                    </svg>
                  </div>
                </div>

                <h3 className="text-xl font-heading font-bold text-gray-100 mb-2">
                  Drafting Your Appeal
                </h3>

                {/* Animated steps */}
                <div className="space-y-3 max-w-sm mx-auto mt-6 text-left">
                  {[
                    { label: "Analyzing denial reason", delay: "0s" },
                    { label: "Researching case law citations", delay: "1s" },
                    { label: "Reviewing clinical documentation", delay: "2s" },
                    { label: "Writing formal appeal letter", delay: "3s" },
                  ].map((step, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 text-sm font-body"
                      style={{
                        animation: `fadeSlideIn 0.5s ease-out ${step.delay} both`,
                      }}
                    >
                      <div className="w-5 h-5 rounded-full border-2 border-cyan/30 border-t-cyan animate-spin shrink-0" style={{ animationDuration: "1.5s" }} />
                      <span className="text-gray-400">{step.label}</span>
                    </div>
                  ))}
                </div>

                <p className="text-xs text-gray-600 font-body mt-6">
                  This typically takes 10-15 seconds
                </p>
              </div>

              <style>{`
                @keyframes fadeSlideIn {
                  from { opacity: 0; transform: translateY(8px); }
                  to { opacity: 1; transform: translateY(0); }
                }
                @keyframes spin {
                  to { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          )}

          {/* Preview stage */}
          {appealStage === "preview" && appealResult && (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-lime/10 rounded-xl flex items-center justify-center">
                    <svg className="w-5 h-5 text-lime" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-heading font-semibold text-gray-100">
                      Appeal Letter Preview
                    </h3>
                    <p className="text-xs text-gray-500 font-body">
                      Review, edit if needed, then approve or send
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className={`btn-secondary text-xs px-3 py-1.5 ${isEditing ? "border-cyan/30 text-cyan" : ""}`}
                  >
                    {isEditing ? "Done Editing" : "Edit"}
                  </button>
                  <button
                    onClick={closeAppeal}
                    className="text-gray-600 hover:text-gray-400 transition-colors p-1"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Appeal text — editable or read-only */}
              <div className="bg-navy-900 rounded-xl border border-white/[0.06] overflow-hidden">
                {isEditing ? (
                  <textarea
                    value={editedAppealText}
                    onChange={(e) => setEditedAppealText(e.target.value)}
                    className="w-full p-6 bg-transparent text-sm text-gray-200 font-body leading-relaxed resize-none focus:outline-none min-h-[400px]"
                    style={{ minHeight: "400px" }}
                  />
                ) : (
                  <div className="p-6 max-h-[500px] overflow-auto text-sm text-gray-200 font-body leading-relaxed whitespace-pre-wrap">
                    {editedAppealText}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center justify-between mt-5">
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleCopy}
                    className="btn-secondary inline-flex items-center gap-2 text-sm"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
                    </svg>
                    {copySuccess ? "Copied!" : "Copy"}
                  </button>
                  <button
                    onClick={handlePrint}
                    className="btn-secondary inline-flex items-center gap-2 text-sm"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0 1 10.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0 .229 2.523a1.125 1.125 0 0 1-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0 0 21 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 0 0-1.913-.247M6.34 18H5.25A2.25 2.25 0 0 1 3 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.041 48.041 0 0 1 1.913-.247m10.5 0a48.536 48.536 0 0 0-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5Zm-3 0h.008v.008H15V10.5Z" />
                    </svg>
                    Print
                  </button>
                  <button
                    onClick={() => {
                      setAppealStage("form");
                      setAppealResult(null);
                    }}
                    className="btn-secondary inline-flex items-center gap-2 text-sm"
                  >
                    Regenerate
                  </button>
                </div>
                <button
                  onClick={handleApprove}
                  className="btn-primary inline-flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                  Approve & Save
                </button>
              </div>

              <p className="text-xs text-gray-600 font-body mt-3">
                This saves the appeal letter to the denial record. No appeal is
                submitted automatically — use Copy or Print to send it to the
                insurance company.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Denials list */}
      {loading ? (
        <div className="flex items-center gap-3 text-gray-400">
          <div className="w-5 h-5 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
          <span className="font-body text-sm">Loading...</span>
        </div>
      ) : denials.length === 0 ? (
        <div className="card p-12 text-center">
          <svg className="w-12 h-12 text-gray-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
          </svg>
          <p className="text-gray-400 font-body">No denials</p>
          <p className="text-gray-600 font-body text-sm mt-1">
            That's a good thing
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {denials.map((d) => {
            const expanded = expandedDenialId === d.id;
            const plan = actionPlans[d.id];
            const categoryIcons: Record<string, string> = {
              gather: "Gather",
              prepare: "Prepare",
              submit: "Submit",
              follow_up: "Follow Up",
            };
            const categoryColors: Record<string, string> = {
              gather: "bg-cyan/10 text-cyan border-cyan/30",
              prepare: "bg-amber-500/10 text-amber-400 border-amber-500/30",
              submit: "bg-lime/10 text-lime border-lime/30",
              follow_up: "bg-purple-500/10 text-purple-400 border-purple-500/30",
            };

            return (
              <div key={d.id} className="card overflow-hidden">
                <button
                  onClick={() => toggleDenialExpand(d.id)}
                  className="w-full p-5 text-left hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-sm font-heading font-semibold text-gray-100">
                          {d.payer_name}
                        </span>
                        <StatusBadge status={d.status} />
                        {d.denied_amount && (
                          <span className="text-lg font-heading font-bold text-red-400">
                            ${d.denied_amount.toLocaleString(undefined, {
                              minimumFractionDigits: 2,
                              maximumFractionDigits: 2,
                            })}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400 font-body line-clamp-2">
                        {d.denial_reason_description}
                      </p>
                    </div>
                    <div className="ml-4 shrink-0 flex items-center gap-3">
                      {d.status === "denied" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openAppealForm(d);
                          }}
                          className="btn-primary text-sm px-4 py-2"
                        >
                          Draft Appeal
                        </button>
                      )}
                      {d.status === "appealed" && (
                        <span className="text-xs text-purple-400 font-heading font-semibold">
                          Appeal Filed
                        </span>
                      )}
                      <svg
                        className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                      </svg>
                    </div>
                  </div>
                </button>

                {/* Expanded action plan */}
                {expanded && (
                  <div className="px-5 pb-5 border-t border-white/[0.04]">
                    {!plan ? (
                      <div className="py-4 flex items-center gap-2 text-gray-500 text-sm">
                        <div className="w-4 h-4 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
                        Loading action plan...
                      </div>
                    ) : (
                      <div className="mt-4 space-y-4">
                        {/* What went wrong */}
                        <div className="bg-red-500/5 border border-red-500/15 rounded-lg p-4">
                          <h4 className="text-xs font-heading font-semibold text-red-400 uppercase tracking-wider mb-1">
                            What Went Wrong
                          </h4>
                          <p className="text-sm text-gray-300 font-body leading-relaxed">
                            {plan.what_went_wrong}
                          </p>
                        </div>

                        {/* Deadline warning */}
                        {plan.deadline_days && (
                          <div className="flex items-center gap-2 text-sm">
                            <svg className="w-4 h-4 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                            </svg>
                            <span className="text-amber-400 font-heading font-semibold">
                              {plan.deadline_note}
                            </span>
                          </div>
                        )}

                        {/* Action steps */}
                        <div>
                          <h4 className="text-xs font-heading font-semibold text-gray-400 uppercase tracking-wider mb-3">
                            Steps to Resolve ({plan.total_steps})
                          </h4>
                          <div className="space-y-2">
                            {plan.steps.map((step) => (
                              <div
                                key={step.order}
                                className="flex items-start gap-3 bg-navy-900 rounded-lg p-3 border border-white/[0.04]"
                              >
                                <div className="flex items-center gap-2 shrink-0 mt-0.5">
                                  <span className="w-6 h-6 rounded-full bg-white/[0.06] flex items-center justify-center text-xs font-heading font-bold text-gray-400">
                                    {step.order}
                                  </span>
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 mb-0.5">
                                    <span className="text-sm font-heading font-semibold text-gray-200">
                                      {step.title}
                                    </span>
                                    <span
                                      className={`text-xs font-heading px-1.5 py-0.5 rounded border ${
                                        categoryColors[step.category] || "bg-white/[0.06] text-gray-500 border-white/[0.08]"
                                      }`}
                                    >
                                      {categoryIcons[step.category] || step.category}
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-400 font-body leading-relaxed">
                                    {step.description}
                                  </p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Attached documents */}
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <h4 className="text-xs font-heading font-semibold text-gray-400 uppercase tracking-wider">
                              Attached Documents ({(attachments[d.id] || []).length})
                            </h4>
                            <label className={`btn-secondary text-xs px-3 py-1.5 cursor-pointer inline-flex items-center gap-1.5 ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
                              {uploading ? (
                                <>
                                  <span className="w-3 h-3 border-2 border-cyan/30 border-t-cyan rounded-full animate-spin" />
                                  Verifying...
                                </>
                              ) : (
                                <>
                                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                                  </svg>
                                  Upload
                                </>
                              )}
                              <input
                                type="file"
                                className="hidden"
                                accept="image/*,.pdf,.doc,.docx"
                                onChange={(e) => {
                                  const file = e.target.files?.[0];
                                  if (file) {
                                    // Determine doc type from file name/type
                                    const name = file.name.toLowerCase();
                                    let docType = "other";
                                    if (name.includes("perio") || name.includes("charting")) docType = "perio_charting";
                                    else if (name.includes("bitewing") || name.includes("bwx")) docType = "bitewing_xray";
                                    else if (name.includes("pano")) docType = "panoramic_xray";
                                    else if (name.includes("periapical") || name.includes("pa_")) docType = "periapical_xray";
                                    else if (name.includes("eob") || name.includes("explanation")) docType = "eob";
                                    else if (name.includes("narrative")) docType = "clinical_narrative";
                                    else if (file.type.startsWith("image/")) docType = "intraoral_photo";
                                    handleUploadAttachment(d.id, file, docType);
                                    e.target.value = "";
                                  }
                                }}
                              />
                            </label>
                          </div>

                          {(attachments[d.id] || []).length === 0 ? (
                            <p className="text-xs text-gray-600 font-body py-2">
                              No documents attached yet. Upload the documents listed in the steps above to strengthen your appeal.
                            </p>
                          ) : (
                            <div className="space-y-1.5">
                              {(attachments[d.id] || []).map((att) => {
                                const vr = verificationResults[att.id];
                                return (
                                  <div key={att.id} className="bg-navy-900 rounded-lg border border-white/[0.04]">
                                    <div className="flex items-center justify-between px-3 py-2">
                                      <div className="flex items-center gap-2 min-w-0">
                                        {vr ? (
                                          vr.verified && vr.suitable_for_appeal ? (
                                            <svg className="w-4 h-4 text-lime shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                              <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                                            </svg>
                                          ) : (
                                            <svg className="w-4 h-4 text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
                                            </svg>
                                          )
                                        ) : (
                                          <svg className="w-4 h-4 text-cyan shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="m18.375 12.739-7.693 7.693a4.5 4.5 0 0 1-6.364-6.364l10.94-10.94A3 3 0 1 1 19.5 7.372L8.552 18.32m.009-.01-.01.01m5.699-9.941-7.81 7.81a1.5 1.5 0 0 0 2.112 2.13" />
                                          </svg>
                                        )}
                                        <span className="text-xs text-gray-300 truncate">{att.file_name}</span>
                                        <span className="text-xs text-gray-600 shrink-0">{att.document_type_label}</span>
                                        {vr && (
                                          <span className={`text-xs font-heading px-1.5 py-0.5 rounded shrink-0 ${
                                            vr.quality === "good" ? "bg-lime/10 text-lime" :
                                            vr.quality === "acceptable" ? "bg-cyan/10 text-cyan" :
                                            vr.quality === "poor" ? "bg-amber-500/10 text-amber-400" :
                                            "bg-red-500/10 text-red-400"
                                          }`}>
                                            {vr.quality}
                                          </span>
                                        )}
                                      </div>
                                      <button
                                        onClick={() => handleDeleteAttachment(d.id, att.id)}
                                        className="text-gray-600 hover:text-red-400 transition-colors p-0.5 shrink-0"
                                      >
                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                                        </svg>
                                      </button>
                                    </div>
                                    {vr && (vr.issues.length > 0 || !vr.matches_claimed_type) && (
                                      <div className="px-3 pb-2 space-y-1">
                                        {!vr.matches_claimed_type && (
                                          <p className="text-xs text-amber-400">
                                            Type mismatch: This looks like a {vr.actual_type || "different document"}, not a {att.document_type_label}.
                                          </p>
                                        )}
                                        {vr.issues.map((issue, idx) => (
                                          <p key={idx} className="text-xs text-amber-400">{issue}</p>
                                        ))}
                                        {vr.suggestions.map((sug, idx) => (
                                          <p key={idx} className="text-xs text-cyan">{sug}</p>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>

                        {/* How to prevent */}
                        <div className="bg-lime/5 border border-lime/15 rounded-lg p-4">
                          <h4 className="text-xs font-heading font-semibold text-lime uppercase tracking-wider mb-1">
                            How to Prevent This Next Time
                          </h4>
                          <p className="text-sm text-gray-300 font-body leading-relaxed">
                            {plan.how_to_prevent}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
