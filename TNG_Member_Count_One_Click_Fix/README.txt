1. Extract this ZIP into your TNG CRM project root.
2. Right-click INSTALL_FIX.ps1 and choose Run with PowerShell,
   or run: powershell -ExecutionPolicy Bypass -File .\INSTALL_FIX.ps1
3. Commit and push the changes.

This fix:
- Counts only people with a PAID MEMBERSHIP product.
- Excludes Clover customers, merchandise buyers, event ticket buyers, and other sales.
- Keeps all old sales and customer records in the database.
- Removes old Clover Customer rows from the Members screen without deleting sales history.
