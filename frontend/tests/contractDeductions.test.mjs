import test from 'node:test';
import assert from 'node:assert/strict';
import {buildOfficialContractHtml} from '../src/utils/officialContract.js';
test('final print includes saved itemized deductions and computed payout',()=>{
 const html=buildOfficialContractHtml({gross_purse:1000,travel_expense:200,deductions:0,boxer_paid:1000,deduction_summary:{items:[{label:'Blood work',amount_cents:12000},{label:'Hotel',amount_cents:8500}],base_deductions_cents:0,total_deductions_cents:20500,net_payout_cents:99500,signed_terms_locked:true}});
 for(const text of ['Blood work','120','Hotel','85','205','995','PAYOUT REVIEW COPY'])assert.ok(html.includes(text),text);
 assert.ok(html.includes('PROJECTED NET PAYOUT'));
});
test('deduction descriptions are escaped and ordinary drafts still render',()=>{
 const html=buildOfficialContractHtml({deduction_summary:{items:[{label:'<script>alert(1)</script>',amount_cents:100}],base_deductions_cents:0,total_deductions_cents:100,net_payout_cents:99900,signed_terms_locked:false}});
 assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<script>alert(1)</script>'));assert.ok(!html.includes('PAYOUT REVIEW COPY'));
 assert.ok(buildOfficialContractHtml({deductions:10,boxer_paid:990}).includes('990'));
});
