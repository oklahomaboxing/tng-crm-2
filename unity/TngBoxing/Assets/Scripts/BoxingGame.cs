using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
namespace TNG.Boxing {
public sealed class BoxingGame : MonoBehaviour {
 BoxerAvatar player,opponent;Camera cameraRig;Canvas canvas;Text hud,cue;TouchPad pad;HoldButton guard,body;Button start;float clock=120,nextAttack,enemyImpact,playerImpact,recover,enemyRecover;int pendingPunch=-1,enemyPunch,score,hits,attempts,mode;bool running,paused;Vector3 cameraVelocity;GameObject bag;AudioSource audioOut;AudioClip bell,impact;
 readonly float[] cost={7,10,11,12,12,13};readonly string[] names={"JAB","CROSS","LEAD HOOK","REAR HOOK","LEAD UPPER","REAR UPPER"};readonly string[] modes={"SPARRING","HEAVY BAG","DEFENSE & COUNTERS","COMBINATION LAB"};readonly int[] combo={0,4,1,2,1};int comboIndex;
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)] static void Boot(){if(!FindFirstObjectByType<BoxingGame>())new GameObject("TNG Boxing").AddComponent<BoxingGame>();}
 void Start(){Screen.sleepTimeout=SleepTimeout.NeverSleep;Application.targetFrameRate=60;QualitySettings.vSyncCount=0;QualitySettings.shadows=SystemInfo.deviceType==DeviceType.Handheld?ShadowQuality.Disable:ShadowQuality.All;BuildArena();BuildUI();audioOut=gameObject.AddComponent<AudioSource>();bell=Tone(660,.35f);impact=Tone(95,.08f);ResetRound();}
 AudioClip Tone(float hz,float seconds){int count=(int)(22050*seconds);var data=new float[count];for(int i=0;i<count;i++)data[i]=Mathf.Sin(i*hz*2*Mathf.PI/22050)*Mathf.Exp(-i/(22050*seconds)*5)*.12f;var clip=AudioClip.Create("TNG cue",count,1,22050,false);clip.SetData(data,0);return clip;}
 void BuildArena(){
  RenderSettings.ambientLight=new Color(.25f,.28f,.36f);RenderSettings.fog=true;RenderSettings.fogColor=new Color(.018f,.023f,.035f);RenderSettings.fogDensity=.025f;
  cameraRig=new GameObject("Broadcast camera").AddComponent<Camera>();cameraRig.fieldOfView=43;cameraRig.backgroundColor=RenderSettings.fogColor;cameraRig.gameObject.AddComponent<AudioListener>();
  var key=new GameObject("Arena key").AddComponent<Light>();key.type=LightType.Directional;key.intensity=1.4f;key.transform.rotation=Quaternion.Euler(48,-25,0);key.shadows=LightShadows.Soft;
  var fill=new GameObject("Blue rim").AddComponent<Light>();fill.type=LightType.Point;fill.color=new Color(.2f,.5f,1);fill.intensity=8;fill.range=12;fill.transform.position=new Vector3(-3,3,-2);
  var mat=BoxerAvatar.Material(new Color(.065f,.085f,.12f));BoxerAvatar.Shape(PrimitiveType.Cube,transform,new Vector3(0,-.2f,0),new Vector3(7,.4f,7),mat);BoxerAvatar.Shape(PrimitiveType.Plane,transform,new Vector3(0,-.41f,0),Vector3.one*5,BoxerAvatar.Material(Color.black));
  var white=BoxerAvatar.Material(new Color(.85f,.88f,.94f));var red=BoxerAvatar.Material(new Color(.75f,.025f,.1f));
  for(int x=-1;x<=1;x+=2)for(int z=-1;z<=1;z+=2){BoxerAvatar.Shape(PrimitiveType.Cylinder,transform,new Vector3(x*3.1f,.65f,z*3.1f),new Vector3(.13f,.85f,.13f),x==z?red:white);}
  for(int h=0;h<4;h++)for(int side=0;side<4;side++){var a=side<2?new Vector3(-3.1f,.55f+h*.27f,side==0?-3.1f:3.1f):new Vector3(side==2?-3.1f:3.1f,.55f+h*.27f,-3.1f);var b=side<2?a+Vector3.right*6.2f:a+Vector3.forward*6.2f;var rope=BoxerAvatar.Shape(PrimitiveType.Cylinder,transform,(a+b)/2,new Vector3(.035f,3.1f,.035f),h%2==0?red:white);rope.transform.up=(b-a).normalized;}
  for(int i=0;i<36;i++){float angle=i*Mathf.PI*2/36;var t=new Vector3(Mathf.Cos(angle)*6,.6f,Mathf.Sin(angle)*6);BoxerAvatar.Shape(PrimitiveType.Capsule,transform,t,new Vector3(.35f,.6f,.35f),mat);}
  player=new GameObject("Red corner").AddComponent<BoxerAvatar>();player.Initialize(new Color(.8f,.025f,.1f),new Color(.65f,.4f,.28f));opponent=new GameObject("Blue corner").AddComponent<BoxerAvatar>();opponent.Initialize(new Color(.06f,.28f,.8f),new Color(.38f,.23f,.16f));
  bag=BoxerAvatar.Shape(PrimitiveType.Capsule,transform,new Vector3(0,1,1),new Vector3(.5f,.65f,.5f),BoxerAvatar.Material(new Color(.1f,.015f,.025f),.5f));
 }
 Text Label(Transform parent,string value,int size,TextAnchor align){var g=new GameObject("Label",typeof(RectTransform));g.transform.SetParent(parent,false);var t=g.AddComponent<Text>();t.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");t.text=value;t.fontSize=size;t.color=Color.white;t.alignment=align;t.raycastTarget=false;var r=g.GetComponent<RectTransform>();r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=Vector2.zero;r.offsetMax=Vector2.zero;return t;}
 RectTransform Panel(string name,Vector2 min,Vector2 max,Color color){var g=new GameObject(name,typeof(RectTransform));g.transform.SetParent(canvas.transform,false);var r=g.GetComponent<RectTransform>();r.anchorMin=min;r.anchorMax=max;r.offsetMin=Vector2.zero;r.offsetMax=Vector2.zero;g.AddComponent<Image>().color=color;return r;}
 Button Button(string label,Vector2 min,Vector2 max,UnityEngine.Events.UnityAction action){var r=Panel(label,min,max,new Color(.6f,.025f,.1f,.88f));var b=r.gameObject.AddComponent<Button>();b.onClick.AddListener(action);Label(r,label,23,TextAnchor.MiddleCenter);return b;}
 void BuildUI(){
  canvas=new GameObject("Touch HUD").AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;var scaler=canvas.gameObject.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(1000,700);scaler.matchWidthOrHeight=.5f;canvas.gameObject.AddComponent<GraphicRaycaster>();if(!FindFirstObjectByType<EventSystem>())new GameObject("Input",typeof(EventSystem),typeof(StandaloneInputModule));
  hud=Label(Panel("Score",new Vector2(.02f,.84f),new Vector2(.72f,.98f),new Color(0,0,0,.65f)),"",23,TextAnchor.MiddleLeft);
  cue=Label(Panel("Coach",new Vector2(.2f,.7f),new Vector2(.8f,.78f),new Color(0,0,0,.55f)),"",23,TextAnchor.MiddleCenter);
  Button("PAUSE",new Vector2(.75f,.88f),new Vector2(.97f,.98f),TogglePause);
  start=Button("START ROUND",new Vector2(.28f,.5f),new Vector2(.72f,.62f),()=>{if(paused){TogglePause();return;}ResetRound();running=true;start.gameObject.SetActive(false);audioOut.PlayOneShot(bell);});
  Button("MODE",new Vector2(.02f,.73f),new Vector2(.18f,.81f),()=>{if(running)return;mode=(mode+1)%modes.Length;ResetRound();});
  var joy=Panel("Movement pad",new Vector2(.025f,.07f),new Vector2(.26f,.36f),new Color(.12f,.2f,.3f,.55f));pad=joy.gameObject.AddComponent<TouchPad>();var thumb=new GameObject("Thumb",typeof(RectTransform),typeof(Image));thumb.transform.SetParent(joy,false);var tr=thumb.GetComponent<RectTransform>();tr.sizeDelta=new Vector2(60,60);thumb.GetComponent<Image>().color=new Color(.7f,.8f,1,.65f);thumb.GetComponent<Image>().raycastTarget=false;pad.Thumb=tr;
  for(int i=0;i<6;i++){int p=i;int col=i%3,row=i/3;Button((i+1)+"\n"+names[i],new Vector2(.51f+col*.157f,.23f-row*.11f),new Vector2(.66f+col*.157f,.33f-row*.11f),()=>Punch(p));}
  guard=Button("HOLD GUARD",new Vector2(.02f,.01f),new Vector2(.25f,.065f),()=>{}).gameObject.AddComponent<HoldButton>();body=Button("BODY",new Vector2(.51f,.01f),new Vector2(.66f,.105f),()=>{}).gameObject.AddComponent<HoldButton>();Button("SLIP",new Vector2(.67f,.01f),new Vector2(.82f,.105f),()=>{if(running&&!paused)player.SlipUntil=Time.time+.4f;});Button("ROLL",new Vector2(.83f,.01f),new Vector2(.98f,.105f),()=>{if(running&&!paused)player.RollUntil=Time.time+.5f;});
 }
 void ResetRound(){Time.timeScale=1;paused=false;running=false;clock=120;score=hits=attempts=comboIndex=0;pendingPunch=-1;enemyImpact=playerImpact=0;recover=enemyRecover=0;player.Health=opponent.Health=player.Stamina=opponent.Stamina=100;player.transform.position=new Vector3(0,0,-.8f);opponent.transform.position=new Vector3(0,0,.8f);nextAttack=Time.time+2;opponent.gameObject.SetActive(mode!=1);bag.SetActive(mode==1);cue.text=modes[mode]+" · Set your feet";if(start){start.gameObject.SetActive(true);start.GetComponentInChildren<Text>().text="START ROUND";}Release();}
 void Release(){if(pad)pad.ResetPad();if(guard)guard.Release();if(body)body.Release();if(player){player.Guard=false;player.BodyGuard=false;}}
 void TogglePause(){if(!running)return;paused=!paused;Time.timeScale=paused?0:1;Release();start.gameObject.SetActive(paused);start.GetComponentInChildren<Text>().text="RESUME";}
 void OnApplicationFocus(bool focused){if(!focused&&running&&!paused)TogglePause();}
 void OnApplicationPause(bool hidden){if(hidden&&running&&!paused)TogglePause();}
 void OnDisable(){Time.timeScale=1;Screen.sleepTimeout=SleepTimeout.SystemSetting;}
 void Punch(int p){if(!running||paused||Time.time<recover||player.Stamina<cost[p])return;player.Stamina-=cost[p];player.Punch=p;player.PunchStart=Time.time;pendingPunch=p;playerImpact=Time.time+.23f;recover=Time.time+(p<2?.42f:.54f);attempts++;}
 void Update(){
  if(!player)return;var midpoint=(player.transform.position+opponent.transform.position)*.5f;var desired=midpoint+new Vector3(-2.7f,1.85f,-3.7f)*(Screen.height>Screen.width?1.38f:1);cameraRig.transform.position=Vector3.SmoothDamp(cameraRig.transform.position,desired,ref cameraVelocity,.2f);cameraRig.transform.LookAt(midpoint+Vector3.up*1.1f);
  if(Input.GetKeyDown(KeyCode.P)||Input.GetKeyDown(KeyCode.Escape))TogglePause();
  hud.text=$"TNG BOXING  /  {modes[mode]}\n{Mathf.CeilToInt(clock)/60}:{Mathf.CeilToInt(clock)%60:00}   SCORE {score}   HITS {hits}/{attempts}\nSTAMINA {player.Stamina:0}%   CONDITION {player.Health:0}%";
  if(!running||paused)return;clock-=Time.deltaTime;player.Stamina=Mathf.Min(100,player.Stamina+Time.deltaTime*11);
  Vector2 move=pad.Value;if(move.magnitude<.2f)move=new Vector2((Input.GetKey(KeyCode.D)?1:0)-(Input.GetKey(KeyCode.A)?1:0),(Input.GetKey(KeyCode.W)?1:0)-(Input.GetKey(KeyCode.S)?1:0));var towards=(opponent.transform.position-player.transform.position).normalized;var side=Vector3.Cross(Vector3.up,towards);var proposed=player.transform.position+(towards*move.y+side*move.x)*Time.deltaTime*1.25f;proposed.x=Mathf.Clamp(proposed.x,-2.6f,2.6f);proposed.z=Mathf.Clamp(proposed.z,-2.6f,2.6f);if(Vector3.Distance(proposed,opponent.transform.position)>.6f)player.transform.position=proposed;
  player.transform.LookAt(opponent.transform.position);opponent.transform.LookAt(player.transform.position);player.Guard=guard.Held||Input.GetKey(KeyCode.Space);player.BodyGuard=body.Held||Input.GetKey(KeyCode.C);
  for(int i=0;i<6;i++)if(Input.GetKeyDown((KeyCode)((int)KeyCode.Alpha1+i)))Punch(i);
  if(Input.GetKeyDown(KeyCode.Q))player.SlipUntil=Time.time+.4f;if(Input.GetKeyDown(KeyCode.E))player.RollUntil=Time.time+.5f;
  float distance=Vector3.Distance(player.transform.position,opponent.transform.position);
  if(pendingPunch>=0&&Time.time>=playerImpact){int p=pendingPunch;pendingPunch=-1;bool range=distance>=(p<2?.65f:.6f)&&distance<=(p<2?1.8f:1.25f);bool blocked=mode==0&&opponent.Guard&&p<4;bool sequence=mode!=3||p==combo[comboIndex];if(range&&!blocked&&sequence){hits++;score+=mode==3?150:100;opponent.Health=Mathf.Max(0,opponent.Health-4);opponent.HitUntil=Time.time+.15f;if(mode==3)comboIndex=(comboIndex+1)%combo.Length;audioOut.PlayOneShot(impact);cue.text=mode==3?"NEXT: "+names[combo[comboIndex]]:"CLEAN CONTACT";}else {cue.text=!range?"ADJUST YOUR RANGE":blocked?"GUARD CAUGHT IT":"RESET THE COMBINATION";if(mode==3)comboIndex=0;}}
  if(mode==0||mode==2){opponent.Guard=Time.time%3>1.8f&&Time.time>enemyRecover;if(Time.time>=nextAttack){enemyPunch=Random.Range(0,6);cue.text="INCOMING: "+names[enemyPunch];enemyImpact=Time.time+.8f;nextAttack=Time.time+Random.Range(2.1f,3.1f);}
   if(enemyImpact>0&&Time.time>=enemyImpact){enemyImpact=0;opponent.Punch=enemyPunch;opponent.PunchStart=Time.time;enemyRecover=Time.time+.7f;bool defended=enemyPunch>=4?player.BodyGuard:enemyPunch<2?(player.Guard||Time.time<player.SlipUntil):(player.Guard||Time.time<player.RollUntil);if(distance<1.9f){if(defended){score+=50;cue.text="DEFENDED · COUNTER NOW";}else{player.Health=Mathf.Max(0,player.Health-7);player.HitUntil=Time.time+.2f;cue.text="PROTECT YOURSELF";}}}
   if(mode==0&&distance>1.55f)opponent.transform.position=Vector3.MoveTowards(opponent.transform.position,player.transform.position,Time.deltaTime*.25f);
  }
  if(clock<=0||player.Health<=0||opponent.Health<=0){clock=Mathf.Max(0,clock);running=false;Release();cue.text=$"ROUND COMPLETE · {score} POINTS · {(attempts>0?100*hits/attempts:0)}% ACCURACY";start.gameObject.SetActive(true);start.GetComponentInChildren<Text>().text="PLAY AGAIN";audioOut.PlayOneShot(bell);}
 }
}
}
