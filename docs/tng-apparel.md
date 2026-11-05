# TNG Apparel

Admin: `/#/tng-apparel`. Public store: `/apparel`. A collection section and shop shortcut are also available in the existing member portal. Only published products appear to customers; buying apparel never grants gym membership.

## First shirt / publishing

The initial shirt is TNG Earned Not Given, black with the white TNG design. Requested prices are $20 presale and $25 event day. The first record is a draft until the owner supplies sizes, the event date, original artwork and pickup instructions. The image visible in the chat is not an accessible workspace file; use **Upload shirt image** in TNG Apparel to upload that original JPG/PNG/WebP without recreating the artwork.

Save the draft and sizes, upload the original image, create/match Clover POS items, then publish. Sizes remain stable after creation; additional size runs use a new product. Published URLs remain permanent. Existing paid/pending purchases keep their original title/size/price snapshots. Clover-linked titles and prices cannot be silently changed; create a new version instead.

This release supports preorder/pickup fulfillment, not shipping/address collection or synchronized physical inventory. Confirm supply and pickup arrangements before publishing. Physical stock is not automatically decremented across the two Clover price SKUs. Unpublish when the drop should stop accepting orders. Confirm merchant tax configuration before opening sales; checkout confirmation requires the Clover payment amount to match the saved total exactly. Refund/exchange policy is not invented by this feature.

## Prices and Clover

The web price switches at midnight America/Chicago on the configured event date. A stale browser price requires the customer to refresh and review the new amount before a new payment page can be created. A previously created $20 checkout remains $20 after the switch. Clover POS receives separately labeled PRESALE and EVENT items for every size; staff select the correct price at the register. Those POS items are catalog entries, not completed sales.

Existing Clover credentials are reused. Inventory read/write access is needed for POS synchronization. Deterministic SKUs are matched before creation; ambiguous/duplicate or differently priced existing SKUs require review. Partial creation is recovered by matching the existing SKU on retry. A product row lock serializes synchronization requests. If inventory access is unavailable, keep the product in draft until it is fixed.

Public checkout reuses the existing merchandise checkout ledger and signed Clover webhook. It has server-side prices, bounded quantities, short-window creation limits and persistent request-key deduplication. An uncertain checkout creation is not automatically replayed. Approved callbacks for apparel also verify the amount and successful payment result with the merchant payment API. Concurrent callbacks lock the checkout and record one merchandise sale. General Clover sale import skips the internal hosted-apparel variant products so it cannot race the callback into a second sale; the separately named POS phase items still import normally. The unit price is taken from the saved checkout snapshot, not the current product price. Legacy staff-created merchandise checkouts now snapshot their prices too.

A return URL never confirms payment. The opaque order-status link checks the saved server state without exposing buyer contact details. Failed verification stays unfulfilled for support review. Admins can mark paid orders ready or collected; unpaid orders cannot be fulfilled. Clover sale-import/refund tooling remains separate; verify any disputed or refunded order before handing over goods.

## Sharing / other online shops

Customers can share the server-rendered product page, which includes the original image in Open Graph metadata, or use the direct branded storefront product link. Paste links into social posts, stories/bios and websites. A public social-preview page links to the size/checkout screen. No social account is automatically posted to.

The admin catalog CSV exports published variants, current prices, descriptions, image URLs and fulfillment notes. It is a general export, not a claim of Meta/TikTok/Google/Shopify catalog approval or an automatic inventory/order integration. Connect and configure each destination separately before importing or publishing there.

No real customer was charged and no social post was sent during automated tests. Payment and inventory-write tests use mocked providers and isolated databases.
