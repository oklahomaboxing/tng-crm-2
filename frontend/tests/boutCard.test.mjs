import test from 'node:test';
import assert from 'node:assert/strict';
import {isCurrentBout} from '../src/utils/boutCard.js';
test('current card excludes cancelled, replaced and withdrawn bouts consistently',()=>{
 for(const status of ['cancelled','canceled','void','withdrawn','declined','rejected','removed','deleted',' VOID '])assert.equal(isCurrentBout({status}),false,status);
 for(const status of ['draft','confirmed','scheduled','completed','finished','',null])assert.equal(isCurrentBout({status}),true,String(status));
});
