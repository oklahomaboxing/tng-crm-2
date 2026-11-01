package com.tngboxing.checkinkiosk;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.net.Uri;

/** Independent optional launcher; does not replace or require InBody software. */
public class MainActivity extends Activity {
    private static final String URL = "https://tngos.tngboxinggym.com/kiosk/checkin";
    private WebView web;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final Runnable retry = () -> { if (web != null) web.loadUrl(URL); };
    static boolean allowed(Uri uri) {
        return uri != null && "https".equals(uri.getScheme()) && "tngos.tngboxinggym.com".equals(uri.getHost())
            && (uri.getPort() == -1 || uri.getPort() == 443) && uri.getUserInfo() == null
            && ("/kiosk/checkin".equals(uri.getPath()) || "/kiosk/checkin/".equals(uri.getPath()));
    }
    @SuppressLint("SetJavaScriptEnabled")
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        web = new WebView(this);
        web.setBackgroundColor(0xff08090b);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setGeolocationEnabled(false);
        settings.setSupportMultipleWindows(false);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !allowed(request.getUrl());
            }
            @Override public void onPageFinished(WebView view, String url) { immersive(); }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    view.loadData("<html><meta name='viewport' content='width=device-width'><body style='background:#08090b;color:white;text-align:center;font:24px sans-serif;padding:40px'><h1>TNG BOXING</h1><p>Check-in is offline. Please visit the front desk.</p><p>Reconnecting automatically…</p></body></html>", "text/html", "UTF-8");
                    handler.removeCallbacks(retry); handler.postDelayed(retry, 15000);
                }
            }
        });
        setContentView(web); web.loadUrl(URL); immersive();
    }
    private void immersive() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }
    @Override public void onWindowFocusChanged(boolean focus) {super.onWindowFocusChanged(focus);if (focus) immersive();}
    @Override protected void onResume() {super.onResume();if (web != null) web.onResume();immersive();}
    @Override protected void onPause() {if (web != null) web.onPause();super.onPause();}
    @Override public void onBackPressed() { /* Remain on the kiosk. Android Home still works. */ }
    @Override protected void onDestroy() {handler.removeCallbacks(retry);if (web != null) {web.destroy();web=null;}super.onDestroy();}
}
