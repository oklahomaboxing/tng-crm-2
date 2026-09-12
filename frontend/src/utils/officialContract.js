export function buildOfficialContractHtml(contract) {
  const money = (value) =>
    Number(value || 0).toLocaleString(
      "en-US",
      {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }
    );

  const eventDate = contract.event_date || "";

  const safe = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  return `
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<title>${safe(contract.boxer_name)} Contract</title>

<style>
  @page {
    size: letter;
    margin: 0.55in;
  }

  body {
    font-family: "Times New Roman", serif;
    color: #111;
    max-width: 8.5in;
    margin: 0 auto;
    font-size: 13px;
    line-height: 1.25;
  }

  h1 {
    text-align: center;
    font-size: 17px;
    margin: 0 0 14px;
  }

  h2 {
    text-align: center;
    font-size: 16px;
    margin: 0 0 18px;
  }

  .contract-date {
    margin-bottom: 24px;
  }

  .info-box {
    border: 1px solid #111;
    display: grid;
    grid-template-columns: 1fr 1fr;
    margin-bottom: 14px;
  }

  .info-col {
    padding: 8px;
    min-height: 120px;
  }

  .info-col + .info-col {
    border-left: 1px solid #111;
  }

  .label {
    font-weight: bold;
  }

  p {
    margin: 10px 0;
  }

  .initials {
    border: 1px solid #111;
    text-align: center;
    font-weight: bold;
    padding: 7px;
    margin: 8px 0 12px;
  }

  .signature-row {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 20px;
    margin-top: 28px;
  }

  .line {
    display: inline-block;
    min-width: 170px;
    border-bottom: 1px solid #111;
  }

  .print-bar {
    margin-bottom: 18px;
    text-align: right;
  }

  .print-bar button {
    padding: 8px 14px;
    font-weight: bold;
  }

  @media print {
    .print-bar {
      display: none;
    }
  }
</style>
</head>

<body>

<div class="print-bar">
  <button onclick="window.print()">
    Print / Save PDF
  </button>
</div>

<h1>OKLAHOMA STATE ATHLETIC COMMISSION</h1>
<h2>PROFESSIONAL BOXING CONTRACT REPORT</h2>

<div class="contract-date">
  Date the contract for this event is entered into:
  <b>${safe(contract.contract_date)}</b>
</div>

<div class="info-box">

  <div class="info-col">
    <div class="label">Boxer???s Information:</div>
    <br />

    Name:
    <b>${safe(contract.boxer_name)}</b>
    <br />

    Federal ID Number:
    <b>${safe(contract.boxer_federal_id)}</b>
    <br /><br />

    Address:
    ${safe(contract.boxer_address)}
    <br /><br />

    Telephone:
    ${safe(contract.boxer_phone)}
  </div>

  <div class="info-col">
    <div class="label">Promoter???s Information:</div>
    <br />

    Name:
    ${safe(contract.promoter_name)}
    <br />

    Address:
    ${safe(contract.promoter_address)}
    <br />

    Telephone:
    ${safe(contract.promoter_phone)}
  </div>

</div>

<p>
Boxer agrees to participate in a
<b>${safe(contract.rounds)}</b> round bout against
<b>${safe(contract.opponent_name)}</b>
at the maximum weight of
<b>${safe(contract.maximum_weight || "")}</b>
pounds.
The event will be held on
<b>${safe(eventDate)}</b>
at
<b>${safe(contract.venue)}</b>
which is located
<b>${safe(contract.venue_address)}</b>.
Boxers will be paid after the final bout of the evening.
</p>

<div style="
  border:1px solid #111;
  padding:10px;
  margin:14px 0;
">
  <div style="
    font-weight:bold;
    text-align:center;
    margin-bottom:8px;
  ">
    TRAVEL / HOTEL / PER DIEM
  </div>

  <div>
    <b>Travel Type:</b>
    ${safe(contract.travel_type || "N/A")}
  </div>

  <div>
    <b>Travel Paid By:</b>
    ${safe(contract.travel_paid_by || "N/A")}
  </div>

  <div>
    <b>Travel Allowance / Reimbursement:</b>
    $${money(contract.travel_expense)}
  </div>

  <div style="margin-top:6px;">
    <b>Hotel Provided:</b>
    ${safe(contract.hotel_provided || "No")}
  </div>

  <div>
    <b>Hotel:</b>
    ${safe(contract.hotel_name || "N/A")}
  </div>

  <div>
    <b>Hotel Nights:</b>
    ${safe(contract.hotel_nights || 0)}
  </div>

  <div style="margin-top:6px;">
    <b>Per Diem:</b>
    $${money(contract.per_diem_daily)}
    per day ?
    ${safe(contract.per_diem_days || 0)}
    days =
    <b>$${money(contract.per_diem_total)}</b>
  </div>
</div>

<p>
<b>Additional Terms:</b>
${safe(contract.additional_terms)}
</p>

<p>
Boxer hereby releases the Promoter, sponsors, and the State of Oklahoma,
or any agent, representative or employee thereof, from any and all claims
for liability, known or unknown at this time, arising from injuries,
mental and physical, which may be sustained by Boxer during participation
in this event.
</p>

<div class="initials">
  Boxer???s Initials: __________________
</div>

<p>
<b>Failure to appear:</b>
If a boxer signs a contract and fails to appear at an event,
Boxer will be suspended for a period of 90 days unless he provides
documentation of extenuating circumstances and it is approved by
the Commission.
</p>

<p>
Boxer agrees not to participate in another event within 30 days
of this event unless approved by the promoter/matchmaker.
<b>Boxer???s Initials:</b> __________________
</p>

<p>
In the event the opponent fails to appear or the event is canceled
due to no fault of the contestant named herein, promoter will pay
the contestant
<b>$${money(contract.cancellation_pay)}</b>.
</p>

<div class="signature-row">

  <div>
    Boxer???s Signature:
    <span class="line"></span>
  </div>

  <div>
    GROSS PURSE:
    <b>$${money(contract.gross_purse)}</b>
  </div>

  <div>
    Boxer???s Manager:
    <span class="line">
      ${safe(contract.boxer_manager)}
    </span>
  </div>

  <div>
    TRAVEL ALLOWANCE:
    <b>$${money(contract.travel_expense)}</b>
  </div>

  <div>
    Promoter/Matchmaker:
    <span class="line">
      ${safe(contract.promoter_matchmaker)}
    </span>
  </div>

  <div>
    Deductions:
    <b>$${money(contract.deductions)}</b>
  </div>

</div>

<p style="
  margin-top:30px;
  text-align:center;
  font-weight:bold;
">
  BOXER WILL BE PAID:
  $${money(contract.boxer_paid)}
</p>

</body>
</html>
`;
}


export function openOfficialContract(
  contract,
  autoPrint = false
) {
  const printWindow = window.open(
    "",
    "_blank",
    "width=900,height=1100"
  );

  if (!printWindow) {
    throw new Error(
      "Popup blocked. Please allow popups for TNGOS."
    );
  }

  const html =
    buildOfficialContractHtml(contract);

  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();

  if (autoPrint) {
    printWindow.onload = () => {
      setTimeout(() => {
        printWindow.focus();
        printWindow.print();
      }, 250);
    };
  }
}
