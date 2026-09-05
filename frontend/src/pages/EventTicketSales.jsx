import { useEffect, useState } from "react";
import axios from "axios";

const money = cents => `$${((cents || 0)/100).toFixed(2)}`;

export default function EventTicketSales({ eventId }) {
  const [data, setData] = useState({ sellers: [] });
  const token = localStorage.getItem("token");

  const load = async () => {
    const { data } = await axios.get(`/api/ticketing/events/${eventId}/sellers/live`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    setData(data);
  };

  useEffect(() => {
    load();
    const timer = setInterval(load, 5000);
    return () => clearInterval(timer);
  }, [eventId]);

  return (
    <div className="p-4">
      <h1>Live Ticket Sales</h1>
      <div style={{overflowX:"auto"}}>
        <table width="100%" cellPadding="10">
          <thead>
            <tr>
              <th align="left">Seller</th>
              <th>Type</th>
              <th>Tickets</th>
              <th>Gross</th>
              <th>Commission</th>
              <th>Seller Code</th>
            </tr>
          </thead>
          <tbody>
            {data.sellers.map(s => (
              <tr key={s.seller_id}>
                <td>{s.display_name}</td>
                <td align="center">{s.seller_type}</td>
                <td align="center">{s.tickets_sold}</td>
                <td align="center">{money(s.gross_sales_cents)}</td>
                <td align="center"><strong>{money(s.commission_cents)}</strong></td>
                <td align="center">{s.public_code}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
