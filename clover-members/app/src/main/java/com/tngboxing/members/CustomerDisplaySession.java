package com.tngboxing.members;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import com.clover.sdk.util.CloverAccount;
import com.clover.sdk.cfp.connector.*;
import org.json.JSONObject;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Only a per-session nonce and public check-in feedback cross to the customer display. */
final class CustomerDisplaySession {
    static final String ACTION = "com.tngboxing.members.CUSTOMER_CHECKIN";
    interface Listener { void code(String value); void scan(); void ready(); void unavailable(); }
    private final Context context;
    private final Listener listener;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private volatile RemoteDeviceConnector connector;
    private volatile String nonce = "";
    private volatile boolean open;
    CustomerDisplaySession(Context context, Listener listener) { this.context=context;this.listener=listener; }
    boolean isOpen(){return open;}
    void open() {
        if(open)return;open=true;String session=UUID.randomUUID().toString();nonce=session;
        io.execute(() -> {
            RemoteDeviceConnector device=null;
            try {
                android.accounts.Account account=CloverAccount.getAccount(context);
                if(account==null)throw new Exception();
                device=new RemoteDeviceConnector(context,account);connector=device;
                if(!device.connect() || !open || !nonce.equals(session))throw new Exception();
                JSONObject initial=new JSONObject();initial.put("session",session);
                device.startCustomActivity(new CustomActivityRequest(ACTION,initial.toString()),new CustomActivityListener(){
                    @Override public void onMessageFromActivity(MessageFromActivity message){
                        if(!open || !nonce.equals(session) || !ACTION.equals(message.name) || message.payload==null || message.payload.length()>1024)return;
                        try {
                            JSONObject body=new JSONObject(message.payload);if(!session.equals(body.optString("session")))return;
                            String type=body.optString("type");
                            if(type.equals("ready"))main.post(listener::ready);
                            else if(type.equals("scan"))main.post(listener::scan);
                            else if(type.equals("checkin")){String code=body.optString("code");if(code.matches("[0-9]{1,12}"))main.post(() -> listener.code(code));}
                        }catch(Exception ignored){}
                    }
                    @Override public void onCustomActivityResult(CustomActivityResponse result){
                        if(!nonce.equals(session))return;open=false;
                        main.post(listener::unavailable);
                    }
                });
            }catch(Exception ignored){
                if(nonce.equals(session)){open=false;main.post(listener::unavailable);}
                if(device!=null)device.disconnect();
            }
        });
    }
    void status(String type,String firstName,String number,String membershipStatus){
        if(!open)return;String session=nonce;
        io.execute(() -> {
            if(!open || !nonce.equals(session) || connector==null)return;
            try {JSONObject body=new JSONObject();body.put("session",session);body.put("type",type);body.put("first_name",firstName);body.put("member_number",number);body.put("membership_status",membershipStatus);connector.sendMessageToActivity(new MessageToActivity(ACTION,body.toString()));}catch(Exception ignored){}
        });
    }
    void close(){
        if(!open && connector==null)return;open=false;String session=nonce;nonce="";
        io.execute(() -> {RemoteDeviceConnector device=connector;connector=null;if(device==null)return;try{JSONObject body=new JSONObject();body.put("session",session);body.put("type","close");device.sendMessageToActivity(new MessageToActivity(ACTION,body.toString()));}catch(Exception ignored){}device.disconnect();});
    }
    void dispose(){close();io.shutdown();}
}
