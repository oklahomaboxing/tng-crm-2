param(
    [ValidateSet('Diagnose', 'Recover', 'Reconcile')]
    [string]$Mode = 'Diagnose',
    [int]$EventId = 2,
    [int]$OrderId,
    [string]$CloverOrderId,
    [string]$ConfirmCheckoutId,
    [string]$Backend = 'https://sea-lion-app-2-gxyfr.ondigitalocean.app'
)
$ErrorActionPreference = 'Stop'
$Backend = $Backend.TrimEnd('/')
if (-not $Backend.StartsWith('https://')) { throw 'Use an HTTPS backend.' }
$health = Invoke-RestMethod "$Backend/api/health"
if ($health.release -ne 'ticket-production-repair-1') {
    throw "Repair is not deployed. Current release: $($health.release)"
}
$email = Read-Host 'TNG admin/staff email'
$securePassword = Read-Host 'TNG password' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    $body = @{ email = $email; password = $password } | ConvertTo-Json
    $login = Invoke-RestMethod "$Backend/api/login" -Method Post -ContentType 'application/json' -Body $body
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    Remove-Variable password, body -ErrorAction SilentlyContinue
}
$headers = @{ Authorization = "Bearer $($login.token)" }
try {
    if ($Mode -eq 'Diagnose') {
        Invoke-RestMethod "$Backend/api/ticketing/events/$EventId/orders/incident" -Headers $headers |
            ConvertTo-Json -Depth 8
    } elseif ($Mode -eq 'Recover') {
        if ($OrderId -lt 1) { throw 'Specify -OrderId.' }
        Invoke-RestMethod "$Backend/api/ticketing/orders/$OrderId/recover" -Method Post -Headers $headers |
            ConvertTo-Json -Depth 8
    } else {
        if ($OrderId -lt 1 -or -not $CloverOrderId -or -not $ConfirmCheckoutId) {
            throw 'Specify -OrderId, -CloverOrderId and -ConfirmCheckoutId after matching the customer purchase in Clover.'
        }
        $body = @{ clover_order_id = $CloverOrderId; confirm_checkout_id = $ConfirmCheckoutId } | ConvertTo-Json
        Invoke-RestMethod "$Backend/api/ticketing/orders/$OrderId/reconcile-clover" -Method Post -Headers $headers `
            -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 8
    }
} finally {
    Remove-Variable login, headers, securePassword -ErrorAction SilentlyContinue
}
