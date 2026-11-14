import test from 'node:test';
import assert from 'node:assert/strict';
import {purchaseAttempt} from '../src/services/ticketPurchaseAttempt.js';
test('a repeated purchase retries the same request, including after reload; a changed cart is new',()=>{
 const values=new Map(),storage={getItem:k=>values.get(k),setItem:(k,v)=>values.set(k,v)};let n=0;const key=()=>String(++n).padStart(32,'0');
 const a=purchaseAttempt({items:[1]},null,storage,key);
 assert.equal(purchaseAttempt({items:[1]},a,storage,key).key,a.key);
 assert.equal(purchaseAttempt({items:[1]},null,storage,key).key,a.key);
 assert.notEqual(purchaseAttempt({items:[2]},a,storage,key).key,a.key);
 const denied={getItem(){throw Error()},setItem(){throw Error()}};
 assert.equal(purchaseAttempt({items:[1]},a,denied,key).key,a.key);
});
