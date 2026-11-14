import test from 'node:test';
import assert from 'node:assert/strict';
import {readDisplayMode,saveDisplayMode} from '../src/services/displayMode.js';
test('mode preference survives reload and safely defaults when storage is unavailable',()=>{
 const values=new Map(),storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};
 assert.equal(readDisplayMode(storage),'standard');
 saveDisplayMode('command',storage);assert.equal(readDisplayMode(storage),'command');
 saveDisplayMode('invalid',storage);assert.equal(readDisplayMode(storage),'standard');
 const denied={getItem(){throw Error()},setItem(){throw Error()}};
 assert.equal(readDisplayMode(denied),'standard');assert.equal(saveDisplayMode('command',denied),'command');
});
