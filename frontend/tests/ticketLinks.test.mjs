import test from 'node:test';
import assert from 'node:assert/strict';
import {ticketSellerFromLocation,publicTicketUrl,legacyPhoneTicketEvent} from '../src/services/ticketLinks.js';
test('fighter ticket paths and legacy seller links open a public seller portal',()=>{
 for(const location of [{pathname:'/tickets/F2-1234ABCD',search:''},{pathname:'/',search:'?seller=F2-1234ABCD'},{pathname:'/',search:'?seller_code=F2-1234ABCD'},{pathname:'/',search:'?fighter=F2-1234ABCD'},{pathname:'/',search:'?join=F2-1234ABCD'}])assert.equal(ticketSellerFromLocation(location),'F2-1234ABCD');
 assert.equal(publicTicketUrl(2,'F2-1234ABCD'),'https://tngos.tngboxinggym.com/tickets/F2-1234ABCD');
});
test('membership referrals and private/admin links keep their existing routes',()=>{
 for(const location of [{pathname:'/',search:'?join=rocky-hernandez'},{pathname:'/',search:'?fighter=50'},{pathname:'/fighter/activate',search:'?token=private'},{pathname:'/events/2/media',search:'?ref=Rocky'},{pathname:'/events/2/tickets',search:'?seller=F2-1234ABCD'},{pathname:'/',search:''}])assert.equal(ticketSellerFromLocation(location),null);
 assert.equal(publicTicketUrl(2,null),'https://tngos.tngboxinggym.com/events/2/tickets');
});

test('old phone texts open the company portal while paid-return and fighter links are preserved',()=>{
 assert.equal(legacyPhoneTicketEvent({pathname:'/events/2/tickets',search:'?source=phone'}),'2');
 assert.equal(legacyPhoneTicketEvent({pathname:'/events/2/tickets',search:'?source=phone&seller=F2-1234ABCD'}),null);
 assert.equal(legacyPhoneTicketEvent({pathname:'/events/2/tickets',search:'?source=phone&ticket_payment=success&order=74&access_token=private'}),null);
});
