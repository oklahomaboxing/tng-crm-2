import React, { useEffect, useMemo, useState } from "react";
import { Button, Stack, Typography } from "@mui/material";

const RECEIVER_APP_ID = import.meta.env.VITE_CAST_APP_ID || "";

function loadCastFramework() {
  return new Promise((resolve, reject) => {
    if (window.cast?.framework && window.chrome?.cast) {
      resolve(true);
      return;
    }

    const existing = document.querySelector(
      'script[src*="cast_sender.js"]'
    );

    window.__onGCastApiAvailable = (isAvailable) => {
      if (isAvailable) resolve(true);
      else reject(new Error("Google Cast API unavailable"));
    };

    if (existing) return;

    const script = document.createElement("script");
    script.src =
      "https://www.gstatic.com/cv/js/sender/v1/cast_sender.js?loadCastFramework=1";
    script.async = true;
    script.onerror = () => reject(new Error("Unable to load Google Cast SDK"));
    document.head.appendChild(script);
  });
}

export default function CastTrainerButton({ liveState = {} }) {
  const [castReady, setCastReady] = useState(false);
  const [status, setStatus] = useState(
    RECEIVER_APP_ID ? "Cast initializing..." : "Cast App ID needed"
  );

  const payload = useMemo(
    () => ({
      type: "TNG_TRAINER_STATE",
      ...liveState,
      sent_at: Date.now(),
    }),
    [liveState]
  );

  useEffect(() => {
    let cancelled = false;

    if (!RECEIVER_APP_ID) {
      setStatus("Add VITE_CAST_APP_ID after Cast registration");
      return undefined;
    }

    loadCastFramework()
      .then(() => {
        if (cancelled) return;

        const context = window.cast.framework.CastContext.getInstance();
        context.setOptions({
          receiverApplicationId: RECEIVER_APP_ID,
          autoJoinPolicy: window.chrome.cast.AutoJoinPolicy.ORIGIN_SCOPED,
        });

        setCastReady(true);
        setStatus("Choose a Cast-compatible TV");
      })
      .catch((error) => {
        console.error("Cast initialization failed", error);
        setStatus("Cast unavailable on this device/browser");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!castReady) return;

    try {
      const session =
        window.cast.framework.CastContext.getInstance().getCurrentSession();

      if (!session) return;

      session.sendMessage(
        "urn:x-cast:com.tngboxing.trainer",
        payload
      ).catch((error) => {
        console.warn("Unable to send TNG Cast state", error);
      });
    } catch (error) {
      console.warn("TNG Cast state update failed", error);
    }
  }, [castReady, payload]);

  async function openCastPicker() {
    if (!RECEIVER_APP_ID) {
      alert(
        "Google Cast receiver registration is required first. Add the App ID as VITE_CAST_APP_ID in DigitalOcean."
      );
      return;
    }

    try {
      await loadCastFramework();
      const context = window.cast.framework.CastContext.getInstance();
      await context.requestSession();
      setStatus("Connected to Cast TV");
    } catch (error) {
      console.error("Cast picker error", error);
      setStatus("No Cast session selected");
    }
  }

  return (
    <Stack spacing={0.5}>
      <Button
        variant="contained"
        color="primary"
        onClick={openCastPicker}
        disabled={!RECEIVER_APP_ID}
      >
        Cast Trainer
      </Button>

      <Typography variant="caption" sx={{ opacity: 0.72 }}>
        {status}
      </Typography>
    </Stack>
  );
}
