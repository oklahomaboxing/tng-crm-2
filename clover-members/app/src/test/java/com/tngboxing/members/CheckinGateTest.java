package com.tngboxing.members;
import org.junit.Test;
import static org.junit.Assert.*;
public class CheckinGateTest {
 @Test public void rapidFramesSubmitOnce(){CheckinGate gate=new CheckinGate();assertTrue(gate.accept("42",100));assertFalse(gate.accept("42",101));assertFalse(gate.accept("43",102));}
 @Test public void nextMemberAndRepeatCooldown(){CheckinGate gate=new CheckinGate();assertTrue(gate.accept("42",100));gate.release();assertFalse(gate.accept("42",200));assertTrue(gate.accept("43",300));gate.release();assertTrue(gate.accept("43",8300));}
 @Test public void blankCodesAreNotCheckins(){CheckinGate gate=new CheckinGate();assertFalse(gate.accept(" ",100));assertFalse(gate.accept(null,100));assertFalse(gate.isBusy());}
}
