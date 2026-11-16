# Returning paper tickets

In Tickets → Paper ticket batches → Manage batch:

1. Choose **Select returnable only (N)** to select unscanned, order-free allocated/released tickets. Unscanned does not prove unsold: staff must verify that no customer purchased these tickets.
2. Choose **Return selected unsold**.
3. Review the selected quantity and face value, then confirm the return inside TNGOS. The codes become permanently invalid. Returning unsold stock records no cash sale, commission or refund.

**Select all unrecorded** also includes admission-used tickets whose cash sale has not been reconciled. These can be selected for cash reconciliation but cannot be returned as unsold. A mixed return selection is rejected atomically, with an explanation beside the controls. Use the returnable-only selection to remove admitted tickets from the selection.

A server rejection appears inside the confirmation dialog. Successful returns clear selection and update the local status immediately. If refreshing the list fails afterward, the UI distinguishes a saved change from a failed refresh. Repeating the same return preserves the result without creating a sale. Order-linked and unknown-status tickets require review and cannot be returned through this flow.

The in-app confirmation replaces the browser confirmation for return and cash-reconciliation actions. Cash reconciliation still requires explicit confirmation of the full face value; no card is charged and fighter remittance is separate.
