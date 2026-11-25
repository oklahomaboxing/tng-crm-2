using UnityEngine;
using UnityEngine.EventSystems;
namespace TNG.Boxing {
public sealed class TouchPad : MonoBehaviour,IPointerDownHandler,IDragHandler,IPointerUpHandler {
 public Vector2 Value; public RectTransform Thumb; int pointer=int.MinValue;
 public void OnPointerDown(PointerEventData e){if(pointer!=int.MinValue)return;pointer=e.pointerId;OnDrag(e);}
 public void OnDrag(PointerEventData e){if(e.pointerId!=pointer)return;var rect=(RectTransform)transform;Vector2 p;RectTransformUtility.ScreenPointToLocalPointInRectangle(rect,e.position,e.pressEventCamera,out p);Value=Vector2.ClampMagnitude(p/(rect.rect.width*.5f),1);Thumb.anchoredPosition=Value*rect.rect.width*.28f;}
 public void OnPointerUp(PointerEventData e){if(e.pointerId==pointer)ResetPad();}
 public void ResetPad(){pointer=int.MinValue;Value=Vector2.zero;if(Thumb)Thumb.anchoredPosition=Vector2.zero;}
 void OnDisable(){ResetPad();}
}
public sealed class HoldButton : MonoBehaviour,IPointerDownHandler,IPointerUpHandler {
 public bool Held;int pointer=int.MinValue;
 public void OnPointerDown(PointerEventData e){if(pointer==int.MinValue){pointer=e.pointerId;Held=true;}}
 public void OnPointerUp(PointerEventData e){if(e.pointerId==pointer)Release();}
 public void Release(){Held=false;pointer=int.MinValue;}
 void OnDisable(){Release();}
}
}
