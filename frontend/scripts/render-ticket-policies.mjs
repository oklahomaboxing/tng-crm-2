import { createServer } from 'vite';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { writeFile } from 'node:fs/promises';
const server = await createServer({ server: { middlewareMode: true, watch: null }, appType: 'custom' });
try {
  const { default: TicketPolicies } = await server.ssrLoadModule('/src/pages/TicketPolicies.jsx');
  for (const [name, privacy] of [['ticket-privacy', true], ['ticket-terms', false]]) {
    const content = renderToStaticMarkup(React.createElement(TicketPolicies, { privacy }));
    const html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${privacy ? 'Ticket Privacy Notice' : 'Ticket Terms'} | TNG Boxing</title><style>body{margin:0;background:#f5f6f8;font:16px/1.7 system-ui,sans-serif}a{color:#aa1219}h1,h2{line-height:1.2}main{box-sizing:border-box}</style></head><body>${content}</body></html>`;
    await writeFile(`public/${name}.html`, html);
  }
} finally { await server.close(); }
