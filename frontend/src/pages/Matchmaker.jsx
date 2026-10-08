import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert, Autocomplete, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, Divider, FormControl,
  Grid, InputLabel, MenuItem, Select, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField, Typography
} from "@mui/material";
import AddRoundedIcon from "@mui/icons-material/AddRounded";
import EventRoundedIcon from "@mui/icons-material/EventRounded";
import ContentCopyRoundedIcon from "@mui/icons-material/ContentCopyRounded";
import SportsMmaRoundedIcon from "@mui/icons-material/SportsMmaRounded";
import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import HubRoundedIcon from "@mui/icons-material/HubRounded";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";
import EventWorkspace from "./EventWorkspace.jsx";
import AutoMatchPlanner from "./AutoMatchPlanner.jsx";
import TicketSellerControls from "../components/tickets/TicketSellerControls.jsx";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const FIGHTER_REGISTRATION_URL =
  "https://tngos.tngboxinggym.com/?fighter-register=1";

const authHeaders = (extra = {}) => ({
  Authorization: `Bearer ${localStorage.getItem("token")}`,
  ...extra,
});

const emptyFighter = {
  legal_name: "",
  dob: "",
  phone: "",
  email: "",
  city: "",
  state: "OK",
  country: "USA",
  sex: "",
  stance: "",
  gym: "",
  coach: "",
  height_in: "",
  reach_in: "",
  walk_weight: "",
  fight_weight: "",
  pro_record: "",
  amateur_record: "",
  boxrec_id: "",
  boxrec_url: "",
  manager_name: "",
  manager_phone: "",
  manager_email: "",
  ok_license_status: "unknown",
  federal_id_status: "unknown",
  suspension_status: "needs_review",
  bloodwork_status: "missing",
  bloodwork_expires: "",
  available: true,
  available_weight_min: "",
  available_weight_max: "",
  last_fight_date: "",
};

const emptyEvent = {
  name: "",
  slug: "",
  venue: "",
  venue_address: "",
  event_date: "",
};

function numberOrNull(value) {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}


const WEIGHT_DIVISIONS = [
  { value: "105", label: "105 lb", min: 0, max: 105 },
  { value: "108", label: "108 lb", min: 105, max: 108 },
  { value: "112", label: "112 lb", min: 108, max: 112 },
  { value: "115", label: "115 lb", min: 112, max: 115 },
  { value: "118", label: "118 lb", min: 115, max: 118 },
  { value: "122", label: "122 lb", min: 118, max: 122 },
  { value: "126", label: "126 lb", min: 122, max: 126 },
  { value: "130", label: "130 lb", min: 126, max: 130 },
  { value: "135", label: "135 lb", min: 130, max: 135 },
  { value: "140", label: "140 lb", min: 135, max: 140 },
  { value: "147", label: "147 lb", min: 140, max: 147 },
  { value: "154", label: "154 lb", min: 147, max: 154 },
  { value: "160", label: "160 lb", min: 154, max: 160 },
  { value: "168", label: "168 lb", min: 160, max: 168 },
  { value: "175", label: "175 lb", min: 168, max: 175 },
  { value: "200", label: "200 lb", min: 175, max: 200 },
  { value: "heavy", label: "Heavyweight", min: 200, max: Infinity },
];

function fighterMatchesDivision(fighter, divisionValue) {
  if (!divisionValue) return true;

  const division = WEIGHT_DIVISIONS.find(
    (item) => item.value === divisionValue
  );

  if (!division) return true;

  const fightWeight = Number(fighter.fight_weight);
  const minWeight = Number(fighter.available_weight_min);
  const maxWeight = Number(fighter.available_weight_max);

  const hasFight =
    Number.isFinite(fightWeight) && fightWeight > 0;

  const hasMin =
    Number.isFinite(minWeight) && minWeight > 0;

  const hasMax =
    Number.isFinite(maxWeight) && maxWeight > 0;

  const inDivision = (weight) => {
    if (division.max === Infinity) {
      return weight > 200;
    }

    return (
      weight > division.min &&
      weight <= division.max
    );
  };

  if (hasFight && inDivision(fightWeight)) {
    return true;
  }

  if (hasMin || hasMax) {
    const low = hasMin
      ? minWeight
      : hasFight
        ? fightWeight
        : 0;

    const high = hasMax
      ? maxWeight
      : hasFight
        ? fightWeight
        : 999;

    if (division.max === Infinity) {
      return high > 200;
    }

    return (
      high > division.min &&
      low <= division.max
    );
  }

  return false;
}

function slugify(value) {
  return (value || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function Matchmaker() {
  const [fighters, setFighters] = useState([]);
  const [events, setEvents] = useState([]);
  const [fighterId, setFighterId] = useState("");
  const [eventId, setEventId] = useState("");
  const [eventWorkspaceId, setEventWorkspaceId] = useState("");
  const [promoterPage, setPromoterPage] = useState("home");
  const [weightDivision, setWeightDivision] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [boxrecSearching, setBoxrecSearching] = useState(false);
  const [boxrecSearchText, setBoxrecSearchText] = useState("");
  const [existingFighterId, setExistingFighterId] = useState("");
  const [msg, setMsg] = useState("");
  const [msgType, setMsgType] = useState("info");

  async function copyFighterRegistrationLink() {
    try {
      await navigator.clipboard.writeText(
        FIGHTER_REGISTRATION_URL
      );

      setMsgType("success");
      setMsg("Fighter registration link copied.");
    } catch (error) {
      setMsgType("error");
      setMsg("Could not copy fighter registration link.");
    }
  }


  const [socialOpen, setSocialOpen] = useState(false);
  const [socialLoading, setSocialLoading] = useState(false);
  const [socialResults, setSocialResults] = useState([]);
  const [socialFighter, setSocialFighter] = useState(null);
  const [socialError, setSocialError] = useState("");


  const [fighterOpen, setFighterOpen] = useState(false);

  const [seriesList, setSeriesList] = useState([]);
  const [seriesFighters, setSeriesFighters] = useState([]);
  const [seriesFighterId, setSeriesFighterId] = useState("");
  const [seriesLoading, setSeriesLoading] = useState(false);

  const [signedFighters, setSignedFighters] = useState([]);
  const [signedFighterId, setSignedFighterId] = useState("");
  const [signedLoading, setSignedLoading] = useState(false);
  const [eventOpen, setEventOpen] = useState(false);

  const boxrecWindowRef = useRef(null);
  const [fighterForm, setFighterForm] = useState(emptyFighter);

  const [editFighterOpen, setEditFighterOpen] = useState(false);
  const [editFighterId, setEditFighterId] = useState("");
  const [editFighterForm, setEditFighterForm] = useState(emptyFighter);

  const [fighterPortalAccount, setFighterPortalAccount] = useState(null);
  const [fighterPortalForm, setFighterPortalForm] = useState({
    login_email: "",
    password: "",
    active: true,
  });
  const [fighterPortalLoading, setFighterPortalLoading] = useState(false);
  const [eventForm, setEventForm] = useState(emptyEvent);

  const [fighterInviteStatus, setFighterInviteStatus] = useState({});
  const [fighterInviteLoading, setFighterInviteLoading] = useState({});

  async function loadFighterInviteStatus(fighterId) {
    try {
      const response = await fetch(
        `${API}/api/fighter/admin/${fighterId}/invite-status`,
        {
          headers: authHeaders(),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not load fighter login status"
        );
      }

      setFighterInviteStatus((current) => ({
        ...current,
        [fighterId]: body,
      }));

      return body;
    } catch (error) {
      console.error(
        "Fighter login status:",
        error
      );

      return null;
    }
  }


  async function loadAllFighterInviteStatuses() {
    if (!fighters.length) return;

    await Promise.all(
      fighters.map((fighter) =>
        loadFighterInviteStatus(fighter.id)
      )
    );
  }


  async function inviteFighterLogin(fighter) {
    if (!fighter?.id) return;

    if (!(fighter.email || "").trim()) {
      setMsgType("warning");
      setMsg(
        `${fighter.legal_name || "Fighter"} needs an email address before login can be activated.`
      );
      return;
    }

    setFighterInviteLoading((current) => ({
      ...current,
      [fighter.id]: true,
    }));

    try {
      const response = await fetch(
        `${API}/api/fighter/admin/invite`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            fighter_id: Number(fighter.id),
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not send fighter activation email"
        );
      }

      setMsgType("success");

      if (body.already_sent) {
        const notice =
          `An activation email has already been sent to ${fighter.legal_name}.`;

        setMsg(notice);
        window.alert(notice);

      } else if (body.email_sent) {
        const notice =
          `Fighter Portal activation email sent to ${fighter.email}.`;

        setMsg(notice);
        window.alert(notice);

      } else {
        const notice =
          `Fighter invite created, but the email could not be sent. ${body.email_error || "Unknown email error."}`;

        setMsgType("error");
        setMsg(notice);
        window.alert(notice);
      }

      await loadFighterInviteStatus(
        fighter.id
      );

    } catch (error) {
      const notice =
        error.message ||
        "Could not activate fighter login";

      setMsgType("error");
      setMsg(notice);
      window.alert(notice);
    } finally {
      setFighterInviteLoading((current) => ({
        ...current,
        [fighter.id]: false,
      }));
    }
  }


  useEffect(() => {
    if (!fighters.length) return;

    loadAllFighterInviteStatuses();
  }, [fighters]);


  async function loadSignedFighters() {
    try {
      const response = await fetch(
        `${API}/api/boxing/signed-fighters`,
        { headers: authHeaders() }
      );

      const body = await readJson(response);

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not load signed fighters"
        );
      }

      setSignedFighters(
        Array.isArray(body) ? body : []
      );

    } catch (error) {
      console.error(
        "Signed Fighters:",
        error
      );
    }
  }


  async function signSelectedFighter() {
    if (!signedFighterId) {
      setMsgType("warning");
      setMsg("Select a fighter to sign.");
      return;
    }

    const fighter = fighters.find(
      (row) =>
        Number(row.id) ===
        Number(signedFighterId)
    );

    setSignedLoading(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/signed-fighters`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            fighter_id: Number(signedFighterId),
            signed_date:
              new Date()
                .toISOString()
                .slice(0, 10),
            status: "active",
            agreement_type: "development",
          }),
        }
      );

      const body = await readJson(response);

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not sign fighter"
        );
      }

      setSignedFighterId("");

      setMsgType("success");
      setMsg(
        `${fighter?.legal_name || "Fighter"} added to Signed Fighters.`
      );

      await loadSignedFighters();

    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not sign fighter"
      );
    } finally {
      setSignedLoading(false);
    }
  }


  async function removeSignedFighter(row) {
    const name =
      row.fighter?.legal_name ||
      "this fighter";

    if (
      !window.confirm(
        `Remove ${name} from Signed Fighters?`
      )
    ) {
      return;
    }

    try {
      const response = await fetch(
        `${API}/api/boxing/signed-fighters/${row.id}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const body = await readJson(response);

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not remove signed fighter"
        );
      }

      await loadSignedFighters();

    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not remove signed fighter"
      );
    }
  }


  async function loadFirstFiveSeries() {
    try {
      const seriesResponse = await fetch(
        `${API}/api/boxing/series`,
        {
          headers: authHeaders(),
        }
      );

      const seriesBody = await readJson(
        seriesResponse
      );

      if (!seriesResponse.ok) {
        throw new Error(
          seriesBody.detail ||
          "Could not load fighter series"
        );
      }

      const list = Array.isArray(seriesBody)
        ? seriesBody
        : [];

      setSeriesList(list);

      const firstFive = list.find(
        (row) =>
          row.slug === "first-5-fights"
      );

      if (!firstFive) {
        setSeriesFighters([]);
        return;
      }

      const fighterResponse = await fetch(
        `${API}/api/boxing/series/${firstFive.id}/fighters`,
        {
          headers: authHeaders(),
        }
      );

      const fighterBody = await readJson(
        fighterResponse
      );

      if (!fighterResponse.ok) {
        throw new Error(
          fighterBody.detail ||
          "Could not load First 5 fighters"
        );
      }

      setSeriesFighters(
        Array.isArray(fighterBody)
          ? fighterBody
          : []
      );

    } catch (error) {
      console.error(
        "First 5 Series:",
        error
      );
    }
  }


  async function addToFirstFive() {
    if (!seriesFighterId) {
      setMsgType("warning");
      setMsg(
        "Select a fighter to add to the First 5 Fights Series."
      );
      return;
    }

    const firstFive = seriesList.find(
      (row) =>
        row.slug === "first-5-fights"
    );

    if (!firstFive) {
      setMsgType("error");
      setMsg(
        "First 5 Fights Series could not be found."
      );
      return;
    }

    const fighter = fighters.find(
      (row) =>
        Number(row.id) ===
        Number(seriesFighterId)
    );

    setSeriesLoading(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/series/${firstFive.id}/fighters`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type":
              "application/json",
          }),
          body: JSON.stringify({
            fighter_id:
              Number(seriesFighterId),

            signed_date:
              new Date()
                .toISOString()
                .slice(0, 10),

            start_record:
              fighter?.pro_record || "",

            target_fights: 5,
            fights_completed: 0,
          }),
        }
      );

      const body = await readJson(
        response
      );

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not add fighter to series"
        );
      }

      setSeriesFighterId("");

      setMsgType("success");
      setMsg(
        `${body.fighter?.legal_name || "Fighter"} added to First 5 Fights Series.`
      );

      await loadFirstFiveSeries();

    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not add fighter to series"
      );
    } finally {
      setSeriesLoading(false);
    }
  }


  async function updateSeriesFighter(
    row,
    changes
  ) {
    try {
      const response = await fetch(
        `${API}/api/boxing/series-fighters/${row.id}`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type":
              "application/json",
          }),
          body: JSON.stringify(changes),
        }
      );

      const body = await readJson(
        response
      );

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not update series fighter"
        );
      }

      setSeriesFighters(
        (old) =>
          old.map((item) =>
            item.id === row.id
              ? {
                  ...item,
                  ...body,
                }
              : item
          )
      );

    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not update series fighter"
      );
    }
  }


  async function removeSeriesFighter(row) {
    const name =
      row.fighter?.legal_name ||
      "this fighter";

    if (
      !window.confirm(
        `Remove ${name} from the First 5 Fights Series?`
      )
    ) {
      return;
    }

    try {
      const response = await fetch(
        `${API}/api/boxing/series-fighters/${row.id}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const body = await readJson(
        response
      );

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not remove fighter"
        );
      }

      await loadFirstFiveSeries();

      setMsgType("success");
      setMsg(
        `${name} removed from the series.`
      );

    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not remove fighter"
      );
    }
  }


  async function readJson(response) {
    try {
      return await response.json();
    } catch {
      return {};
    }
  }

  async function load() {
    setLoading(true);
    setMsg("");
    try {
      const [fr, er] = await Promise.all([
        fetch(`${API}/api/boxing/fighters`, { headers: authHeaders() }),
        fetch(`${API}/api/boxing/events`, { headers: authHeaders() }),
      ]);

      const fd = await readJson(fr);
      const ed = await readJson(er);

      if (!fr.ok) throw new Error(fd.detail || "Could not load fighters");
      if (!er.ok) throw new Error(ed.detail || "Could not load events");

      setFighters(Array.isArray(fd) ? fd : []);
      setEvents(Array.isArray(ed) ? ed : []);
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not load Matchmaker data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    loadFirstFiveSeries();
  }, []);

  function openBoxRecProfile(searchValue = null) {
    const query = String(
      searchValue ??
      boxrecSearchText ??
      fighterForm.boxrec_id ??
      ""
    ).trim();

    if (!query) {
      setMsgType("warning");
      setMsg("Enter a fighter name or BoxRec ID.");
      return;
    }

    const isBoxRecId = /^\d+$/.test(query);

    const url = isBoxRecId
      ? `https://boxrec.com/en/box-pro/${encodeURIComponent(query)}`
      : `https://boxrec.com/en/search?search%5Bquery%5D=${encodeURIComponent(query)}`;

    try {
      if (
        boxrecWindowRef.current &&
        !boxrecWindowRef.current.closed
      ) {
        boxrecWindowRef.current.location.href = url;
        boxrecWindowRef.current.focus();
        return;
      }

      boxrecWindowRef.current = window.open(
        url,
        "tngBoxRecProfile",
        "popup=yes,width=1100,height=820,resizable=yes,scrollbars=yes"
      );

      if (!boxrecWindowRef.current) {
        window.open(
          url,
          "_blank",
          "noopener,noreferrer"
        );
      }
    } catch {
      window.open(
        url,
        "_blank",
        "noopener,noreferrer"
      );
    }
  }


  function closeBoxRecProfile() {
    try {
      if (
        boxrecWindowRef.current &&
        !boxrecWindowRef.current.closed
      ) {
        boxrecWindowRef.current.close();
      }
    } catch {
      // Ignore cross-window browser restrictions.
    }

    boxrecWindowRef.current = null;
  }


  async function lookupBoxRec() {
    const query = String(
      boxrecSearchText ||
      fighterForm.boxrec_id ||
      ""
    ).trim();

    if (!query) {
      setMsgType("warning");
      setMsg("Enter a fighter name or BoxRec ID first.");
      return;
    }

    const isBoxRecId = /^\d+$/.test(query);

    // Name search: open BoxRec search only.
    if (!isBoxRecId) {
      openBoxRecProfile(query);

      setMsgType("info");
      setMsg(
        `Searching BoxRec for "${query}". Once you find the correct fighter, enter their BoxRec ID to link them to TNG.`
      );

      return;
    }

    // ID search: direct profile + check TNG database.
    setFighterForm({
      ...fighterForm,
      boxrec_id: query,
    });

    openBoxRecProfile(query);

    setBoxrecSearching(true);
    setExistingFighterId("");
    setMsg("");

    try {
      const r = await fetch(
        `${API}/api/boxing/fighters/by-boxrec/${encodeURIComponent(query)}`,
        { headers: authHeaders() }
      );

      const d = await readJson(r);

      if (r.status === 404) {
        setMsgType("info");
        setMsg(
          `BoxRec ID ${query} is not in TNG yet. Verify the fighter on BoxRec, complete the fighter information below, then click Add Fighter.`
        );
        return;
      }

      if (!r.ok) {
        throw new Error(
          d.detail || "Could not search BoxRec ID"
        );
      }

      setFighterForm({
        ...emptyFighter,
        ...d,
        boxrec_id: query,
        available: d.available ?? true,
      });

      setBoxrecSearchText(query);
      setExistingFighterId(d.id || "");

      setMsgType("success");
      setMsg(
        `${d.legal_name || "Fighter"} already exists in TNG. Their saved information has been loaded.`
      );

    } catch (e) {
      setMsgType("error");
      setMsg(
        e.message || "Could not search BoxRec ID"
      );
    } finally {
      setBoxrecSearching(false);
    }
  }



  const filteredFighters = fighters.filter((fighter) =>
    fighterMatchesDivision(
      fighter,
      weightDivision
    )
  );

  async function createFighter(findAfterSave = false) {
    if (existingFighterId) {
      setFighterId(existingFighterId);
      setFighterOpen(false);

      if (findAfterSave) {
        await findMatches(existingFighterId);
      } else {
        setMsgType("success");
        setMsg("Existing fighter selected for matchmaking.");
      }

      return;
    }

    if (!fighterForm.legal_name.trim()) {
      setMsgType("warning");
      setMsg("Fighter name is required.");
      return;
    }

    setWorking(true);
    try {
      const payload = {
        ...fighterForm,
        legal_name: fighterForm.legal_name.trim(),
        height_in: numberOrNull(fighterForm.height_in),
        reach_in: numberOrNull(fighterForm.reach_in),
        walk_weight: numberOrNull(fighterForm.walk_weight),
        fight_weight: numberOrNull(fighterForm.fight_weight),
        available_weight_min: numberOrNull(fighterForm.available_weight_min),
        available_weight_max: numberOrNull(fighterForm.available_weight_max),
      };

      const r = await fetch(`${API}/api/boxing/fighters`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Could not add fighter");

      setFighterForm(emptyFighter);
      setExistingFighterId("");
      setFighterOpen(false);
      closeBoxRecProfile();
      setMsgType("success");
      setMsg(`${d.legal_name || payload.legal_name} added to the fighter pool.`);

      await load();

      if (d.id) {
        setFighterId(d.id);

        if (findAfterSave) {
          await findMatches(d.id);
        }
      }
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not add fighter");
    } finally {
      setWorking(false);
    }
  }


  async function deleteFighterFromPool(fighter) {
    if (!fighter?.id) return;

    const name =
      fighter.legal_name || "this fighter";

    const confirmed = window.confirm(
      `Delete ${name} from the fighter pool?\n\n` +
      "This cannot be undone. Fighters connected to " +
      "bouts, contracts, signed agreements, or the " +
      "First 5 series cannot be deleted."
    );

    if (!confirmed) return;

    try {
      const response = await fetch(
        `${API}/api/boxing/fighters/${fighter.id}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const body = await readJson(response);

      if (!response.ok) {
        throw new Error(
          body.detail ||
          "Could not delete fighter"
        );
      }

      if (
        Number(fighterId) ===
        Number(fighter.id)
      ) {
        setFighterId("");
        setResult(null);
      }

      setMsgType("success");
      setMsg(
        body.message ||
        `${name} deleted from fighter pool.`
      );

      await load();
    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not delete fighter"
      );
    }
  }



  async function previewFighterPortal(fighter) {
    const previewWindow = window.open("about:blank", "_blank");

    if (!previewWindow) {
      setMsgType("warning");
      setMsg("Allow pop-ups for TNGOS to preview a fighter portal.");
      return;
    }

    try {
      previewWindow.document.write(
        "<p style='font-family:Arial;padding:24px'>Opening Fighter Portal...</p>"
      );

      const response = await fetch(
        `${API}/api/fighter/admin/fighters/${fighter.id}/preview-token`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not open Fighter Portal"
        );
      }

      previewWindow.sessionStorage.setItem(
        "fighterPreviewToken",
        data.token
      );

      previewWindow.location.href = "/fighter/preview";
    } catch (error) {
      previewWindow.close();
      setMsgType("error");
      setMsg(
        error.message || "Could not open Fighter Portal"
      );
    }
  }


  async function openEditFighter(fighter) {
    setEditFighterId(fighter.id);

    setEditFighterForm({
      ...emptyFighter,
      ...fighter,

      boxrec_id: fighter.boxrec_id || "",

      fight_weight:
        fighter.fight_weight ?? "",

      walk_weight:
        fighter.walk_weight ?? "",

      height_in:
        fighter.height_in ?? "",

      reach_in:
        fighter.reach_in ?? "",

      available_weight_min:
        fighter.available_weight_min ?? "",

      available_weight_max:
        fighter.available_weight_max ?? "",
    });

    setFighterPortalAccount(null);
    setFighterPortalForm({
      login_email: fighter.email || "",
      password: "",
      active: true,
    });

    setEditFighterOpen(true);
    setFighterPortalLoading(true);

    try {
      const response = await fetch(
        `${API}/api/fighter/admin/fighters/${fighter.id}/portal-account`,
        {
          headers: authHeaders(),
        }
      );

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not load fighter portal account"
        );
      }

      setFighterPortalAccount(data);

      setFighterPortalForm({
        login_email:
          data.login_email ||
          data.fighter_email ||
          fighter.email ||
          "",
        password: "",
        active: data.portal_account_exists
          ? Boolean(data.active)
          : true,
      });
    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not load fighter portal account"
      );
    } finally {
      setFighterPortalLoading(false);
    }
  }


  async function saveFighterEdits() {
    if (!editFighterId) return;

    if (!editFighterForm.legal_name?.trim()) {
      setMsgType("warning");
      setMsg("Fighter name is required.");
      return;
    }

    setWorking(true);

    try {
      const payload = {
        ...editFighterForm,

        legal_name:
          editFighterForm.legal_name.trim(),

        boxrec_id:
          (editFighterForm.boxrec_id || "").trim(),

        height_in:
          numberOrNull(editFighterForm.height_in),

        reach_in:
          numberOrNull(editFighterForm.reach_in),

        walk_weight:
          numberOrNull(editFighterForm.walk_weight),

        fight_weight:
          numberOrNull(editFighterForm.fight_weight),

        available_weight_min:
          numberOrNull(
            editFighterForm.available_weight_min
          ),

        available_weight_max:
          numberOrNull(
            editFighterForm.available_weight_max
          ),
      };

      const response = await fetch(
        `${API}/api/boxing/fighters/${editFighterId}`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(payload),
        }
      );

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not update fighter"
        );
      }

      setEditFighterOpen(false);
      setEditFighterId("");
      setEditFighterForm(emptyFighter);

      setMsgType("success");
      setMsg(
        `${data.legal_name || payload.legal_name} updated.`
      );

      await load();

      if (
        fighterId &&
        Number(fighterId) === Number(data.id)
      ) {
        setResult(null);
      }
    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message || "Could not update fighter"
      );
    } finally {
      setWorking(false);
    }
  }


  async function saveFighterPortalAccount() {
    if (!editFighterId) return;

    const loginEmail =
      (fighterPortalForm.login_email || "").trim().toLowerCase();

    if (!loginEmail || !loginEmail.includes("@")) {
      setMsgType("warning");
      setMsg("Enter a valid fighter portal login email.");
      return;
    }

    if (
      !fighterPortalAccount?.portal_account_exists &&
      !(fighterPortalForm.password || "").trim()
    ) {
      setMsgType("warning");
      setMsg(
        "Enter a password to create fighter portal access."
      );
      return;
    }

    if (
      fighterPortalForm.password &&
      fighterPortalForm.password.length < 8
    ) {
      setMsgType("warning");
      setMsg("Portal password must be at least 8 characters.");
      return;
    }

    setFighterPortalLoading(true);

    try {
      const payload = {
        login_email: loginEmail,
        active: Boolean(fighterPortalForm.active),
      };

      if (fighterPortalForm.password) {
        payload.password = fighterPortalForm.password;
      }

      const response = await fetch(
        `${API}/api/fighter/admin/fighters/${editFighterId}/portal-account`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify(payload),
        }
      );

      const data = await readJson(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Could not update fighter portal login"
        );
      }

      setFighterPortalAccount({
        ...(fighterPortalAccount || {}),
        portal_account_exists: true,
        user_id: data.user_id,
        login_email: data.login_email,
        active: Boolean(data.active),
      });

      setFighterPortalForm({
        login_email: data.login_email || loginEmail,
        password: "",
        active: Boolean(data.active),
      });

      setMsgType("success");
      setMsg("Fighter portal login updated.");

      await loadFighterInviteStatus(editFighterId);
    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message ||
        "Could not update fighter portal login"
      );
    } finally {
      setFighterPortalLoading(false);
    }
  }


  async function createEvent() {
    if (!eventForm.name.trim()) {
      setMsgType("warning");
      setMsg("Event name is required.");
      return;
    }

    setWorking(true);
    try {
      const payload = {
        ...eventForm,
        name: eventForm.name.trim(),
        slug: (eventForm.slug || slugify(eventForm.name)).trim(),
      };

      const r = await fetch(`${API}/api/boxing/events`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Could not add event");

      setEventForm(emptyEvent);
      setEventOpen(false);
      setMsgType("success");
      setMsg(`${payload.name} added.`);
      await load();
      if (d.id) setEventId(d.id);
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not add event");
    } finally {
      setWorking(false);
    }
  }

  async function findSocials() {
    if (!fighterId) {
      setMsgType("warning");
      setMsg("Select a fighter first.");
      return;
    }

    const fighter = fighters.find(
      (row) => Number(row.id) === Number(fighterId)
    );

    setSocialFighter(fighter || null);
    setSocialResults([]);
    setSocialError("");
    setSocialOpen(true);
    setSocialLoading(true);

    try {
      const response = await fetch(
        `${API}/api/boxing/fighters/${fighterId}/find-socials`,
        {
          method: "POST",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
        }
      );

      const responseText = await response.text();

      let body = {};

      try {
        body = responseText
          ? JSON.parse(responseText)
          : {};
      } catch {
        throw new Error(
          `Social search returned HTTP ${response.status} instead of JSON. ` +
          `Response: ${responseText.slice(0, 180)}`
        );
      }

      if (!response.ok) {
        throw new Error(
          body.detail ||
          `Social search failed with HTTP ${response.status}`
        );
      }

      setSocialFighter(body.fighter || fighter);

      setSocialResults(
        Array.isArray(body.candidates)
          ? body.candidates
          : []
      );

    } catch (error) {
      const message =
        error.message ||
        "Could not search fighter social media";

      setSocialError(message);
      setMsgType("error");
      setMsg(message);
    } finally {
      setSocialLoading(false);
    }
  }


  async function saveSocialCandidate(candidate) {
    if (!socialFighter?.id) return;

    try {
      const response = await fetch(
        `${API}/api/boxing/fighters/${socialFighter.id}/socials`,
        {
          method: "PATCH",
          headers: authHeaders({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            [candidate.platform]: candidate.url,
          }),
        }
      );

      const body = await response.json();

      if (!response.ok) {
        throw new Error(
          body.detail || "Could not save social profile"
        );
      }

      setFighters((old) =>
        old.map((row) =>
          Number(row.id) === Number(body.id)
            ? { ...row, ...body }
            : row
        )
      );

      setSocialFighter(body);

      setMsgType("success");
      setMsg(
        `${candidate.platform} saved for ${body.legal_name}.`
      );

    } catch (error) {
      setMsgType("error");
      setMsg(
        error.message || "Could not save social profile"
      );
    }
  }


  async function findMatches(targetFighterId = fighterId) {
    // React onClick can pass a MouseEvent when a function is used directly.
    // Only accept a numeric/string fighter ID here.
    if (
      targetFighterId &&
      typeof targetFighterId === "object"
    ) {
      targetFighterId = fighterId;
    }

    if (!targetFighterId) {
      // Instead of warning that the fighter must already exist,
      // immediately open Add Fighter.
      setFighterOpen(true);
      return;
    }

    setWorking(true);
    setMsg("");
    try {
      const resolvedFighterId = Number(targetFighterId);

      if (!Number.isInteger(resolvedFighterId) || resolvedFighterId <= 0) {
        throw new Error("A valid fighter must be selected before finding opponents.");
      }

      const q = eventId ? `?event_id=${eventId}` : "";
      const r = await fetch(`${API}/api/boxing/match/${resolvedFighterId}${q}`, {
        headers: authHeaders(),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Matchmaking failed");

      setResult(d);
      setMsgType("success");
      setMsg(`Found ${d.matches?.length || 0} ranked opponent options.`);
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Matchmaking failed");
    } finally {
      setWorking(false);
    }
  }

  async function buildBout(match) {
    if (!eventId) {
      setMsgType("warning");
      setMsg("Choose an event before building a bout.");
      return;
    }

    setWorking(true);
    try {
      const payload = {
        event_id: Number(eventId),
        red_fighter_id: Number(fighterId),
        blue_fighter_id: match.fighter.id,
        weight_agreed: result?.fighter?.fight_weight || match.fighter.fight_weight || null,
        rounds: 4,
        bout_type: "pro",
        red_purse: 0,
        blue_purse: 0,
        match_score: match.score,
        notes: `TNG Matchmaker ${match.score}% recommendation`,
      };

      const r = await fetch(`${API}/api/boxing/bouts`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      });
      const d = await readJson(r);

      if (!r.ok) throw new Error(d.detail || "Could not build bout");

      setMsgType("success");
      setMsg(`Bout #${d.id} created as a draft.`);
      await findMatches();
    } catch (e) {
      setMsgType("error");
      setMsg(e.message || "Could not build bout");
    } finally {
      setWorking(false);
    }
  }

  const eligible = useMemo(
    () => fighters.filter((f) => f.eligible).length,
    [fighters]
  );

  if (eventWorkspaceId) {
    return (
      <EventWorkspace
        eventId={eventWorkspaceId}
        onBack={() => setEventWorkspaceId("")}
      />
    );
  }

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>

      <Stack spacing={2}>
        {msg && <Alert severity={msgType}>{msg}</Alert>}

        {promoterPage === "home" && (
          <Box>
            <Card
              sx={{
                mb: 3,
                borderRadius: 4,
                overflow: "hidden",
                border: "1px solid",
                borderColor: "divider",
                background:
                  "linear-gradient(135deg, #111 0%, #222 68%, #400b0f 100%)",
                color: "#fff",
                boxShadow: "0 18px 50px rgba(0,0,0,.12)",
              }}
            >
              <CardContent sx={{ p: { xs: 3, md: 4 } }}>
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  justifyContent="space-between"
                  alignItems={{ xs: "flex-start", md: "center" }}
                  spacing={3}
                >
                  <Box>
                    <Chip
                      label="TNG PROMOTER OS"
                      size="small"
                      sx={{
                        bgcolor: "rgba(255,255,255,.10)",
                        color: "#fff",
                        fontWeight: 900,
                        mb: 1.5,
                      }}
                    />

                    <Typography
                      variant="h3"
                      fontWeight={950}
                      sx={{
                        fontSize: { xs: 30, md: 44 },
                        letterSpacing: "-0.04em",
                      }}
                    >
                      Promoter Command Center
                    </Typography>

                    <Typography
                      sx={{
                        mt: 1,
                        maxWidth: 720,
                        color: "rgba(255,255,255,.72)",
                      }}
                    >
                      Run your boxing operation from one place. Open events,
                      manage fighters, build matchups, and move each promotion
                      toward fight night.
                    </Typography>
                  </Box>

                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<AddRoundedIcon />}
                    onClick={() => setEventOpen(true)}
                    sx={{
                      borderRadius: 2.5,
                      px: 2.5,
                      py: 1.25,
                      fontWeight: 900,
                      whiteSpace: "nowrap",
                    }}
                  >
                    Create Event
                  </Button>
                </Stack>
              </CardContent>
            </Card>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              {[
                {
                  title: "Events",
                  description:
                    "Open an event and manage the fight card, contracts, tickets, compliance, revenue, and fight night.",
                  icon: <EventRoundedIcon />,
                  action: () => {
                    setPromoterPage("events");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  },
                },
                {
                  title: "Fighter Pool",
                  description:
                    "Manage your roster, fighter logins, signed talent, First 5 fighters, and matchmaking readiness.",
                  icon: <GroupsRoundedIcon />,
                  action: () => {
                    setResult(null);
                    setPromoterPage("fighter-pool");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  },
                },
                {
                  title: "Matchmaking",
                  description:
                    "Select a fighter, rank opponents, and build bouts for an event.",
                  icon: <SportsMmaRoundedIcon />,
                  action: () => {
                    setResult(null);
                    setSocialOpen(false);
                    setPromoterPage("matchmaking");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  },
                },
                {
                  title: "Event Operations",
                  description:
                    "Move from planning to contracts, medicals, tickets, revenue, compliance, and fight night.",
                  icon: <HubRoundedIcon />,
                  action: () => {
                    setPromoterPage("events");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  },
                },
              ].map((item) => (
                <Grid item xs={12} sm={6} lg={3} key={item.title}>
                  <Card
                    onClick={item.action}
                    sx={{
                      height: "100%",
                      cursor: "pointer",
                      borderRadius: 3.5,
                      border: "1px solid",
                      borderColor: "divider",
                      boxShadow: "0 4px 18px rgba(0,0,0,.04)",
                      transition:
                        "transform .18s ease, box-shadow .18s ease, border-color .18s ease",
                      "&:hover": {
                        transform: "translateY(-4px)",
                        boxShadow: "0 18px 42px rgba(0,0,0,.09)",
                        borderColor: "rgba(215,25,32,.35)",
                      },
                    }}
                  >
                    <CardContent
                      sx={{
                        p: 2.5,
                        minHeight: 205,
                        display: "flex",
                        flexDirection: "column",
                      }}
                    >
                      <Box
                        sx={{
                          width: 48,
                          height: 48,
                          display: "grid",
                          placeItems: "center",
                          borderRadius: 2.5,
                          bgcolor: "rgba(215,25,32,.08)",
                          color: "#d71920",
                          mb: 2,
                        }}
                      >
                        {item.icon}
                      </Box>

                      <Typography variant="h6" fontWeight={950}>
                        {item.title}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{ mt: 0.75, flex: 1 }}
                      >
                        {item.description}
                      </Typography>

                      <Stack
                        direction="row"
                        alignItems="center"
                        spacing={0.25}
                        sx={{ mt: 2, color: "#d71920" }}
                      >
                        <Typography variant="body2" fontWeight={900}>
                          Open
                        </Typography>
                        <ChevronRightRoundedIcon fontSize="small" />
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>

            <Card
              variant="outlined"
              sx={{
                mb: 3,
                borderRadius: 3,
                bgcolor: "rgba(215,25,32,.025)",
              }}
            >
              <CardContent>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  justifyContent="space-between"
                  alignItems={{ xs: "stretch", sm: "center" }}
                  spacing={2}
                >
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Box
                      sx={{
                        width: 42,
                        height: 42,
                        borderRadius: 2,
                        bgcolor: "rgba(215,25,32,.08)",
                        color: "#d71920",
                        display: "grid",
                        placeItems: "center",
                      }}
                    >
                      <BoltRoundedIcon />
                    </Box>

                    <Box>
                      <Typography fontWeight={900}>
                        Fighter Registration
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Send your public registration link to fighters,
                        managers, and coaches.
                      </Typography>
                    </Box>
                  </Stack>

                  <Button
                    variant="outlined"
                    startIcon={<ContentCopyRoundedIcon />}
                    onClick={copyFighterRegistrationLink}
                    sx={{ fontWeight: 850 }}
                  >
                    Copy Registration Link
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          </Box>
        )}



        {promoterPage === "events" && (
          <Box>
            <Stack
              direction={{ xs: "column", md: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "stretch", md: "center" }}
              spacing={2}
              sx={{ mb: 3 }}
            >
              <Box>
                <Button
                  startIcon={<ArrowBackRoundedIcon />}
                  onClick={() => {
                    setPromoterPage("home");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  sx={{
                    px: 0,
                    mb: 1,
                    color: "text.secondary",
                    fontWeight: 850,
                  }}
                >
                  Promoter Home
                </Button>

                <Typography
                  variant="h3"
                  fontWeight={950}
                  sx={{
                    fontSize: { xs: 30, md: 40 },
                    letterSpacing: "-0.04em",
                  }}
                >
                  Events
                </Typography>

                <Typography
                  color="text.secondary"
                  sx={{ mt: 0.5, maxWidth: 720 }}
                >
                  Create promotions and open each event workspace to manage
                  the fight card, contracts, fighters, medicals, compliance,
                  tickets, revenue, expenses, and fight night.
                </Typography>
              </Box>

              <Button
                variant="contained"
                color="error"
                startIcon={<AddRoundedIcon />}
                onClick={() => setEventOpen(true)}
                sx={{
                  fontWeight: 900,
                  px: 2.5,
                  py: 1.15,
                  borderRadius: 2.5,
                }}
              >
                Create Event
              </Button>
            </Stack>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Total Events
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {events.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Dates Scheduled
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {
                        events.filter(
                          (event) => Boolean(event.event_date)
                        ).length
                      }
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Venues Assigned
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {
                        events.filter(
                          (event) => Boolean(event.venue)
                        ).length
                      }
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {!events.length ? (
              <Card
                sx={{
                  borderRadius: 3.5,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <CardContent
                  sx={{
                    textAlign: "center",
                    py: { xs: 5, md: 7 },
                  }}
                >
                  <EventRoundedIcon
                    sx={{
                      fontSize: 58,
                      color: "#d71920",
                      mb: 1.5,
                    }}
                  />

                  <Typography variant="h5" fontWeight={950}>
                    No events yet
                  </Typography>

                  <Typography
                    color="text.secondary"
                    sx={{ mt: 0.75, mb: 2.5 }}
                  >
                    Create your first promotion to start building the
                    fight card and event workflow.
                  </Typography>

                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<AddRoundedIcon />}
                    onClick={() => setEventOpen(true)}
                    sx={{ fontWeight: 900 }}
                  >
                    Create First Event
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <Grid container spacing={2}>
                {events.map((event) => (
                  <Grid
                    item
                    xs={12}
                    md={6}
                    lg={4}
                    key={event.id}
                  >
                    <Card
                      sx={{
                        height: "100%",
                        borderRadius: 3.5,
                        border: "1px solid",
                        borderColor: "divider",
                        boxShadow: "0 5px 20px rgba(0,0,0,.045)",
                        transition:
                          "transform .18s ease, box-shadow .18s ease, border-color .18s ease",
                        "&:hover": {
                          transform: "translateY(-3px)",
                          boxShadow:
                            "0 18px 42px rgba(0,0,0,.09)",
                          borderColor:
                            "rgba(215,25,32,.35)",
                        },
                      }}
                    >
                      <CardContent
                        sx={{
                          p: 2.5,
                          height: "100%",
                          display: "flex",
                          flexDirection: "column",
                        }}
                      >
                        <Stack
                          direction="row"
                          justifyContent="space-between"
                          alignItems="flex-start"
                          spacing={1}
                        >
                          <Box
                            sx={{
                              width: 46,
                              height: 46,
                              borderRadius: 2.5,
                              display: "grid",
                              placeItems: "center",
                              bgcolor: "rgba(215,25,32,.08)",
                              color: "#d71920",
                              flexShrink: 0,
                            }}
                          >
                            <EventRoundedIcon />
                          </Box>

                          <Chip
                            size="small"
                            variant="outlined"
                            label={
                              (event.status || "planning")
                                .replaceAll("_", " ")
                                .replace(/\b\w/g, (char) =>
                                  char.toUpperCase()
                                )
                            }
                            sx={{ fontWeight: 800 }}
                          />
                        </Stack>

                        <Typography
                          variant="h5"
                          fontWeight={950}
                          sx={{
                            mt: 2,
                            lineHeight: 1.15,
                          }}
                        >
                          {event.name}
                        </Typography>

                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ mt: 1 }}
                        >
                          {event.event_date || "Date not set"}
                        </Typography>

                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ mt: 0.4 }}
                        >
                          {event.venue || "Venue not set"}
                        </Typography>

                        {event.venue_address && (
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ mt: 0.4 }}
                          >
                            {event.venue_address}
                          </Typography>
                        )}

                        <Box sx={{ flex: 1, minHeight: 24 }} />

                        <Button
                          fullWidth
                          variant="contained"
                          color="error"
                          endIcon={<ChevronRightRoundedIcon />}
                          onClick={() => {
                            setEventId(event.id);
                            setResult(null);
                            setEventWorkspaceId(event.id);
                          }}
                          sx={{
                            mt: 2.5,
                            borderRadius: 2.5,
                            fontWeight: 900,
                          }}
                        >
                          Open Event
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        )}

        {promoterPage === "matchmaking" && (
          <Box>
            <Stack
              direction={{ xs: "column", md: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "stretch", md: "center" }}
              spacing={2}
              sx={{ mb: 3 }}
            >
              <Box>
                <Button
                  startIcon={<ArrowBackRoundedIcon />}
                  onClick={() => {
                    setResult(null);
                    setSocialOpen(false);
                    setPromoterPage("home");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  sx={{
                    px: 0,
                    mb: 1,
                    color: "text.secondary",
                    fontWeight: 850,
                  }}
                >
                  Promoter Home
                </Button>

                <Typography
                  variant="h3"
                  fontWeight={950}
                  sx={{
                    fontSize: { xs: 30, md: 40 },
                    letterSpacing: "-0.04em",
                  }}
                >
                  Matchmaking
                </Typography>

                <Typography
                  color="text.secondary"
                  sx={{ mt: 0.5, maxWidth: 720 }}
                >
                  Select a fighter and event, review possible opponents,
                  verify fighter information, and build the bout when the
                  matchup is ready.
                </Typography>
              </Box>

              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
              >
                <Button
                  variant="outlined"
                  startIcon={<GroupsRoundedIcon />}
                  onClick={() => {
                    setResult(null);
                    setSocialOpen(false);
                    setPromoterPage("fighter-pool");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  sx={{ fontWeight: 850 }}
                >
                  Fighter Pool
                </Button>

                <Button
                  variant="contained"
                  color="error"
                  startIcon={<AddRoundedIcon />}
                  onClick={() => setFighterOpen(true)}
                  sx={{ fontWeight: 900 }}
                >
                  Add Fighter
                </Button>
              </Stack>
            </Stack>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Available Fighters
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {fighters.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

            <Card
              sx={{
                mb: 3,
                borderRadius: 3.5,
                border: "1px solid",
                borderColor: "divider",
                overflow: "hidden",
              }}
            >
              <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
                <Stack spacing={0.75} sx={{ mb: 2 }}>
                  <Typography variant="h5" fontWeight={950}>
                    Auto Match
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Generate proposed matchups for an event, review the card,
                    and move approved matchups into the fight workflow.
                  </Typography>
                </Stack>

                <AutoMatchPlanner
                  events={events}
                />
              </CardContent>
            </Card>

              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Match Ready
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {eligible}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Events
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {events.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

        <Card
          id="promoter-matchmaking"
          sx={{ scrollMarginTop: 24, borderRadius: 3 }}
        >
          <CardContent>
            <Typography variant="h6" fontWeight={900} sx={{ mb: 2 }}>
              Find a Match
            </Typography>

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <Autocomplete
                fullWidth
                options={fighters}
                value={
                  fighters.find(
                    (f) =>
                      Number(f.id) === Number(fighterId)
                  ) || null
                }
                getOptionLabel={(f) =>
                  `${f.legal_name || ""} — ${
                    f.fight_weight || "?"
                  } lb — ${
                    f.pro_record || "record N/A"
                  }`
                }
                isOptionEqualToValue={(option, value) =>
                  Number(option.id) === Number(value.id)
                }
                onChange={(event, value) => {
                  setFighterId(value ? value.id : "");
                  setResult(null);
                }}
                filterOptions={(options, state) => {
                  const search =
                    state.inputValue
                      .toLowerCase()
                      .trim();

                  if (!search) return options;

                  return options.filter((f) =>
                    [
                      f.legal_name,
                      f.pro_record,
                      f.gym,
                      f.city,
                      f.state,
                      f.boxrec_id,
                    ]
                      .filter(Boolean)
                      .join(" ")
                      .toLowerCase()
                      .includes(search)
                  );
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Search Fighter"
                    placeholder="Type fighter name..."
                  />
                )}
              />

              <FormControl fullWidth>
                <InputLabel>Event</InputLabel>
                <Select
                  value={eventId}
                  label="Event"
                  onChange={(e) => setEventId(e.target.value)}
                >
                  <MenuItem value="">Any / not assigned</MenuItem>
                  {events.map((e) => (
                    <MenuItem key={e.id} value={e.id}>
                      {e.event_date || "No date"} — {e.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="outlined"
                disabled={!eventId}
                onClick={() => setEventWorkspaceId(eventId)}
                sx={{ minWidth: 130 }}
              >
                Open Event
              </Button>

                            <Button
                variant="outlined"
                disabled={!fighterId || working}
                onClick={findSocials}
                sx={{ minWidth: 150 }}
              >
                Find Socials
              </Button>

<Button
                variant="contained"
                startIcon={<SportsMmaRoundedIcon />}
                disabled={!fighterId || working}
                onClick={() => findMatches()}
                sx={{ minWidth: 190, bgcolor: "#e31b23" }}
              >
                Find Opponents
              </Button>
            </Stack>

            {socialOpen && (
              <Card
                variant="outlined"
                sx={{
                  mt: 2,
                  borderColor: "divider",
                }}
              >
                <CardContent>
                  <Stack spacing={2}>

                    <Box>
                      <Typography
                        variant="h6"
                        fontWeight={950}
                      >
                        Fighter Social Media Results
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        {socialFighter?.legal_name ||
                          "Selected fighter"}
                      </Typography>
                    </Box>

                    {socialError && (
                      <Alert severity="error">
                        {socialError}
                      </Alert>
                    )}

                    {socialLoading && (
                      <Stack
                        direction="row"
                        spacing={2}
                        alignItems="center"
                        sx={{ py: 2 }}
                      >
                        <CircularProgress size={26} />

                        <Typography>
                          Searching public social media profiles...
                        </Typography>
                      </Stack>
                    )}

                    {!socialLoading &&
                      !socialError &&
                      socialResults.length === 0 && (
                        <Alert severity="info">
                          No strong public social media matches
                          were found for this fighter.
                        </Alert>
                      )}

                    {!socialLoading &&
                      socialResults.map(
                        (candidate, index) => (
                          <Card
                            key={`${candidate.platform}-${candidate.url}-${index}`}
                            variant="outlined"
                          >
                            <CardContent>
                              <Stack spacing={1.5}>
                                <Stack
                                  direction={{
                                    xs: "column",
                                    sm: "row",
                                  }}
                                  spacing={1}
                                  justifyContent="space-between"
                                  alignItems={{
                                    xs: "flex-start",
                                    sm: "center",
                                  }}
                                >
                                  <Box>
                                    <Typography
                                      fontWeight={950}
                                      sx={{
                                        textTransform:
                                          "capitalize",
                                      }}
                                    >
                                      {candidate.platform}
                                    </Typography>

                                    <Typography>
                                      {candidate.handle ||
                                        candidate.url}
                                    </Typography>
                                  </Box>

                                  <Chip
                                    label={`${
                                      candidate.confidence || 0
                                    }% confidence`}
                                    color={
                                      Number(
                                        candidate.confidence
                                      ) >= 85
                                        ? "success"
                                        : Number(
                                            candidate.confidence
                                          ) >= 65
                                        ? "warning"
                                        : "default"
                                    }
                                  />
                                </Stack>

                                {candidate.reason && (
                                  <Typography
                                    variant="body2"
                                    color="text.secondary"
                                  >
                                    {candidate.reason}
                                  </Typography>
                                )}

                                <Typography
                                  variant="caption"
                                  sx={{
                                    overflowWrap: "anywhere",
                                  }}
                                >
                                  {candidate.url}
                                </Typography>

                                <Stack
                                  direction={{
                                    xs: "column",
                                    sm: "row",
                                  }}
                                  spacing={1}
                                >
                                  <Button
                                    variant="outlined"
                                    onClick={() =>
                                      window.open(
                                        candidate.url,
                                        "_blank",
                                        "noopener,noreferrer"
                                      )
                                    }
                                  >
                                    View Profile
                                  </Button>

                                  <Button
                                    variant="contained"
                                    onClick={() =>
                                      saveSocialCandidate(
                                        candidate
                                      )
                                    }
                                  >
                                    Confirm & Save
                                  </Button>
                                </Stack>
                              </Stack>
                            </CardContent>
                          </Card>
                        )
                      )}

                    {!socialLoading && (
                      <Stack
                        direction="row"
                        spacing={1}
                      >
                        <Button
                          variant="text"
                          onClick={findSocials}
                        >
                          Search Again
                        </Button>

                        <Button
                          variant="text"
                          onClick={() => {
                            setSocialOpen(false);
                            setSocialResults([]);
                            setSocialError("");
                          }}
                        >
                          Close Results
                        </Button>
                      </Stack>
                    )}

                  </Stack>
                </CardContent>
              </Card>
            )}

          </CardContent>
        </Card>

            <Box sx={{ mt: 3 }}>
        {result && (
          <>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="h6" fontWeight={900}>
                  Ranked Opponents for {result.fighter?.legal_name}
                </Typography>
                <Typography color="text.secondary">
                  Higher scores indicate closer competitive matches.
                </Typography>
              </Box>
              <Button
                variant="outlined"
                onClick={() => setResult(null)}
                sx={{ fontWeight: 850 }}
              >
                Clear Results
              </Button>
            </Stack>

            <TableContainer component={Card}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Rank</TableCell>
                    <TableCell>Match</TableCell>
                    <TableCell>Opponent</TableCell>
                    <TableCell>Weight</TableCell>
                    <TableCell>Record</TableCell>
                    <TableCell>Why</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(result.matches || []).map((m, i) => (
                    <TableRow key={m.fighter.id}>
                      <TableCell>#{i + 1}</TableCell>
                      <TableCell>
                        <Typography variant="h5" fontWeight={950}>{m.score}%</Typography>
                        <Typography variant="caption">{m.tier}</Typography>
                      </TableCell>
                      <TableCell>
                        <b>{m.fighter.legal_name}</b>
                        <Typography display="block" variant="caption">
                          {[m.fighter.gym, m.fighter.city, m.fighter.state]
                            .filter(Boolean)
                            .join(" • ")}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {m.fighter.fight_weight || "?"} lb
                        <br />
                        <Typography variant="caption">Δ {m.weight_diff} lb</Typography>
                      </TableCell>
                      <TableCell>{m.fighter.pro_record || "N/A"}</TableCell>
                      <TableCell>
                        <Stack direction="row" useFlexGap flexWrap="wrap" spacing={0.5}>
                          {(m.reasons || []).slice(0, 4).map((x) => (
                            <Chip key={x} size="small" label={x} />
                          ))}
                          {(m.warnings || []).map((x) => (
                            <Chip key={x} size="small" variant="outlined" label={`Review: ${x}`} />
                          ))}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="contained"
                          disabled={!eventId || working}
                          onClick={() => buildBout(m)}
                          sx={{ bgcolor: "#e31b23" }}
                        >
                          Build Bout
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}

                  {!result.matches?.length && (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        No eligible opponent matches found. Add more fighters or review eligibility.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
            </Box>
          </Box>
        )}

        {promoterPage === "fighter-pool" && (
          <Box>
            <Stack
              direction={{ xs: "column", md: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "stretch", md: "center" }}
              spacing={2}
              sx={{ mb: 3 }}
            >
              <Box>
                <Button
                  startIcon={<ArrowBackRoundedIcon />}
                  onClick={() => {
                    setResult(null);
                    setPromoterPage("home");
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  sx={{
                    px: 0,
                    mb: 1,
                    color: "text.secondary",
                    fontWeight: 850,
                  }}
                >
                  Promoter Home
                </Button>

                <Typography
                  variant="h3"
                  fontWeight={950}
                  sx={{
                    fontSize: { xs: 30, md: 40 },
                    letterSpacing: "-0.04em",
                  }}
                >
                  Fighter Pool
                </Typography>

                <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                  Manage your roster, portal access, signed talent,
                  development fighters, and matchmaking readiness.
                </Typography>
              </Box>

              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
              >
                <Button
                  variant="outlined"
                  startIcon={<ContentCopyRoundedIcon />}
                  onClick={copyFighterRegistrationLink}
                  sx={{ fontWeight: 850 }}
                >
                  Registration Link
                </Button>

                <Button
                  variant="contained"
                  color="error"
                  startIcon={<AddRoundedIcon />}
                  onClick={() => setFighterOpen(true)}
                  sx={{
                    fontWeight: 900,
                    px: 2.25,
                  }}
                >
                  Add Fighter
                </Button>
              </Stack>
            </Stack>

            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Total Fighters
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {fighters.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Match Ready
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {eligible}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Card sx={{ borderRadius: 3 }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      Signed to TNG
                    </Typography>
                    <Typography variant="h4" fontWeight={950}>
                      {signedFighters.length}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

        {!fighters.length && (
          <Card>
            <CardContent sx={{ textAlign: "center", py: 5 }}>
              <SportsMmaRoundedIcon sx={{ fontSize: 54, mb: 1 }} />
              <Typography variant="h5" fontWeight={900}>No fighters yet</Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                Add your first fighter to start using the Matchmaker.
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddRoundedIcon />}
                onClick={() => setFighterOpen(true)}
                sx={{ bgcolor: "#e31b23" }}
              >
                Add Fighter
              </Button>
            </CardContent>
          </Card>
        )}

        {!!fighters.length && !result && (
          <>
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={900}>Fighter Pool</Typography>
              <Typography color="text.secondary">
                Click a fighter to select them for matchmaking.
              </Typography>


              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={2}
                alignItems={{ sm: "center" }}
                sx={{ mt: 2 }}
              >
                <FormControl
                  size="small"
                  sx={{ minWidth: 260 }}
                >
                  <InputLabel>
                    Weight Division
                  </InputLabel>

                  <Select
                    value={weightDivision}
                    label="Weight Division"
                    onChange={(e) => {
                      setWeightDivision(
                        e.target.value
                      );
                      setResult(null);
                    }}
                  >
                    <MenuItem value="">
                      All Divisions
                    </MenuItem>

                    {WEIGHT_DIVISIONS.map(
                      (division) => (
                        <MenuItem
                          key={division.value}
                          value={division.value}
                        >
                          {division.label}
                        </MenuItem>
                      )
                    )}
                  </Select>
                </FormControl>

                <Typography
                  variant="body2"
                  color="text.secondary"
                >
                  Showing{" "}
                  <b>{filteredFighters.length}</b>
                  {" "}of{" "}
                  <b>{fighters.length}</b>
                  {" "}fighters
                </Typography>
              </Stack>


              <TicketSellerControls
                eventId={eventId}
                fighterId={fighterId}
              />

              <TableContainer sx={{ mt: 2 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Name</TableCell>
                      <TableCell>Weight</TableCell>
                      <TableCell>Record</TableCell>
                      <TableCell>Gym</TableCell>
                      <TableCell>Eligibility</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredFighters.map((f) => (
                      <TableRow
                        hover
                        key={f.id}
                        selected={Number(fighterId) === Number(f.id)}
                        onClick={() => {
                          setFighterId(f.id);
                          setResult(null);
                        }}
                        sx={{ cursor: "pointer" }}
                      >
                        <TableCell><b>{f.legal_name}</b></TableCell>
                        <TableCell>{f.fight_weight || "—"}</TableCell>
                        <TableCell>{f.pro_record || "—"}</TableCell>
                        <TableCell>{f.gym || "—"}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={f.eligible ? "Eligible" : "Needs review"}
                            color={f.eligible ? "success" : "default"}
                          />
                        </TableCell>

                        <TableCell align="right">
                          <Stack
                            direction="row"
                            spacing={1}
                            justifyContent="flex-end"
                          >
                            <Button
                              size="small"
                              variant={
                                fighterInviteStatus[f.id]?.activated
                                  ? "contained"
                                  : "outlined"
                              }
                              color={
                                fighterInviteStatus[f.id]?.activated
                                  ? "success"
                                  : "primary"
                              }
                              disabled={
                                fighterInviteLoading[f.id] ||
                                (
                                  !fighterInviteStatus[f.id]?.activated &&
                                  !(f.email || "").trim()
                                )
                              }
                              onClick={(e) => {
                                e.stopPropagation();

                                if (
                                  fighterInviteStatus[f.id]?.activated
                                ) {
                                  previewFighterPortal(f);
                                } else {
                                  inviteFighterLogin(f);
                                }
                              }}
                            >
                              {fighterInviteLoading[f.id]
                                ? "Sending..."
                                : !(f.email || "").trim()
                                  ? "Email Required"
                                  : fighterInviteStatus[f.id]?.activated
                                    ? "Login as Fighter"
                                    : fighterInviteStatus[f.id]?.invite_pending
                                      ? "Resend Invite"
                                      : "Activate Login"}
                            </Button>

                            <Button
                              size="small"
                              variant="outlined"
                              onClick={(e) => {
                                e.stopPropagation();
                                openEditFighter(f);
                              }}
                            >
                              Edit
                            </Button>

                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteFighterFromPool(f);
                              }}
                            >
                              Delete
                            </Button>
                          </Stack>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

        <Card
          sx={{
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          
        <Card
          sx={{
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <CardContent>
            <Stack spacing={2}>

              <Stack
                direction={{
                  xs: "column",
                  md: "row",
                }}
                justifyContent="space-between"
                spacing={1}
              >
                <Box>
                  <Typography
                    variant="h5"
                    fontWeight={950}
                  >
                    SIGNED FIGHTERS
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                  >
                    Fighters currently signed to a
                    TNG developmental series.
                  </Typography>
                </Box>

                <Chip
                  label={`${seriesFighters.length} Signed`}
                  color="primary"
                  variant="outlined"
                />
              </Stack>

              <Divider />

              {seriesFighters.length === 0 ? (
                <Alert severity="info">
                  No signed fighters yet. Add a fighter
                  to the First 5 Fights Series below.
                </Alert>
              ) : (
                <TableContainer>
                  <Table size="small">

                    <TableHead>
                      <TableRow>
                        <TableCell>
                          Fighter
                        </TableCell>

                        <TableCell>
                          Record
                        </TableCell>

                        <TableCell>
                          Weight
                        </TableCell>

                        <TableCell>
                          Series
                        </TableCell>

                        <TableCell>
                          Progress
                        </TableCell>

                        <TableCell>
                          Signed
                        </TableCell>

                        <TableCell>
                          Status
                        </TableCell>
                      </TableRow>
                    </TableHead>

                    <TableBody>
                      {seriesFighters.map((row) => {
                        const fighter =
                          row.fighter || {};

                        const completed =
                          Number(
                            row.fights_completed || 0
                          );

                        const target =
                          Number(
                            row.target_fights || 5
                          );

                        return (
                          <TableRow
                            key={`signed-${row.id}`}
                            hover
                            sx={{
                              cursor: "pointer",
                            }}
                            onClick={() => {
                              if (fighter.id) {
                                setFighterId(
                                  fighter.id
                                );

                                setResult(null);
                              }
                            }}
                          >
                            <TableCell>
                              <Typography
                                fontWeight={900}
                              >
                                {fighter.legal_name ||
                                  "Unnamed Fighter"}
                              </Typography>

                              {fighter.boxrec_id && (
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  BoxRec #
                                  {fighter.boxrec_id}
                                </Typography>
                              )}
                            </TableCell>

                            <TableCell>
                              {fighter.pro_record ||
                                "N/A"}
                            </TableCell>

                            <TableCell>
                              {fighter.fight_weight
                                ? `${fighter.fight_weight} lb`
                                : fighter.preferred_weight
                                ? `${fighter.preferred_weight} lb`
                                : "N/A"}
                            </TableCell>

                            <TableCell>
                              First 5 Fights
                            </TableCell>

                            <TableCell>
                              <Chip
                                size="small"
                                color={
                                  completed >= target
                                    ? "success"
                                    : "primary"
                                }
                                label={
                                  completed >= target
                                    ? "Graduated"
                                    : `${completed} of ${target}`
                                }
                              />
                            </TableCell>

                            <TableCell>
                              {row.signed_date ||
                                "—"}
                            </TableCell>

                            <TableCell>
                              <Chip
                                size="small"
                                variant="outlined"
                                label={
                                  (
                                    row.status ||
                                    "active"
                                  )
                                    .charAt(0)
                                    .toUpperCase() +
                                  (
                                    row.status ||
                                    "active"
                                  ).slice(1)
                                }
                              />
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>

                  </Table>
                </TableContainer>
              )}

            </Stack>
          </CardContent>
        </Card>


        <Card
          sx={{
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <CardContent>
            <Stack spacing={2}>

              <Stack
                direction={{
                  xs: "column",
                  md: "row",
                }}
                justifyContent="space-between"
                spacing={1}
              >
                <Box>
                  <Typography
                    variant="h5"
                    fontWeight={950}
                  >
                    SIGNED FIGHTERS
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                  >
                    Fighters signed directly to TNG.
                    First 5 Fights Series membership
                    is separate.
                  </Typography>
                </Box>

                <Chip
                  label={`${signedFighters.length} Signed`}
                  color="primary"
                  variant="outlined"
                />
              </Stack>

              <Stack
                direction={{
                  xs: "column",
                  md: "row",
                }}
                spacing={1.5}
              >
                <Autocomplete
                  fullWidth
                  options={fighters.filter(
                    (fighter) =>
                      !signedFighters.some(
                        (row) =>
                          Number(row.fighter_id) ===
                          Number(fighter.id)
                      )
                  )}
                  value={
                    fighters.find(
                      (fighter) =>
                        Number(fighter.id) ===
                        Number(signedFighterId)
                    ) || null
                  }
                  getOptionLabel={(fighter) =>
                    `${fighter.legal_name || ""} — ${
                      fighter.pro_record ||
                      "record N/A"
                    }`
                  }
                  isOptionEqualToValue={(option, value) =>
                    Number(option.id) ===
                    Number(value.id)
                  }
                  onChange={(event, value) =>
                    setSignedFighterId(
                      value ? value.id : ""
                    )
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Select Fighter to Sign"
                      placeholder="Search fighter pool..."
                    />
                  )}
                />

                <Button
                  variant="contained"
                  disabled={
                    !signedFighterId ||
                    signedLoading
                  }
                  onClick={signSelectedFighter}
                  sx={{ minWidth: 170 }}
                >
                  {signedLoading
                    ? "Signing..."
                    : "Sign Fighter"}
                </Button>
              </Stack>

              <Divider />

              {!signedFighters.length ? (
                <Alert severity="info">
                  No fighters are currently signed
                  directly to TNG.
                </Alert>
              ) : (
                <Stack spacing={1}>
                  {signedFighters.map((row) => {
                    const fighter =
                      row.fighter || {};

                    return (
                      <Card
                        key={`signed-${row.id}`}
                        variant="outlined"
                      >
                        <CardContent>
                          <Stack
                            direction={{
                              xs: "column",
                              md: "row",
                            }}
                            justifyContent="space-between"
                            alignItems={{
                              xs: "flex-start",
                              md: "center",
                            }}
                            spacing={1}
                          >
                            <Box>
                              <Typography
                                fontWeight={900}
                              >
                                {fighter.legal_name ||
                                  "Unnamed Fighter"}
                              </Typography>

                              <Typography
                                variant="body2"
                                color="text.secondary"
                              >
                                {fighter.pro_record ||
                                  "Record N/A"}
                                {" • "}
                                Signed:{" "}
                                {row.signed_date || "—"}
                              </Typography>
                            </Box>

                            <Stack
                              direction="row"
                              spacing={1}
                            >
                              <Chip
                                size="small"
                                label={
                                  row.status ||
                                  "active"
                                }
                              />

                              <Button
                                size="small"
                                color="error"
                                onClick={() =>
                                  removeSignedFighter(row)
                                }
                              >
                                Remove
                              </Button>
                            </Stack>
                          </Stack>
                        </CardContent>
                      </Card>
                    );
                  })}
                </Stack>
              )}

            </Stack>
          </CardContent>
        </Card>


<CardContent>
            <Stack spacing={2.5}>

              <Box>
                <Typography
                  variant="h5"
                  fontWeight={950}
                >
                  FIRST 5 FIGHTS SERIES
                </Typography>

                <Typography
                  variant="body2"
                  color="text.secondary"
                >
                  The Next Generation developmental
                  fighter program.
                </Typography>
              </Box>

              <Stack
                direction={{
                  xs: "column",
                  md: "row",
                }}
                spacing={1.5}
              >
                <Autocomplete
                  fullWidth
                  options={fighters.filter(
                    (fighter) =>
                      !seriesFighters.some(
                        (row) =>
                          Number(row.fighter_id) ===
                          Number(fighter.id)
                      )
                  )}
                  value={
                    fighters.find(
                      (fighter) =>
                        Number(fighter.id) ===
                        Number(seriesFighterId)
                    ) || null
                  }
                  getOptionLabel={(fighter) =>
                    `${fighter.legal_name || ""} — ${
                      fighter.pro_record || "record N/A"
                    } — ${
                      fighter.fight_weight || "?"
                    } lb`
                  }
                  isOptionEqualToValue={(option, value) =>
                    Number(option.id) === Number(value.id)
                  }
                  onChange={(event, value) =>
                    setSeriesFighterId(
                      value ? value.id : ""
                    )
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Add Fighter to First 5"
                      placeholder="Search fighter pool..."
                    />
                  )}
                />

                <Button
                  variant="contained"
                  disabled={
                    !seriesFighterId ||
                    seriesLoading
                  }
                  onClick={addToFirstFive}
                  sx={{ minWidth: 180 }}
                >
                  {seriesLoading
                    ? "Adding..."
                    : "Add to Series"}
                </Button>
              </Stack>

              <Divider />

              {seriesFighters.length === 0 && (
                <Alert severity="info">
                  No fighters are currently in the
                  First 5 Fights Series.
                </Alert>
              )}

              {seriesFighters.map((row) => {
                const fighter =
                  row.fighter || {};

                const completed =
                  Number(
                    row.fights_completed || 0
                  );

                const target =
                  Number(
                    row.target_fights || 5
                  );

                return (
                  <Card
                    key={row.id}
                    variant="outlined"
                  >
                    <CardContent>
                      <Stack spacing={2}>

                        <Stack
                          direction={{
                            xs: "column",
                            md: "row",
                          }}
                          justifyContent="space-between"
                          spacing={1}
                        >
                          <Box>
                            <Typography
                              variant="h6"
                              fontWeight={950}
                            >
                              {fighter.legal_name}
                            </Typography>

                            <Typography
                              variant="body2"
                              color="text.secondary"
                            >
                              Start Record:{" "}
                              {row.start_record || "N/A"}
                              {" • "}
                              Current:{" "}
                              {fighter.pro_record || "N/A"}
                              {" • "}
                              {fighter.fight_weight
                                ? `${fighter.fight_weight} lb`
                                : "Weight N/A"}
                            </Typography>
                          </Box>

                          <Chip
                            label={
                              completed >= target
                                ? "GRADUATED"
                                : `FIGHT ${completed} OF ${target}`
                            }
                            color={
                              completed >= target
                                ? "success"
                                : "primary"
                            }
                          />
                        </Stack>

                        <Grid container spacing={2}>

                          <Grid
                            item
                            xs={12}
                            md={3}
                          >
                            <TextField
                              fullWidth
                              type="date"
                              label="Signed Date"
                              InputLabelProps={{
                                shrink: true,
                              }}
                              value={
                                row.signed_date || ""
                              }
                              onChange={(e) => {
                                const value =
                                  e.target.value;

                                setSeriesFighters(
                                  (old) =>
                                    old.map(
                                      (item) =>
                                        item.id === row.id
                                          ? {
                                              ...item,
                                              signed_date:
                                                value,
                                            }
                                          : item
                                    )
                                );
                              }}
                              onBlur={(e) =>
                                updateSeriesFighter(
                                  row,
                                  {
                                    signed_date:
                                      e.target.value,
                                  }
                                )
                              }
                            />
                          </Grid>

                          <Grid
                            item
                            xs={12}
                            md={3}
                          >
                            <TextField
                              fullWidth
                              type="number"
                              label="Fights Completed"
                              value={
                                row.fights_completed ??
                                0
                              }
                              inputProps={{
                                min: 0,
                                max: target,
                              }}
                              onChange={(e) => {
                                const value =
                                  e.target.value;

                                setSeriesFighters(
                                  (old) =>
                                    old.map(
                                      (item) =>
                                        item.id === row.id
                                          ? {
                                              ...item,
                                              fights_completed:
                                                value,
                                            }
                                          : item
                                    )
                                );
                              }}
                              onBlur={(e) =>
                                updateSeriesFighter(
                                  row,
                                  {
                                    fights_completed:
                                      Number(
                                        e.target.value
                                      ),
                                  }
                                )
                              }
                            />
                          </Grid>

                          <Grid
                            item
                            xs={12}
                            md={3}
                          >
                            <TextField
                              select
                              fullWidth
                              label="Status"
                              value={
                                row.status ||
                                "active"
                              }
                              onChange={(e) => {
                                const value =
                                  e.target.value;

                                setSeriesFighters(
                                  (old) =>
                                    old.map(
                                      (item) =>
                                        item.id === row.id
                                          ? {
                                              ...item,
                                              status:
                                                value,
                                            }
                                          : item
                                    )
                                );

                                updateSeriesFighter(
                                  row,
                                  {
                                    status: value,
                                  }
                                );
                              }}
                            >
                              <MenuItem value="active">
                                Active
                              </MenuItem>

                              <MenuItem value="paused">
                                Paused
                              </MenuItem>

                              <MenuItem value="graduated">
                                Graduated
                              </MenuItem>

                              <MenuItem value="released">
                                Released
                              </MenuItem>
                            </TextField>
                          </Grid>

                          <Grid
                            item
                            xs={12}
                            md={3}
                          >
                            <Button
                              fullWidth
                              variant="outlined"
                              color="error"
                              sx={{
                                minHeight: 56,
                              }}
                              onClick={() =>
                                removeSeriesFighter(row)
                              }
                            >
                              Remove
                            </Button>
                          </Grid>

                          <Grid
                            item
                            xs={12}
                          >
                            <TextField
                              fullWidth
                              multiline
                              minRows={2}
                              label="Development Notes"
                              value={
                                row.notes || ""
                              }
                              onChange={(e) => {
                                const value =
                                  e.target.value;

                                setSeriesFighters(
                                  (old) =>
                                    old.map(
                                      (item) =>
                                        item.id === row.id
                                          ? {
                                              ...item,
                                              notes:
                                                value,
                                            }
                                          : item
                                    )
                                );
                              }}
                              onBlur={(e) =>
                                updateSeriesFighter(
                                  row,
                                  {
                                    notes:
                                      e.target.value,
                                  }
                                )
                              }
                            />
                          </Grid>

                        </Grid>

                      </Stack>
                    </CardContent>
                  </Card>
                );
              })}

            </Stack>
          </CardContent>
        </Card>

          </>
        )}



          </Box>
        )}

      </Stack>

      <Dialog
        open={fighterOpen}
        onClose={() => !working && setFighterOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>
          <Typography variant="h5" fontWeight={950}>
            Add Fighter
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Add only what you need for matchmaking. More details can be completed later.
          </Typography>
        </DialogTitle>

        <DialogContent>
          <Stack spacing={2.5} sx={{ pt: 1 }}>

            {/* BOXREC LOOKUP */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 1 }}
              >
                BoxRec
              </Typography>

              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
              >
                <TextField
                  fullWidth
                  label="Find Fighter on BoxRec"
                  placeholder="Type fighter name or BoxRec ID"
                  value={boxrecSearchText}
                  onChange={(e) => {
                    const value = e.target.value;

                    setExistingFighterId("");
                    setBoxrecSearchText(value);

                    if (/^\d*$/.test(value)) {
                      setFighterForm({
                        ...fighterForm,
                        boxrec_id: value,
                      });
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      lookupBoxRec();
                    }
                  }}
                />

                <Button
                  variant="outlined"
                  disabled={boxrecSearching || !boxrecSearchText.trim()}
                  onClick={lookupBoxRec}
                  sx={{
                    minWidth: 120,
                    minHeight: 56,
                    fontWeight: 900,
                  }}
                >
                  {boxrecSearching ? "Checking..." : "Find Fighter"}
                </Button>

                <Button
                  variant="text"
                  onClick={closeBoxRecProfile}
                  disabled={!boxrecSearchText.trim()}
                  sx={{
                    minHeight: 56,
                    whiteSpace: "nowrap",
                  }}
                >
                  Close BoxRec
                </Button>
              </Stack>

              {existingFighterId && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  Fighter already exists in TNG. Saved information has been loaded.
                </Alert>
              )}
            </Box>

            <Divider />

            {/* FIGHTER */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Fighter
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    required
                    autoFocus={!fighterForm.boxrec_id}
                    label="Fighter Name"
                    placeholder="First and last name"
                    value={fighterForm.legal_name}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        legal_name: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Pro Record"
                    placeholder="5-1-0"
                    value={fighterForm.pro_record}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        pro_record: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Fight Weight"
                    placeholder="140"
                    value={fighterForm.fight_weight}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        fight_weight: e.target.value,
                      })
                    }
                    InputProps={{
                      endAdornment: (
                        <Typography color="text.secondary">
                          lb
                        </Typography>
                      ),
                    }}
                  />
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth required>
                    <InputLabel>Sex</InputLabel>
                    <Select
                      value={fighterForm.sex || ""}
                      label="Sex"
                      onChange={(e) =>
                        setFighterForm({
                          ...fighterForm,
                          sex: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="">Select</MenuItem>
                      <MenuItem value="male">Male</MenuItem>
                      <MenuItem value="female">Female</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Stance</InputLabel>
                    <Select
                      value={fighterForm.stance}
                      label="Stance"
                      onChange={(e) =>
                        setFighterForm({
                          ...fighterForm,
                          stance: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="">Unknown</MenuItem>
                      <MenuItem value="orthodox">Orthodox</MenuItem>
                      <MenuItem value="southpaw">Southpaw</MenuItem>
                      <MenuItem value="switch">Switch</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Gym"
                    value={fighterForm.gym}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        gym: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            {/* LOCATION */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 1.5 }}
              >
                Location
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="City"
                    value={fighterForm.city}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        city: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="State"
                    value={fighterForm.state}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        state: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} sm={3}>
                  <TextField
                    fullWidth
                    label="Country"
                    value={fighterForm.country}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        country: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            {/* AVAILABLE WEIGHT */}
            <Box>
              <Typography
                variant="subtitle2"
                fontWeight={900}
                sx={{ mb: 0.5 }}
              >
                Available Weight Range
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 1.5 }}
              >
                Optional — useful when searching for opponents.
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Minimum"
                    placeholder="138"
                    value={fighterForm.available_weight_min}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        available_weight_min: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Maximum"
                    placeholder="143"
                    value={fighterForm.available_weight_max}
                    onChange={(e) =>
                      setFighterForm({
                        ...fighterForm,
                        available_weight_max: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

          </Stack>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            disabled={working}
            onClick={() => {
              setFighterOpen(false);
              setExistingFighterId("");
              closeBoxRecProfile();
            }}
          >
            Cancel
          </Button>

          <Button
            variant="outlined"
            disabled={working || !fighterForm.legal_name.trim()}
            onClick={() => createFighter(false)}
            sx={{
              fontWeight: 900,
            }}
          >
            {working
              ? "Saving..."
              : existingFighterId
                ? "Use Fighter"
                : "Save Fighter"}
          </Button>

          <Button
            variant="contained"
            disabled={
              working ||
              !fighterForm.legal_name.trim() ||
              (
                !fighterForm.fight_weight &&
                !fighterForm.available_weight_min &&
                !fighterForm.available_weight_max
              )
            }
            onClick={() => createFighter(true)}
            sx={{
              bgcolor: "#e31b23",
              fontWeight: 950,
              px: 3,
            }}
          >
            {working
              ? "Finding..."
              : "Save & Find Opponents"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={editFighterOpen}
        onClose={() => !working && setEditFighterOpen(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          <Typography variant="h5" fontWeight={950}>
            Edit Fighter
          </Typography>

          <Typography variant="body2" color="text.secondary">
            Update the information used for matchmaking and event operations.
          </Typography>
        </DialogTitle>

        <DialogContent>
          <Stack spacing={3} sx={{ pt: 1 }}>

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Fighter
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={8}>
                  <TextField
                    fullWidth
                    required
                    label="Fighter Name"
                    value={editFighterForm.legal_name || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        legal_name: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="BoxRec ID"
                    value={editFighterForm.boxrec_id || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        boxrec_id:
                          e.target.value.replace(/[^0-9]/g, ""),
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Pro Record"
                    placeholder="8-2-0"
                    value={editFighterForm.pro_record || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        pro_record: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <FormControl fullWidth required>
                    <InputLabel>Sex</InputLabel>
                    <Select
                      label="Sex"
                      value={editFighterForm.sex || ""}
                      onChange={(e) =>
                        setEditFighterForm({
                          ...editFighterForm,
                          sex: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="">Select</MenuItem>
                      <MenuItem value="male">Male</MenuItem>
                      <MenuItem value="female">Female</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Stance</InputLabel>

                    <Select
                      label="Stance"
                      value={editFighterForm.stance || ""}
                      onChange={(e) =>
                        setEditFighterForm({
                          ...editFighterForm,
                          stance: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="">Unknown</MenuItem>
                      <MenuItem value="orthodox">Orthodox</MenuItem>
                      <MenuItem value="southpaw">Southpaw</MenuItem>
                      <MenuItem value="switch">Switch</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Gym"
                    value={editFighterForm.gym || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        gym: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Matchmaking Weight
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={6} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Low Weight"
                    value={editFighterForm.available_weight_min ?? ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        available_weight_min: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="High Weight"
                    value={editFighterForm.available_weight_max ?? ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        available_weight_max: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Preferred Fight Weight"
                    value={editFighterForm.fight_weight ?? ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        fight_weight: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Contact
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Phone"
                    value={editFighterForm.phone || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        phone: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    type="email"
                    label="Email"
                    value={editFighterForm.email || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        email: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Instagram"
                    value={editFighterForm.instagram || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        instagram: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Facebook"
                    value={editFighterForm.facebook || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        facebook: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="TikTok"
                    value={editFighterForm.tiktok || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        tiktok: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Location
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <TextField
                    fullWidth
                    label="City"
                    value={editFighterForm.city || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        city: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <TextField
                    fullWidth
                    label="State"
                    value={editFighterForm.state || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        state: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={6} md={4}>
                  <TextField
                    fullWidth
                    label="Country"
                    value={editFighterForm.country || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        country: e.target.value,
                      })
                    }
                  />
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Typography variant="subtitle2" fontWeight={900} sx={{ mb: 1.5 }}>
                Commission / Medical
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Bloodwork</InputLabel>

                    <Select
                      label="Bloodwork"
                      value={editFighterForm.bloodwork_status || "missing"}
                      onChange={(e) =>
                        setEditFighterForm({
                          ...editFighterForm,
                          bloodwork_status: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="missing">Missing</MenuItem>
                      <MenuItem value="verified">Verified</MenuItem>
                      <MenuItem value="expired">Expired</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="date"
                    label="Bloodwork Expires"
                    InputLabelProps={{ shrink: true }}
                    value={editFighterForm.bloodwork_expires || ""}
                    onChange={(e) =>
                      setEditFighterForm({
                        ...editFighterForm,
                        bloodwork_expires: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Suspension</InputLabel>

                    <Select
                      label="Suspension"
                      value={
                        editFighterForm.suspension_status ||
                        "needs_review"
                      }
                      onChange={(e) =>
                        setEditFighterForm({
                          ...editFighterForm,
                          suspension_status: e.target.value,
                        })
                      }
                    >
                      <MenuItem value="needs_review">
                        Needs Review
                      </MenuItem>

                      <MenuItem value="verified_clear">
                        Verified Clear
                      </MenuItem>

                      <MenuItem value="suspended">
                        Suspended
                      </MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </Box>

            <Divider />

            <Box>
              <Stack
                direction={{
                  xs: "column",
                  sm: "row",
                }}
                justifyContent="space-between"
                alignItems={{
                  xs: "flex-start",
                  sm: "center",
                }}
                spacing={1}
                sx={{ mb: 1.5 }}
              >
                <Box>
                  <Typography
                    variant="subtitle2"
                    fontWeight={900}
                  >
                    Fighter Portal Login
                  </Typography>

                  <Typography
                    variant="caption"
                    color="text.secondary"
                  >
                    Set or reset this fighter's TNGOS login.
                  </Typography>
                </Box>

                <Chip
                  size="small"
                  color={
                    fighterPortalAccount?.portal_account_exists &&
                    fighterPortalForm.active
                      ? "success"
                      : "default"
                  }
                  label={
                    fighterPortalLoading
                      ? "Loading..."
                      : fighterPortalAccount?.portal_account_exists
                        ? fighterPortalForm.active
                          ? "Login Active"
                          : "Login Disabled"
                        : "No Portal Account"
                  }
                />
              </Stack>

              <Grid container spacing={2}>
                <Grid item xs={12} md={5}>
                  <TextField
                    fullWidth
                    type="email"
                    label="Portal Login Email"
                    value={fighterPortalForm.login_email}
                    disabled={fighterPortalLoading}
                    onChange={(e) =>
                      setFighterPortalForm({
                        ...fighterPortalForm,
                        login_email: e.target.value,
                      })
                    }
                  />
                </Grid>

                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    type="password"
                    label={
                      fighterPortalAccount?.portal_account_exists
                        ? "New Password"
                        : "Create Password"
                    }
                    placeholder={
                      fighterPortalAccount?.portal_account_exists
                        ? "Leave blank to keep current password"
                        : "Minimum 8 characters"
                    }
                    value={fighterPortalForm.password}
                    disabled={fighterPortalLoading}
                    onChange={(e) =>
                      setFighterPortalForm({
                        ...fighterPortalForm,
                        password: e.target.value,
                      })
                    }
                    helperText={
                      fighterPortalAccount?.portal_account_exists
                        ? "Only enter a password when resetting it."
                        : "Required for a new portal account."
                    }
                  />
                </Grid>

                <Grid item xs={12} md={3}>
                  <FormControl fullWidth>
                    <InputLabel>Portal Access</InputLabel>

                    <Select
                      label="Portal Access"
                      value={
                        fighterPortalForm.active
                          ? "active"
                          : "disabled"
                      }
                      disabled={fighterPortalLoading}
                      onChange={(e) =>
                        setFighterPortalForm({
                          ...fighterPortalForm,
                          active: e.target.value === "active",
                        })
                      }
                    >
                      <MenuItem value="active">
                        Active
                      </MenuItem>

                      <MenuItem value="disabled">
                        Disabled
                      </MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                <Grid item xs={12}>
                  <Stack
                    direction={{
                      xs: "column",
                      sm: "row",
                    }}
                    spacing={1}
                    alignItems={{
                      xs: "stretch",
                      sm: "center",
                    }}
                  >
                    <Button
                      variant="outlined"
                      disabled={
                        fighterPortalLoading ||
                        !fighterPortalForm.login_email?.trim()
                      }
                      onClick={saveFighterPortalAccount}
                      sx={{ fontWeight: 900 }}
                    >
                      {fighterPortalLoading
                        ? "Saving..."
                        : fighterPortalAccount?.portal_account_exists
                          ? "Save Portal Login"
                          : "Create Portal Login"}
                    </Button>

                    <Typography
                      variant="caption"
                      color="text.secondary"
                    >
                      Login uses email and password. Existing
                      passwords cannot be viewed, only reset.
                    </Typography>
                  </Stack>
                </Grid>
              </Grid>
            </Box>

          </Stack>
        </DialogContent>

        <DialogActions>
          <Button
            disabled={working}
            onClick={() => setEditFighterOpen(false)}
          >
            Cancel
          </Button>

          <Button
            variant="contained"
            disabled={
              working ||
              !editFighterForm.legal_name?.trim()
            }
            onClick={saveFighterEdits}
            sx={{
              bgcolor: "#e31b23",
              fontWeight: 900,
            }}
          >
            {working ? "Saving..." : "Save Changes"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={eventOpen} onClose={() => !working && setEventOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add Boxing Event</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField
              fullWidth
              required
              label="Event Name"
              value={eventForm.name}
              onChange={(e) => {
                const name = e.target.value;
                setEventForm({
                  ...eventForm,
                  name,
                  slug: eventForm.slug || slugify(name),
                });
              }}
            />
            <TextField
              fullWidth
              label="Event Slug"
              helperText="Used internally. Example: fall-brawl-6"
              value={eventForm.slug}
              onChange={(e) => setEventForm({ ...eventForm, slug: slugify(e.target.value) })}
            />
            <TextField
              fullWidth
              type="date"
              label="Event Date"
              InputLabelProps={{ shrink: true }}
              value={eventForm.event_date}
              onChange={(e) => setEventForm({ ...eventForm, event_date: e.target.value })}
            />
            <TextField
              fullWidth
              label="Venue"
              value={eventForm.venue}
              onChange={(e) => setEventForm({ ...eventForm, venue: e.target.value })}
            />
            <TextField
              fullWidth
              label="Venue Address"
              value={eventForm.venue_address}
              onChange={(e) => setEventForm({ ...eventForm, venue_address: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button disabled={working} onClick={() => setEventOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={working}
            onClick={createEvent}
            sx={{ bgcolor: "#e31b23" }}
          >
            {working ? "Saving..." : "Add Event"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
