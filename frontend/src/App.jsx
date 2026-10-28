// Placeholder — main frontend component (company search form + verdict display).
// To be implemented.

import { useState } from "react";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const initialForm = {
  company_name: "",
  cin: "",
  website: "",
  offer_text: "",
};

function humanize(value) {
  if (!value) return "Not provided";
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function firstValue(...values) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== ""
  );
}

function getStatusColor(status) {
  const normalized = String(status || "").toLowerCase();

  if (["found", "verified", "completed", "scored", "success"].includes(normalized)) {
    return "good";
  }

  if (["not_found", "error", "failed", "high", "critical"].includes(normalized)) {
    return "bad";
  }

  return "neutral";
}

function Section({ title, subtitle, children }) {
  return (
    <section className="panel">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function StatusPill({ status }) {
  return (
    <span className={`status-pill ${getStatusColor(status)}`}>
      {humanize(status)}
    </span>
  );
}

function DetailRow({ label, value }) {
  if (value === undefined || value === null || value === "") return null;

  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>{typeof value === "object" ? JSON.stringify(value) : String(value)}</strong>
    </div>
  );
}

function getFindings(data) {
  const findings = data?.scoring?.findings_considered;
  const scannerFindings =
    data?.offer_scan?.findings ??
    data?.offer_scan?.red_flags ??
    data?.offer_scan?.results;

  if (Array.isArray(findings) && findings.length > 0) return findings;
  if (Array.isArray(scannerFindings)) return scannerFindings;

  return [];
}

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: form.company_name.trim(),
          cin: form.cin.trim(),
          website: form.website.trim(),
          offer_text: form.offer_text.trim(),
        }),
      });

      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        const detail = payload?.detail;
        const message =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((item) => item.msg || JSON.stringify(item)).join(", ")
              : `The server returned HTTP ${response.status}.`;

        throw new Error(message);
      }

      if (!payload || typeof payload !== "object") {
        throw new Error("The server returned an invalid response.");
      }

      setResult(payload);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Could not connect to the backend. Check that FastAPI is running and the API URL is correct."
          : err.message || "Something went wrong while verifying this submission."
      );
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setForm(initialForm);
    setResult(null);
    setError("");
  }

  const scoring = result?.scoring ?? {};
  const score = Number(scoring.risk_score);
  const validScore = Number.isFinite(score) && score >= 0 && score <= 100;
  const findings = result ? getFindings(result) : [];
  const identity =
    result?.company_identity ?? result?.checks?.company_identity ?? {};
  const webPresence =
    result?.web_presence ?? result?.checks?.web_presence ?? {};
  const investigation = result?.investigation ?? {};
  const report =
    typeof investigation === "string"
      ? investigation
      : firstValue(
          investigation.report,
          investigation.summary,
          investigation.output
        );

  const companyName = firstValue(
    result?.company_name,
    result?.input?.company_name,
    form.company_name
  );

  const identityMatches = firstValue(
    identity.matches,
    identity.records,
    identity.results
  );

  const webResults = firstValue(
    webPresence.results,
    webPresence.matches,
    webPresence.items
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
          <span className="brand-mark">J</span>
          <span>JobShield<span className="brand-ai"> AI</span></span>
        </a>
        <div className="topbar-status">
          <span className="live-dot" />
          Verification workspace
        </div>
      </header>

      <main className="main-content">
        <section className="hero">
          <div className="eyebrow">
            <span className="eyebrow-line" />
            SMARTER JOB-OFFER VERIFICATION
          </div>
          <h1>
            Verify before
            <br />
            you <span className="gradient-text">trust.</span>
          </h1>
          <p className="hero-description">
            Investigate company records, online presence, and suspicious
            job-offer signals with a multi-agent AI verification workflow.
          </p>
          <div className="hero-points">
            <span>✓ Company checks</span>
            <span>✓ Offer risk indicators</span>
            <span>✓ AI investigation</span>
          </div>
        </section>

        <div className="workspace">
          <Section
            title="Start a verification"
            subtitle="Enter the details you have. Only the company name is required."
          >
            <form className="verification-form" onSubmit={handleSubmit}>
              <label>
                Company name <span className="required">*</span>
                <input
                  name="company_name"
                  value={form.company_name}
                  onChange={updateField}
                  placeholder="e.g. Example Technologies Pvt Ltd"
                  required
                  maxLength={200}
                />
              </label>

              <div className="form-grid">
                <label>
                  CIN <span className="optional">(optional)</span>
                  <input
                    name="cin"
                    value={form.cin}
                    onChange={updateField}
                    placeholder="Corporate Identification Number"
                    maxLength={30}
                  />
                </label>

                <label>
                  Company website <span className="optional">(optional)</span>
                  <input
                    name="website"
                    type="text"
                    value={form.website}
                    onChange={updateField}
                    placeholder="https://company.com"
                    maxLength={500}
                  />
                </label>
              </div>

              <label>
                Job offer or message
                <span className="optional"> (recommended)</span>
                <textarea
                  name="offer_text"
                  value={form.offer_text}
                  onChange={updateField}
                  placeholder="Paste the job offer, recruiter message, payment request, or other details you want checked..."
                  rows={6}
                  maxLength={20000}
                />
                <span className="field-hint">
                  {form.offer_text.length.toLocaleString()} / 20,000 characters
                </span>
              </label>

              {error && (
                <div className="error-banner" role="alert">
                  <span className="error-icon">!</span>
                  <div>
                    <strong>Verification could not be completed</strong>
                    <p>{error}</p>
                  </div>
                </div>
              )}

              <button className="primary-button" type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <span className="spinner" />
                    Investigating company...
                  </>
                ) : (
                  <>
                    Run verification <span aria-hidden="true">→</span>
                  </>
                )}
              </button>

              <p className="privacy-note">
                Results are evidence-based indicators, not a definitive
                determination of fraud.
              </p>
            </form>
          </Section>

          {loading && (
            <div className="loading-panel" role="status">
              <span className="large-spinner" />
              <h2>Investigating the details</h2>
              <p>
                Collecting available evidence and preparing the verification
                report. This may take a little while.
              </p>
            </div>
          )}

          {result && !loading && (
            <div className="results-area" aria-live="polite">
              <div className="results-header">
                <div>
                  <div className="eyebrow">VERIFICATION REPORT</div>
                  <h2>{companyName}</h2>
                  <p>Review each result alongside its available evidence.</p>
                </div>
                <button className="secondary-button" onClick={resetForm} type="button">
                  New verification
                </button>
              </div>

              <div className="summary-grid">
                <article className="metric-card score-card">
                  <span className="metric-label">DETERMINISTIC RISK SCORE</span>
                  {validScore ? (
                    <div className="score-value">
                      <strong>{score}</strong>
                      <span>/ 100</span>
                    </div>
                  ) : (
                    <div className="score-unavailable">Unavailable</div>
                  )}
                  <div className="score-track">
                    <span
                      style={{
                        width: `${validScore ? score : 0}%`,
                      }}
                    />
                  </div>
                  <StatusPill status={scoring.risk_level || "not_available"} />
                  <p className="metric-note">
                    Based on configured risk indicators detected by the backend.
                  </p>
                </article>

                <article className="metric-card">
                  <span className="metric-label">COMPANY REGISTRY</span>
                  <h3>{humanize(identity.status || "not_available")}</h3>
                  <p className="metric-note">
                    {Array.isArray(identityMatches)
                      ? `${identityMatches.length} matching record(s) returned`
                      : "Based on available registry lookup results."}
                  </p>
                  <StatusPill status={identity.status || "unknown"} />
                </article>

                <article className="metric-card">
                  <span className="metric-label">WEB PRESENCE</span>
                  <h3>{humanize(webPresence.status || "not_available")}</h3>
                  <p className="metric-note">
                    Search results must match the target company to count as
                    supporting evidence.
                  </p>
                  <StatusPill status={webPresence.status || "unknown"} />
                </article>

                <article className="metric-card">
                  <span className="metric-label">INVESTIGATION</span>
                  <h3>{humanize(investigation.status || "not_available")}</h3>
                  <p className="metric-note">
                    AI-generated findings are separate from the official score.
                  </p>
                  <StatusPill status={investigation.status || "unknown"} />
                </article>
              </div>

              <Section
                title="Detected warning signs"
                subtitle="Findings considered by the scoring engine, with their supplied severity and evidence."
              >
                {findings.length ? (
                  <div className="findings-list">
                    {findings.map((finding, index) => (
                      <article className="finding-item" key={`${finding.rule_id || finding.name || "finding"}-${index}`}>
                        <div className="finding-icon">!</div>
                        <div className="finding-body">
                          <div className="finding-title-row">
                            <h3>
                              {humanize(
                                finding.rule_id ||
                                  finding.name ||
                                  finding.title ||
                                  "Detected finding"
                              )}
                            </h3>
                            {finding.severity && (
                              <StatusPill status={finding.severity} />
                            )}
                          </div>
                          {firstValue(finding.description, finding.message) && (
                            <p>{firstValue(finding.description, finding.message)}</p>
                          )}
                          {finding.evidence && (
                            <blockquote>{finding.evidence}</blockquote>
                          )}
                          <div className="finding-meta">
                            {finding.points !== undefined &&
                              `${finding.points} risk points`}
                          </div>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state">
                    <span className="empty-check">✓</span>
                    <div>
                      <strong>No scored findings were returned</strong>
                      <p>
                        This does not guarantee that the company or offer is
                        legitimate. Review the remaining evidence carefully.
                      </p>
                    </div>
                  </div>
                )}
                {scoring.disclaimer && (
                  <p className="disclaimer">{scoring.disclaimer}</p>
                )}
              </Section>

              <Section
                title="Company registry evidence"
                subtitle="What the registry lookup returned."
              >
                <div className="detail-list">
                  <DetailRow label="Lookup status" value={identity.status} />
                  <DetailRow
                    label="Matching records"
                    value={Array.isArray(identityMatches) ? identityMatches.length : undefined}
                  />
                  <DetailRow
                    label="Partial failure"
                    value={identity.partial_failure === true ? "Yes" : identity.partial_failure === false ? "No" : undefined}
                  />
                  <DetailRow
                    label="Error"
                    value={identity.error}
                  />
                </div>
                {Array.isArray(identityMatches) && identityMatches.length > 0 && (
                  <div className="records-list">
                    {identityMatches.map((match, index) => (
                      <pre key={index}>{JSON.stringify(match, null, 2)}</pre>
                    ))}
                  </div>
                )}
                {identity.status === "not_found" && (
                  <p className="disclaimer">
                    No matching record was found in the sources checked. This
                    alone does not prove that the company does not exist or is
                    fraudulent.
                  </p>
                )}
              </Section>

              <Section
                title="Online presence evidence"
                subtitle="Review the returned sources and confirm that they refer to this exact company."
              >
                {Array.isArray(webResults) && webResults.length > 0 ? (
                  <div className="records-list">
                    {webResults.map((item, index) => (
                      <pre key={index}>{JSON.stringify(item, null, 2)}</pre>
                    ))}
                  </div>
                ) : (
                  <p className="muted-copy">
                    {webPresence.summary ||
                      "No structured web-result list was included in the response."}
                  </p>
                )}
              </Section>

              <Section
                title="AI investigation report"
                subtitle="The manager's narrative interpretation of the collected evidence."
              >               
                {report ? (
                <div className="investigation-report">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {String(report)}
                    </ReactMarkdown>                </div>
                ) : (
                <p className="muted-copy">
                    No investigation narrative was included in this response.
                    The deterministic verification results are shown above.
                </p>
                )}
                <p className="disclaimer">
                  AI-generated analysis may contain errors. Verify important
                  claims independently and never rely on the report alone before
                  making financial or employment decisions.
                </p>
              </Section>

              <div className="report-footer">
                <span>
                  Verification status:{" "}
                  <strong>{humanize(result.status || "completed")}</strong>
                </span>
                <button className="secondary-button" onClick={resetForm} type="button">
                  Verify another offer
                </button>
              </div>
            </div>
          )}
        </div>

        <footer className="site-footer">
          <span className="brand-mark small">J</span>
          <span>JobShield AI</span>
          <span className="footer-divider">·</span>
          <span>Verify carefully. Decide confidently.</span>
        </footer>
      </main>
    </div>
  );
}
