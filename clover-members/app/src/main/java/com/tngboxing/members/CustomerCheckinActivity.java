package com.tngboxing.members;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.*;
import com.clover.sdk.cfp.activity.helper.CloverCFPActivityHelper;
import com.clover.sdk.cfp.activity.helper.CloverCFPCommsHelper;
import org.json.JSONObject;

/** Customer-side activity deliberately contains no credentials, profiles or directory access. */
public class CustomerCheckinActivity extends Activity implements CloverCFPCommsHelper.MessageListener {
    private CloverCFPActivityHelper activityHelper;
    private CloverCFPCommsHelper comms;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private String session="",digits="";
    private TextView number,status;
    private LinearLayout keypad;
    private boolean busy;
    private final Runnable reset=() -> ready();
    @Override public void onCreate(Bundle state){
        super.onCreate(state);getWindow().addFlags(WindowManager.LayoutParams.FLAG_SECURE|WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        activityHelper=new CloverCFPActivityHelper(this);comms=new CloverCFPCommsHelper(this,getIntent(),this);
        try{session=new JSONObject(activityHelper.getInitialPayload()).optString("session");}catch(Exception ignored){}
        if(session.isEmpty()){finish();return;}
        LinearLayout page=new LinearLayout(this);page.setOrientation(LinearLayout.VERTICAL);page.setGravity(Gravity.CENTER);page.setPadding(24,20,24,20);page.setBackgroundColor(Color.rgb(15,15,22));
        page.addView(label("TNG BOXING",34));page.addView(label("MEMBER CHECK-IN",22));
        status=label("Welcome. Scan your QR card or enter your member number.",20);page.addView(status);
        Button scan=new Button(this);scan.setText("Scan my QR card");scan.setMinHeight(64);scan.setOnClickListener(v -> {if(!busy){busy=true;status.setText("Opening the QR scanner…");send("scan","");}});page.addView(scan);
        number=label("Member number",30);page.addView(number);
        keypad=new LinearLayout(this);keypad.setOrientation(LinearLayout.VERTICAL);
        String[][] rows={{"1","2","3"},{"4","5","6"},{"7","8","9"},{"Clear","0","⌫"}};
        for(String[] keys:rows){LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER);for(String key:keys){Button button=new Button(this);button.setText(key);button.setTextSize(24);button.setMinHeight(58);button.setOnClickListener(v -> {if(busy)return;if(key.equals("Clear"))digits="";else if(key.equals("⌫")){if(!digits.isEmpty())digits=digits.substring(0,digits.length()-1);}else if(digits.length()<12)digits+=key;number.setText(digits.isEmpty()?"Member number":digits);});row.addView(button,new LinearLayout.LayoutParams(110,64));}keypad.addView(row);}
        page.addView(keypad);Button submit=new Button(this);submit.setText("Check me in");submit.setMinHeight(64);submit.setOnClickListener(v -> {if(!busy&&!digits.isEmpty()){busy=true;status.setText("Verifying membership…");send("checkin",digits);}});page.addView(submit);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.addView(page);setContentView(scroll);send("ready","");
    }
    private TextView label(String text,int size){TextView v=new TextView(this);v.setText(text);v.setTextSize(size);v.setTextColor(Color.WHITE);v.setGravity(Gravity.CENTER);v.setPadding(8,8,8,8);return v;}
    private void send(String type,String code){try{JSONObject body=new JSONObject();body.put("session",session);body.put("type",type);body.put("code",code);comms.sendMessage(body.toString());handler.removeCallbacks(reset);handler.postDelayed(reset,20000);}catch(Exception ignored){busy=false;status.setText("Please ask the front desk for help.");}}
    private void ready(){busy=false;digits="";number.setText("Member number");status.setTextColor(Color.WHITE);status.setText("Welcome. Scan your QR card or enter your member number.");}
    @Override public void onMessage(String payload){
        try{JSONObject data=new JSONObject(payload);if(!session.equals(data.optString("session")))return;String type=data.optString("type");handler.removeCallbacks(reset);
            if(type.equals("close")){activityHelper.setResultAndFinish(RESULT_CANCELED,"");return;}
            if(type.equals("processing")){busy=true;status.setText("Verifying membership…");handler.postDelayed(reset,25000);}
            else if(type.equals("success")){busy=true;status.setTextColor(Color.rgb(94,225,142));status.setText("✓ Welcome, "+data.optString("first_name")+"!\nMembership: "+data.optString("membership_status")+"\nCheck-in complete");handler.postDelayed(reset,3500);}
            else if(type.equals("error")){busy=true;status.setTextColor(Color.rgb(255,170,170));status.setText("Please see the front desk to confirm your membership or check-in.");handler.postDelayed(reset,4500);}
            else if(type.equals("ready"))ready();
        }catch(Exception ignored){}
    }
    // Clover's customer display can remain paused while visible: do not stop in onPause.
    @Override protected void onDestroy(){handler.removeCallbacksAndMessages(null);if(comms!=null)comms.dispose();if(activityHelper!=null)activityHelper.dispose();super.onDestroy();}
}
