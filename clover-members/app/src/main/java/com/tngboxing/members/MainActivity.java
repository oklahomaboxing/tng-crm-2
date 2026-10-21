package com.tngboxing.members;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.widget.*;
import com.clover.sdk.v1.Intents;
import com.clover.sdk.v3.scanner.BarcodeResult;
import com.clover.sdk.v3.scanner.BarcodeScanner;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.EncodeHintType;
import com.google.zxing.common.BitMatrix;
import com.google.zxing.qrcode.QRCodeWriter;
import org.json.JSONArray;
import org.json.JSONObject;
import java.net.SocketTimeoutException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final CheckinGate gate = new CheckinGate();
    private CustomerDisplaySession customerDisplay;
    private TextView recentCheckin;
    private String latestCheckin="";
    private int latestColor=MUTED;
    private TokenStore store;
    private String token = "";
    private LinearLayout root, content;
    private TextView checkinStatus;
    private EditText numberInput;
    private BarcodeScanner scanner;
    private boolean receiverRegistered, scanning, scanScreen, foreground;
    private int screenVersion;
    private int facing = BarcodeScanner.BARCODE_SCANNER_FACING_CUSTOMER;
    private static final int BG = Color.rgb(15,15,22), MUTED = Color.rgb(189,189,200);

    interface Done { void accept(JSONObject data); }
    private final BroadcastReceiver receiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            BarcodeResult result = new BarcodeResult(intent);
            if (foreground && scanning && result.isBarcodeAction() && result.getBarcode() != null) {
                stopScanner(); submitCheckin(result.getBarcode());
            }
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        store = new TokenStore(this); token = store.load(); scanner = new BarcodeScanner(this);
        customerDisplay=new CustomerDisplaySession(this,new CustomerDisplaySession.Listener(){
            public void code(String value){submitCheckin(value);}
            public void scan(){beginScan(BarcodeScanner.BARCODE_SCANNER_FACING_CUSTOMER);}
            public void ready(){customerDisplay.status("ready","","","");}
            public void unavailable(){if(!isFinishing()&&!token.isEmpty())recentCheckin.setText("Customer screen unavailable or closed. Use Open customer check-in to retry when Clover is idle.");}
        });
        if (token.isEmpty()) showLogin(); else {
            screen("Opening your gym…", false);
            request("GET", "/session", null, data -> showCheckin());
        }
    }
    @Override protected void onResume() {
        super.onResume(); foreground = true;
        if (!receiverRegistered) {
            IntentFilter filter = new IntentFilter(BarcodeResult.INTENT_ACTION);
            if(android.os.Build.VERSION.SDK_INT >= 33) registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED);
            else registerReceiver(receiver, filter);
            receiverRegistered = true;
        }
    }
    @Override protected void onPause() {
        foreground = false; stopScanner();
        if (receiverRegistered) { unregisterReceiver(receiver); receiverRegistered = false; }
        super.onPause();
    }
    @Override protected void onStop(){if(customerDisplay!=null)customerDisplay.close();super.onStop();}
    private void openCustomerDisplay(){
        if(android.os.Build.VERSION.SDK_INT>=23 && checkSelfPermission(android.Manifest.permission.GET_ACCOUNTS)!=android.content.pm.PackageManager.PERMISSION_GRANTED){requestPermissions(new String[]{android.Manifest.permission.GET_ACCOUNTS},201);return;}
        customerDisplay.open();
    }
    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] results){super.onRequestPermissionsResult(code,permissions,results);if(code==201 && results.length>0 && results[0]==android.content.pm.PackageManager.PERMISSION_GRANTED)customerDisplay.open();}
    @Override protected void onDestroy() {
        if(customerDisplay!=null)customerDisplay.dispose();
        screenVersion++; handler.removeCallbacksAndMessages(null); network.shutdownNow(); super.onDestroy();
    }
    @Override public void onBackPressed() { if (!gate.isBusy()) { if (token.isEmpty()) super.onBackPressed(); else showCheckin(); } }

    private int dp(int value) { return (int)(value * getResources().getDisplayMetrics().density); }
    private TextView text(String value, int size, int color) {
        TextView view = new TextView(this); view.setText(value); view.setTextSize(size); view.setTextColor(color); view.setPadding(0,dp(7),0,dp(7)); return view;
    }
    private LinearLayout row() { LinearLayout view = new LinearLayout(this); view.setOrientation(LinearLayout.HORIZONTAL); view.setGravity(Gravity.CENTER_VERTICAL); return view; }
    private Button button(String label, Runnable action) {
        Button button = new Button(this); button.setText(label); button.setAllCaps(false); button.setMinHeight(dp(52));
        button.setOnClickListener(v -> { if (!gate.isBusy()) action.run(); }); return button;
    }
    private EditText field(String hint, String value, int type) {
        EditText edit = new EditText(this); edit.setHint(hint); edit.setText(value); edit.setTextColor(Color.WHITE); edit.setHintTextColor(MUTED); edit.setTextSize(22); edit.setInputType(type); edit.setSingleLine(true); edit.setPadding(dp(12),dp(12),dp(12),dp(12)); edit.setMinHeight(dp(58)); return edit;
    }
    private void screen(String title, boolean navigation) {
        stopScanner(); scanScreen = false; screenVersion++;
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(BG); root.setPadding(dp(24),dp(18),dp(24),dp(18));
        LinearLayout top = row(); TextView brand = text("TNG MEMBERS",24,Color.WHITE); brand.setTypeface(null,Typeface.BOLD); top.addView(brand,new LinearLayout.LayoutParams(0,-2,1));
        if (navigation) {
            top.addView(button("Check in",this::showCheckin)); top.addView(button("Members",() -> showMembers("",1)));
            top.addView(button("Sign out",() -> new AlertDialog.Builder(this).setTitle("Sign out of TNG Members?").setPositiveButton("Sign out",(d,w) -> { customerDisplay.close(); token=""; store.clear(); showLogin(); }).setNegativeButton("Cancel",null).show()));
        }
        root.addView(top); root.addView(text(title,30,Color.WHITE));
        recentCheckin=text(latestCheckin,17,latestColor);root.addView(recentCheckin);
        if(navigation)root.addView(button("Open customer check-in screen",this::openCustomerDisplay));
        ScrollView scroll = new ScrollView(this); scroll.setFillViewport(true);
        content = new LinearLayout(this); content.setOrientation(LinearLayout.VERTICAL); scroll.addView(content);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1)); root.addView(text("TNG Boxing  •  Member services  •  Preview " + BuildConfig.VERSION_NAME,12,MUTED)); setContentView(root);
    }
    private void showLogin() {
        latestCheckin="";latestColor=MUTED;
        screen("Your gym, on Clover.",false);
        content.addView(text("Sign in here with your TNG staff or admin account. Your session stays on this Clover for up to eight hours. No separate tablet is needed.",19,MUTED));
        EditText email=field("Staff email","",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText password=field("Password","",InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        content.addView(email); content.addView(password);
        Button signIn=new Button(this); signIn.setText("Sign in to TNG Members"); signIn.setMinHeight(dp(60)); content.addView(signIn);
        signIn.setOnClickListener(v -> {
            JSONObject body=new JSONObject(); try { body.put("email",email.getText().toString().trim()); body.put("password",password.getText().toString()); } catch(Exception ignored) { return; }
            signIn.setEnabled(false);
            request("POST","/login",body,data -> {
                String received=data.optString("token","");
                try { if(received.isEmpty()) throw new Exception(); store.save(received); token=received; password.setText(""); showCheckin(); }
                catch(Exception ignored) { signIn.setEnabled(true); message("Could not securely save this session. Sign in again."); }
            },() -> signIn.setEnabled(true));
        });
        content.addView(text("Support: marketing@tngboxinggym.com  •  405-959-5823",16,MUTED));
    }
    private void showCheckin() {
        screen("Welcome to TNG Boxing",true); scanScreen=true;
        content.addView(text("Scan your member QR card or enter your short member number.",23,MUTED));
        numberInput=field("Member number, e.g. 42","",InputType.TYPE_CLASS_NUMBER); numberInput.setImeOptions(EditorInfo.IME_ACTION_GO);
        numberInput.setOnEditorActionListener((v,action,event) -> { if(action==EditorInfo.IME_ACTION_GO || (event!=null && event.getAction()==android.view.KeyEvent.ACTION_DOWN && event.getKeyCode()==android.view.KeyEvent.KEYCODE_ENTER)) { submitCheckin(numberInput.getText().toString()); return true; } return false; });
        content.addView(numberInput); content.addView(button("Check in with number",() -> submitCheckin(numberInput.getText().toString())));
        LinearLayout cameras=row(); cameras.addView(button("Scan customer-facing QR",() -> beginScan(BarcodeScanner.BARCODE_SCANNER_FACING_CUSTOMER)));
        cameras.addView(button("Scan merchant-facing QR",() -> beginScan(BarcodeScanner.BARCODE_SCANNER_FACING_MERCHANT))); content.addView(cameras);
        checkinStatus=text("Ready for the next member",26,Color.WHITE); content.addView(checkinStatus);
        content.addView(text("Use TNG Members on the merchant display. QR scanning can use the customer-facing camera; member profiles remain on the staff screen.",17,MUTED));
    }
    private void beginScan(int requestedFacing) {
        facing=requestedFacing;
        try {
            List<Integer> available=scanner.getAvailable();
            if (!available.contains(facing)) { message("That Clover camera is not available. Try the other camera or type the member number."); return; }
            Bundle options=new Bundle(); options.putInt(Intents.EXTRA_SCANNER_FACING,facing); options.putBoolean(Intents.EXTRA_SCAN_QR_CODE,true); options.putBoolean(Intents.EXTRA_SCAN_1D_CODE,false); options.putBoolean(Intents.EXTRA_SHOW_PREVIEW,true);
            scanning=true;
            if(!scanner.startScan(options)) { scanning=false; message("Clover could not open the scanner. Try entering the member number."); }
        } catch(Exception ignored) { scanning=false; message("The native scanner needs a supported Clover Station Duo. Number check-in is available."); }
    }
    private void stopScanner() { if (scanner!=null && scanning) { try { scanner.stopScan(); } catch(Exception ignored) {} } scanning=false; }
    private void submitCheckin(String value) {
        String code=value==null?"":value.trim();
        if ((!scanScreen && !customerDisplay.isOpen()) || !gate.accept(code,SystemClock.elapsedRealtime())) { if(code.isEmpty()) message("Enter your member number first."); return; }
        stopScanner(); recentCheckin.setText("Checking membership…");
        if(scanScreen){checkinStatus.setText("Checking membership…");checkinStatus.setTextColor(Color.WHITE);}
        customerDisplay.status("processing","","","");
        JSONObject body=new JSONObject(); try { body.put("code",code); } catch(Exception ignored) { gate.release(); return; }
        request("POST","/checkin",body,data -> {
            gate.release(); JSONObject member=data.optJSONObject("member");
            if(member==null) { message("Check-in could not be confirmed. Ask staff to review recent visits before retrying."); return; }
            if(numberInput!=null)numberInput.setText(""); recentCheckin.setText("✓ Checked in: "+member.optString("name")+"  •  Member #"+member.optString("member_number")); recentCheckin.setTextColor(Color.rgb(94,225,142));latestCheckin=recentCheckin.getText().toString();latestColor=Color.rgb(94,225,142);
            if(scanScreen){checkinStatus.setText(recentCheckin.getText());checkinStatus.setTextColor(Color.rgb(94,225,142));}
            customerDisplay.status("success",member.optString("first_name"),member.optString("member_number"),member.optString("status"));
            int version=screenVersion; handler.postDelayed(() -> { if(screenVersion==version && scanScreen) { checkinStatus.setText("Ready for the next member");checkinStatus.setTextColor(Color.WHITE);numberInput.requestFocus(); } },2500);
        },() -> { gate.release(); customerDisplay.status("error","","",""); recentCheckin.setText("Member check-in requires staff review."); if(scanScreen && checkinStatus!=null) { checkinStatus.setText("Check-in not confirmed. Review the message before retrying."); checkinStatus.setTextColor(Color.rgb(255,170,170)); } });
    }
    private void showMembers(String query,int page) {
        screen("Member directory",true); LinearLayout search=row(); EditText input=field("Search name or member number",query,InputType.TYPE_CLASS_TEXT); search.addView(input,new LinearLayout.LayoutParams(0,-2,1)); search.addView(button("Search",() -> showMembers(input.getText().toString(),1))); content.addView(search);
        TextView loading=text("Loading members…",18,MUTED); content.addView(loading);
        request("GET","/members?q="+Uri.encode(query)+"&page="+page,null,data -> {
            loading.setText(data.optInt("total")+" matching members"); JSONArray items=data.optJSONArray("items");
            if(items!=null) for(int i=0;i<items.length();i++) { JSONObject member=items.optJSONObject(i); if(member==null)continue; int id=member.optInt("id");
                Button item=button(member.optString("name")+"   #"+member.optString("member_number")+"\n"+member.optString("membership")+"  •  "+member.optString("status"),() -> showProfile(id)); item.setGravity(Gravity.START|Gravity.CENTER_VERTICAL); content.addView(item);
            }
            LinearLayout pages=row(); if(page>1)pages.addView(button("Previous",() -> showMembers(query,page-1))); if(page*30<data.optInt("total"))pages.addView(button("Next",() -> showMembers(query,page+1)));content.addView(pages);
        });
    }
    private void showProfile(int id) {
        screen("Member profile",true); content.addView(text("Loading profile…",18,MUTED));
        request("GET","/members/"+id,null,member -> {
            content.removeAllViews();content.addView(text(member.optString("name")+"  #"+member.optString("member_number"),30,Color.WHITE));
            content.addView(text(member.optString("membership")+"  •  "+member.optString("status"),23,Color.WHITE));
            content.addView(text("Membership ends: "+displayDate(member.optString("membership_end"))+"\nVisits: "+member.optInt("total_checkins")+"\nWaiver: "+(member.optBoolean("waiver_signed")?"On file":"Not on file"),19,MUTED));
            content.addView(text(member.optString("email")+"\n"+member.optString("phone"),20,Color.WHITE));
            LinearLayout actions=row();actions.addView(button("Show QR card",() -> showQr(member)));actions.addView(button("Edit contact details",() -> editContact(member)));content.addView(actions);
            content.addView(text("Recent visits",23,Color.WHITE));JSONArray visits=member.optJSONArray("attendance");if(visits!=null && visits.length()>0)for(int i=0;i<visits.length();i++)content.addView(text(displayDate(visits.optString(i)),18,MUTED));else content.addView(text("No visits recorded yet.",18,MUTED));
        });
    }
    private String displayDate(String value) {
        if(value==null||value.isEmpty()||value.equals("null"))return "Not recorded";
        try {
            java.text.SimpleDateFormat input=new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss",java.util.Locale.US);
            input.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
            java.util.Date date=input.parse(value);
            java.text.SimpleDateFormat output=new java.text.SimpleDateFormat("MMM d, yyyy h:mm a",java.util.Locale.US);
            output.setTimeZone(java.util.TimeZone.getTimeZone("America/Chicago"));return output.format(date);
        }catch(Exception ignored){return value;}
    }
    private void editContact(JSONObject member) {
        int id=member.optInt("id");screen("Edit member contact",true);String[] keys={"first_name","last_name","email","phone"};String[] labels={"First name","Last name","Email","Phone"};EditText[] edits=new EditText[4];
        for(int i=0;i<keys.length;i++){edits[i]=field(labels[i],member.optString(keys[i]),i==2?InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS:i==3?InputType.TYPE_CLASS_PHONE:InputType.TYPE_CLASS_TEXT);content.addView(text(labels[i],16,MUTED));content.addView(edits[i]);}
        Button save=new Button(this);save.setText("Save contact details");save.setMinHeight(dp(54));content.addView(save);save.setOnClickListener(v -> {JSONObject body=new JSONObject();try{for(int i=0;i<keys.length;i++)body.put(keys[i],edits[i].getText().toString().trim());}catch(Exception ignored){return;}save.setEnabled(false);request("PATCH","/members/"+id,body,data -> showProfile(id),() -> save.setEnabled(true));});
        content.addView(text("Membership status and billing remain controlled by TNG’s existing purchase and renewal process.",17,MUTED));
    }
    private void showQr(JSONObject member) {
        try {
            String value=member.optString("qr_value");if(value.isEmpty()){message("This member does not have a QR credential yet.");return;}
            Map<EncodeHintType,Object> hints=new HashMap<>();hints.put(EncodeHintType.MARGIN,4);
            BitMatrix matrix=new QRCodeWriter().encode(value,BarcodeFormat.QR_CODE,512,512,hints);Bitmap image=Bitmap.createBitmap(512,512,Bitmap.Config.ARGB_8888);
            for(int y=0;y<512;y++)for(int x=0;x<512;x++)image.setPixel(x,y,matrix.get(x,y)?Color.BLACK:Color.WHITE);
            ImageView view=new ImageView(this);view.setImageBitmap(image);view.setAdjustViewBounds(true);view.setPadding(dp(20),dp(20),dp(20),dp(20));view.setBackgroundColor(Color.WHITE);
            new AlertDialog.Builder(this).setTitle(member.optString("name")+"  #"+member.optString("member_number")).setView(view).setPositiveButton("Close",null).show();
        } catch(Exception ignored){message("Could not display this QR card. Use the member number.");}
    }
    private void request(String method,String path,JSONObject body,Done done) { request(method,path,body,done,() -> {}); }
    private void request(String method,String path,JSONObject body,Done done,Runnable failed) {
        int version=screenVersion;String session=token;
        network.execute(() -> {
            try {JSONObject data=ApiClient.call(session,method,path,body);handler.post(() -> {if(!isFinishing()&&screenVersion==version)done.accept(data);});}
            catch(Exception error){handler.post(() -> {
                if(isFinishing()||screenVersion!=version)return;failed.run();
                if(error instanceof ApiClient.Failure && ((ApiClient.Failure)error).status==401 && !path.equals("/login")){customerDisplay.close();token="";store.clear();showLogin();}
                String detail=error instanceof ApiClient.Failure?error.getMessage():method.equals("POST")&&path.equals("/checkin")?"Connection interrupted. The check-in may have been recorded. Review the member’s recent visits before trying again.":"Could not reach the gym service. Check this Clover’s internet connection.";
                message(detail);
            });}
        });
    }
    private void message(String value) { if(!isFinishing())new AlertDialog.Builder(this).setMessage(value).setPositiveButton("OK",null).show(); }
}
