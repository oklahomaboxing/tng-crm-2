import html2canvas from "html2canvas";
import { useEffect, useMemo, useState } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  "https://sea-lion-app-2-gxyfr.ondigitalocean.app";

function revenueFetch(url, options = {}) {
  return fetch(url, { ...options, headers: { ...options.headers, Authorization: `Bearer ${localStorage.getItem("token")}` } });
}

function money(value) {
  const num = Number(value || 0);

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(num);
}

function ScoreBadge({ score }) {
  const value = Number(score || 0);

  let label = "Low";

  if (value >= 85) label = "Hot";
  else if (value >= 70) label = "Strong";
  else if (value >= 50) label = "Developing";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "5px 10px",
        borderRadius: 999,
        background: "#17171d",
        border: "1px solid #34343d",
        fontWeight: 700,
        fontSize: 12,
      }}
    >
      {value}/100 · {label}
    </span>
  );
}

function EmailStatusBadge({ status }) {
  const value = (status || "NOT_SENT").toUpperCase();

  const labels = {
    NOT_SENT: "Not Sent",
    DRAFT: "Draft",
    QUEUED: "Queued",
    SENT: "Sent",
    DELIVERED: "Delivered",
    OPENED: "Opened",
    CLICKED: "Clicked",
    REPLIED: "Replied",
    BOUNCED: "Bounced",
    FAILED: "Failed",
    COMPLAINED: "Complained",
    CANCELLED: "Cancelled",
  };

  return (
    <span
      style={{
        display: "inline-flex",
        padding: "5px 9px",
        borderRadius: 999,
        border: "1px solid #34343d",
        background:
          value === "OPENED" ||
          value === "CLICKED" ||
          value === "REPLIED"
            ? "#12251a"
            : value === "BOUNCED" ||
              value === "FAILED" ||
              value === "COMPLAINED"
            ? "#2a1114"
            : "#17171d",
        fontSize: 12,
        fontWeight: 800,
      }}
    >
      {labels[value] || value}
    </span>
  );
}

function MetricCard({ label, value, subtext }) {
  return (
    <div
      style={{
        background: "#111116",
        border: "1px solid #27272f",
        borderRadius: 16,
        padding: 18,
        minHeight: 110,
      }}
    >
      <div
        style={{
          color: "#9999a5",
          fontSize: 12,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: 0.6,
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize: 30,
          fontWeight: 900,
          marginTop: 8,
        }}
      >
        {value}
      </div>

      {subtext ? (
        <div
          style={{
            color: "#777783",
            fontSize: 12,
            marginTop: 6,
          }}
        >
          {subtext}
        </div>
      ) : null}


    </div>
  );
}

export default function EventRevenue({ eventId = 1, event = {} }) {
  const [tab, setTab] = useState("SPONSOR");

  const [dashboard, setDashboard] = useState({
    prospects: 0,
    high_intent_prospects: 0,
    pipeline_value: 0,
    committed: 0,
    collected: 0,
  });

  const [prospects, setProspects] = useState([]);
  const [packages, setPackages] = useState([]);

  const [scoutResults, setScoutResults] = useState([]);
  const [scoutLoading, setScoutLoading] = useState(false);
  const [addingSponsor, setAddingSponsor] = useState("");
  const [proposalLoadingId, setProposalLoadingId] = useState(null);
  const [emailSendingId, setEmailSendingId] = useState(null);
  const [customRecipientEmails, setCustomRecipientEmails] = useState({});
  const [contactFindingId, setContactFindingId] = useState(null);
  const [proposalDraft, setProposalDraft] = useState(null);
  const [proposalActionLoading, setProposalActionLoading] = useState(false);
  const [inventorySeeding, setInventorySeeding] = useState(false);
  const [packageEditor, setPackageEditor] = useState(null);
  const [packageSaving, setPackageSaving] = useState(false);
  const [mockupBuilder, setMockupBuilder] = useState(null);
  const [mockupLogoUrl, setMockupLogoUrl] = useState("");
  const [mockupLogoName, setMockupLogoName] = useState("");
  const [mockupScale, setMockupScale] = useState(42);
  const [mockupX, setMockupX] = useState(50);
  const [mockupY, setMockupY] = useState(50);
  const [mockupSavedAt, setMockupSavedAt] = useState("");
  const [mockupSurface, setMockupSurface] = useState("canvas");
  const [mockupPlacements, setMockupPlacements] = useState({});
  const [mockupLogos, setMockupLogos] = useState({});
  const [mockupRopeBranding, setMockupRopeBranding] = useState({
    type: "website",
    value: "",
  });
  const [scoutError, setScoutError] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchJson(path) {
    const response = await revenueFetch(`${API_BASE}${path}`);

    if (!response.ok) {
      const text = await response.text();

      throw new Error(
        `Request failed ${response.status}: ${text || response.statusText}`
      );
    }

    return response.json();
  }

  async function processDueFollowups() {
    try {
      await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/process-followups`,
        {
          method: "POST",
        }
      );
    } catch (err) {
      console.error(
        "Automatic sponsor follow-up check failed:",
        err
      );
    }
  }

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [dashboardData, prospectData, packageData] = await Promise.all([
        fetchJson(`/api/events/${eventId}/revenue/dashboard`),

        fetchJson(
          `/api/events/${eventId}/revenue/prospects?prospect_type=${tab}`
        ),

        fetchJson(
          `/api/events/${eventId}/revenue/packages?package_type=${tab}`
        ),
      ]);

      setDashboard(dashboardData || {});
      setProspects(Array.isArray(prospectData) ? prospectData : []);
      setPackages(Array.isArray(packageData) ? packageData : []);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unable to load revenue data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function refreshRevenue() {
      await processDueFollowups();
      await loadData();
    }

    refreshRevenue();
  }, [eventId, tab]);

  const tabPipeline = useMemo(() => {
    return prospects.reduce((total, prospect) => {
      return total + Number(prospect.recommended_ask || 0);
    }, 0);
  }, [prospects]);

  const highIntentCount = useMemo(() => {
    return prospects.filter(
      (prospect) => Number(prospect.fit_score || 0) >= 80
    ).length;
  }, [prospects]);

  const revenueAttention = useMemo(() => {
    const now = new Date();

    return prospects
      .map((prospect) => {
        const followUpDue =
          prospect.next_follow_up_at &&
          new Date(prospect.next_follow_up_at) <= now;

        if (prospect.proposal_status === "DRAFT") {
          return {
            ...prospect,
            attention_priority: 1,
            attention_label: "Proposal needs approval",
            attention_detail:
              "Review the proposal, package, and Clover payment link before sending.",
            attention_action: "REVIEW",
          };
        }

        if (prospect.proposal_status === "APPROVED") {
          return {
            ...prospect,
            attention_priority: 2,
            attention_label: "Approved - ready to send",
            attention_detail:
              "The proposal is approved and ready to email.",
            attention_action: "REVIEW",
          };
        }

        if (
          prospect.status === "PAYMENT_PENDING" ||
          prospect.status === "COMMITTED"
        ) {
          return {
            ...prospect,
            attention_priority: 3,
            attention_label: "Payment pending",
            attention_detail:
              "This deal is waiting for payment or payment confirmation.",
            attention_action: prospect.proposal_id
              ? "REVIEW"
              : "NONE",
          };
        }

        if (
          prospect.status === "REPLIED" ||
          prospect.status === "INTERESTED" ||
          prospect.email_status === "REPLIED"
        ) {
          return {
            ...prospect,
            attention_priority: 4,
            attention_label: "Reply needs attention",
            attention_detail:
              "This business has replied or shown interest. Move the deal forward.",
            attention_action: prospect.proposal_id
              ? "REVIEW"
              : "NONE",
          };
        }

        if (
          followUpDue &&
          !["PAID", "DECLINED", "NO_RESPONSE"].includes(
            prospect.status
          )
        ) {
          return {
            ...prospect,
            attention_priority: 5,
            attention_label: "Follow-up due",
            attention_detail:
              "The scheduled follow-up date has arrived.",
            attention_action: prospect.proposal_id
              ? "REVIEW"
              : "NONE",
          };
        }

        return null;
      })
      .filter(Boolean)
      .sort(
        (a, b) =>
          a.attention_priority - b.attention_priority
      );
  }, [prospects]);

  const needsApprovalCount = useMemo(() => {
    return prospects.filter(
      (prospect) => prospect.proposal_status === "DRAFT"
    ).length;
  }, [prospects]);

  const followupsDueCount = useMemo(() => {
    const now = new Date();

    return prospects.filter((prospect) => {
      if (!prospect.next_follow_up_at) return false;

      if (
        ["PAID", "DECLINED", "NO_RESPONSE"].includes(
          prospect.status
        )
      ) {
        return false;
      }

      return new Date(prospect.next_follow_up_at) <= now;
    }).length;
  }, [prospects]);

  const paymentPendingCount = useMemo(() => {
    return prospects.filter((prospect) =>
      ["PAYMENT_PENDING", "COMMITTED"].includes(
        prospect.status
      )
    ).length;
  }, [prospects]);
  function mockupDefaultsForAsset(assetName) {
    const name = String(assetName || "").toLowerCase();

    if (name.includes("side a")) return { x: 50, y: 18, scale: 30 };
    if (name.includes("side b")) return { x: 82, y: 48, scale: 24 };
    if (name.includes("side c")) return { x: 50, y: 83, scale: 30 };
    if (name.includes("side d")) return { x: 18, y: 48, scale: 24 };
    if (name.includes("corner post")) return { x: 18, y: 24, scale: 20 };
    if (name.includes("corner pad")) return { x: 82, y: 24, scale: 48 };
    if (name.includes("ring skirt")) return { x: 50, y: 82, scale: 34 };
    if (name.includes("rope")) return { x: 50, y: 26, scale: 26 };

    return { x: 50, y: 50, scale: 38 };
  }

  function mockupSurfaceOptions(assetName) {
    const name = String(assetName || "").toLowerCase();

    if (name.includes("full ring")) {
      return [
        { key: "canvas", label: "Center Canvas" },
        { key: "front_skirt", label: "Front Ring Skirt" },
        { key: "ropes", label: "Ropes" },
        { key: "corner_pad_1", label: "Corner Pad 1" },
        { key: "corner_pad_2", label: "Corner Pad 2" },
        { key: "corner_pad_3", label: "Corner Pad 3" },
        { key: "corner_pad_4", label: "Corner Pad 4" },
      ];
    }

    if (name.includes("corner pad")) {
      return [{ key: "corner_pad_2", label: "Corner Pad" }];
    }

    if (name.includes("corner post")) {
      return [{ key: "corner_pad_2", label: "Corner Post" }];
    }

    if (name.includes("rope")) {
      return [{ key: "ropes", label: "Ropes" }];
    }

    if (
      name.includes("skirt") ||
      name.includes("ring side")
    ) {
      return [{ key: "front_skirt", label: "Ring Skirt / Side" }];
    }

    return [{ key: "canvas", label: "Center Canvas" }];
  }

  function defaultMockupPlacement(surface) {
    if (String(surface).startsWith("corner_pad")) {
      return {
        x: 50,
        y: 50,
        width: 92,
        height: 84,
        rotation: 0,
        orientation: "horizontal",
        fit: "contain",
        lockAspect: true,
      };
    }

    if (surface === "ropes") {
      return {
        x: 50,
        y: 24,
        width: 58,
        height: 18,
        rotation: 0,
        orientation: "horizontal",
        fit: "contain",
        lockAspect: false,
      };
    }

    if (surface === "front_skirt") {
      return {
        x: 50,
        y: 50,
        width: 58,
        height: 70,
        rotation: 0,
        orientation: "horizontal",
        fit: "contain",
        lockAspect: false,
      };
    }

    return {
      x: 50,
      y: 50,
      width: 42,
      height: 28,
      rotation: 0,
      orientation: "horizontal",
      fit: "contain",
      lockAspect: true,
    };
  }

  function getMockupPlacement(surface) {
    return (
      mockupPlacements?.[surface] ||
      defaultMockupPlacement(surface)
    );
  }

  function updateMockupPlacement(field, value) {
    setMockupPlacements((old) => {
      const current =
        old?.[mockupSurface] ||
        defaultMockupPlacement(mockupSurface);

      const next = {
        ...current,
        [field]: value,
      };

      if (current.lockAspect && field === "width") {
        next.height = value;
      }

      if (current.lockAspect && field === "height") {
        next.width = value;
      }

      return {
        ...old,
        [mockupSurface]: next,
      };
    });

    setMockupSavedAt("");
  }

  function resetCurrentMockupSurface() {
    setMockupPlacements((old) => ({
      ...old,
      [mockupSurface]:
        defaultMockupPlacement(mockupSurface),
    }));

    setMockupSavedAt("");
  }

  function applyCurrentPlacementToAllCornerPads() {
    const current = {
      ...getMockupPlacement(mockupSurface),
    };

    setMockupPlacements((old) => ({
      ...old,
      corner_pad_1: { ...current },
      corner_pad_2: { ...current },
      corner_pad_3: { ...current },
      corner_pad_4: { ...current },
    }));

    setMockupSavedAt("");
  }

  function mockupPlacementRotation(surface) {
    const placement = getMockupPlacement(surface);

    return (
      Number(placement.rotation || 0) +
      (placement.orientation === "vertical" ? 90 : 0)
    );
  }
  function getMockupLogo(surface) {
    return (
      mockupLogos?.[surface] || {
        url: "",
        name: "",
      }
    );
  }

  function applyCurrentLogoToAllCornerPads() {
    const current = getMockupLogo(mockupSurface);

    if (!current?.url) {
      alert("Choose a logo for this corner pad first.");
      return;
    }

    setMockupLogos((old) => ({
      ...old,
      corner_pad_1: { ...current },
      corner_pad_2: { ...current },
      corner_pad_3: { ...current },
      corner_pad_4: { ...current },
    }));

    setMockupSavedAt("");
  }
  function mockupStorageKey(packageId) {
    return `tng-revenue-mockup-${eventId}-${packageId}`;
  }

  function openMockupBuilder(pkg) {
    const defaults = mockupDefaultsForAsset(pkg?.name);
    const storageKey = mockupStorageKey(pkg.id);

    let saved = null;

    try {
      const raw = localStorage.getItem(storageKey);

      if (raw) {
        saved = JSON.parse(raw);
      }
    } catch (err) {
      console.warn("Unable to read saved mockup", err);
    }

    setMockupLogoUrl(saved?.logo_data_url || "");
    setMockupLogoName(saved?.logo_name || "");
    setMockupScale(
      Number(saved?.scale ?? defaults.scale)
    );
    setMockupX(
      Number(saved?.x ?? defaults.x)
    );
    setMockupY(
      Number(saved?.y ?? defaults.y)
    );
    setMockupSavedAt(saved?.saved_at || "");

    const surfaceOptions = mockupSurfaceOptions(pkg?.name);
    const firstSurface =
      saved?.active_surface ||
      surfaceOptions[0]?.key ||
      "canvas";

    const nextPlacements = {};
    const nextLogos = {};

    surfaceOptions.forEach((surface) => {
      nextPlacements[surface.key] =
        saved?.placements?.[surface.key] ||
        defaultMockupPlacement(surface.key);

      nextLogos[surface.key] =
        saved?.logos?.[surface.key] ||
        (saved?.logo_data_url
          ? {
              url: saved.logo_data_url,
              name:
                saved.logo_name ||
                "Sponsor logo",
            }
          : {
              url: "",
              name: "",
            });
    });

    setMockupSurface(firstSurface);
    setMockupPlacements(nextPlacements);
    setMockupLogos(nextLogos);
    setMockupRopeBranding(
      saved?.rope_branding || {
        type: "website",
        value: "",
      }
    );

    setMockupBuilder({
      package_id: pkg.id,
      asset_name: pkg.name || "",
      price: Number(pkg.price || 0),
      sponsor_name: saved?.sponsor_name || "",
    });
  }

  function closeMockupBuilder() {
    setMockupLogoUrl("");
    setMockupLogoName("");
    setMockupSavedAt("");
    setMockupPlacements({});
    setMockupLogos({});
    setMockupRopeBranding({
      type: "website",
      value: "",
    });
    setMockupSurface("canvas");
    setMockupBuilder(null);
  }

  function resetMockupPlacement() {
    if (!mockupBuilder) return;

    const defaults = mockupDefaultsForAsset(
      mockupBuilder.asset_name
    );

    setMockupScale(defaults.scale);
    setMockupX(defaults.x);
    setMockupY(defaults.y);
  }

  function handleMockupLogoChange(event) {
    const file = event.target.files?.[0];

    if (!file) return;

    const allowed = [
      "image/jpeg",
      "image/png",
      "image/webp",
    ];

    if (!allowed.includes(file.type)) {
      alert("Please select a JPG, PNG, or WEBP image.");
      event.target.value = "";
      return;
    }

    if (file.size > 1500 * 1024) {
      alert(
        "For saved mockups, please use a logo smaller than 1.5 MB."
      );
      event.target.value = "";
      return;
    }

    const reader = new FileReader();

    reader.onload = () => {
      const nextUrl = String(reader.result || "");
      const nextName = file.name || "Sponsor logo";

      setMockupLogoUrl(nextUrl);
      setMockupLogoName(nextName);

      setMockupLogos((old) => ({
        ...old,
        [mockupSurface]: {
          url: nextUrl,
          name: nextName,
        },
      }));

      setMockupSavedAt("");
    };

    reader.onerror = () => {
      alert("Unable to read that image.");
    };

    reader.readAsDataURL(file);
    event.target.value = "";
  }

  async function saveMockup() {
    if (!mockupBuilder?.package_id) return;

    const preview = document.getElementById(
      "sponsorship-mockup-capture"
    );

    if (!preview) {
      alert("Mockup preview could not be captured.");
      return;
    }

    try {
      const canvas = await html2canvas(preview, {
        backgroundColor: "#101015",
        scale: 1.5,
        useCORS: true,
        logging: false,
      });

      const pngDataUrl = canvas.toDataURL("image/png");
      const savedAt = new Date().toISOString();

      const payload = {
        package_id: mockupBuilder.package_id,
        asset_name: mockupBuilder.asset_name,
        sponsor_name: mockupBuilder.sponsor_name || "",
        logo_data_url:
          getMockupLogo(mockupSurface).url ||
          mockupLogoUrl ||
          "",
        logo_name:
          getMockupLogo(mockupSurface).name ||
          mockupLogoName ||
          "",
        logos: mockupLogos,
        rope_branding: mockupRopeBranding,
        scale: Number(mockupScale),
        x: Number(mockupX),
        y: Number(mockupY),
        mockup_png_data_url: pngDataUrl,
        active_surface: mockupSurface,
        placements: mockupPlacements,
        saved_at: savedAt,
      };

      localStorage.setItem(
        mockupStorageKey(mockupBuilder.package_id),
        JSON.stringify(payload)
      );

      setMockupSavedAt(savedAt);

      alert(
        "Mockup saved and prepared for proposal email."
      );
    } catch (err) {
      console.error(err);

      alert(
        "Unable to capture the sponsorship mockup image."
      );
    }
  }
  function clearSavedMockup() {
    if (!mockupBuilder?.package_id) return;

    localStorage.removeItem(
      mockupStorageKey(mockupBuilder.package_id)
    );

    setMockupSavedAt("");
    alert("Saved mockup removed.");
  }
  function editPackage(pkg) {
    setPackageEditor({
      id: pkg.id,
      name: pkg.name || "",
      description: pkg.description || "",
      price: Number(pkg.price || 0),
      quantity_available:
        pkg.quantity_available == null
          ? ""
          : Number(pkg.quantity_available),
      clover_payment_url: pkg.clover_payment_url || "",
      active: pkg.active !== false,
    });
  }

  async function savePackageEdits() {
    if (!packageEditor?.id) return;

    setPackageSaving(true);
    setScoutError("");

    try {
      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/packages/${packageEditor.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: packageEditor.name,
            description: packageEditor.description || null,
            price: Number(packageEditor.price || 0),
            quantity_available:
              packageEditor.quantity_available === ""
                ? null
                : Number(packageEditor.quantity_available),
            clover_payment_url:
              packageEditor.clover_payment_url || null,
            active: Boolean(packageEditor.active),
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Unable to update sponsorship asset (${response.status})`
        );
      }

      setPackageEditor(null);
      await loadData();
      alert("Sponsorship asset updated.");
    } catch (err) {
      console.error(err);
      setScoutError(
        err.message || "Unable to update sponsorship asset."
      );
    } finally {
      setPackageSaving(false);
    }
  }
async function seedSponsorshipInventory() {
    setInventorySeeding(true);
    setScoutError("");

    try {
      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/packages/seed-sponsorship-inventory`,
        {
          method: "POST",
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Unable to add sponsorship inventory (${response.status})`
        );
      }

      await loadData();

      alert(
        body?.created
          ? `${body.created} sponsorship inventory items added.`
          : "Ring sponsorship inventory is already loaded."
      );
    } catch (err) {
      console.error(err);
      setScoutError(
        err.message || "Unable to add sponsorship inventory."
      );
    } finally {
      setInventorySeeding(false);
    }
  }
  async function addSponsorToPipeline(candidate) {
    const key = candidate.business_name || "";

    setAddingSponsor(key);
    setScoutError("");

    try {
      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/scout/sponsors/add-to-pipeline`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            business_name: candidate.business_name,
            website: candidate.website || null,
            city: candidate.city || null,
            state: candidate.state || null,
            industry: candidate.industry || null,

            why_good_fit:
              candidate.why_good_fit || null,

            marketing_evidence:
              candidate.marketing_evidence || [],

            sponsorship_evidence:
              candidate.sponsorship_evidence || [],

            source_urls:
              candidate.source_urls || [],

            marketing_activity_score:
              candidate.marketing_activity_score || 0,

            sponsorship_history_score:
              candidate.sponsorship_history_score || 0,

            audience_fit_score:
              candidate.audience_fit_score || 0,

            business_capacity_score:
              candidate.business_capacity_score || 0,

            distance_score:
              candidate.distance_score || 0,

            relationship_score:
              candidate.relationship_score || 20,

            distance_miles:
              candidate.distance_miles ?? null,

            marketing_propensity:
              candidate.marketing_propensity || "UNKNOWN",

            verified_sponsorship_history:
              candidate.verified_sponsorship_history ?? null,

            lead_source:
              candidate.lead_source || "OPENAI_WEB_SEARCH",
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Unable to add sponsor (${response.status})`
        );
      }

      const prospectId =
        body.prospect_id || body.id;

      if (prospectId) {
        try {
          const autoResponse = await revenueFetch(
            `${API_BASE}/api/events/${eventId}/revenue/prospects/${prospectId}/auto-outreach`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                event_name:
                  event?.name ||
                  event?.title ||
                  event?.event_name ||
                  "TNG Boxing Event",

                event_date:
                  event?.event_date || null,

                event_venue:
                  event?.venue || null,

                event_address:
                  event?.venue_address || null,

                send_if_ready: true,
              }),
            }
          );

          const autoBody = await autoResponse.json();

          if (!autoResponse.ok) {
            console.error(
              "Automatic outreach failed:",
              autoBody
            );
          } else {
            console.log(
              "Automatic outreach:",
              autoBody
            );
          }
        } catch (autoError) {
          console.error(
            "Automatic sponsor outreach error:",
            autoError
          );
        }
      }

      await loadData();

      setScoutResults((current) =>
        current.filter(
          (item) =>
            item.business_name !== candidate.business_name
        )
      );

      if (body.already_exists) {
        alert(
          `${candidate.business_name} is already in this event pipeline.`
        );
      }
    } catch (err) {
      console.error(err);

      setScoutError(
        err.message ||
        "Unable to add sponsor to pipeline."
      );
    } finally {
      setAddingSponsor("");
    }
  }

  async function findSponsorContact(prospect) {
    setContactFindingId(prospect.id);
    setScoutError("");

    try {
      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/prospects/${prospect.id}/find-contact`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prospect_id: prospect.id,
            business_name:
              prospect.business_name || "",
            website:
              prospect.website || null,
            city:
              prospect.city || null,
            state:
              prospect.state || null,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Contact research failed (${response.status})`
        );
      }

      await loadData();

      const contactName =
        [body.first_name, body.last_name]
          .filter(Boolean)
          .join(" ") || "Contact";

      if (body.email) {
        alert(
          `${contactName} found\n${body.job_title || ""}\n${body.email}`
        );
      } else {
        alert(
          `${contactName} found, but no verified public email was located.`
        );
      }
    } catch (err) {
      console.error(err);

      setScoutError(
        err.message ||
        "Unable to research sponsor contact."
      );
    } finally {
      setContactFindingId(null);
    }
  }

  async function sendSponsorEmail(prospect) {
    const businessName =
      prospect.business_name || "this sponsor";

    const recipientEmail = (
      customRecipientEmails[prospect.id] ||
      prospect.contact_email ||
      ""
    ).trim();

    if (!recipientEmail) {
      setScoutError("Enter an email address before sending.");
      return;
    }

    if (
      !window.confirm(
        `Send the latest saved proposal for ${businessName} to ${recipientEmail}?`
      )
    ) {
      return;
    }

    setEmailSendingId(prospect.id);
    setScoutError("");

    try {
      const proposalPackageId =
        prospect.proposal_package_id ||
        prospect.recommended_package_id ||
        null;

      let savedMockup = null;

      if (proposalPackageId) {
        try {
          const rawMockup = localStorage.getItem(
            mockupStorageKey(proposalPackageId)
          );

          if (rawMockup) {
            savedMockup = JSON.parse(rawMockup);
          }
        } catch (err) {
          console.warn(
            "Unable to read saved sponsorship mockup",
            err
          );
        }
      }

      const mockupImage =
        savedMockup?.mockup_png_data_url || "";

      const mockupBase64 = mockupImage.includes(",")
        ? mockupImage.split(",")[1]
        : mockupImage;

      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/prospects/${prospect.id}/send-latest-proposal?recipient_email=${encodeURIComponent(recipientEmail)}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            mockup_image_base64:
              mockupBase64 || null,
            mockup_asset_name:
              savedMockup?.asset_name || null,
            mockup_sponsor_name:
              savedMockup?.sponsor_name || null,
          }),
        }
      );
      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Email failed with status ${response.status}`
        );
      }

      await loadData();

      alert(
        `Proposal sent successfully to ${recipientEmail}.`
      );
    } catch (err) {
      console.error(err);

      setScoutError(
        err.message || "Unable to send proposal email."
      );
    } finally {
      setEmailSendingId(null);
    }
  }

  async function generateProposal(prospect) {
    setProposalLoadingId(prospect.id);
    setScoutError("");

    try {
      const eventName =
        event?.name ||
        event?.title ||
        event?.event_name ||
        `TNG Event ${eventId}`;

      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/proposals/generate-ai`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prospect_id: prospect.id,
            package_id: prospect.recommended_package_id || null,
            event_name: eventName,
            event_date: event?.event_date || null,
            event_venue: event?.venue || null,
            event_address: event?.venue_address || null,
            additional_instructions: null,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Proposal generation failed (${response.status})`
        );
      }

      setProposalDraft(body);
    } catch (err) {
      console.error(err);

      setScoutError(
        err.message || "Unable to generate proposal."
      );
    } finally {
      setProposalLoadingId(null);
    }
  }

  async function saveProposalDraft() {
    if (!proposalDraft?.proposal_id) return;

    setProposalActionLoading(true);
    setScoutError("");

    try {
      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/proposals/${proposalDraft.proposal_id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: proposalDraft.title,
            message: proposalDraft.message,
            clover_payment_url:
              proposalDraft.clover_payment_url || null,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Proposal update failed (${response.status})`
        );
      }

      setProposalDraft(body);
      await loadData();
      alert("Proposal draft saved.");
    } catch (err) {
      console.error(err);
      setScoutError(
        err.message || "Unable to save proposal."
      );
    } finally {
      setProposalActionLoading(false);
    }
  }

  async function approveProposalDraft() {
    if (!proposalDraft?.proposal_id) return;

    setProposalActionLoading(true);
    setScoutError("");

    try {
      const saveResponse = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/proposals/${proposalDraft.proposal_id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title: proposalDraft.title,
            message: proposalDraft.message,
            clover_payment_url:
              proposalDraft.clover_payment_url || null,
          }),
        }
      );

      const saveBody = await saveResponse.json();

      if (!saveResponse.ok) {
        throw new Error(
          saveBody?.detail ||
          `Proposal update failed (${saveResponse.status})`
        );
      }

      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/proposals/${proposalDraft.proposal_id}/approve`,
        {
          method: "POST",
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Proposal approval failed (${response.status})`
        );
      }

      setProposalDraft(body);
      await loadData();
      alert("Proposal approved and ready to send.");
    } catch (err) {
      console.error(err);
      setScoutError(
        err.message || "Unable to approve proposal."
      );
    } finally {
      setProposalActionLoading(false);
    }
  }

  function reviewProposal(prospect) {
    if (!prospect.proposal_id) return;

    setProposalDraft({
      proposal_id: prospect.proposal_id,
      prospect_id: prospect.id,
      title: prospect.proposal_title || "",
      message: prospect.proposal_message || "",
      clover_payment_url:
        prospect.proposal_clover_payment_url || "",
      status: prospect.proposal_status || "DRAFT",
    });
  }
  async function runSponsorScout() {
    if (tab !== "SPONSOR") {
      alert("Vendor Scout will be connected next.");
      return;
    }

    setScoutLoading(true);
    setScoutError("");
    setScoutResults([]);

    const eventName =
      event?.name ||
      event?.title ||
      event?.event_name ||
      `TNG Event ${eventId}`;

    const eventAddress =
      event?.venue_address ||
      event?.venue ||
      "Oklahoma City, OK";

    try {
      const response = await revenueFetch(
        `${API_BASE}/api/events/${eventId}/revenue/scout/sponsors`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            event_name: eventName,
            event_address: eventAddress,
            radius_miles: 10,
            max_results: 5,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
          `Sponsor Scout failed with status ${response.status}`
        );
      }

      setScoutResults(body.results || []);
    } catch (err) {
      console.error(err);
      setScoutError(
        err.message || "Unable to run Sponsor Scout."
      );
    } finally {
      setScoutLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100%",
        color: "#f5f5f7",
        padding: 24,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: 20,
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              fontSize: 12,
              color: "#e6202d",
              fontWeight: 900,
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            TNG Promotions
          </div>

          <h1
            style={{
              fontSize: 32,
              margin: "5px 0 6px",
              fontWeight: 900,
            }}
          >
            Event Revenue Engine
          </h1>

          <p
            style={{
              margin: 0,
              color: "#9999a5",
              maxWidth: 650,
            }}
          >
            Find, rank, contact, close, and collect revenue from sponsors and
            vendors for this event.
          </p>
        </div>

        <button
          type="button"
          onClick={runSponsorScout}
          disabled={scoutLoading}
          style={{
            border: 0,
            background: "#e6202d",
            color: "white",
            borderRadius: 10,
            padding: "12px 18px",
            fontWeight: 900,
            cursor: "pointer",
          }}
        >
          {scoutLoading
            ? "Searching..."
            : tab === "SPONSOR"
            ? "Find Sponsors"
            : "Find Vendors"}
        </button>
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          marginTop: 26,
          marginBottom: 18,
        }}
      >
        {[
          ["SPONSOR", "Sponsors"],
          ["VENDOR", "Vendors"],
        ].map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setTab(value)}
            style={{
              border:
                tab === value
                  ? "1px solid #e6202d"
                  : "1px solid #2a2a32",
              background: tab === value ? "#241014" : "#111116",
              color: "white",
              borderRadius: 10,
              padding: "10px 16px",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {error ? (
        <div
          style={{
            background: "#2a1114",
            border: "1px solid #6f2028",
            color: "#ffb4ba",
            padding: 14,
            borderRadius: 12,
            marginBottom: 18,
          }}
        >
          {error}
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
        }}
      >
        <MetricCard
          label="Pipeline Value"
          value={money(tabPipeline)}
          subtext={`${prospects.length} ${
            tab === "SPONSOR" ? "sponsor" : "vendor"
          } prospects`}
        />

        <MetricCard
          label="Needs Approval"
          value={needsApprovalCount}
          subtext="Proposal drafts to review"
        />

        <MetricCard
          label="Follow-Ups Due"
          value={followupsDueCount}
          subtext="Needs contact now"
        />

        <MetricCard
          label="Payment Pending"
          value={paymentPendingCount}
          subtext="Deals waiting to close"
        />

        <MetricCard
          label="Collected"
          value={money(dashboard.collected)}
          subtext="Paid event revenue"
        />
      </div>
      {scoutError ? (
        <div
          style={{
            marginTop: 20,
            padding: 14,
            borderRadius: 12,
            background: "#2a1114",
            border: "1px solid #6f2028",
            color: "#ffb4ba",
          }}
        >
          {scoutError}
        </div>
      ) : null}

      {scoutResults.length > 0 ? (
        <div
          style={{
            marginTop: 24,
            background: "#0f0f14",
            border: "1px solid #27272f",
            borderRadius: 16,
            padding: 20,
          }}
        >
          <div style={{ marginBottom: 16 }}>
            <h2 style={{ margin: 0, fontSize: 20 }}>
              Sponsor Scout Results
            </h2>

            <div
              style={{
                color: "#81818d",
                fontSize: 13,
                marginTop: 5,
              }}
            >
              AI-researched businesses ranked for this event.
              These have not been added to your pipeline yet.
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gap: 12,
            }}
          >
            {scoutResults.map((candidate, index) => (
              <div
                key={`${candidate.business_name}-${index}`}
                style={{
                  border: "1px solid #292931",
                  borderRadius: 12,
                  padding: 16,
                  background: "#141419",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 14,
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: 18,
                        fontWeight: 900,
                      }}
                    >
                      {candidate.business_name}
                    </div>

                    <div
                      style={{
                        color: "#92929d",
                        fontSize: 13,
                        marginTop: 4,
                      }}
                    >
                      {candidate.industry || "Business"}
                      {candidate.city
                        ? ` · ${candidate.city}${
                            candidate.state
                              ? `, ${candidate.state}`
                              : ""
                          }`
                        : ""}
                    </div>
                  </div>

                  <ScoreBadge
                    score={candidate.discovery_score}
                  />
                </div>

                {candidate.why_good_fit ? (
                  <div
                    style={{
                      color: "#d0d0d6",
                      marginTop: 12,
                      lineHeight: 1.5,
                      fontSize: 14,
                    }}
                  >
                    {candidate.why_good_fit}
                  </div>
                ) : null}

                {candidate.marketing_evidence?.length > 0 ? (
                  <div
                    style={{
                      marginTop: 12,
                      color: "#aaaab4",
                      fontSize: 13,
                    }}
                  >
                    <strong>Marketing evidence:</strong>{" "}
                    {candidate.marketing_evidence.join(" • ")}
                  </div>
                ) : null}

                {candidate.sponsorship_evidence?.length > 0 ? (
                  <div
                    style={{
                      marginTop: 8,
                      color: "#aaaab4",
                      fontSize: 13,
                    }}
                  >
                    <strong>Sponsorship evidence:</strong>{" "}
                    {candidate.sponsorship_evidence.join(" • ")}
                  </div>
                ) : null}

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    marginTop: 14,
                    flexWrap: "wrap",
                  }}
                >
                  {candidate.website ? (
                    <button
                      type="button"
                      style={smallButtonStyle}
                      onClick={() =>
                        window.open(
                          candidate.website,
                          "_blank",
                          "noopener,noreferrer"
                        )
                      }
                    >
                      Website
                    </button>
                  ) : null}

                  <button
                    type="button"
                    style={{
                      ...smallButtonStyle,
                      background: "#e6202d",
                      borderColor: "#e6202d",
                    }}
                    disabled={
                      addingSponsor === candidate.business_name
                    }
                    onClick={() =>
                      addSponsorToPipeline(candidate)
                    }
                  >
                    {addingSponsor === candidate.business_name
                      ? "Adding..."
                      : "Add to Pipeline"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div
        style={{
          marginTop: 26,
          background: "#0f0f14",
          border: "1px solid #27272f",
          borderRadius: 16,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "18px 20px",
            borderBottom: "1px solid #27272f",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          {/* SPONSORSHIP INVENTORY PANEL */}
      {tab === "SPONSOR" ? (
        <div
          style={{
            marginTop: 24,
            background: "#0f0f14",
            border: "1px solid #27272f",
            borderRadius: 16,
            padding: 20,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 12,
                  color: "#e6202d",
                  fontWeight: 900,
                  textTransform: "uppercase",
                  letterSpacing: 0.8,
                }}
              >
                Sellable Ring Assets
              </div>

              <h2
                style={{
                  margin: "5px 0 0",
                  fontSize: 21,
                }}
              >
                Sponsorship Inventory
              </h2>

              <div
                style={{
                  marginTop: 6,
                  color: "#858590",
                  fontSize: 13,
                  maxWidth: 650,
                }}
              >
                Sell individual ring branding positions or combine them
                into larger sponsorship packages.
              </div>
            </div>

            <button
              type="button"
              disabled={inventorySeeding}
              onClick={seedSponsorshipInventory}
              style={{
                border: 0,
                background: "#e6202d",
                color: "#fff",
                borderRadius: 9,
                padding: "10px 14px",
                fontWeight: 900,
                cursor: inventorySeeding ? "default" : "pointer",
                opacity: inventorySeeding ? 0.65 : 1,
              }}
            >
              {inventorySeeding
                ? "Adding..."
                : packages.length > 0
                ? "Add Missing Ring Inventory"
                : "Add Ring Inventory"}
            </button>
          </div>

          {packages.length === 0 ? (
            <div
              style={{
                marginTop: 18,
                border: "1px dashed #33333c",
                borderRadius: 12,
                padding: 24,
                textAlign: "center",
                color: "#858590",
              }}
            >
              No sponsor inventory is loaded yet. Add the standard ring
              inventory to begin selling branding positions.
            </div>
          ) : (
            <div
              style={{
                marginTop: 18,
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(230px, 1fr))",
                gap: 12,
              }}
            >
              {packages.map((pkg) => {
                const available =
                  pkg.quantity_available == null
                    ? null
                    : Math.max(
                        Number(pkg.quantity_available || 0) -
                          Number(pkg.quantity_sold || 0),
                        0
                      );

                return (
                  <div
                    key={`inventory-${pkg.id}`}
                    style={{
                      background: "#15151b",
                      border: "1px solid #2b2b34",
                      borderRadius: 12,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        minHeight: 105,
                        padding: 15,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        textAlign: "center",
                        background:
                          pkg.name === "Full Ring Package"
                            ? "linear-gradient(135deg, #3a0d12, #15151b)"
                            : pkg.name === "Center Canvas"
                            ? "linear-gradient(135deg, #292932, #111116)"
                            : "#18181f",
                        borderBottom: "1px solid #2b2b34",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            color: "#e6202d",
                            fontSize: 10,
                            fontWeight: 900,
                            textTransform: "uppercase",
                            letterSpacing: 0.8,
                          }}
                        >
                          Ring Sponsorship
                        </div>

                        <div
                          style={{
                            marginTop: 7,
                            fontWeight: 900,
                            fontSize: 18,
                          }}
                        >
                          {pkg.name}
                        </div>
                      </div>
                    </div>

                    <div style={{ padding: 15 }}>
                      <div
                        style={{
                          fontSize: 22,
                          fontWeight: 900,
                        }}
                      >
                        {money(pkg.price)}
                      </div>

                      <div
                        style={{
                          marginTop: 7,
                          color: "#9999a5",
                          fontSize: 12,
                          lineHeight: 1.45,
                          minHeight: 54,
                        }}
                      >
                        {pkg.description ||
                          "Sponsor branding opportunity."}
                      </div>

                      <div
                        style={{
                          marginTop: 13,
                          paddingTop: 11,
                          borderTop: "1px solid #292931",
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 10,
                          color: "#858590",
                          fontSize: 12,
                        }}
                      >
                        <span>
                          Sold: {Number(pkg.quantity_sold || 0)}
                        </span>

                        <span>
                          {available == null
                            ? "Open inventory"
                            : `${available} available`}
                        </span>
                      </div>

                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          marginTop: 13,
                          flexWrap: "wrap",
                        }}
                      >
                        <button
                          type="button"
                          style={smallButtonStyle}
                          onClick={() => editPackage(pkg)}
                        >
                          Edit Asset
                        </button>
                        <button
                          type="button"
                          style={{
                            ...smallButtonStyle,
                            background: "#241014",
                            borderColor: "#6f2028",
                          }}
                          onClick={() => openMockupBuilder(pkg)}
                        >
                          Create Mockup
                        </button>

                        {pkg.clover_payment_url ? (
                          <a
                            href={pkg.clover_payment_url}
                            target="_blank"
                            rel="noreferrer"
                            style={{
                              ...smallButtonStyle,
                              display: "inline-block",
                              textDecoration: "none",
                            }}
                          >
                            Test Clover Link
                          </a>
                        ) : (
                          <span
                            style={{
                              color: "#f2cc60",
                              fontSize: 11,
                              fontWeight: 800,
                              alignSelf: "center",
                            }}
                          >
                            No Clover link
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}
      <div>
            <h2
              style={{
                margin: 0,
                fontSize: 20,
              }}
            >
              {tab === "SPONSOR"
                ? "Sponsor Pipeline"
                : "Vendor Pipeline"}
            </h2>

            <div
              style={{
                color: "#81818d",
                fontSize: 13,
                marginTop: 4,
              }}
            >
              Highest-fit prospects appear first.
            </div>
          </div>

          <div
            style={{
              color: "#9999a5",
              fontSize: 13,
            }}
          >
            Packages: {packages.length}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 28 }}>Loading revenue data...</div>
        ) : prospects.length === 0 ? (
          <div
            style={{
              padding: 36,
              textAlign: "center",
              color: "#8f8f99",
            }}
          >
            <div
              style={{
                fontSize: 18,
                fontWeight: 800,
                color: "#eeeeef",
                marginBottom: 8,
              }}
            >
              No {tab === "SPONSOR" ? "sponsors" : "vendors"} yet
            </div>

            <div>
              Use{" "}
              <strong>
                {tab === "SPONSOR" ? "Find Sponsors" : "Find Vendors"}
              </strong>{" "}
              or add a lead manually.
            </div>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                minWidth: 900,
              }}
            >
              <thead>
                <tr
                  style={{
                    background: "#15151b",
                    color: "#9696a2",
                    fontSize: 12,
                    textTransform: "uppercase",
                  }}
                >
                  <th style={thStyle}>Business</th>
                  <th style={thStyle}>Contact</th>
                  <th style={thStyle}>Title</th>
                  <th style={thStyle}>Email</th>
                  <th style={thStyle}>Fit</th>
                  <th style={thStyle}>Industry</th>
                  <th style={thStyle}>Distance</th>
                  <th style={thStyle}>Suggested Ask</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Email Status</th>
                  <th style={thStyle}>Actions</th>
                </tr>
              </thead>

              <tbody>
                {prospects.map((prospect) => (
                  <tr
                    key={prospect.id}
                    style={{
                      borderTop: "1px solid #24242b",
                    }}
                  >
                    <td style={tdStyle}>
                      <div
                        style={{
                          fontWeight: 900,
                          color: "#ffffff",
                        }}
                      >
                        {prospect.business_name || "Unnamed Business"}
                      </div>

                      <div
                        style={{
                          color: "#777783",
                          fontSize: 12,
                          marginTop: 3,
                        }}
                      >
                        {prospect.city || ""}
                        {prospect.city && prospect.state ? ", " : ""}
                        {prospect.state || ""}
                      </div>
                    </td>

                    <td style={tdStyle}>
                      <div
                        style={{
                          fontWeight: 800,
                          color: "#ffffff",
                        }}
                      >
                        {prospect.contact_name || "No contact"}
                      </div>

                      {prospect.contact_verified ? (
                        <div
                          style={{
                            color: "#8fca9a",
                            fontSize: 11,
                            marginTop: 3,
                          }}
                        >
                          Verified public contact
                        </div>
                      ) : null}
                    </td>

                    <td style={tdStyle}>
                      {prospect.contact_title || "--"}
                    </td>

                    <td style={tdStyle}>
                      {prospect.contact_email ? (
                        <div>
                          <div
                            style={{
                              fontSize: 12,
                              color: "#ffffff",
                            }}
                          >
                            {prospect.contact_email}
                          </div>

                          {prospect.contact_phone ? (
                            <div
                              style={{
                                color: "#777783",
                                fontSize: 11,
                                marginTop: 3,
                              }}
                            >
                              {prospect.contact_phone}
                            </div>
                          ) : null}
                        </div>
                      ) : (
                        <span
                          style={{
                            color: "#777783",
                            fontSize: 12,
                          }}
                        >
                          Not found
                        </span>
                      )}
                    </td>

                    <td style={tdStyle}>
                      <ScoreBadge score={prospect.fit_score} />
                    </td>

                    <td style={tdStyle}>
                      {prospect.industry || "—"}
                    </td>

                    <td style={tdStyle}>
                      {prospect.distance_miles !== null &&
                      prospect.distance_miles !== undefined
                        ? `${prospect.distance_miles} mi`
                        : "—"}
                    </td>

                    <td style={tdStyle}>
                      <strong>
                        {prospect.recommended_ask
                          ? money(prospect.recommended_ask)
                          : "—"}
                      </strong>
                    </td>

                    <td style={tdStyle}>
                      {prospect.status || "NEW"}
                    </td>

                    <td style={tdStyle}>
                      <EmailStatusBadge
                        status={prospect.email_status}
                      />

                      {prospect.email_opened_at ? (
                        <div
                          style={{
                            color: "#777783",
                            fontSize: 11,
                            marginTop: 5,
                          }}
                        >
                          Open tracked
                        </div>
                      ) : null}
                    </td>

                    <td style={tdStyle}>
                      <div
                        style={{
                          display: "flex",
                          gap: 6,
                          flexWrap: "wrap",
                        }}
                      >
                        <button
                          type="button"
                          style={smallButtonStyle}
                          disabled={
                            contactFindingId === prospect.id
                          }
                          onClick={() =>
                            findSponsorContact(prospect)
                          }
                        >
                          {contactFindingId === prospect.id
                            ? "Finding..."
                            : prospect.contact_email
                            ? "Refresh Contact"
                            : "Find Contact"}
                        </button>

                        <button
                          type="button"
                          style={smallButtonStyle}
                          disabled={
                            proposalLoadingId === prospect.id
                          }
                          onClick={() =>
                            generateProposal(prospect)
                          }
                        >
                          {proposalLoadingId === prospect.id
                            ? "Generating..."
                            : "Proposal"}
                        </button>

                        {prospect.proposal_id ? (
                          <button
                            type="button"
                            style={smallButtonStyle}
                            onClick={() =>
                              reviewProposal(prospect)
                            }
                          >
                            {prospect.proposal_status === "APPROVED"
                              ? "Approved Proposal"
                              : prospect.proposal_status === "SENT"
                              ? "View Sent Proposal"
                              : "Review Proposal"}
                          </button>
                        ) : null}
                        <input
                          type="email"
                          placeholder="Send to email"
                          value={customRecipientEmails[prospect.id] || ""}
                          onChange={(e) =>
                            setCustomRecipientEmails((old) => ({
                              ...old,
                              [prospect.id]: e.target.value,
                            }))
                          }
                          style={{
                            minWidth: 220,
                            padding: "8px 10px",
                            borderRadius: 8,
                            border: "1px solid #3a3a44",
                            background: "#101014",
                            color: "#fff",
                          }}
                        />

                        <button
                          type="button"
                          style={smallButtonStyle}
                          disabled={
                            emailSendingId === prospect.id ||
                            prospect.proposal_status !== "APPROVED" ||
                            (!(
                              customRecipientEmails[prospect.id] || ""
                            ).trim() && !prospect.contact_email)
                          }
                          onClick={() =>
                            sendSponsorEmail(prospect)
                          }
                        >
                          {emailSendingId === prospect.id
                            ? "Sending..."
                            : prospect.proposal_status !== "APPROVED"
                            ? "Approve First"
                            : ((customRecipientEmails[prospect.id] || "").trim() || prospect.contact_email)
                            ? "Email Proposal"
                            : "Enter Email"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {mockupBuilder ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.82)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
            zIndex: 11000,
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 980,
              maxHeight: "94vh",
              overflowY: "auto",
              background: "#111116",
              border: "1px solid #33333c",
              borderRadius: 16,
              padding: 24,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 16,
                flexWrap: "wrap",
              }}
            >
              <div>
                <div
                  style={{
                    color: "#e6202d",
                    fontSize: 12,
                    fontWeight: 900,
                    textTransform: "uppercase",
                  }}
                >
                  Sponsorship Preview
                </div>

                <h2 style={{ margin: "6px 0 0" }}>
                  Sponsor Ring Mockup
                </h2>

                <div
                  style={{
                    marginTop: 5,
                    color: "#858590",
                    fontSize: 13,
                  }}
                >
                  Build a 3D sales preview and save it for this event and asset.
                </div>
              </div>

              <button
                type="button"
                style={smallButtonStyle}
                onClick={closeMockupBuilder}
              >
                Close
              </button>
            </div>

            <div
              style={{
                marginTop: 22,
                display: "grid",
                gridTemplateColumns:
                  "minmax(260px, 0.8fr) minmax(420px, 1.5fr)",
                gap: 22,
              }}
            >
              <div>
                <div style={{ marginBottom: 16 }}>
                  <div
                    style={{
                      fontSize: 11,
                      color: "#9999a5",
                      fontWeight: 900,
                      marginBottom: 6,
                    }}
                  >
                    RING ASSET
                  </div>

                  <select
                    value={mockupBuilder.package_id}
                    onChange={(e) => {
                      const id = Number(e.target.value);
                      const pkg = packages.find(
                        (item) => Number(item.id) === id
                      );

                      if (!pkg) return;

                      const defaults =
                        mockupDefaultsForAsset(pkg.name);

                      setMockupBuilder((old) => ({
                        ...old,
                        package_id: pkg.id,
                        asset_name: pkg.name || "",
                        price: Number(pkg.price || 0),
                      }));

                      setMockupScale(defaults.scale);
                      setMockupX(defaults.x);
                      setMockupY(defaults.y);
                    }}
                    style={{
                      width: "100%",
                      boxSizing: "border-box",
                      padding: 11,
                      borderRadius: 9,
                      border: "1px solid #33333c",
                      background: "#0d0d12",
                      color: "#fff",
                    }}
                  >
                    {packages.map((pkg) => (
                      <option key={pkg.id} value={pkg.id}>
                        {pkg.name} - {money(pkg.price)}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ marginBottom: 16 }}>
                  <div
                    style={{
                      fontSize: 11,
                      color: "#9999a5",
                      fontWeight: 900,
                      marginBottom: 6,
                    }}
                  >
                    SPONSOR / BUSINESS NAME
                  </div>

                  <input
                    type="text"
                    placeholder="Example: Delta Dental"
                    value={mockupBuilder.sponsor_name}
                    onChange={(e) =>
                      setMockupBuilder((old) => ({
                        ...old,
                        sponsor_name: e.target.value,
                      }))
                    }
                    style={{
                      width: "100%",
                      boxSizing: "border-box",
                      padding: 11,
                      borderRadius: 9,
                      border: "1px solid #33333c",
                      background: "#0d0d12",
                      color: "#fff",
                    }}
                  />
                </div>

                {mockupSurface === "ropes" ? (
                  <div
                    style={{
                      marginBottom: 18,
                      padding: 12,
                      border: "1px solid #32323b",
                      borderRadius: 10,
                      background: "#101015",
                    }}
                  >
                    <div
                      style={{
                        fontSize: 11,
                        color: "#9999a5",
                        fontWeight: 900,
                        marginBottom: 10,
                      }}
                    >
                      ROPE BRANDING
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 8,
                        marginBottom: 10,
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => {
                          setMockupRopeBranding((old) => ({
                            ...old,
                            type: "website",
                          }));
                          setMockupSavedAt("");
                        }}
                        style={{
                          ...smallButtonStyle,
                          background:
                            mockupRopeBranding.type === "website"
                              ? "#e6202d"
                              : smallButtonStyle.background,
                        }}
                      >
                        Website
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setMockupRopeBranding((old) => ({
                            ...old,
                            type: "phone",
                          }));
                          setMockupSavedAt("");
                        }}
                        style={{
                          ...smallButtonStyle,
                          background:
                            mockupRopeBranding.type === "phone"
                              ? "#e6202d"
                              : smallButtonStyle.background,
                        }}
                      >
                        Telephone
                      </button>
                    </div>

                    <div
                      style={{
                        color: "#858590",
                        fontSize: 10,
                        fontWeight: 900,
                        marginBottom: 6,
                      }}
                    >
                      {mockupRopeBranding.type === "phone"
                        ? "TELEPHONE NUMBER"
                        : "WEBSITE ADDRESS"}
                    </div>

                    <input
                      type={
                        mockupRopeBranding.type === "phone"
                          ? "tel"
                          : "text"
                      }
                      value={mockupRopeBranding.value}
                      onChange={(e) => {
                        setMockupRopeBranding((old) => ({
                          ...old,
                          value: e.target.value,
                        }));
                        setMockupSavedAt("");
                      }}
                      placeholder={
                        mockupRopeBranding.type === "phone"
                          ? "(405) 555-1234"
                          : "www.company.com"
                      }
                      style={{
                        width: "100%",
                        boxSizing: "border-box",
                        padding: "10px 11px",
                        background: "#0d0d12",
                        color: "#fff",
                        border: "1px solid #34343d",
                        borderRadius: 8,
                        fontSize: 13,
                        fontWeight: 800,
                      }}
                    />

                    <div
                      style={{
                        marginTop: 8,
                        color: "#71717c",
                        fontSize: 10,
                        lineHeight: 1.4,
                      }}
                    >
                      Ring ropes support website addresses or telephone
                      numbers only.
                    </div>
                  </div>
                ) : (
                  <div style={{ marginBottom: 18 }}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#9999a5",
                        fontWeight: 900,
                        marginBottom: 7,
                      }}
                    >
                      LOGO FOR{" "}
                      {mockupSurfaceOptions(
                        mockupBuilder.asset_name
                      ).find(
                        (surface) =>
                          surface.key === mockupSurface
                      )?.label || "SELECTED LOCATION"}
                    </div>

                    <label
                      style={{
                        display: "inline-block",
                        background: "#18181f",
                        border: "1px solid #3a3a44",
                        borderRadius: 8,
                        padding: "9px 12px",
                        fontSize: 12,
                        fontWeight: 900,
                        cursor: "pointer",
                      }}
                    >
                      Choose Logo
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        onChange={handleMockupLogoChange}
                        style={{ display: "none" }}
                      />
                    </label>

                    {getMockupLogo(mockupSurface).name ? (
                      <div
                        style={{
                          marginTop: 8,
                          color: "#858590",
                          fontSize: 11,
                          wordBreak: "break-all",
                        }}
                      >
                        {getMockupLogo(mockupSurface).name}
                      </div>
                    ) : null}

                    {getMockupLogo(mockupSurface).url ? (
                      <div
                        style={{
                          marginTop: 12,
                          padding: 10,
                          border: "1px solid #32323b",
                          borderRadius: 10,
                          background: "#101015",
                        }}
                      >
                        <div
                          style={{
                            fontSize: 10,
                            fontWeight: 900,
                            color: "#858590",
                            marginBottom: 8,
                            textTransform: "uppercase",
                            letterSpacing: 0.7,
                          }}
                        >
                          Uploaded Logo Preview
                        </div>

                        <img
                          src={getMockupLogo(mockupSurface).url}
                          alt="Uploaded sponsor logo"
                          style={{
                            display: "block",
                            width: "100%",
                            maxWidth: 220,
                            maxHeight: 100,
                            objectFit: "contain",
                            background: "#ffffff",
                            padding: 8,
                            borderRadius: 6,
                          }}
                        />
                      </div>
                    ) : null}
                  </div>
                )}
                <div style={{ marginBottom: 16 }}>
                  <div
                    style={{
                      color: "#9999a5",
                      fontSize: 11,
                      fontWeight: 900,
                      marginBottom: 7,
                    }}
                  >
                    LOCATION
                  </div>

                  <select
                    value={mockupSurface}
                    onChange={(e) =>
                      setMockupSurface(e.target.value)
                    }
                    style={{
                      width: "100%",
                      background: "#101015",
                      color: "#fff",
                      border: "1px solid #34343d",
                      borderRadius: 8,
                      padding: "10px 11px",
                      fontWeight: 800,
                    }}
                  >
                    {mockupSurfaceOptions(
                      mockupBuilder.asset_name
                    ).map((surface) => (
                      <option
                        key={surface.key}
                        value={surface.key}
                      >
                        {surface.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div
                  style={{
                    marginBottom: 16,
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 8,
                  }}
                >
                  <button
                    type="button"
                    onClick={() =>
                      updateMockupPlacement(
                        "orientation",
                        "horizontal"
                      )
                    }
                    style={{
                      ...smallButtonStyle,
                      background:
                        getMockupPlacement(mockupSurface)
                          .orientation === "horizontal"
                          ? "#e6202d"
                          : smallButtonStyle.background,
                    }}
                  >
                    Horizontal
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      updateMockupPlacement(
                        "orientation",
                        "vertical"
                      )
                    }
                    style={{
                      ...smallButtonStyle,
                      background:
                        getMockupPlacement(mockupSurface)
                          .orientation === "vertical"
                          ? "#e6202d"
                          : smallButtonStyle.background,
                    }}
                  >
                    Vertical
                  </button>
                </div>

                <div style={{ marginBottom: 15 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      color: "#9999a5",
                      fontSize: 11,
                      fontWeight: 900,
                    }}
                  >
                    <span>WIDTH</span>
                    <span>
                      {getMockupPlacement(mockupSurface).width}%
                    </span>
                  </div>

                  <input
                    type="range"
                    min="10"
                    max="100"
                    value={
                      getMockupPlacement(mockupSurface).width
                    }
                    onChange={(e) =>
                      updateMockupPlacement(
                        "width",
                        Number(e.target.value)
                      )
                    }
                    style={{ width: "100%" }}
                  />
                </div>

                <div style={{ marginBottom: 15 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      color: "#9999a5",
                      fontSize: 11,
                      fontWeight: 900,
                    }}
                  >
                    <span>HEIGHT</span>
                    <span>
                      {getMockupPlacement(mockupSurface).height}%
                    </span>
                  </div>

                  <input
                    type="range"
                    min="10"
                    max="100"
                    value={
                      getMockupPlacement(mockupSurface).height
                    }
                    onChange={(e) =>
                      updateMockupPlacement(
                        "height",
                        Number(e.target.value)
                      )
                    }
                    style={{ width: "100%" }}
                  />
                </div>

                <div style={{ marginBottom: 15 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      color: "#9999a5",
                      fontSize: 11,
                      fontWeight: 900,
                    }}
                  >
                    <span>LEFT / RIGHT</span>
                    <span>
                      {getMockupPlacement(mockupSurface).x}%
                    </span>
                  </div>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={getMockupPlacement(mockupSurface).x}
                    onChange={(e) =>
                      updateMockupPlacement(
                        "x",
                        Number(e.target.value)
                      )
                    }
                    style={{ width: "100%" }}
                  />
                </div>

                <div style={{ marginBottom: 15 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      color: "#9999a5",
                      fontSize: 11,
                      fontWeight: 900,
                    }}
                  >
                    <span>UP / DOWN</span>
                    <span>
                      {getMockupPlacement(mockupSurface).y}%
                    </span>
                  </div>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={getMockupPlacement(mockupSurface).y}
                    onChange={(e) =>
                      updateMockupPlacement(
                        "y",
                        Number(e.target.value)
                      )
                    }
                    style={{ width: "100%" }}
                  />
                </div>

                <div style={{ marginBottom: 15 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      color: "#9999a5",
                      fontSize: 11,
                      fontWeight: 900,
                    }}
                  >
                    <span>ROTATION</span>
                    <span>
                      {getMockupPlacement(mockupSurface).rotation}°
                    </span>
                  </div>

                  <input
                    type="range"
                    min="-180"
                    max="180"
                    value={
                      getMockupPlacement(mockupSurface).rotation
                    }
                    onChange={(e) =>
                      updateMockupPlacement(
                        "rotation",
                        Number(e.target.value)
                      )
                    }
                    style={{ width: "100%" }}
                  />
                </div>

                <div style={{ marginBottom: 15 }}>
                  <div
                    style={{
                      color: "#9999a5",
                      fontSize: 11,
                      fontWeight: 900,
                      marginBottom: 7,
                    }}
                  >
                    LOGO FIT
                  </div>

                  <select
                    value={getMockupPlacement(mockupSurface).fit}
                    onChange={(e) =>
                      updateMockupPlacement(
                        "fit",
                        e.target.value
                      )
                    }
                    style={{
                      width: "100%",
                      background: "#101015",
                      color: "#fff",
                      border: "1px solid #34343d",
                      borderRadius: 8,
                      padding: "10px 11px",
                    }}
                  >
                    <option value="contain">
                      Contain - keep full logo
                    </option>
                    <option value="cover">
                      Cover - fill area
                    </option>
                    <option value="fill">
                      Stretch
                    </option>
                  </select>
                </div>

                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 15,
                    color: "#b5b5bf",
                    fontSize: 12,
                    fontWeight: 800,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={
                      !!getMockupPlacement(mockupSurface)
                        .lockAspect
                    }
                    onChange={(e) =>
                      updateMockupPlacement(
                        "lockAspect",
                        e.target.checked
                      )
                    }
                  />
                  Lock width / height proportions
                </label>

                <div
                  style={{
                    display: "flex",
                    gap: 8,
                    flexWrap: "wrap",
                    marginBottom: 12,
                  }}
                >
                  <button
                    type="button"
                    style={smallButtonStyle}
                    onClick={resetCurrentMockupSurface}
                  >
                    Reset This Location
                  </button>

                  {String(mockupBuilder.asset_name || "")
                    .toLowerCase()
                    .includes("full ring") &&
                  String(mockupSurface).startsWith(
                    "corner_pad"
                  ) ? (
                    <>
                      <button
                        type="button"
                        style={smallButtonStyle}
                        onClick={
                          applyCurrentPlacementToAllCornerPads
                        }
                      >
                        Apply Placement to All 4 Pads
                      </button>

                      <button
                        type="button"
                        style={smallButtonStyle}
                        onClick={
                          applyCurrentLogoToAllCornerPads
                        }
                      >
                        Apply Logo to All 4 Pads
                      </button>
                    </>
                  ) : null}
                </div>
                <div
                  style={{
                    marginTop: 10,
                    display: "flex",
                    gap: 8,
                    flexWrap: "wrap",
                  }}
                >
                  <button
                    type="button"
                    onClick={saveMockup}
                    style={{
                      border: 0,
                      background: "#e6202d",
                      color: "#fff",
                      borderRadius: 8,
                      padding: "9px 13px",
                      fontSize: 12,
                      fontWeight: 900,
                      cursor: "pointer",
                    }}
                  >
                    Save Mockup
                  </button>

                  {mockupSavedAt ? (
                    <button
                      type="button"
                      style={smallButtonStyle}
                      onClick={clearSavedMockup}
                    >
                      Remove Saved Mockup
                    </button>
                  ) : null}
                </div>

                {mockupSavedAt ? (
                  <div
                    style={{
                      marginTop: 8,
                      color: "#7ee787",
                      fontSize: 11,
                      fontWeight: 800,
                    }}
                  >
                    Saved for this asset
                  </div>
                ) : null}

                <div
                  style={{
                    marginTop: 18,
                    padding: 12,
                    borderRadius: 10,
                    background: "#18181f",
                    border: "1px solid #292931",
                  }}
                >
                  <div
                    style={{
                      color: "#858590",
                      fontSize: 11,
                      fontWeight: 900,
                    }}
                  >
                    SELECTED INVENTORY
                  </div>

                  <div
                    style={{
                      marginTop: 5,
                      fontWeight: 900,
                    }}
                  >
                    {mockupBuilder.asset_name}
                  </div>

                  <div
                    style={{
                      marginTop: 3,
                      color: "#7ee787",
                      fontWeight: 900,
                    }}
                  >
                    {money(mockupBuilder.price)}
                  </div>
                </div>
              </div>

              <div>
                <div
                  style={{
                    fontSize: 11,
                    color: "#9999a5",
                    fontWeight: 900,
                    marginBottom: 8,
                  }}
                >
                  LIVE RING PREVIEW
                </div>

                <div
                  id="sponsorship-mockup-capture"
                  style={{
                    position: "relative",
                    width: "100%",
                    aspectRatio: "4 / 3",
                    minHeight: 430,
                    overflow: "hidden",
                    borderRadius: 14,
                    background:
                      "radial-gradient(circle at 50% 30%, #2b2b34 0%, #101015 58%, #07070a 100%)",
                    border: "1px solid #3a3a44",
                    perspective: 1000,
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: "50%",
                      bottom: "5%",
                      width: "78%",
                      height: "68%",
                      transform:
                        "translateX(-50%) rotateX(58deg) rotateZ(-28deg)",
                      transformStyle: "preserve-3d",
                    }}
                  >
                    {/* Canvas floor */}
                    <div
                      style={{
                        position: "absolute",
                        inset: "7%",
                        background:
                          "linear-gradient(135deg, #f2f2ed, #c5c5be)",
                        border:
                          String(mockupBuilder.asset_name || "")
                            .toLowerCase()
                            .includes("canvas") ||
                          String(mockupBuilder.asset_name || "")
                            .toLowerCase()
                            .includes("full ring")
                            ? "8px solid #e6202d"
                            : "6px solid #55555e",
                        boxShadow:
                          "0 28px 50px rgba(0,0,0,0.55)",
                        overflow: "hidden",
                      }}
                    >
                      {String(mockupBuilder.asset_name || "")
                        .toLowerCase()
                        .includes("canvas") ||
                      String(mockupBuilder.asset_name || "")
                        .toLowerCase()
                        .includes("full ring") ? (
                        <div
                          style={{
                            position: "absolute",
                            left: `${
                              getMockupPlacement("canvas").x
                            }%`,
                            top: `${
                              getMockupPlacement("canvas").y
                            }%`,
                            width: `${
                              getMockupPlacement("canvas").width
                            }%`,
                            height: `${
                              getMockupPlacement("canvas").height
                            }%`,
                            transform: `translate(-50%, -50%) rotate(${mockupPlacementRotation(
                              "canvas"
                            )}deg)`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            overflow: "hidden",
                          }}
                        >
                          {getMockupLogo("canvas").url ? (
                            <img
                              src={getMockupLogo("canvas").url}
                              alt="Sponsor canvas logo"
                              style={{
                                display: "block",
                                width: "100%",
                                height: "100%",
                                objectFit:
                                  getMockupPlacement("canvas").fit,
                              }}
                            />
                          ) : (
                            <div
                              style={{
                                color: "#111",
                                fontWeight: 900,
                                textAlign: "center",
                                fontSize: 14,
                              }}
                            >
                              {mockupBuilder.sponsor_name ||
                                "SPONSOR LOGO"}
                            </div>
                          )}
                        </div>
                      ) : null}
                    </div>

                    {/* Front skirt surface */}
                    <div
                      style={{
                        position: "absolute",
                        left: "10%",
                        right: "10%",
                        bottom: "-7%",
                        height: "19%",
                        background:
                          String(mockupBuilder.asset_name || "")
                            .toLowerCase()
                            .includes("skirt") ||
                          String(mockupBuilder.asset_name || "")
                            .toLowerCase()
                            .includes("ring side") ||
                          String(mockupBuilder.asset_name || "")
                            .toLowerCase()
                            .includes("full ring")
                            ? "linear-gradient(#7d151e,#30080d)"
                            : "linear-gradient(#292930,#101014)",
                        border: "2px solid #4b4b55",
                        transform:
                          "rotateX(-90deg) translateZ(1px)",
                        transformOrigin: "top",
                        overflow: "hidden",
                      }}
                    >
                      {String(mockupBuilder.asset_name || "")
                        .toLowerCase()
                        .includes("skirt") ||
                      String(mockupBuilder.asset_name || "")
                        .toLowerCase()
                        .includes("ring side") ||
                      String(mockupBuilder.asset_name || "")
                        .toLowerCase()
                        .includes("full ring") ? (
                        <div
                          style={{
                            position: "absolute",
                            left: `${
                              getMockupPlacement("front_skirt").x
                            }%`,
                            top: `${
                              getMockupPlacement("front_skirt").y
                            }%`,
                            width: `${
                              getMockupPlacement("front_skirt")
                                .width
                            }%`,
                            height: `${
                              getMockupPlacement("front_skirt")
                                .height
                            }%`,
                            transform: `translate(-50%, -50%) rotate(${mockupPlacementRotation(
                              "front_skirt"
                            )}deg)`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            overflow: "hidden",
                          }}
                        >
                          {getMockupLogo("front_skirt").url ? (
                            <img
                              src={getMockupLogo("front_skirt").url}
                              alt="Sponsor skirt logo"
                              style={{
                                display: "block",
                                width: "100%",
                                height: "100%",
                                objectFit:
                                  getMockupPlacement(
                                    "front_skirt"
                                  ).fit,
                              }}
                            />
                          ) : (
                            <div
                              style={{
                                color: "#fff",
                                fontWeight: 900,
                                textAlign: "center",
                              }}
                            >
                              {mockupBuilder.sponsor_name ||
                                "SPONSOR"}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div
                          style={{
                            height: "100%",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "#777783",
                            fontWeight: 900,
                            fontSize: 11,
                          }}
                        >
                          TNG BOXING
                        </div>
                      )}
                    </div>

                    {/* Four ropes */}
                    {[0, 1, 2, 3].map((rope) => (
                      <div
                        key={`rope-front-${rope}`}
                        style={{
                          position: "absolute",
                          left: "7%",
                          right: "7%",
                          top: `${12 + rope * 6}%`,
                          height: 4,
                          background:
                            String(mockupBuilder.asset_name || "")
                              .toLowerCase()
                              .includes("rope") ||
                            String(mockupBuilder.asset_name || "")
                              .toLowerCase()
                              .includes("full ring")
                              ? "#ffd43b"
                              : rope < 2
                              ? "#e6202d"
                              : "#23232a",
                          transform: "translateZ(70px)",
                          boxShadow:
                            "0 2px 4px rgba(0,0,0,0.45)",
                        }}
                      />
                    ))}

                    {String(mockupBuilder.asset_name || "")
                      .toLowerCase()
                      .includes("rope") ||
                    String(mockupBuilder.asset_name || "")
                      .toLowerCase()
                      .includes("full ring") ? (
                      <div
                        style={{
                          position: "absolute",
                          left: `${
                            getMockupPlacement("ropes").x
                          }%`,
                          top: `${
                            getMockupPlacement("ropes").y
                          }%`,
                          width: `${
                            getMockupPlacement("ropes").width
                          }%`,
                          height: `${
                            getMockupPlacement("ropes").height
                          }%`,
                          transform: `translate(-50%, -50%) translateZ(82px) rotate(${mockupPlacementRotation(
                            "ropes"
                          )}deg)`,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          background: "rgba(255,255,255,0.94)",
                          border: "2px solid #ffd43b",
                          borderRadius: 5,
                          overflow: "hidden",
                          boxShadow:
                            "0 5px 12px rgba(0,0,0,0.45)",
                          zIndex: 10,
                        }}
                      >
                        <span
                          style={{
                            color: "#111",
                            fontSize: 11,
                            fontWeight: 900,
                            textAlign: "center",
                            whiteSpace: "nowrap",
                            width: "100%",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            padding: "0 6px",
                            boxSizing: "border-box",
                            letterSpacing: 0.3,
                          }}
                        >
                          {mockupRopeBranding.value ||
                            (mockupRopeBranding.type === "phone"
                              ? "(405) 555-1234"
                              : "www.company.com")}
                        </span>
                      </div>
                    ) : null}

                    {/* Corner posts / pads */}
                    {[
                      { left: "7%", top: "7%", label: "A" },
                      { left: "93%", top: "7%", label: "B" },
                      { left: "7%", top: "93%", label: "C" },
                      { left: "93%", top: "93%", label: "D" },
                    ].map((post, index) => {
                      const assetName = String(
                        mockupBuilder.asset_name || ""
                      ).toLowerCase();

                      const isCornerPost =
                        assetName.includes("corner post");

                      const isCornerPad =
                        assetName.includes("corner pad");

                      const isFullRing =
                        assetName.includes("full ring");

                      const postSelected =
                        isCornerPost ||
                        isCornerPad ||
                        isFullRing;

                      const showLogo =
                        isFullRing ||
                        ((isCornerPad || isCornerPost) &&
                          index === 1);

                      const useLargePad =
                        isCornerPad || isFullRing;

                      const surfaceKey =
                        `corner_pad_${index + 1}`;

                      const placement =
                        getMockupPlacement(surfaceKey);

                      return (
                        <div
                          key={`three-d-post-${index}`}
                          style={{
                            position: "absolute",
                            left: post.left,
                            top: post.top,
                            width: useLargePad ? 52 : 22,
                            height: useLargePad ? 122 : 100,
                            transform:
                              "translate(-50%, -72%) rotateX(-58deg)",
                            transformOrigin: "bottom",
                            background: postSelected
                              ? "linear-gradient(90deg,#7e151e,#e6202d,#7e151e)"
                              : "linear-gradient(90deg,#17171d,#494951,#17171d)",
                            border: postSelected
                              ? "2px solid #ff6069"
                              : "2px solid #65656f",
                            borderRadius: useLargePad ? 8 : 5,
                            boxShadow:
                              "8px 10px 15px rgba(0,0,0,0.45)",
                            overflow: "hidden",
                            zIndex: 12,
                          }}
                        >
                          {showLogo ? (
                            <div
                              style={{
                                position: "absolute",
                                left: `${placement.x}%`,
                                top: `${placement.y}%`,
                                width: `${placement.width}%`,
                                height: `${placement.height}%`,
                                transform: `translate(-50%, -50%) rotate(${mockupPlacementRotation(
                                  surfaceKey
                                )}deg)`,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                overflow: "hidden",
                              }}
                            >
                              {getMockupLogo(surfaceKey).url ? (
                                <img
                                  src={getMockupLogo(surfaceKey).url}
                                  alt={`Sponsor corner ${post.label} logo`}
                                  style={{
                                    display: "block",
                                    width: "100%",
                                    height: "100%",
                                    objectFit: placement.fit,
                                  }}
                                />
                              ) : (
                                <span
                                  style={{
                                    color: "#fff",
                                    fontSize: 8,
                                    fontWeight: 900,
                                    textAlign: "center",
                                    lineHeight: 1.05,
                                  }}
                                >
                                  {mockupBuilder.sponsor_name ||
                                    "SPONSOR"}
                                </span>
                              )}
                            </div>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                  {/* Asset indicator */}
                  <div
                    style={{
                      position: "absolute",
                      left: 12,
                      top: 12,
                      padding: "7px 10px",
                      background: "rgba(0,0,0,0.72)",
                      border: "1px solid #40404a",
                      borderRadius: 7,
                      color: "#fff",
                      fontSize: 11,
                      fontWeight: 900,
                    }}
                  >
                    3D VIEW · {mockupBuilder.asset_name}
                  </div>

                  <div
                    style={{
                      position: "absolute",
                      right: 12,
                      bottom: 12,
                      padding: "7px 10px",
                      background: "rgba(0,0,0,0.72)",
                      borderRadius: 7,
                      color: "#aaaab4",
                      fontSize: 10,
                    }}
                  >
                    Highlighted surface = selected inventory
                  </div>
                </div>
                <div
                  style={{
                    marginTop: 10,
                    color: "#858590",
                    fontSize: 11,
                    lineHeight: 1.5,
                  }}
                >
                  This is a conceptual sales mockup, not a production print
                  proof. Final logo dimensions and placement can be confirmed
                  after the sponsorship is sold.
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
      {packageEditor ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.78)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
            zIndex: 10000,
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 680,
              maxHeight: "90vh",
              overflowY: "auto",
              background: "#111116",
              border: "1px solid #33333c",
              borderRadius: 16,
              padding: 24,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 16,
              }}
            >
              <div>
                <div
                  style={{
                    color: "#e6202d",
                    fontSize: 12,
                    fontWeight: 900,
                    textTransform: "uppercase",
                  }}
                >
                  Sponsorship Inventory
                </div>

                <h2 style={{ margin: "6px 0 0" }}>
                  Edit Sponsorship Asset
                </h2>
              </div>

              <button
                type="button"
                style={smallButtonStyle}
                disabled={packageSaving}
                onClick={() => setPackageEditor(null)}
              >
                Close
              </button>
            </div>

            <div style={{ marginTop: 22 }}>
              <div style={{ fontSize: 11, color: "#9999a5", fontWeight: 900, marginBottom: 6 }}>
                ASSET NAME
              </div>

              <input
                type="text"
                value={packageEditor.name}
                onChange={(e) =>
                  setPackageEditor((old) => ({
                    ...old,
                    name: e.target.value,
                  }))
                }
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: 12,
                  borderRadius: 9,
                  border: "1px solid #33333c",
                  background: "#0d0d12",
                  color: "#fff",
                }}
              />
            </div>

            <div
              style={{
                marginTop: 18,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 14,
              }}
            >
              <div>
                <div style={{ fontSize: 11, color: "#9999a5", fontWeight: 900, marginBottom: 6 }}>
                  PRICE
                </div>

                <input
                  type="number"
                  min="0"
                  step="1"
                  value={packageEditor.price}
                  onChange={(e) =>
                    setPackageEditor((old) => ({
                      ...old,
                      price: e.target.value,
                    }))
                  }
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: 12,
                    borderRadius: 9,
                    border: "1px solid #33333c",
                    background: "#0d0d12",
                    color: "#fff",
                  }}
                />
              </div>

              <div>
                <div style={{ fontSize: 11, color: "#9999a5", fontWeight: 900, marginBottom: 6 }}>
                  QUANTITY AVAILABLE
                </div>

                <input
                  type="number"
                  min="0"
                  step="1"
                  value={packageEditor.quantity_available}
                  onChange={(e) =>
                    setPackageEditor((old) => ({
                      ...old,
                      quantity_available: e.target.value,
                    }))
                  }
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: 12,
                    borderRadius: 9,
                    border: "1px solid #33333c",
                    background: "#0d0d12",
                    color: "#fff",
                  }}
                />
              </div>
            </div>

            <div style={{ marginTop: 18 }}>
              <div style={{ fontSize: 11, color: "#9999a5", fontWeight: 900, marginBottom: 6 }}>
                DESCRIPTION
              </div>

              <textarea
                rows={6}
                value={packageEditor.description}
                onChange={(e) =>
                  setPackageEditor((old) => ({
                    ...old,
                    description: e.target.value,
                  }))
                }
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: 12,
                  borderRadius: 9,
                  border: "1px solid #33333c",
                  background: "#0d0d12",
                  color: "#fff",
                  resize: "vertical",
                  lineHeight: 1.5,
                }}
              />
            </div>

            <div style={{ marginTop: 18 }}>
              <div style={{ fontSize: 11, color: "#9999a5", fontWeight: 900, marginBottom: 6 }}>
                CLOVER PAYMENT LINK
              </div>

              <input
                type="url"
                placeholder="https://..."
                value={packageEditor.clover_payment_url}
                onChange={(e) =>
                  setPackageEditor((old) => ({
                    ...old,
                    clover_payment_url: e.target.value,
                  }))
                }
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: 12,
                  borderRadius: 9,
                  border: "1px solid #33333c",
                  background: "#0d0d12",
                  color: "#fff",
                }}
              />

              {packageEditor.clover_payment_url ? (
                <a
                  href={packageEditor.clover_payment_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: "inline-block",
                    marginTop: 10,
                    color: "#fff",
                    textDecoration: "none",
                    border: "1px solid #3a3a44",
                    borderRadius: 8,
                    padding: "8px 10px",
                    fontSize: 12,
                    fontWeight: 900,
                  }}
                >
                  Test Clover Payment Link
                </a>
              ) : null}
            </div>

            <label
              style={{
                marginTop: 20,
                display: "flex",
                alignItems: "center",
                gap: 10,
                cursor: "pointer",
                fontWeight: 800,
              }}
            >
              <input
                type="checkbox"
                checked={packageEditor.active}
                onChange={(e) =>
                  setPackageEditor((old) => ({
                    ...old,
                    active: e.target.checked,
                  }))
                }
              />

              Active Sponsorship Asset
            </label>

            <div
              style={{
                marginTop: 24,
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
              }}
            >
              <button
                type="button"
                disabled={packageSaving}
                onClick={savePackageEdits}
                style={{
                  border: 0,
                  background: "#e6202d",
                  color: "#fff",
                  borderRadius: 9,
                  padding: "10px 16px",
                  fontWeight: 900,
                  cursor: packageSaving ? "default" : "pointer",
                  opacity: packageSaving ? 0.65 : 1,
                }}
              >
                {packageSaving ? "Saving..." : "Save Changes"}
              </button>

              <button
                type="button"
                style={smallButtonStyle}
                disabled={packageSaving}
                onClick={() => setPackageEditor(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}
      {proposalDraft ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 20,
            zIndex: 9999,
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 760,
              maxHeight: "90vh",
              overflowY: "auto",
              background: "#111116",
              border: "1px solid #33333c",
              borderRadius: 16,
              padding: 24,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 16,
                alignItems: "flex-start",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: 12,
                    color: "#e6202d",
                    fontWeight: 900,
                    textTransform: "uppercase",
                  }}
                >
                  AI Proposal Draft
                </div>

                <h2
                  style={{
                    margin: "6px 0 0",
                  }}
                >
                  {proposalDraft.title}
                </h2>
              </div>

              <button
                type="button"
                style={smallButtonStyle}
                onClick={() => setProposalDraft(null)}
              >
                Close
              </button>
            </div>

            <div
              style={{
                marginTop: 18,
                padding: 14,
                borderRadius: 10,
                background: "#18181f",
                border: "1px solid #33333c",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "#9999a5",
                  fontWeight: 900,
                  marginBottom: 6,
                  textTransform: "uppercase",
                }}
              >
                Proposal Status
              </div>

              <div
                style={{
                  fontWeight: 900,
                  color:
                    proposalDraft.status === "APPROVED"
                      ? "#7ee787"
                      : proposalDraft.status === "SENT"
                      ? "#79c0ff"
                      : "#f2cc60",
                }}
              >
                {proposalDraft.status || "DRAFT"}
              </div>
            </div>

            <div style={{ marginTop: 20 }}>
              <div
                style={{
                  fontSize: 11,
                  color: "#9999a5",
                  fontWeight: 900,
                  marginBottom: 6,
                  textTransform: "uppercase",
                }}
              >
                Proposal Title
              </div>

              <input
                type="text"
                value={proposalDraft.title || ""}
                disabled={proposalDraft.status === "SENT"}
                onChange={(e) =>
                  setProposalDraft((old) => ({
                    ...old,
                    title: e.target.value,
                    status:
                      old.status === "APPROVED"
                        ? "DRAFT"
                        : old.status,
                  }))
                }
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: 12,
                  borderRadius: 9,
                  border: "1px solid #33333c",
                  background: "#0d0d12",
                  color: "#fff",
                }}
              />
            </div>

            <div style={{ marginTop: 18 }}>
              <div
                style={{
                  fontSize: 11,
                  color: "#9999a5",
                  fontWeight: 900,
                  marginBottom: 6,
                  textTransform: "uppercase",
                }}
              >
                Proposal Message
              </div>

              <textarea
                rows={14}
                value={proposalDraft.message || ""}
                disabled={proposalDraft.status === "SENT"}
                onChange={(e) =>
                  setProposalDraft((old) => ({
                    ...old,
                    message: e.target.value,
                    status:
                      old.status === "APPROVED"
                        ? "DRAFT"
                        : old.status,
                  }))
                }
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: 12,
                  borderRadius: 9,
                  border: "1px solid #33333c",
                  background: "#0d0d12",
                  color: "#fff",
                  lineHeight: 1.5,
                  resize: "vertical",
                }}
              />
            </div>

            <div style={{ marginTop: 18 }}>
              <div
                style={{
                  fontSize: 11,
                  color: "#9999a5",
                  fontWeight: 900,
                  marginBottom: 6,
                  textTransform: "uppercase",
                }}
              >
                Clover Payment Link
              </div>

              <input
                type="url"
                value={proposalDraft.clover_payment_url || ""}
                disabled={proposalDraft.status === "SENT"}
                placeholder="https://..."
                onChange={(e) =>
                  setProposalDraft((old) => ({
                    ...old,
                    clover_payment_url: e.target.value,
                    status:
                      old.status === "APPROVED"
                        ? "DRAFT"
                        : old.status,
                  }))
                }
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  padding: 12,
                  borderRadius: 9,
                  border: "1px solid #33333c",
                  background: "#0d0d12",
                  color: "#fff",
                }}
              />

              {proposalDraft.clover_payment_url ? (
                <a
                  href={proposalDraft.clover_payment_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: "inline-block",
                    marginTop: 10,
                    background: "#18181f",
                    border: "1px solid #33333c",
                    color: "#fff",
                    padding: "9px 12px",
                    borderRadius: 8,
                    textDecoration: "none",
                    fontWeight: 900,
                  }}
                >
                  Test Clover Payment Link
                </a>
              ) : null}
            </div>

            {proposalDraft.status !== "SENT" ? (
              <div
                style={{
                  marginTop: 22,
                  display: "flex",
                  gap: 10,
                  flexWrap: "wrap",
                }}
              >
                <button
                  type="button"
                  style={smallButtonStyle}
                  disabled={proposalActionLoading}
                  onClick={saveProposalDraft}
                >
                  {proposalActionLoading
                    ? "Working..."
                    : "Save Draft"}
                </button>

                <button
                  type="button"
                  disabled={proposalActionLoading}
                  onClick={approveProposalDraft}
                  style={{
                    border: 0,
                    background: "#e6202d",
                    color: "white",
                    borderRadius: 8,
                    padding: "9px 14px",
                    fontWeight: 900,
                    cursor: "pointer",
                  }}
                >
                  {proposalActionLoading
                    ? "Working..."
                    : "Approve Proposal"}
                </button>
              </div>
            ) : null}

            <div
              style={{
                marginTop: 18,
                color: "#858590",
                fontSize: 12,
              }}
            >
              {proposalDraft.status === "APPROVED"
                ? "Approved. This proposal is ready to email."
                : proposalDraft.status === "SENT"
                ? "This proposal has already been emailed."
                : "Review, edit, and approve this proposal before sending."}
            </div>
          </div>
        </div>
      ) : null}

    </div>
  );
}

const thStyle = {
  textAlign: "left",
  padding: "12px 16px",
  fontWeight: 800,
};

const tdStyle = {
  padding: "15px 16px",
  verticalAlign: "middle",
};

const smallButtonStyle = {
  background: "#18181f",
  border: "1px solid #33333c",
  color: "#f1f1f3",
  borderRadius: 8,
  padding: "7px 10px",
  fontSize: 12,
  fontWeight: 800,
  cursor: "pointer",
};

