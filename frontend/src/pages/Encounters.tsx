import { useEffect, useState, useRef } from "react";
import { Link } from "react-router-dom";
import {
  listPatients,
  createEncounterFromNotes,
  createEncounterFromImage,
  codeEncounter,
  approveCodedEncounter,
  createClaim,
  verifyImages,
  validateEncounter,
  checkImageQuality,
  getDocumentationTemplate,
} from "../api/client";
import type { Patient, Encounter, CodedEncounter, Claim, ImageVerification, ValidationResult, ImageQualityResult, DocumentationTemplate } from "../api/types";

type Step = "input" | "parsing" | "coding" | "review" | "claim" | "done";

export default function Encounters() {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientId, setPatientId] = useState("");
  const [patientSearch, setPatientSearch] = useState("");
  const [providerName, setProviderName] = useState(() => {
    try {
      const setup = JSON.parse(localStorage.getItem("pp_practice_setup") || "{}");
      return setup.practice?.provider_name || "Dr. Smith";
    } catch { return "Dr. Smith"; }
  });
  const [notes, setNotes] = useState("");
  const [step, setStep] = useState<Step>("input");
  const [error, setError] = useState<string | null>(null);

  // Results from each stage
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [coded, setCoded] = useState<CodedEncounter | null>(null);
  const [claim, setClaim] = useState<Claim | null>(null);
  const [verification, setVerification] = useState<ImageVerification | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [docTemplate, setDocTemplate] = useState<DocumentationTemplate | null>(null);

  // Images
  const [images, setImages] = useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = useState<string[]>([]);
  const [imageQuality, setImageQuality] = useState<(ImageQualityResult | null)[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Voice
  const [listening, setListening] = useState(false);
  const [interimText, setInterimText] = useState("");
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const finalTranscriptRef = useRef("");
  const wantListeningRef = useRef(false);

  useEffect(() => {
    listPatients()
      .then((p) => {
        setPatients(p);
        if (p.length > 0) setPatientId(p[0].id);
      })
      .catch(() => {});
  }, []);

  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setError("Speech recognition not supported in this browser. Use Chrome on Android, or Safari on iOS.");
      return;
    }

    // Stop any existing instance
    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    // Store current notes as the baseline
    finalTranscriptRef.current = notes;
    wantListeningRef.current = true;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscriptRef.current = (finalTranscriptRef.current + " " + transcript).trim();
          setNotes(finalTranscriptRef.current);
          setInterimText("");
        } else {
          interim += transcript;
        }
      }
      if (interim) {
        setInterimText(interim);
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      // "no-speech" and "aborted" are normal — don't show as errors
      if (event.error !== "aborted" && event.error !== "no-speech") {
        setError(`Voice error: ${event.error}. Make sure you're using HTTPS and have granted microphone permission.`);
        wantListeningRef.current = false;
        setListening(false);
      }
    };

    recognition.onend = () => {
      // Chrome auto-stops after silence — restart if user hasn't clicked stop
      if (wantListeningRef.current) {
        try {
          recognition.start();
        } catch {
          setListening(false);
          wantListeningRef.current = false;
        }
      } else {
        setListening(false);
        setInterimText("");
      }
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
      setError(null);
    } catch (err) {
      setError("Could not start microphone. Check browser permissions.");
    }
  }

  function stopListening() {
    wantListeningRef.current = false;
    setInterimText("");
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
    }
    setListening(false);
  }

  function handleImageAdd(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    setImages((prev) => [...prev, ...files]);

    // Generate previews and run quality checks
    files.forEach((file, idx) => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setImagePreviews((prev) => [...prev, ev.target?.result as string]);
      };
      reader.readAsDataURL(file);

      // Quality check (async, non-blocking)
      checkImageQuality(file)
        .then((result) => {
          setImageQuality((prev) => {
            const next = [...prev];
            next[images.length + idx] = result;
            return next;
          });
        })
        .catch(() => {
          // Silently fail — quality check is optional
        });
    });

    // Reset input so same file can be re-selected
    e.target.value = "";
  }

  function handleImageRemove(index: number) {
    setImages((prev) => prev.filter((_, i) => i !== index));
    setImagePreviews((prev) => prev.filter((_, i) => i !== index));
    setImageQuality((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleProcess() {
    if (!patientId || (!notes.trim() && images.length === 0)) return;
    setError(null);

    try {
      // Step 1: Parse notes and/or images
      setStep("parsing");
      const today = new Date().toISOString().split("T")[0];

      let enc: Encounter;

      if (images.length > 0) {
        // Analyze the first image, with notes as context
        enc = await createEncounterFromImage(
          patientId,
          providerName,
          today,
          images[0],
          notes.trim() || undefined,
        );
      } else {
        enc = await createEncounterFromNotes({
          patient_id: patientId,
          provider_name: providerName,
          date_of_service: today,
          notes: notes.trim(),
        });
      }
      setEncounter(enc);

      // Step 1b: Get documentation template (non-blocking)
      getDocumentationTemplate(enc.id)
        .then((tmpl) => setDocTemplate(tmpl))
        .catch(() => {});

      // Step 2: AI coding
      setStep("coding");
      const codedEnc = await codeEncounter(enc.id);
      setCoded(codedEnc);

      // Step 2b: Run pre-submission validation
      try {
        const valResult = await validateEncounter(enc.id, images.length > 0);
        setValidation(valResult);
      } catch {
        // Non-blocking
      }

      // Step 2c: If images attached, verify them against coded procedures
      if (images.length > 0) {
        try {
          const verResult = await verifyImages(enc.id, images[0]);
          setVerification(verResult);
        } catch {
          // Non-blocking — verification is a bonus, don't fail the flow
          console.warn("Image verification failed, continuing without it");
        }
      }

      // Step 3: Review
      setStep("review");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Processing failed";
      setError(
        msg.includes("Internal Server Error")
          ? "AI processing failed. This usually means the API key is invalid or has no credits. Check Practice Setup."
          : msg,
      );
      setStep("input");
    }
  }

  async function handleApproveAndClaim() {
    if (!coded || !encounter) return;
    setError(null);

    try {
      setStep("claim");
      await approveCodedEncounter(encounter.id);
      const newClaim = await createClaim(coded.id);
      setClaim(newClaim);
      setStep("done");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create claim";
      setError(
        msg.includes("Internal Server Error")
          ? "Claim creation failed. Check that the API key is valid in Practice Setup."
          : msg,
      );
      setStep("review");
    }
  }

  function handleReset() {
    setNotes("");
    setImages([]);
    setImagePreviews([]);
    setImageQuality([]);
    setVerification(null);
    setValidation(null);
    setDocTemplate(null);
    setEncounter(null);
    setCoded(null);
    setClaim(null);
    setStep("input");
    setError(null);
  }

  const selectedPatient = patients.find((p) => p.id === patientId);

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-heading font-bold text-gray-100">
          New Encounter
        </h1>
        <p className="text-sm font-body text-gray-500 mt-1">
          Dictate or type clinical notes — AI handles the rest
        </p>
      </div>

      {/* Progress steps */}
      <div className="flex items-center gap-2 mb-8">
        {(
          [
            ["input", "Notes"],
            ["parsing", "Parsing"],
            ["coding", "Coding"],
            ["review", "Review"],
            ["done", "Done"],
          ] as const
        ).map(([key, label], i) => {
          const steps: Step[] = [
            "input",
            "parsing",
            "coding",
            "review",
            "done",
          ];
          const currentIdx = steps.indexOf(step === "claim" ? "done" : step);
          const thisIdx = steps.indexOf(key);
          const isActive = thisIdx === currentIdx;
          const isDone = thisIdx < currentIdx;

          return (
            <div key={key} className="flex items-center gap-2">
              {i > 0 && (
                <div
                  className={`w-8 h-px ${isDone ? "bg-cyan" : "bg-white/10"}`}
                />
              )}
              <div
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-heading font-semibold transition-all ${
                  isActive
                    ? "bg-cyan/10 text-cyan border border-cyan/30"
                    : isDone
                      ? "bg-lime/10 text-lime border border-lime/30"
                      : "text-gray-600 border border-white/[0.06]"
                }`}
              >
                {isDone && (
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="m4.5 12.75 6 6 9-13.5"
                    />
                  </svg>
                )}
                {label}
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="mb-5 p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-sm font-body">
          {error}
        </div>
      )}

      {/* Step: Input */}
      {step === "input" && (
        <div className="space-y-5">
          {/* How it works — dismissible */}
          {!localStorage.getItem("pp_hide_howto") && (
            <div className="card p-5 border-cyan/20 bg-cyan-50 relative">
              <button
                onClick={() => {
                  localStorage.setItem("pp_hide_howto", "1");
                  // Force re-render
                  setError((e) => e);
                }}
                className="absolute top-3 right-3 text-gray-600 hover:text-gray-400 transition-colors"
                title="Dismiss"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
              <h3 className="text-sm font-heading font-semibold text-cyan mb-2">
                How it works
              </h3>
              <ol className="text-sm text-gray-400 font-body space-y-1.5 list-decimal list-inside">
                <li>
                  <strong className="text-gray-300">Select a patient</strong> and
                  enter the provider name
                </li>
                <li>
                  <strong className="text-gray-300">Dictate or type</strong>{" "}
                  clinical notes — describe what you did and what you found
                </li>
                <li>
                  <strong className="text-gray-300">Attach X-rays or photos</strong>{" "}
                  — AI verifies images match the procedures and flags missing
                  documentation
                </li>
                <li>
                  <strong className="text-gray-300">Review AI results</strong> —
                  suggested CDT codes, confidence scores, and any documentation
                  alerts
                </li>
                <li>
                  <strong className="text-gray-300">Approve</strong> to
                  automatically generate the insurance claim
                </li>
              </ol>
            </div>
          )}

          {/* Patient + Provider */}
          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              Patient & Provider
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="relative">
                <input
                  value={patientSearch}
                  onChange={(e) => setPatientSearch(e.target.value)}
                  placeholder="Search patients..."
                  className="input-field w-full"
                />
                {patientSearch && (
                  <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-navy-800 border border-white/[0.1] rounded-xl shadow-lg max-h-48 overflow-y-auto">
                    {patients
                      .filter((p) =>
                        `${p.first_name} ${p.last_name}`
                          .toLowerCase()
                          .includes(patientSearch.toLowerCase()),
                      )
                      .map((p) => (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => {
                            setPatientId(p.id);
                            setPatientSearch(`${p.first_name} ${p.last_name}`);
                          }}
                          className={`w-full text-left px-4 py-2.5 text-sm font-body hover:bg-white/[0.04] transition-colors ${
                            patientId === p.id ? "text-cyan" : "text-gray-300"
                          }`}
                        >
                          {p.first_name} {p.last_name}
                          <span className="text-gray-600 ml-2 text-xs">
                            DOB: {p.date_of_birth}
                          </span>
                        </button>
                      ))}
                    {patients.filter((p) =>
                      `${p.first_name} ${p.last_name}`
                        .toLowerCase()
                        .includes(patientSearch.toLowerCase()),
                    ).length === 0 && (
                      <p className="px-4 py-2.5 text-sm text-gray-500">
                        No patients found
                      </p>
                    )}
                  </div>
                )}
                {!patientSearch && patientId && (
                  <p className="text-xs text-cyan mt-1">
                    {patients.find((p) => p.id === patientId)?.first_name}{" "}
                    {patients.find((p) => p.id === patientId)?.last_name} selected
                  </p>
                )}
              </div>
              <input
                value={providerName}
                onChange={(e) => setProviderName(e.target.value)}
                placeholder="Provider name"
                className="input-field"
              />
            </div>
          </div>

          {/* Clinical Notes */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-heading font-semibold text-gray-300">
                Clinical Notes
              </h3>
              <button
                type="button"
                onClick={listening ? stopListening : startListening}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-heading font-semibold transition-all ${
                  listening
                    ? "bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse"
                    : "bg-cyan/10 text-cyan border border-cyan/30 hover:bg-cyan/20"
                }`}
              >
                <svg
                  className="w-4 h-4"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                  <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                </svg>
                {listening ? "Stop Recording" : "Dictate"}
              </button>
            </div>
            <div className="relative">
              <textarea
                value={notes}
                onChange={(e) => {
                  setNotes(e.target.value);
                  finalTranscriptRef.current = e.target.value;
                }}
                placeholder="Dictate or type clinical notes...&#10;&#10;Example: Patient presents for routine prophy and BWX. Moderate calculus noted. Healthy gingiva. No new carious lesions."
                rows={6}
                className="input-field w-full resize-none"
              />
              {interimText && (
                <div className="absolute bottom-3 left-4 right-4 text-sm text-cyan/60 italic font-body pointer-events-none truncate">
                  {interimText}...
                </div>
              )}
            </div>
            {listening && (
              <div className="mt-3 flex items-center gap-3 text-sm">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="inline-block w-1.5 h-3 rounded-full bg-red-500/60 animate-pulse" style={{ animationDelay: "150ms" }} />
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500/40 animate-pulse" style={{ animationDelay: "300ms" }} />
                </span>
                <span className="text-gray-400">
                  Listening — speak naturally, pauses are OK
                </span>
              </div>
            )}
          </div>

          {/* Image Attachments */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-heading font-semibold text-gray-300">
                X-Rays & Photos
              </h3>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 px-4 py-2 bg-white/[0.06] text-gray-300 border border-white/[0.08] rounded-xl text-sm font-heading font-semibold transition-all hover:bg-white/[0.1] hover:border-white/[0.15]"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                </svg>
                Add Image
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                multiple
                onChange={handleImageAdd}
                className="hidden"
              />
            </div>

            {imagePreviews.length === 0 ? (
              <p className="text-sm text-gray-600 font-body">
                Attach X-rays, periapical radiographs, or intraoral photos for AI analysis. Optional if you have written notes.
              </p>
            ) : (
              <div className="space-y-3">
                {imagePreviews.map((src, i) => {
                  const quality = imageQuality[i];
                  const hasErrors = quality && quality.error_count > 0;
                  const hasWarnings = quality && quality.warning_count > 0;

                  return (
                    <div
                      key={i}
                      className={`bg-navy-900 rounded-lg p-3 border ${
                        hasErrors
                          ? "border-red-500/30"
                          : hasWarnings
                            ? "border-amber-500/20"
                            : quality?.passed
                              ? "border-lime/20"
                              : "border-white/[0.06]"
                      }`}
                    >
                      <div className="flex gap-3">
                        <div className="relative shrink-0 group">
                          <img
                            src={src}
                            alt={`Attachment ${i + 1}`}
                            className="w-24 h-24 object-cover rounded-lg"
                          />
                          <button
                            type="button"
                            onClick={() => handleImageRemove(i)}
                            className="absolute top-1 right-1 w-5 h-5 bg-red-500/80 text-white rounded-full flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            &times;
                          </button>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-xs text-gray-400 truncate">
                              {images[i]?.name}
                            </p>
                            {quality && (
                              <span
                                className={`shrink-0 text-xs font-heading font-semibold px-1.5 py-0.5 rounded ${
                                  hasErrors
                                    ? "bg-red-500/20 text-red-400"
                                    : hasWarnings
                                      ? "bg-amber-500/15 text-amber-400"
                                      : "bg-lime/10 text-lime"
                                }`}
                              >
                                {hasErrors
                                  ? "Issues Found"
                                  : hasWarnings
                                    ? "Warnings"
                                    : "Good"}
                              </span>
                            )}
                          </div>
                          {quality?.issues.map((issue, j) => (
                            <div key={j} className="mt-1.5">
                              <p
                                className={`text-xs font-medium ${
                                  issue.severity === "error"
                                    ? "text-red-400"
                                    : "text-amber-400"
                                }`}
                              >
                                {issue.message}
                              </p>
                              <p className="text-xs text-gray-500 mt-0.5">
                                {issue.suggestion}
                              </p>
                            </div>
                          ))}
                          {quality && quality.metadata.width && (
                            <p className="text-xs text-gray-600 mt-1">
                              {quality.metadata.width as number}x{quality.metadata.height as number} &middot;{" "}
                              {((quality.metadata.file_size as number) / 1000).toFixed(0)}KB
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <button
            onClick={handleProcess}
            disabled={
              !patientId ||
              (!notes.trim() && images.length === 0) ||
              imageQuality.some((q) => q && q.error_count > 0) ||
              step !== "input"
            }
            className="btn-primary w-full py-3 text-base disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {imageQuality.some((q) => q && q.error_count > 0)
              ? "Fix image issues before processing"
              : step !== "input"
                ? "Processing..."
                : "Process with AI"}
          </button>
        </div>
      )}

      {/* Step: Processing (parsing or coding) */}
      {(step === "parsing" || step === "coding") && (
        <div className="card p-12 text-center">
          <div className="w-12 h-12 border-3 border-cyan/20 border-t-cyan rounded-full animate-spin mx-auto mb-5" />
          <p className="text-lg font-heading font-semibold text-gray-200">
            {step === "parsing"
              ? "Parsing clinical notes..."
              : "AI suggesting CDT codes..."}
          </p>
          <p className="text-sm font-body text-gray-500 mt-2">
            {step === "parsing"
              ? "Extracting procedures, teeth, and diagnoses"
              : "Matching procedures to CDT codes with confidence scoring"}
          </p>
        </div>
      )}

      {/* Step: Review */}
      {step === "review" && encounter && coded && (
        <div className="space-y-5">
          {/* Patient info bar */}
          {selectedPatient && (
            <div className="card px-5 py-3 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-cyan/10 flex items-center justify-center text-cyan text-sm font-heading font-bold">
                {selectedPatient.first_name[0]}
                {selectedPatient.last_name[0]}
              </div>
              <div>
                <p className="text-sm font-medium text-gray-200">
                  {selectedPatient.first_name} {selectedPatient.last_name}
                </p>
                <p className="text-xs text-gray-500">
                  DOB: {selectedPatient.date_of_birth}
                </p>
              </div>
            </div>
          )}

          {/* Parsed Procedures */}
          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              Parsed Procedures
            </h3>
            <div className="space-y-3">
              {encounter.procedures.map((proc) => (
                <div
                  key={proc.id}
                  className="bg-navy-900 rounded-lg p-4 border border-white/[0.06]"
                >
                  <p className="text-sm font-medium text-gray-200">
                    {proc.description}
                  </p>
                  <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-400">
                    {proc.tooth_numbers && proc.tooth_numbers.length > 0 && (
                      <span>
                        Teeth: {proc.tooth_numbers.join(", ")}
                      </span>
                    )}
                    {proc.surfaces && proc.surfaces.length > 0 && (
                      <span>
                        Surfaces: {proc.surfaces.join(", ")}
                      </span>
                    )}
                    {proc.quadrant && <span>Quadrant: {proc.quadrant}</span>}
                    {proc.diagnosis && (
                      <span className="text-cyan">Dx: {proc.diagnosis}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* AI-Suggested CDT Codes */}
          <div className="card p-5">
            <h3 className="text-sm font-heading font-semibold text-gray-300 mb-4">
              AI-Suggested CDT Codes
            </h3>
            <div className="space-y-3">
              {coded.coded_procedures.map((cp) => (
                <div
                  key={cp.id}
                  className="bg-navy-900 rounded-lg p-4 border border-white/[0.06]"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-heading font-bold text-cyan">
                          {cp.cdt_code}
                        </span>
                        <span className="text-sm text-gray-300">
                          {cp.cdt_description}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-3 mt-1.5 text-xs text-gray-500">
                        {cp.tooth_number && (
                          <span>Tooth: {cp.tooth_number}</span>
                        )}
                        {cp.surfaces && <span>Surfaces: {cp.surfaces}</span>}
                      </div>
                    </div>
                    <ConfidenceBadge score={cp.confidence_score} />
                  </div>
                  {cp.ai_reasoning && (
                    <p className="text-xs text-gray-500 mt-2 leading-relaxed">
                      {cp.ai_reasoning}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Documentation Template — what the dentist needs to provide */}
          {docTemplate && docTemplate.prompts.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-heading font-semibold text-gray-300 mb-1">
                Required Documentation
              </h3>
              <p className="text-xs text-gray-500 font-body mb-4">
                {docTemplate.summary}
              </p>
              <div className="space-y-2">
                {docTemplate.prompts.map((prompt, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 bg-navy-900 rounded-lg p-3 border ${
                      prompt.required
                        ? "border-cyan/20"
                        : "border-white/[0.04]"
                    }`}
                  >
                    <span className="mt-0.5 shrink-0">
                      {prompt.category === "image" ? (
                        <svg className="w-4 h-4 text-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                        </svg>
                      ) : prompt.category === "measurement" ? (
                        <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                        </svg>
                      )}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm text-gray-200 font-medium">
                          {prompt.label}
                        </p>
                        {prompt.required && (
                          <span className="text-xs font-heading font-semibold text-cyan bg-cyan/10 border border-cyan/30 px-1.5 py-0.5 rounded">
                            Required
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {prompt.description}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        For: {prompt.for_procedure}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pre-Submission Validation */}
          {validation && validation.issues.length > 0 && (
            <div
              className={`card p-5 border ${
                !validation.passed
                  ? "border-red-500/30 bg-red-500/5"
                  : "border-amber-500/20 bg-amber-500/5"
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <svg
                    className={`w-5 h-5 ${!validation.passed ? "text-red-400" : "text-amber-400"}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
                    />
                  </svg>
                  <h3 className="text-sm font-heading font-semibold text-gray-200">
                    Pre-Submission Check
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Denial Risk:</span>
                  <span
                    className={`text-sm font-heading font-bold ${
                      validation.overall_denial_risk >= 60
                        ? "text-red-400"
                        : validation.overall_denial_risk >= 30
                          ? "text-amber-400"
                          : "text-lime"
                    }`}
                  >
                    {validation.overall_denial_risk}%
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-400 mb-3 font-body">
                {validation.summary}
              </p>
              <div className="space-y-2">
                {validation.issues.map((issue, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 rounded-lg p-3 ${
                      issue.severity === "block"
                        ? "bg-red-500/10 border border-red-500/20"
                        : issue.severity === "warn"
                          ? "bg-amber-500/5 border border-amber-500/15"
                          : "bg-white/[0.02] border border-white/[0.06]"
                    }`}
                  >
                    <span
                      className={`mt-0.5 shrink-0 text-xs font-heading font-bold px-1.5 py-0.5 rounded ${
                        issue.severity === "block"
                          ? "bg-red-500/20 text-red-400"
                          : issue.severity === "warn"
                            ? "bg-amber-500/15 text-amber-400"
                            : "bg-white/[0.06] text-gray-500"
                      }`}
                    >
                      {issue.severity === "block" ? "BLOCKER" : issue.severity === "warn" ? "WARNING" : "NOTE"}
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm text-gray-200">
                        {issue.message}
                      </p>
                      {issue.recommendation && (
                        <p className="text-xs text-cyan mt-1">
                          {issue.recommendation}
                        </p>
                      )}
                    </div>
                    <span
                      className={`shrink-0 text-xs font-heading font-bold ${
                        issue.denial_probability >= 60
                          ? "text-red-400"
                          : issue.denial_probability >= 30
                            ? "text-amber-400"
                            : "text-gray-600"
                      }`}
                    >
                      {issue.denial_probability}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Image Verification Results */}
          {verification && (
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-heading font-semibold text-gray-300">
                  Image Verification
                </h3>
                <span
                  className={`inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-heading font-semibold border ${
                    verification.overall_assessment.documentation_strength === "strong"
                      ? "bg-lime/10 text-lime border-lime/30"
                      : verification.overall_assessment.documentation_strength === "moderate"
                        ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                        : "bg-red-500/15 text-red-400 border-red-500/30"
                  }`}
                >
                  {verification.overall_assessment.documentation_strength} documentation
                </span>
              </div>

              <p className="text-sm text-gray-400 mb-4 font-body">
                {verification.overall_assessment.summary}
              </p>

              {/* Per-procedure verification */}
              <div className="space-y-2 mb-4">
                {verification.verifications.map((v, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 bg-navy-900 rounded-lg p-3 border ${
                      v.status === "supported"
                        ? "border-lime/20"
                        : v.status === "unsupported"
                          ? "border-red-500/30"
                          : "border-amber-500/20"
                    }`}
                  >
                    <span className="mt-0.5">
                      {v.status === "supported" ? (
                        <svg className="w-4 h-4 text-lime" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      ) : v.status === "unsupported" ? (
                        <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                        </svg>
                      )}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-heading font-bold text-cyan">{v.cdt_code}</span>
                        <span className="text-xs text-gray-500">{v.confidence}% confidence</span>
                      </div>
                      <p className="text-xs text-gray-400 mt-0.5">{v.finding}</p>
                      {v.concern && (
                        <p className="text-xs text-amber-400 mt-1">
                          Concern: {v.concern}
                        </p>
                      )}
                      {v.recommendation && (
                        <p className="text-xs text-cyan mt-0.5">
                          {v.recommendation}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Missed findings */}
              {verification.missed_findings.length > 0 && (
                <div>
                  <h4 className="text-xs font-heading font-semibold text-amber-400 mb-2 uppercase tracking-wider">
                    Missed Findings in Image
                  </h4>
                  {verification.missed_findings.map((f, i) => (
                    <div
                      key={i}
                      className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-3 mb-2"
                    >
                      <p className="text-sm text-gray-300 font-medium">{f.description}</p>
                      <div className="flex flex-wrap gap-3 mt-1.5 text-xs text-gray-500">
                        {f.tooth_number && <span>Tooth: {f.tooth_number}</span>}
                        {f.suggested_code && (
                          <span className="text-cyan">
                            Suggested: {f.suggested_code} — {f.suggested_description}
                          </span>
                        )}
                      </div>
                      {f.reasoning && (
                        <p className="text-xs text-gray-500 mt-1">{f.reasoning}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Original Notes (collapsed) */}
          <details className="card">
            <summary className="px-5 py-3 text-sm font-heading font-semibold text-gray-400 cursor-pointer hover:text-gray-300">
              Original Notes
            </summary>
            <div className="px-5 pb-4 text-sm text-gray-400 font-body whitespace-pre-wrap">
              {encounter.raw_notes}
            </div>
          </details>

          {/* Actions */}
          <div className="flex gap-3">
            <button onClick={handleReset} className="btn-secondary flex-1">
              Start Over
            </button>
            <button
              onClick={handleApproveAndClaim}
              className="btn-primary flex-1 py-3"
            >
              Approve & Generate Claim
            </button>
          </div>
        </div>
      )}

      {/* Step: Creating claim */}
      {step === "claim" && (
        <div className="card p-12 text-center">
          <div className="w-12 h-12 border-3 border-lime/20 border-t-lime rounded-full animate-spin mx-auto mb-5" />
          <p className="text-lg font-heading font-semibold text-gray-200">
            Generating claim...
          </p>
        </div>
      )}

      {/* Step: Done */}
      {step === "done" && claim && (
        <div className="space-y-5">
          <div className="card p-8 text-center">
            <div className="w-16 h-16 bg-lime/10 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-lime"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="m4.5 12.75 6 6 9-13.5"
                />
              </svg>
            </div>
            <h2 className="text-xl font-heading font-bold text-gray-100">
              Claim Generated
            </h2>
            <p className="text-sm text-gray-400 mt-2 font-body">
              Status: <span className="text-cyan">{claim.status}</span>
            </p>
            {claim.total_fee_submitted && (
              <p className="text-2xl font-heading font-bold text-lime mt-3">
                ${claim.total_fee_submitted.toFixed(2)}
              </p>
            )}
          </div>

          {/* Claim procedures */}
          {claim.procedures.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-heading font-semibold text-gray-300 mb-3">
                Claim Procedures
              </h3>
              {claim.procedures.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between py-2 border-b border-white/[0.04] last:border-0"
                >
                  <div>
                    <span className="text-sm font-heading font-bold text-cyan">
                      {p.cdt_code}
                    </span>
                    <span className="text-sm text-gray-400 ml-2">
                      {p.cdt_description}
                    </span>
                  </div>
                  {p.fee_submitted && (
                    <span className="text-sm font-medium text-gray-200">
                      ${p.fee_submitted.toFixed(2)}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-3">
            <Link
              to="/claims"
              className="btn-secondary flex-1 py-3 text-center"
            >
              View Claims
            </Link>
            <button onClick={handleReset} className="btn-primary flex-1 py-3">
              New Encounter
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function ConfidenceBadge({ score }: { score: number }) {
  const color =
    score >= 90
      ? "bg-lime/10 text-lime border-lime/30"
      : score >= 70
        ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
        : "bg-red-500/15 text-red-400 border-red-500/30";

  return (
    <span
      className={`inline-flex items-center rounded-lg px-2 py-1 text-xs font-heading font-semibold border ${color}`}
    >
      {score}%
    </span>
  );
}
