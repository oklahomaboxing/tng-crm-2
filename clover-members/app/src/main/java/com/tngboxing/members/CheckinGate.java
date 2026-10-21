package com.tngboxing.members;

/** Single submission per burst of native scanner broadcasts. No automatic HTTP retry. */
final class CheckinGate {
    private boolean busy;
    private String last = "";
    private long at;
    boolean accept(String code, long now) {
        if (busy || code == null || code.trim().isEmpty()) return false;
        if (code.equals(last) && now - at >= 0 && now - at < 8000) return false;
        busy = true; last = code; at = now; return true;
    }
    void release() { busy = false; }
    boolean isBusy() { return busy; }
}
