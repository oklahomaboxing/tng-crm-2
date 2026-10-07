import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  InputAdornment,
  Typography,
} from "@mui/material";

import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import BloodtypeRoundedIcon from "@mui/icons-material/BloodtypeRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import { buildOfficialContractHtml } from "../utils/officialContract";
import EventRevenue from "./EventRevenue";
import TicketingDashboard from "./TicketingDashboard.jsx";
import EventCommandCenter from "./EventCommandCenter.jsx";
import EventFightCardBuilder from "./EventFightCardBuilder.jsx";
import EventHomeNavigation from "./EventHomeNavigation.jsx";
import EventFightCardPage from "./EventFightCardPage.jsx";
import EventContractsPage from "./EventContractsPage.jsx";
import EventMedicalsPage from "./EventMedicalsPage.jsx";
import EventExpensesPage from "./EventExpensesPage.jsx";
import EventCompliancePage from "./EventCompliancePage.jsx";

const API =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

const REQUEST_A_TEST_URL =
  "https://requestatest.com/combative";

const statusLabels = {
  not_started: "Not Started",
  in_progress: "In Progress",
  submitted: "Submitted",
  complete: "Complete",
  needs_attention: "Needs Attention",
};

function statusColor(status) {
  if (status === "complete") return "success";
  if (status === "needs_attention") return "error";
  if (status === "submitted") return "info";
  if (status === "in_progress") return "warning";
  return "default";
}

const eventPageTitles = {
  0: "Event Home",
  1: "Fight Card",
  2: "Contracts",
  3: "Compliance",
  4: "Matchmaker Checklist",
  5: "Medicals",
  6: "Expenses",
  7: "Sponsors & Vendors",
  8: "Event Settings",
  9: "Tickets",
  10: "Matchmaking",
};

function fighterLocation(fighter) {
  return [
    fighter?.city,
    fighter?.state,
    fighter?.country,
  ]
    .filter(Boolean)
    .join(", ");
}

export default function EventWorkspace({
  eventId,
  onBack,
}) {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState(0);
  const [cancelBoutOpen, setCancelBoutOpen] = useState(false);
  const [cancelBout, setCancelBout] = useState(null);
  const [cancelBoutNotes, setCancelBoutNotes] = useState("");
  const [cancelBoutWorking, setCancelBoutWorking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [contractWeights, setContractWeights] = useState({});
  const [contractCommissions, setContractCommissions] =
    useState({});
  const [contractTravel, setContractTravel] = useState({});
  const [expandedBouts, setExpandedBouts] = useState({});
  const [contractTermsSaving, setContractTermsSaving] =
    useState({});
  const [promoImage, setPromoImage] = useState("");
  const [promoLoading, setPromoLoading] = useState(false);
  const [venueName, setVenueName] = useState("");
  const [venueAddress, setVenueAddress] = useState("");
  const [venueSaving, setVenueSaving] = useState(false);


  async function load() {
    setLoading(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/workspace`,
        {
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not load event workspace"
        );
      }

      setData(body);
    } catch (error) {
      setMessage(
        error.message ||
          "Could not load event workspace"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [eventId]);

  useEffect(() => {
    if (data?.event) {
      setVenueName(data.event.venue || "");
      setVenueAddress(data.event.venue_address || "");
    }
  }, [data?.event?.id, data?.event?.venue, data?.event?.venue_address]);

  async function saveVenue() {
    try {
      setVenueSaving(true);
      setMessage("");

      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/venue`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            venue: venueName,
            venue_address: venueAddress,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update venue"
        );
      }

      await load();

      const updated = body.contracts_updated || 0;
      const preserved =
        body.signed_contracts_preserved || 0;

      setMessage(
        `Venue updated. ${updated} contract${
          updated === 1 ? "" : "s"
        } synchronized.${
          preserved
            ? ` ${preserved} electronically signed contract${
                preserved === 1 ? "" : "s"
              } preserved.`
            : ""
        }`
      );
    } catch (error) {
      setMessage(
        error.message || "Could not update venue"
      );
    } finally {
      setVenueSaving(false);
    }
  }

  async function updateBloodwork(fighter, changes) {
    try {
      const response = await fetch(
        `${API}/api/boxing/fighters/${fighter.id}/bloodwork`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(changes),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update bloodwork"
        );
      }

      setData((old) => ({
        ...old,
        fighters: old.fighters.map((row) =>
          row.id === fighter.id
            ? { ...row, ...body }
            : row
        ),
      }));

      setMessage(`${fighter.legal_name} bloodwork updated.`);
    } catch (error) {
      setMessage(
        error.message || "Could not update bloodwork"
      );
    }
  }

  async function updateFee(fee, changes) {
    try {
      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/fees/${fee.id}`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(changes),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update fee"
        );
      }

      setData((old) => ({
        ...old,
        fees: old.fees.map((row) =>
          row.id === fee.id
            ? { ...row, ...body }
            : row
        ),
      }));
    } catch (error) {
      setMessage(
        error.message || "Could not update fee"
      );
    }
  }


  async function updateChecklist(item, changes) {
    const response = await fetch(
      `${API}/api/boxing/events/${eventId}/checklist/${item.id}`,
      {
        method: "PATCH",
        headers: authHeaders({
          "Content-Type": "application/json",
        }),
        body: JSON.stringify(changes),
      }
    );

    const body = await response.json();

    if (!response.ok) {
      setMessage(
        body.detail || "Could not update checklist"
      );
      return;
    }

    setData((old) => ({
      ...old,
      checklist: old.checklist.map((row) =>
        row.id === item.id
          ? { ...row, ...body }
          : row
      ),
    }));
  }

  function contractTravelValue(
    boutId,
    corner,
    field,
    fallback = ""
  ) {
    const key = `${boutId}-${corner}`;

    if (
      contractTravel[key] &&
      contractTravel[key][field] !== undefined
    ) {
      return contractTravel[key][field];
    }

    const bout = (data?.bouts || []).find(
      (row) => Number(row.id) === Number(boutId)
    );

    const savedContract =
      corner === "red"
        ? bout?.red_contract
        : bout?.blue_contract;

    return (
      savedContract?.[field] ??
      fallback
    );
  }

  function setContractTravelValue(
    boutId,
    corner,
    field,
    value
  ) {
    const key = `${boutId}-${corner}`;

    setContractTravel((old) => ({
      ...old,
      [key]: {
        ...(old[key] || {}),
        [field]: value,
      },
    }));
  }


  async function saveContractTerms(
    bout,
    corner
  ) {
    const contract =
      corner === "red"
        ? bout.red_contract
        : bout.blue_contract;

    if (!contract?.id) {
      window.alert(
        "Generate this fighter's contract first, then save the terms."
      );
      return;
    }

    const key = `${bout.id}-${corner}`;

    setContractTermsSaving((old) => ({
      ...old,
      [key]: true,
    }));

    try {
      const payload = {
        ticket_commission_percent:
          contractCommissions[key] ??
          contract.ticket_commission_percent ??
          0,

        travel_type:
          contractTravelValue(
            bout.id,
            corner,
            "travel_type",
            ""
          ),

        travel_paid_by:
          contractTravelValue(
            bout.id,
            corner,
            "travel_paid_by",
            ""
          ),

        travel_expense:
          contractTravelValue(
            bout.id,
            corner,
            "travel_expense",
            0
          ),

        hotel_provided:
          contractTravelValue(
            bout.id,
            corner,
            "hotel_provided",
            ""
          ),

        hotel_name:
          contractTravelValue(
            bout.id,
            corner,
            "hotel_name",
            ""
          ),

        hotel_nights:
          contractTravelValue(
            bout.id,
            corner,
            "hotel_nights",
            0
          ),

        per_diem_daily:
          contractTravelValue(
            bout.id,
            corner,
            "per_diem_daily",
            0
          ),

        per_diem_days:
          contractTravelValue(
            bout.id,
            corner,
            "per_diem_days",
            0
          ),
      };

      const response = await fetch(
        `${API}/api/boxing/contracts/${contract.id}/terms`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(payload),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not save contract terms."
        );
      }

      const saved = body.contract || {};

      setContractCommissions((old) => ({
        ...old,
        [key]:
          saved.ticket_commission_percent ?? 0,
      }));

      setContractTravel((old) => ({
        ...old,
        [key]: {
          ...(old[key] || {}),
          travel_type:
            saved.travel_type ?? "",
          travel_paid_by:
            saved.travel_paid_by ?? "",
          travel_expense:
            saved.travel_expense ?? 0,
          hotel_provided:
            saved.hotel_provided ?? "",
          hotel_name:
            saved.hotel_name ?? "",
          hotel_nights:
            saved.hotel_nights ?? 0,
          per_diem_daily:
            saved.per_diem_daily ?? 0,
          per_diem_days:
            saved.per_diem_days ?? 0,
          per_diem_total:
            saved.per_diem_total ?? 0,
        },
      }));

      setData((old) => ({
        ...old,
        bouts: (old?.bouts || []).map((row) => {
          if (
            Number(row.id) !== Number(bout.id)
          ) {
            return row;
          }

          const contractKey =
            corner === "red"
              ? "red_contract"
              : "blue_contract";

          return {
            ...row,
            [contractKey]: {
              ...(row[contractKey] || {}),
              ...saved,
            },
          };
        }),
      }));

      setMessage(
        `${
          corner === "red"
            ? "Red"
            : "Blue"
        } corner contract terms saved.`
      );

      window.alert(
        "Contract terms saved successfully."
      );
    } catch (error) {
      window.alert(
        error.message ||
        "Could not save contract terms."
      );
    } finally {
      setContractTermsSaving((old) => ({
        ...old,
        [key]: false,
      }));
    }
  }


  async function uploadSignedContract(
    contractId,
    fighterName
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first."
      );
      return;
    }

    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/pdf,.pdf";

    input.onchange = async () => {
      const file = input.files?.[0];

      if (!file) return;

      if (
        file.type &&
        file.type !== "application/pdf"
      ) {
        window.alert(
          "Please select a PDF contract."
        );
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      try {
        const token =
          localStorage.getItem("token");

        const response = await fetch(
          `${API}/api/boxing/contracts/${contractId}/signed-upload`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${token}`,
            },
            body: formData,
          }
        );

        const body = await response.json();

        if (!response.ok) {
          throw new Error(
            body.detail ||
              "Could not upload signed contract."
          );
        }

        const notice =
          body.message ||
          `${fighterName} signed contract uploaded.`;

        setMessage(notice);
        window.alert(notice);

        await load();
      } catch (error) {
        const notice =
          error.message ||
          "Could not upload signed contract.";

        setMessage(notice);
        window.alert(notice);
      }
    };

    input.click();
  }


  async function downloadSignedContract(
    contractId,
    fighterName
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first."
      );
      return;
    }

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/boxing/contracts/${contractId}/signed-file`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        let detail =
          "No signed contract is available yet.";

        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch {
          // response may not be JSON
        }

        throw new Error(detail);
      }

      const blob = await response.blob();

      const disposition =
        response.headers.get(
          "Content-Disposition"
        ) || "";

      const match =
        disposition.match(
          /filename="([^"]+)"/i
        );

      const fallbackName =
        `${fighterName || "fighter"}-signed-contract.pdf`
          .replace(/[^a-z0-9._-]+/gi, "-");

      const fileName =
        match?.[1] || fallbackName;

      const url =
        window.URL.createObjectURL(blob);

      const link =
        document.createElement("a");

      link.href = url;
      link.download = fileName;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      setMessage(
        `Downloaded signed contract for ${fighterName}.`
      );
    } catch (error) {
      const notice =
        error.message ||
        "Could not download signed contract.";

      setMessage(notice);
      window.alert(notice);
    }
  }


  async function sendContractEmail(
    contractId,
    fighterName
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first, then send it."
      );
      return;
    }

    try {
      const response = await fetch(
        `${API}/api/boxing/contracts/${contractId}/send-email`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not send contract email."
        );
      }

      setMessage(body.message);
      window.alert(body.message);
    } catch (error) {
      const notice =
        error.message ||
        "Could not send contract email.";

      setMessage(notice);
      window.alert(notice);
    }
  }

  async function sendContractWithDocuSign(
    contractId,
    fighterName
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first."
      );
      return;
    }

    const confirmed = window.confirm(
      `Send ${fighterName}'s contract through DocuSign?`
    );

    if (!confirmed) return;

    try {
      const response = await fetch(
        `${API}/api/boxing/contracts/${contractId}/docusign/send`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not send contract with DocuSign."
        );
      }

      const notice =
        body.message ||
        `${fighterName}'s contract was sent with DocuSign.`;

      setMessage(notice);
      window.alert(notice);

      await load();

    } catch (error) {
      const notice =
        error.message ||
        "Could not send contract with DocuSign.";

      setMessage(notice);
      window.alert(notice);
    }
  }


  async function syncDocuSignContract(
    contractId,
    fighterName
  ) {
    if (!contractId) return;

    try {
      const response = await fetch(
        `${API}/api/boxing/contracts/${contractId}/docusign/sync`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
            "Could not sync DocuSign contract."
        );
      }

      const status =
        body.status ||
        body.status ||
        "Updated";

      const notice =
        `${fighterName} DocuSign status: ${status}`;

      setMessage(notice);
      window.alert(notice);

      await load();

    } catch (error) {
      const notice =
        error.message ||
        "Could not sync DocuSign contract.";

      setMessage(notice);
      window.alert(notice);
    }
  }


  async function viewOfficialContractPdf(
    contractId
  ) {
    if (!contractId) {
      window.alert(
        "Generate the contract first."
      );
      return;
    }

    const pdfWindow = window.open(
      "",
      "_blank"
    );

    if (!pdfWindow) {
      window.alert(
        "Please allow popups for TNGOS."
      );
      return;
    }

    pdfWindow.document.write(
      "<p style='font-family:Arial;padding:30px'>Loading official contract...</p>"
    );

    try {
      const token =
        localStorage.getItem("token");

      const response = await fetch(
        `${API}/api/boxing/contracts/${contractId}/official-pdf`,
        {
          headers: {
            Authorization:
              `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        let detail =
          "Could not load official contract PDF.";

        try {
          const body = await response.json();
          detail = body.detail || detail;
        } catch (_) {}

        throw new Error(detail);
      }

      const blob = await response.blob();

      const url =
        window.URL.createObjectURL(blob);

      pdfWindow.location.href = url;

      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 60000);

    } catch (error) {
      try {
        pdfWindow.close();
      } catch (_) {}

      const notice =
        error.message ||
        "Could not load official contract PDF.";

      setMessage(notice);
      window.alert(notice);
    }
  }


  async function generateContract(bout, corner) {
    const printWindow = window.open(
      "",
      "_blank",
      "width=900,height=1000,scrollbars=yes"
    );

    if (!printWindow) {
      setMessage(
        "Your browser blocked the contract window. Allow popups for TNG."
      );
      return;
    }

    printWindow.document.write(
      "<p style='font-family:Arial;padding:30px'>Generating contract...</p>"
    );

    try {
      const travelKey = `${bout.id}-${corner}`;
      const travel =
        contractTravel[travelKey] || {};

      const response = await fetch(
        `${API}/api/boxing/bouts/${bout.id}/contracts/${corner}`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            maximum_weight:
              contractWeights[bout.id] ??
              bout.weight_agreed ??
              "",

            ticket_commission_percent:
              contractCommissions[
                `${bout.id}-${corner}`
              ] ??
              bout[
                `${corner}_contract`
              ]?.ticket_commission_percent ??
              0,

            travel_type:
              travel.travel_type || "",

            travel_paid_by:
              travel.travel_paid_by || "",

            travel_expense:
              travel.travel_expense || 0,

            hotel_provided:
              travel.hotel_provided || "",

            hotel_name:
              travel.hotel_name || "",

            hotel_nights:
              travel.hotel_nights || 0,

            per_diem_daily:
              travel.per_diem_daily || 0,

            per_diem_days:
              travel.per_diem_days || 0,
          }),
        }
      );

      const contract = await response.json();

      if (!response.ok) {
        throw new Error(
          contract.detail || "Could not generate contract"
        );
      }

      const savedBoutWeight =
        contract.weight_agreed ??
        contract.maximum_weight ??
        bout.weight_agreed;

      setData((old) => ({
        ...old,
        bouts: old.bouts.map((row) =>
          row.id === bout.id
            ? {
                ...row,
                weight_agreed: savedBoutWeight,
              }
            : row
        ),
      }));

      setContractWeights((old) => ({
        ...old,
        [bout.id]: savedBoutWeight ?? "",
      }));

      const html =
        buildOfficialContractHtml(contract);

      printWindow.document.open();
      printWindow.document.write(html);
      printWindow.document.close();

      setMessage(
        `${contract.boxer_name} contract generated.`
      );

      await load();

    } catch (error) {
      printWindow.close();

      setMessage(
        error.message ||
        "Could not generate contract"
      );
    }
  }


  async function updateBoutPurse(bout, changes) {
    try {
      const response = await fetch(
        `${API}/api/boxing/bouts/${bout.id}/purse`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(changes),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update purse"
        );
      }

      setData((old) => ({
        ...old,
        bouts: old.bouts.map((row) =>
          row.id === bout.id
            ? {
                ...row,
                red_purse: body.red_purse,
                blue_purse: body.blue_purse,
              }
            : row
        ),
      }));

      setMessage("Fight purse updated.");
    } catch (error) {
      setMessage(
        error.message || "Could not update purse"
      );
    }
  }


  async function updateBoutOrder(bout, value) {
    const order = Number(value);

    if (!Number.isInteger(order) || order < 1) {
      setMessage("Bout order must be 1 or higher.");
      return;
    }

    try {
      const response = await fetch(
        `${API}/api/boxing/bouts/${bout.id}/order`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            bout_order: order,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not update bout order"
        );
      }

      setData((old) => ({
        ...old,
        bouts: old.bouts
          .map((row) =>
            row.id === bout.id
              ? { ...row, bout_order: order }
              : row
          )
          .sort(
            (a, b) =>
              Number(a.bout_order || 999) -
              Number(b.bout_order || 999)
          ),
      }));

      setMessage(`Bout moved to #${order}`);
    } catch (error) {
      setMessage(
        error.message || "Could not update bout order"
      );
    }
  }

  async function generateEventPromo() {
    setPromoLoading(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API}/api/boxing/events/${eventId}/generate-promo`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not generate event promo"
        );
      }

      setPromoImage(body.image);

      setMessage(
        "Event promo generated from the current fight card."
      );

    } catch (error) {

      setMessage(
        error.message ||
        "Could not generate event promo"
      );

    } finally {
      setPromoLoading(false);
    }
  }


  const promoterItems = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.section === "promoter"
      ),
    [data]
  );

  const matchmakerItems = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.section === "matchmaker"
      ),
    [data]
  );

  const completed = useMemo(
    () =>
      (data?.checklist || []).filter(
        (x) => x.status === "complete"
      ).length,
    [data]
  );

  const bloodworkVerified = useMemo(
    () =>
      (data?.fighters || []).filter(
        (x) => x.bloodwork_status === "verified"
      ).length,
    [data]
  );

  if (loading) {
    return (
      <Box sx={{ p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!data) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          {message || "Event could not be loaded."}
        </Alert>

        <Button
          sx={{ mt: 2 }}
          onClick={onBack}
        >
          Back
        </Button>
      </Box>
    );
  }

  const event = data.event;
  const bouts = data.bouts || [];

  const activeBouts = bouts.filter(
    (bout) =>
      bout.status !== "cancelled" &&
      bout.status !== "void"
  );

  const cancelledBouts = bouts.filter(
    (bout) =>
      bout.status === "cancelled" ||
      bout.status === "void"
  );

  const fighters = data.fighters || [];
  const totalChecklist =
    data.checklist?.length || 0;

  async function submitBoutCancellation() {
    if (!cancelBout) return;

    const notes = cancelBoutNotes.trim();

    if (!notes) {
      alert("Please enter a reason for removing this bout.");
      return;
    }

    setCancelBoutWorking(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/bouts/${cancelBout.id}/cancel`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            notes,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.detail || "Could not remove bout."
        );
      }

      setData((old) => ({
        ...old,
        bouts: old.bouts.map((bout) =>
          bout.id === cancelBout.id
            ? {
                ...bout,
                status: "cancelled",
                notes: result.notes || bout.notes,
              }
            : bout
        ),
      }));

      setCancelBoutOpen(false);
      setCancelBout(null);
      setCancelBoutNotes("");
    } catch (error) {
      alert(error.message || "Could not remove bout.");
    } finally {
      setCancelBoutWorking(false);
    }
  }


  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack spacing={2.5}>
        <Stack
          direction={{
            xs: "column",
            md: "row",
          }}
          spacing={2}
          justifyContent="space-between"
        >
          <Box>
            <Button
              startIcon={<ArrowBackRoundedIcon />}
              onClick={onBack}
              sx={{ mb: 1 }}
            >
              Back to Matchmaker
            </Button>

            <Typography
              variant="h4"
              fontWeight={950}
            >
              {event.name}
            </Typography>

            <Typography color="text.secondary">
              {event.event_date || "No date"}
              {event.venue
                ? ` - ${event.venue}`
                : ""}
            </Typography>

            {event.venue_address && (
              <Typography
                variant="body2"
                color="text.secondary"
              >
                {event.venue_address}
              </Typography>
            )}
          </Box>

          <Chip
            label={event.status || "planning"}
            sx={{
              alignSelf: {
                xs: "flex-start",
                md: "center",
              },
            }}
          />
        </Stack>

        {message && (
          <Alert
            severity="info"
            onClose={() => setMessage("")}
          >
            {message}
          </Alert>
        )}

        {tab === 0 ? (
          <Stack spacing={3}>
            <EventCommandCenter
              data={data}
              setTab={setTab}
            />

            <EventHomeNavigation
              setTab={setTab}
            />
          </Stack>
        ) : (
          <Card
            sx={{
              borderRadius: 4,
              border: "1px solid",
              borderColor: "divider",
              boxShadow: "0 10px 30px rgba(15,23,42,.05)",
            }}
          >
            <CardContent>
              <Stack
                direction={{ xs: "column", md: "row" }}
                justifyContent="space-between"
                alignItems={{ xs: "stretch", md: "center" }}
                spacing={2}
              >
                <Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    fontWeight={900}
                  >
                    EVENT OPERATIONS
                  </Typography>

                  <Typography
                    variant="h4"
                    fontWeight={950}
                  >
                    {eventPageTitles[tab] || "Event Operations"}
                  </Typography>
                </Box>

                <Button
                  variant="outlined"
                  onClick={() => setTab(0)}
                  sx={{ fontWeight: 900 }}
                >
                  ? Event Home
                </Button>
              </Stack>
            </CardContent>
          </Card>
        )}

        {tab === 8 && (
          <Stack spacing={2}>
            <Card>
              <CardContent>
                <Typography
                  variant="h6"
                  fontWeight={900}
                  sx={{ mb: 2 }}
                >
                  Event Venue
                </Typography>

                <Grid container spacing={2}>
                  <Grid item xs={12} md={5}>
                    <TextField
                      fullWidth
                      label="Venue Name"
                      value={venueName}
                      onChange={(e) =>
                        setVenueName(e.target.value)
                      }
                    />
                  </Grid>

                  <Grid item xs={12} md={5}>
                    <TextField
                      fullWidth
                      label="Venue Address"
                      value={venueAddress}
                      onChange={(e) =>
                        setVenueAddress(e.target.value)
                      }
                    />
                  </Grid>

                  <Grid item xs={12} md={2}>
                    <Button
                      fullWidth
                      variant="contained"
                      color="error"
                      onClick={saveVenue}
                      disabled={venueSaving}
                      sx={{ height: "100%", minHeight: 56 }}
                    >
                      {venueSaving
                        ? "Saving..."
                        : "Save Venue"}
                    </Button>
                  </Grid>
                </Grid>

                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mt: 1.5 }}
                >
                  Updating the venue also updates all unsigned
                  contracts for this event. Electronically signed
                  contracts remain unchanged.
                </Typography>
              </CardContent>
            </Card>
          </Stack>
        )}

        {tab === 9 && (
          <Card>
            <TicketingDashboard key={eventId} eventId={eventId} event={event} />
          </Card>
        )}

        {/* OVERVIEW */}
        {false && (
          <Grid container spacing={2}>
            <Grid item xs={12} md={7}>
              <Card>
                <CardContent>
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    Fight Card
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  {!activeBouts.length && (
                    <Typography color="text.secondary">
                      No bouts have been built for
                      this event yet.
                    </Typography>
                  )}

                  <Stack spacing={1}>
                    {activeBouts.map((bout, index) => (
                      <Box
                        key={bout.id}
                        sx={{
                          p: 1.5,
                          borderRadius: 2,
                          bgcolor: "#fafafa",
                        }}
                      >
                        <Typography
                          fontWeight={900}
                        >
                          Bout {index + 1}
                        </Typography>

                        <Typography>
                          {bout.red?.legal_name}
                          {" vs "}
                          {bout.blue?.legal_name}
                        </Typography>

                        <Typography
                          variant="caption"
                          color="text.secondary"
                        >
                          {bout.weight_agreed
                            ? `${bout.weight_agreed} lb`
                            : "Weight TBD"}
                          {" - "}
                          {bout.rounds} rounds
                          {" - "}
                          {bout.status}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={5}>
              <Card>
                <CardContent>
                  <Typography
                    variant="h6"
                    fontWeight={900}
                  >
                    Needs Attention
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  <Stack spacing={1}>
                    {fighters
                      .filter(
                        (fighter) =>
                          fighter.bloodwork_status !==
                          "verified"
                      )
                      .map((fighter) => (
                        <Alert
                          severity="warning"
                          key={fighter.id}
                        >
                          {fighter.legal_name}: bloodwork{" "}
                          {fighter.bloodwork_status ||
                            "missing"}
                        </Alert>
                      ))}

                    {data.checklist
                      .filter(
                        (item) =>
                          item.status ===
                          "needs_attention"
                      )
                      .map((item) => (
                        <Alert
                          severity="error"
                          key={item.id}
                        >
                          {item.label}
                        </Alert>
                      ))}

                    {!fighters.some(
                      (f) =>
                        f.bloodwork_status !==
                        "verified"
                    ) &&
                      !data.checklist.some(
                        (x) =>
                          x.status ===
                          "needs_attention"
                      ) && (
                        <Alert severity="success">
                          No current attention flags.
                        </Alert>
                      )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* FIGHT CARD */}
                {tab === 10 && (
          <EventFightCardBuilder
            eventId={eventId}
            event={event}
            bouts={bouts}
            onRefresh={load}
          />
        )}

{tab === 1 && (
          <EventFightCardPage
            activeBouts={activeBouts}
            cancelledBouts={cancelledBouts}
            setData={setData}
            updateBoutOrder={updateBoutOrder}
            setCancelBout={setCancelBout}
            setCancelBoutNotes={setCancelBoutNotes}
            setCancelBoutOpen={setCancelBoutOpen}
          />
        )}

        {/* BOUT SHEETS */}
        {tab === 2 && (
          <EventContractsPage
            activeBouts={activeBouts}
            expandedBouts={expandedBouts}
            setExpandedBouts={setExpandedBouts}
            setData={setData}
            updateBoutPurse={updateBoutPurse}
            contractWeights={contractWeights}
            setContractWeights={setContractWeights}
            contractCommissions={contractCommissions}
            setContractCommissions={setContractCommissions}
            contractTravelValue={contractTravelValue}
            setContractTravelValue={setContractTravelValue}
            contractTermsSaving={contractTermsSaving}
            saveContractTerms={saveContractTerms}
            sendContractWithDocuSign={sendContractWithDocuSign}
            syncDocuSignContract={syncDocuSignContract}
            viewOfficialContractPdf={viewOfficialContractPdf}
            sendContractEmail={sendContractEmail}
            uploadSignedContract={uploadSignedContract}
            downloadSignedContract={downloadSignedContract}
            generateContract={generateContract}
          />
        )}

        {/* PROMOTER */}
        {tab === 3 && (
          <EventCompliancePage
            mode="promoter"
            items={promoterItems}
            updateChecklist={updateChecklist}
            setData={setData}
            statusLabels={statusLabels}
            statusColor={statusColor}
          />
        )}

        {/* MATCHMAKER */}
        {tab === 4 && (
          <EventCompliancePage
            mode="matchmaker"
            items={matchmakerItems}
            updateChecklist={updateChecklist}
            setData={setData}
            statusLabels={statusLabels}
            statusColor={statusColor}
          />
        )}

        {/* BLOODWORK */}
        {tab === 5 && (
          <EventMedicalsPage
            fighters={fighters}
            updateBloodwork={updateBloodwork}
          />
        )}

        {/* FEES */}
        {tab === 6 && (
          <EventExpensesPage
            fees={data.fees || []}
            updateFee={updateFee}
          />
        )}

      </Stack>
      {tab === 7 && (
        <EventRevenue eventId={eventId} event={event} />
      )}

      <Dialog
        open={cancelBoutOpen}
        onClose={() => {
          if (!cancelBoutWorking) {
            setCancelBoutOpen(false);
          }
        }}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          Remove Bout
        </DialogTitle>

        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will remove the bout from the active fight card,
            but it will remain in TNGOS records as cancelled.
          </Alert>

          {cancelBout && (
            <Typography fontWeight={900} sx={{ mb: 2 }}>
              {cancelBout.red?.legal_name || "Red Corner"}
              {" vs "}
              {cancelBout.blue?.legal_name || "Blue Corner"}
            </Typography>
          )}

          <TextField
            autoFocus
            required
            fullWidth
            multiline
            minRows={4}
            label="Reason / Notes"
            placeholder="Example: Opponent withdrew, purse disagreement, medical issue, weight issue..."
            value={cancelBoutNotes}
            onChange={(e) =>
              setCancelBoutNotes(e.target.value)
            }
            helperText="Required. This note will stay with the bout record."
          />
        </DialogContent>

        <DialogActions>
          <Button
            disabled={cancelBoutWorking}
            onClick={() => {
              setCancelBoutOpen(false);
              setCancelBout(null);
              setCancelBoutNotes("");
            }}
          >
            Keep Bout
          </Button>

          <Button
            variant="contained"
            color="error"
            disabled={
              cancelBoutWorking ||
              !cancelBoutNotes.trim()
            }
            onClick={submitBoutCancellation}
          >
            {cancelBoutWorking
              ? "Removing..."
              : "Remove Bout"}
          </Button>
        </DialogActions>
      </Dialog>


    </Box>
  );
}
